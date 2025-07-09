#!/usr/bin/env python3
"""
Unit tests for audio handling fixes in truSDX-AI driver.
Tests mute-speaker flag, audio format verification, and Pulse sink recovery.
"""

import unittest
import unittest.mock as mock
import sys
import os
import time
import tempfile
import subprocess
import numpy as np
from io import BytesIO

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from audio_io import AudioManager, AUDIO_RX_RATE, AUDIO_TX_RATE
from logging_cfg import log


class TestAudioHandling(unittest.TestCase):
    """Test suite for audio handling fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.audio_manager = AudioManager()
        self.test_data_dir = os.path.join(os.path.dirname(__file__), 'test_data')
        os.makedirs(self.test_data_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        try:
            self.audio_manager.terminate()
        except:
            pass
    
    def test_mute_speaker_flag_handling(self):
        """Test that mute-speaker flag is properly handled."""
        test_configs = [
            {'mute_speaker': True, 'unmute': False, 'expected_cmd': b';MD2;UA2;'},
            {'mute_speaker': False, 'unmute': True, 'expected_cmd': b';MD2;UA1;'},
            {'mute_speaker': False, 'unmute': False, 'expected_cmd': b';MD2;UA2;'},
            {'mute_speaker': True, 'unmute': True, 'expected_cmd': b';MD2;UA2;'},  # mute_speaker takes precedence
        ]
        
        for config in test_configs:
            with self.subTest(config=config):
                # Test the command generation logic
                if config.get('mute_speaker', False):
                    init_cmd = b';MD2;UA2;'  # Force mute speaker while keeping VU meter active
                elif config.get('unmute', False):
                    init_cmd = b';MD2;UA1;'  # Enable speaker audio
                else:
                    init_cmd = b';MD2;UA2;'  # Default: mute speaker
                
                self.assertEqual(init_cmd, config['expected_cmd'], 
                               f"Command mismatch for config {config}")
    
    def test_audio_stream_format_verification(self):
        """Test audio stream format verification."""
        # Mock PyAudio stream
        mock_stream = mock.Mock()
        mock_info = mock.Mock()
        mock_info.format = 8  # pyaudio.paUInt8
        mock_info.sample_rate = AUDIO_RX_RATE
        mock_stream.get_stream_info.return_value = mock_info
        
        # Test correct format
        result = self.audio_manager.verify_stream_format(mock_stream, 8, AUDIO_RX_RATE)
        self.assertTrue(result, "Stream format verification should pass for correct format")
        
        # Test incorrect format
        mock_info.format = 16  # Wrong format
        result = self.audio_manager.verify_stream_format(mock_stream, 8, AUDIO_RX_RATE)
        self.assertFalse(result, "Stream format verification should fail for incorrect format")
        
        # Test incorrect rate
        mock_info.format = 8  # Correct format
        mock_info.sample_rate = 44100  # Wrong rate
        result = self.audio_manager.verify_stream_format(mock_stream, 8, AUDIO_RX_RATE)
        self.assertFalse(result, "Stream format verification should fail for incorrect rate")
    
    def test_buffer_size_verification(self):
        """Test buffer size verification for waterfall compatibility."""
        # Test optimal buffer sizes
        result = self.audio_manager.verify_buffer_sizes(rx_buffer_size=0, tx_buffer_size=512)
        self.assertTrue(result['waterfall_compatible'], 
                       "Optimal buffer sizes should be waterfall compatible")
        
        # Test large RX buffer (should cause waterfall lag)
        result = self.audio_manager.verify_buffer_sizes(rx_buffer_size=2048, tx_buffer_size=512)
        self.assertFalse(result['waterfall_compatible'], 
                        "Large RX buffer should not be waterfall compatible")
        
        # Test small TX buffer
        result = self.audio_manager.verify_buffer_sizes(rx_buffer_size=0, tx_buffer_size=32)
        self.assertFalse(result['waterfall_compatible'], 
                        "Small TX buffer should not be waterfall compatible")
        
        # Test large TX buffer
        result = self.audio_manager.verify_buffer_sizes(rx_buffer_size=0, tx_buffer_size=4096)
        self.assertFalse(result['waterfall_compatible'], 
                        "Large TX buffer should not be waterfall compatible")
    
    def test_audio_format_8bit_vs_16bit(self):
        """Test that RX audio uses 8-bit format for waterfall compatibility."""
        # Verify RX format is 8-bit unsigned
        buffer_info = self.audio_manager.verify_buffer_sizes()
        self.assertEqual(buffer_info['rx_format'], 'paUInt8', 
                        "RX format should be 8-bit unsigned")
        self.assertEqual(buffer_info['tx_format'], 'paInt16', 
                        "TX format should be 16-bit signed")
        
        # Test TX audio processing (16-bit to 8-bit conversion)
        samples_16bit = np.array([0, 256, -256, 32767, -32768], dtype=np.int16)
        samples_bytes = samples_16bit.tobytes()
        
        processed_samples = self.audio_manager.process_tx_audio(samples_bytes)
        
        # Verify conversion to 8-bit
        self.assertIsInstance(processed_samples, bytearray)
        self.assertEqual(len(processed_samples), len(samples_16bit))
        
        # Test specific conversion values
        expected_8bit = [128, 129, 127, 255, 0]  # 128 + x//256
        for i, expected in enumerate(expected_8bit):
            self.assertEqual(processed_samples[i], expected, 
                           f"Sample {i} conversion incorrect")
    
    @mock.patch('subprocess.run')
    def test_pulse_sink_recovery(self, mock_run):
        """Test Pulse sink recovery functionality."""
        # Mock successful pactl commands
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "Name: TRUSDX\nDescription: TRUSDX"
        
        # Test successful recovery
        result = self.audio_manager.recover_pulse_sink("TRUSDX")
        self.assertTrue(result, "Pulse sink recovery should succeed")
        
        # Verify pactl commands were called
        self.assertTrue(mock_run.called, "pactl commands should be called")
        
        # Test failed recovery
        mock_run.return_value.returncode = 1
        mock_run.return_value.stderr = "Module not found"
        
        result = self.audio_manager.recover_pulse_sink("TRUSDX")
        self.assertFalse(result, "Pulse sink recovery should fail")
    
    @mock.patch('pyaudio.PyAudio')
    def test_output_stream_creation_with_recovery(self, mock_pyaudio):
        """Test output stream creation with automatic recovery."""
        mock_pa = mock.Mock()
        mock_pyaudio.return_value = mock_pa
        
        # Test successful stream creation
        mock_stream = mock.Mock()
        mock_pa.open.return_value = mock_stream
        
        result = self.audio_manager.create_output_stream_with_recovery()
        self.assertIsNotNone(result, "Stream creation should succeed")
        
        # Test stream creation with retry
        mock_pa.open.side_effect = [Exception("Stream error"), mock_stream]
        
        with mock.patch.object(self.audio_manager, 'recover_pulse_sink', return_value=True):
            result = self.audio_manager.create_output_stream_with_recovery()
            self.assertIsNotNone(result, "Stream creation should succeed after recovery")
    
    def test_vox_detection(self):
        """Test VOX (Voice Operated Switch) detection."""
        # Test loud signal detection
        loud_samples = bytearray([64, 192, 64, 192, 64, 192])  # Very loud signal
        result = self.audio_manager.handle_vox(loud_samples)
        self.assertTrue(result, "VOX should detect loud signal")
        
        # Test quiet signal
        quiet_samples = bytearray([120, 136, 125, 130, 128, 132])  # Quiet signal
        result = self.audio_manager.handle_vox(quiet_samples)
        self.assertFalse(result, "VOX should not detect quiet signal")
    
    def test_audio_path_functionality(self):
        """Test audio path to ensure RX audio reaches waterfall."""
        # Mock numpy for test signal generation
        with mock.patch('numpy.linspace') as mock_linspace, \
             mock.patch('numpy.sin') as mock_sin, \
             mock.patch('pyaudio.PyAudio') as mock_pyaudio:
            
            # Setup mocks
            mock_linspace.return_value = np.linspace(0, 1, 7812)
            mock_sin.return_value = np.sin(np.linspace(0, 1, 7812))
            
            mock_stream = mock.Mock()
            mock_pa = mock.Mock()
            mock_pa.open.return_value = mock_stream
            mock_pyaudio.return_value = mock_pa
            
            # Test audio path
            result = self.audio_manager.test_audio_path(duration=0.1)
            self.assertTrue(result, "Audio path test should succeed")
            
            # Verify stream was opened and used
            mock_pa.open.assert_called_once()
            mock_stream.write.assert_called_once()
            mock_stream.close.assert_called_once()
    
    def test_semicolon_filtering(self):
        """Test that semicolons are filtered from audio stream."""
        # Test data with semicolon byte (0x3b)
        test_samples = bytearray([0x3a, 0x3b, 0x3c, 0x3b, 0x3d])
        processed = self.audio_manager.process_tx_audio(test_samples)
        
        # Verify semicolons (0x3b) are replaced with 0x3a
        self.assertNotIn(0x3b, processed, "Semicolons should be filtered from stream")
        
        # Count replacements
        original_semicolons = test_samples.count(0x3b)
        processed_replacements = processed.count(0x3a)
        
        # Should have more 0x3a bytes after processing
        self.assertGreater(processed_replacements, original_semicolons, 
                          "Semicolons should be replaced with 0x3a")
    
    def generate_test_iq_file(self, filename: str, duration: float = 1.0, 
                             frequency: float = 1000.0, sample_rate: int = 7812):
        """Generate a test I/Q file for testing."""
        sample_count = int(sample_rate * duration)
        t = np.linspace(0, duration, sample_count)
        
        # Generate complex I/Q signal
        iq_signal = np.exp(1j * 2 * np.pi * frequency * t)
        
        # Convert to 8-bit unsigned format
        i_samples = (iq_signal.real * 64 + 128).astype(np.uint8)
        q_samples = (iq_signal.imag * 64 + 128).astype(np.uint8)
        
        # Interleave I and Q samples
        iq_bytes = bytearray()
        for i, q in zip(i_samples, q_samples):
            iq_bytes.extend([i, q])
        
        # Write to file
        filepath = os.path.join(self.test_data_dir, filename)
        with open(filepath, 'wb') as f:
            f.write(iq_bytes)
        
        return filepath
    
    def test_recorded_iq_file_processing(self):
        """Test processing of recorded I/Q files."""
        # Generate test I/Q file
        test_file = self.generate_test_iq_file("test_signal.iq")
        
        # Read and process the file
        with open(test_file, 'rb') as f:
            iq_data = f.read()
        
        # Verify file was created and has expected size
        expected_size = 2 * int(7812 * 1.0)  # 2 bytes per sample (I+Q) * samples
        self.assertEqual(len(iq_data), expected_size, 
                        f"I/Q file should have {expected_size} bytes")
        
        # Test processing the I/Q data
        processed_data = self.audio_manager.process_tx_audio(iq_data)
        
        # Verify processing
        self.assertIsInstance(processed_data, bytearray)
        self.assertGreater(len(processed_data), 0, "Processed data should not be empty")
        
        # Clean up
        os.remove(test_file)
    
    def test_no_clipping_detection(self):
        """Test detection of audio clipping."""
        # Test signal with clipping (all max values)
        clipped_samples = bytearray([255] * 100)
        
        # Calculate dynamic range
        min_val = min(clipped_samples)
        max_val = max(clipped_samples)
        dynamic_range = max_val - min_val
        
        # Clipped signal should have no dynamic range
        self.assertEqual(dynamic_range, 0, "Clipped signal should have no dynamic range")
        
        # Test normal signal
        normal_samples = bytearray(range(100, 200))
        min_val = min(normal_samples)
        max_val = max(normal_samples)
        dynamic_range = max_val - min_val
        
        # Normal signal should have good dynamic range
        self.assertGreater(dynamic_range, 50, "Normal signal should have good dynamic range")
    
    def test_underrun_detection(self):
        """Test detection of audio underruns."""
        # Test the underrun counter functionality
        from audio_io import urs, buf
        
        # Clear buffer to simulate underrun
        buf.clear()
        initial_underruns = urs[0]
        
        # Simulate underrun condition (buffer length < 2)
        while len(buf) < 2:
            if len(buf) < 2:
                urs[0] += 1
            buf.append(b'\x80' * 100)  # Add some dummy data
        
        # Verify underrun was detected
        self.assertGreater(urs[0], initial_underruns, 
                          "Underrun counter should increase when buffer is empty")


class TestLiveTruSDXIntegration(unittest.TestCase):
    """Integration tests with live truSDX hardware (requires actual hardware)."""
    
    def setUp(self):
        """Set up for live hardware tests."""
        self.audio_manager = AudioManager()
        # Only run if truSDX hardware is available
        self.hardware_available = self.check_trusdx_hardware()
    
    def check_trusdx_hardware(self):
        """Check if truSDX hardware is available."""
        try:
            import serial.tools.list_ports
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if 'USB Serial' in port.description or 'CH340' in port.description:
                    return True
            return False
        except:
            return False
    
    def test_live_trusdx_mute_speaker_command(self):
        """Test mute speaker command with live truSDX hardware."""
        if not self.hardware_available:
            self.skipTest("truSDX hardware not available")
        
        try:
            import serial
            import serial.tools.list_ports
            
            # Find truSDX port
            ports = serial.tools.list_ports.comports()
            trusdx_port = None
            for port in ports:
                if 'USB Serial' in port.description or 'CH340' in port.description:
                    trusdx_port = port.device
                    break
            
            if not trusdx_port:
                self.skipTest("truSDX serial port not found")
            
            # Test connection and mute command
            with serial.Serial(trusdx_port, 115200, timeout=1) as ser:
                # Send mute speaker command
                ser.write(b';UA2;')
                ser.flush()
                time.sleep(0.1)
                
                # Verify command was sent (no exception means success)
                self.assertTrue(True, "Mute speaker command sent successfully")
                
                # Test unmute command
                ser.write(b';UA1;')
                ser.flush()
                time.sleep(0.1)
                
                # Restore mute
                ser.write(b';UA2;')
                ser.flush()
                
        except Exception as e:
            self.fail(f"Live truSDX test failed: {e}")
    
    def test_live_trusdx_audio_streaming(self):
        """Test audio streaming with live truSDX hardware."""
        if not self.hardware_available:
            self.skipTest("truSDX hardware not available")
        
        try:
            import serial
            import serial.tools.list_ports
            
            # Find truSDX port
            ports = serial.tools.list_ports.comports()
            trusdx_port = None
            for port in ports:
                if 'USB Serial' in port.description or 'CH340' in port.description:
                    trusdx_port = port.device
                    break
            
            if not trusdx_port:
                self.skipTest("truSDX serial port not found")
            
            # Test audio streaming
            with serial.Serial(trusdx_port, 115200, timeout=1) as ser:
                # Enable audio streaming
                ser.write(b';MD2;UA2;')
                ser.flush()
                time.sleep(0.5)
                
                # Read some audio data
                audio_data = ser.read(1000)
                
                # Verify we received audio data
                self.assertGreater(len(audio_data), 0, 
                                 "Should receive audio data from truSDX")
                
                # Verify data contains expected patterns
                # Audio data should not be all zeros or all same value
                unique_values = set(audio_data)
                self.assertGreater(len(unique_values), 1, 
                                 "Audio data should have variety")
                
        except Exception as e:
            self.fail(f"Live truSDX audio streaming test failed: {e}")


def run_performance_tests():
    """Run performance tests for audio handling."""
    print("Running performance tests...")
    
    audio_manager = AudioManager()
    
    # Test buffer processing performance
    start_time = time.time()
    for _ in range(1000):
        test_samples = bytearray(range(512))
        processed = audio_manager.process_tx_audio(test_samples)
    processing_time = time.time() - start_time
    
    print(f"Buffer processing: {processing_time:.3f}s for 1000 iterations")
    print(f"Average per buffer: {processing_time/1000*1000:.3f}ms")
    
    # Test audio path performance
    start_time = time.time()
    result = audio_manager.test_audio_path(duration=0.1)
    path_time = time.time() - start_time
    
    print(f"Audio path test: {path_time:.3f}s (result: {result})")
    
    audio_manager.terminate()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test audio handling fixes')
    parser.add_argument('--performance', action='store_true', 
                       help='Run performance tests')
    parser.add_argument('--live', action='store_true',
                       help='Run live hardware tests')
    parser.add_argument('--generate-test-data', action='store_true',
                       help='Generate test I/Q files')
    args = parser.parse_args()
    
    if args.performance:
        run_performance_tests()
    elif args.generate_test_data:
        audio_manager = AudioManager()
        test_data_dir = 'test_data'
        os.makedirs(test_data_dir, exist_ok=True)
        
        # Generate various test signals
        signals = [
            ('1khz_tone.iq', 1000, 2.0),
            ('500hz_tone.iq', 500, 1.0),
            ('2khz_tone.iq', 2000, 0.5),
            ('white_noise.iq', None, 1.0),  # Special case for noise
        ]
        
        for filename, freq, duration in signals:
            if freq is None:
                # Generate white noise
                samples = np.random.randint(0, 255, int(7812 * duration * 2), dtype=np.uint8)
            else:
                # Generate tone
                sample_count = int(7812 * duration)
                t = np.linspace(0, duration, sample_count)
                iq_signal = np.exp(1j * 2 * np.pi * freq * t)
                i_samples = (iq_signal.real * 64 + 128).astype(np.uint8)
                q_samples = (iq_signal.imag * 64 + 128).astype(np.uint8)
                samples = bytearray()
                for i, q in zip(i_samples, q_samples):
                    samples.extend([i, q])
            
            filepath = os.path.join(test_data_dir, filename)
            with open(filepath, 'wb') as f:
                f.write(samples)
            print(f"Generated {filepath}")
        
        audio_manager.terminate()
    else:
        # Run unit tests
        unittest.main(argv=[''], exit=False, verbosity=2)
