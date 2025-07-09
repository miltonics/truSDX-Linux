#!/usr/bin/env python3
"""
Audio I/O module for truSDX-AI driver.
Handles audio device management, streaming, and audio processing.
"""

import pyaudio
import array
import time
from typing import Optional, List
from logging_cfg import log

# Audio-related constants and configurations
AUDIO_TX_RATE_TRUSDX = 4800
AUDIO_TX_RATE = 11520  # 11521
AUDIO_RX_RATE = 7812

# Global audio buffer for received audio
buf = []  # buffer for received audio
urs = [0]  # underrun counter


class AudioManager:
    """Manages audio devices and streams for truSDX communication."""
    
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.in_stream = None
        self.out_stream = None
    
    def show_audio_devices(self):
        """Display all available audio devices."""
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            print(f"Device {i}: {device_info['name']} - {device_info['hostApi']}")
        
        for i in range(self.p.get_host_api_count()):
            host_info = self.p.get_host_api_info_by_index(i)
            print(f"Host API {i}: {host_info['name']}")
    
    def find_audio_device(self, name: str, occurrence: int = 0) -> int:
        """Find audio device by name.
        
        Args:
            name: Device name to search for
            occurrence: Which occurrence to return if multiple matches
            
        Returns:
            Device index or -1 if not found
        """
        try:
            result = []
            for i in range(self.p.get_device_count()):
                device_info = self.p.get_device_info_by_index(i)
                device_name = device_info['name']
                if name.lower() in device_name.lower():
                    result.append(i)
                    log(f"Found audio device: {device_name} (index {i})")
            
            if len(result) > occurrence:
                log(f"Using audio device index {result[occurrence]} for '{name}'")
                return result[occurrence]
            else:
                log(f"Audio device '{name}' not found, using default (-1)")
                return -1
        except Exception as e:
            log(f"Error finding audio device '{name}': {e}")
            return -1
    
    def create_input_stream(self, 
                           device_index: int = -1, 
                           block_size: int = 512) -> pyaudio.Stream:
        """Create audio input stream for transmission.
        
        Args:
            device_index: Audio device index (-1 for default)
            block_size: Buffer size in frames
            
        Returns:
            PyAudio stream object
        """
        try:
            stream = self.p.open(
                frames_per_buffer=block_size,
                format=pyaudio.paInt16,
                channels=1,
                rate=AUDIO_TX_RATE,
                input=True,
                input_device_index=device_index if device_index != -1 else None
            )
            log(f"Created input stream with device {device_index}, block size {block_size}")
            return stream
        except Exception as e:
            log(f"Error creating input stream: {e}")
            raise
    
    def create_output_stream(self, device_index: int = -1) -> pyaudio.Stream:
        """Create audio output stream for reception.
        
        Args:
            device_index: Audio device index (-1 for default)
            
        Returns:
            PyAudio stream object
        """
        try:
            stream = self.p.open(
                frames_per_buffer=0,
                format=pyaudio.paUInt8,
                channels=1,
                rate=AUDIO_RX_RATE,
                output=True,
                output_device_index=device_index if device_index != -1 else None
            )
            log(f"Created output stream with device {device_index}")
            return stream
        except Exception as e:
            log(f"Error creating output stream: {e}")
            raise
    
    def process_tx_audio(self, samples: bytes) -> bytearray:
        """Process audio samples for transmission.
        
        Args:
            samples: Raw audio samples
            
        Returns:
            Processed 8-bit audio samples
        """
        arr = array.array('h', samples)
        samples8 = bytearray([128 + x//256 for x in arr])
        # Filter ; from stream to avoid CAT command conflicts
        samples8 = samples8.replace(b'\x3b', b'\x3a')
        return samples8
    
    def handle_vox(self, samples8: bytearray) -> bool:
        """Handle VOX (Voice Operated Switch) detection.
        
        Args:
            samples8: 8-bit audio samples
            
        Returns:
            True if loud signal detected, False otherwise
        """
        # Check for very loud signal
        if (128 - min(samples8)) == 64 and (max(samples8) - 127) == 64:
            return True
        return False
    
    def play_receive_audio(self, pastream, status: List[bool]):
        """Play received audio from buffer.
        
        Args:
            pastream: PyAudio output stream
            status: Global status array
        """
        try:
            log("play_receive_audio")
            while status[2]:  # while running
                if len(buf) < 2:
                    urs[0] += 1  # underrun counter
                    while len(buf) < 10:
                        time.sleep(0.001)
                if not status[0]:  # if not in TX mode
                    pastream.write(buf[0])
                buf.remove(buf[0])
        except Exception as e:
            log(f"Error in play_receive_audio: {e}")
            status[2] = False
    
    def check_audio_setup(self) -> bool:
        """Check if TRUSDX audio device is properly configured.
        
        Returns:
            True if audio setup is correct, False otherwise
        """
        try:
            import os
            # Check if TRUSDX sink exists
            result = os.popen('pactl list sinks | grep -c "Name: TRUSDX"').read().strip()
            if result == '0':
                print(f"\033[1;33m[AUDIO] Creating TRUSDX audio device...\033[0m")
                os.system('pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"')
                time.sleep(1)
            
            # Verify it exists now
            result = os.popen('pactl list sinks | grep -c "Name: TRUSDX"').read().strip()
            return result == '1'
            
        except Exception as e:
            log(f"Audio setup error: {e}")
            return False
    
    def recover_pulse_sink(self, sink_name: str = "TRUSDX") -> bool:
        """Recover from Pulse sink disappearance.
        
        Args:
            sink_name: Name of the sink to recover
            
        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            import os
            import subprocess
            
            log(f"Attempting to recover Pulse sink: {sink_name}")
            
            # Check if PulseAudio is running
            try:
                subprocess.run(['pactl', 'info'], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                log("PulseAudio not running, attempting to restart...")
                try:
                    subprocess.run(['pulseaudio', '--start'], check=True)
                    time.sleep(2)
                except subprocess.CalledProcessError as e:
                    log(f"Failed to restart PulseAudio: {e}")
                    return False
            
            # Remove existing sink if it exists but is broken
            try:
                result = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True)
                if sink_name in result.stdout:
                    log(f"Removing broken sink: {sink_name}")
                    subprocess.run(['pactl', 'unload-module', 'module-null-sink'], capture_output=True)
            except Exception as e:
                log(f"Error removing broken sink: {e}")
            
            # Recreate the sink
            cmd = f'pactl load-module module-null-sink sink_name={sink_name} sink_properties=device.description="{sink_name}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                log(f"Successfully recreated sink: {sink_name}")
                time.sleep(1)
                
                # Verify it exists
                verify_result = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True)
                if sink_name in verify_result.stdout:
                    log(f"Sink {sink_name} recovery successful")
                    return True
                else:
                    log(f"Sink {sink_name} not found after recreation")
                    return False
            else:
                log(f"Failed to recreate sink: {result.stderr}")
                return False
                
        except Exception as e:
            log(f"Error during sink recovery: {e}")
            return False
    
    def create_output_stream_with_recovery(self, device_index: int = -1, retries: int = 3) -> Optional[pyaudio.Stream]:
        """Create audio output stream with automatic recovery on failure.
        
        Args:
            device_index: Audio device index (-1 for default)
            retries: Number of retry attempts
            
        Returns:
            PyAudio stream object or None if failed
        """
        for attempt in range(retries):
            try:
                stream = self.p.open(
                    frames_per_buffer=0,
                    format=pyaudio.paUInt8,
                    channels=1,
                    rate=AUDIO_RX_RATE,
                    output=True,
                    output_device_index=device_index if device_index != -1 else None
                )
                log(f"Created output stream with device {device_index}")
                return stream
            except Exception as e:
                log(f"Error creating output stream (attempt {attempt + 1}/{retries}): {e}")
                
                if attempt < retries - 1:
                    # Try to recover the sink
                    if self.recover_pulse_sink():
                        log("Pulse sink recovery successful, retrying stream creation...")
                        time.sleep(1)
                        continue
                    else:
                        log("Pulse sink recovery failed")
                        time.sleep(2)
                else:
                    log("All stream creation attempts failed")
                    return None
        
        return None
    
    def verify_stream_format(self, stream: pyaudio.Stream, expected_format: int, expected_rate: int) -> bool:
        """Verify audio stream format and rate.
        
        Args:
            stream: PyAudio stream to verify
            expected_format: Expected audio format (e.g., pyaudio.paInt16)
            expected_rate: Expected sample rate
            
        Returns:
            True if format matches, False otherwise
        """
        try:
            # Get stream info
            info = stream.get_stream_info()
            
            # Check format
            if hasattr(info, 'format') and info.format != expected_format:
                log(f"Stream format mismatch: expected {expected_format}, got {info.format}")
                return False
            
            # Check sample rate
            if hasattr(info, 'sample_rate') and info.sample_rate != expected_rate:
                log(f"Stream rate mismatch: expected {expected_rate}, got {info.sample_rate}")
                return False
            
            log(f"Stream format verified: format={expected_format}, rate={expected_rate}")
            return True
            
        except Exception as e:
            log(f"Error verifying stream format: {e}")
            return False
    
    def verify_buffer_sizes(self, rx_buffer_size: int = 0, tx_buffer_size: int = 512) -> dict:
        """Verify audio buffer sizes are appropriate for waterfall display.
        
        Args:
            rx_buffer_size: Expected RX buffer size (0 for streaming)
            tx_buffer_size: Expected TX buffer size
            
        Returns:
            Dictionary with buffer size information
        """
        try:
            buffer_info = {
                'rx_buffer_size': rx_buffer_size,
                'tx_buffer_size': tx_buffer_size,
                'rx_format': 'paUInt8',
                'tx_format': 'paInt16',
                'rx_rate': AUDIO_RX_RATE,
                'tx_rate': AUDIO_TX_RATE,
                'rx_channels': 1,
                'tx_channels': 1,
                'waterfall_compatible': True
            }
            
            # Check if buffer sizes are reasonable for waterfall display
            if rx_buffer_size > 1024:
                log(f"Warning: RX buffer size {rx_buffer_size} may cause waterfall lag")
                buffer_info['waterfall_compatible'] = False
            
            if tx_buffer_size < 64 or tx_buffer_size > 2048:
                log(f"Warning: TX buffer size {tx_buffer_size} may cause audio issues")
                buffer_info['waterfall_compatible'] = False
            
            # Verify format compatibility
            if buffer_info['rx_format'] != 'paUInt8':
                log("Warning: RX format is not 8-bit, may affect waterfall display")
                buffer_info['waterfall_compatible'] = False
            
            log(f"Buffer verification: {buffer_info}")
            return buffer_info
            
        except Exception as e:
            log(f"Error verifying buffer sizes: {e}")
            return {'error': str(e)}
    
    def test_audio_path(self, duration: float = 1.0) -> bool:
        """Test audio path to ensure RX audio reaches waterfall.
        
        Args:
            duration: Test duration in seconds
            
        Returns:
            True if audio path is working, False otherwise
        """
        try:
            import numpy as np
            
            log(f"Testing audio path for {duration} seconds...")
            
            # Create test stream
            test_stream = self.p.open(
                frames_per_buffer=0,
                format=pyaudio.paUInt8,
                channels=1,
                rate=AUDIO_RX_RATE,
                output=True,
                output_device_index=-1
            )
            
            # Generate test tone (1kHz sine wave)
            sample_count = int(AUDIO_RX_RATE * duration)
            t = np.linspace(0, duration, sample_count)
            frequency = 1000  # 1kHz test tone
            amplitude = 64  # Moderate amplitude for 8-bit
            
            # Generate 8-bit unsigned sine wave
            test_signal = (amplitude * np.sin(2 * np.pi * frequency * t) + 128).astype(np.uint8)
            
            # Play test signal
            test_stream.write(test_signal.tobytes())
            test_stream.close()
            
            log("Audio path test completed successfully")
            return True
            
        except Exception as e:
            log(f"Audio path test failed: {e}")
            return False
    
    def terminate(self):
        """Clean up audio resources."""
        try:
            if self.in_stream:
                self.in_stream.close()
            if self.out_stream:
                self.out_stream.close()
            self.p.terminate()
            log("Audio resources cleaned up")
        except Exception as e:
            log(f"Error terminating audio: {e}")


def get_platform_audio_config(platform: str) -> dict:
    """Get platform-specific audio configuration.
    
    Args:
        platform: Platform identifier (linux, win32, darwin)
        
    Returns:
        Dictionary with audio device configuration
    """
    if platform == "linux" or platform == "linux2":
        return {
            'virtual_audio_dev_out': "",  # Default audio device
            'virtual_audio_dev_in': "",   # Default audio device
        }
    elif platform == "win32":
        return {
            'virtual_audio_dev_out': "CABLE Output",
            'virtual_audio_dev_in': "CABLE Input",
        }
    else:  # darwin
        return {
            'virtual_audio_dev_out': "BlackHole 2ch",
            'virtual_audio_dev_in': "BlackHole 2ch",
        }
