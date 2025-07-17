#!/usr/bin/env python3
"""
Audio Routing Test for JS8Call and TruSDX Driver
Tests audio flow between JS8Call and the TruSDX driver
"""

import subprocess
import time
import numpy as np
import sounddevice as sd
import threading
import queue
import signal
import sys
from datetime import datetime

class AudioRoutingTester:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.running = True
        self.monitor_thread = None
        self.test_results = {
            'trusdx_sink_exists': False,
            'trusdx_monitor_exists': False,
            'audio_detected_on_monitor': False,
            'audio_level_peak': 0.0,
            'audio_samples_received': 0,
            'pw_connections': [],
            'active_streams': []
        }
        
    def check_audio_devices(self):
        """Check if TRUSDX audio devices exist"""
        print("\n=== Checking Audio Devices ===")
        
        # Check PulseAudio sinks
        try:
            result = subprocess.run(['pactl', 'list', 'short', 'sinks'], 
                                    capture_output=True, text=True)
            if 'TRUSDX' in result.stdout:
                self.test_results['trusdx_sink_exists'] = True
                print("✅ TRUSDX sink found in PulseAudio")
            else:
                print("❌ TRUSDX sink not found in PulseAudio")
                
            # Check sources (monitors)
            result = subprocess.run(['pactl', 'list', 'short', 'sources'], 
                                    capture_output=True, text=True)
            if 'TRUSDX.monitor' in result.stdout:
                self.test_results['trusdx_monitor_exists'] = True
                print("✅ TRUSDX.monitor source found in PulseAudio")
            else:
                print("❌ TRUSDX.monitor source not found in PulseAudio")
                
        except Exception as e:
            print(f"Error checking PulseAudio devices: {e}")
            
        # List all audio devices
        print("\n--- Available Audio Devices ---")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if 'TRUSDX' in device['name']:
                print(f"[{i}] {device['name']} - {device['max_input_channels']} in, {device['max_output_channels']} out")
                
    def check_pipewire_connections(self):
        """Check PipeWire connections"""
        print("\n=== Checking PipeWire Connections ===")
        
        try:
            # List all PipeWire links
            result = subprocess.run(['pw-link', '-l'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            
            connections = []
            current_connection = {}
            
            for line in lines:
                if line.startswith('  '):
                    # This is a port
                    if 'TRUSDX' in line or 'JS8Call' in line:
                        if ':' in line:
                            node, port = line.strip().split(':', 1)
                            if not current_connection:
                                current_connection = {'output': f"{node}:{port}"}
                            else:
                                current_connection['input'] = f"{node}:{port}"
                                connections.append(current_connection)
                                current_connection = {}
                                
            self.test_results['pw_connections'] = connections
            
            if connections:
                print("Found PipeWire connections:")
                for conn in connections:
                    print(f"  {conn.get('output', '?')} -> {conn.get('input', '?')}")
            else:
                print("No TRUSDX/JS8Call connections found in PipeWire")
                
        except Exception as e:
            print(f"Error checking PipeWire connections: {e}")
            
    def monitor_audio_callback(self, indata, frames, time, status):
        """Callback for monitoring audio from TRUSDX.monitor"""
        if status:
            print(f"Audio callback status: {status}")
            
        # Calculate audio level
        level = np.abs(indata).max()
        if level > self.test_results['audio_level_peak']:
            self.test_results['audio_level_peak'] = level
            
        if level > 0.001:  # Threshold for detecting audio
            self.test_results['audio_detected_on_monitor'] = True
            self.test_results['audio_samples_received'] += frames
            
        # Put audio data in queue for further analysis
        self.audio_queue.put((indata.copy(), level))
        
    def start_audio_monitoring(self):
        """Start monitoring TRUSDX.monitor for audio"""
        print("\n=== Starting Audio Monitoring ===")
        
        try:
            # Find TRUSDX.monitor device
            devices = sd.query_devices()
            monitor_device = None
            
            for i, device in enumerate(devices):
                if 'TRUSDX.monitor' in device['name'] and device['max_input_channels'] > 0:
                    monitor_device = i
                    print(f"Found TRUSDX.monitor at device index {i}")
                    break
                    
            if monitor_device is None:
                print("❌ Could not find TRUSDX.monitor device")
                return
                
            # Start audio stream
            print(f"Starting audio stream on device {monitor_device}...")
            self.stream = sd.InputStream(
                device=monitor_device,
                channels=1,
                samplerate=48000,
                callback=self.monitor_audio_callback,
                blocksize=4800  # 100ms blocks
            )
            self.stream.start()
            print("✅ Audio monitoring started")
            
            # Monitor for 30 seconds
            print("\nMonitoring for audio (30 seconds)...")
            print("If JS8Call is transmitting, we should see audio levels here.")
            print("Press Ctrl+C to stop early.\n")
            
            start_time = time.time()
            last_print = start_time
            
            while self.running and (time.time() - start_time) < 30:
                # Process audio queue
                try:
                    while True:
                        audio_data, level = self.audio_queue.get_nowait()
                        
                        # Print audio level bar
                        if time.time() - last_print > 0.1:  # Update every 100ms
                            bar_length = int(level * 50)
                            bar = '█' * bar_length + '░' * (50 - bar_length)
                            print(f"\rAudio Level: [{bar}] {level:.4f}", end='', flush=True)
                            last_print = time.time()
                            
                except queue.Empty:
                    time.sleep(0.01)
                    
            self.stream.stop()
            print("\n\n✅ Audio monitoring complete")
            
        except Exception as e:
            print(f"Error in audio monitoring: {e}")
            
    def check_active_streams(self):
        """Check for active audio streams"""
        print("\n=== Checking Active Audio Streams ===")
        
        try:
            # Check PulseAudio streams
            result = subprocess.run(['pactl', 'list', 'short', 'source-outputs'], 
                                    capture_output=True, text=True)
            if result.stdout:
                print("Active source outputs:")
                for line in result.stdout.strip().split('\n'):
                    if line:
                        print(f"  {line}")
                        self.test_results['active_streams'].append(('source-output', line))
                        
            result = subprocess.run(['pactl', 'list', 'short', 'sink-inputs'], 
                                    capture_output=True, text=True)
            if result.stdout:
                print("\nActive sink inputs:")
                for line in result.stdout.strip().split('\n'):
                    if line:
                        print(f"  {line}")
                        self.test_results['active_streams'].append(('sink-input', line))
                        
        except Exception as e:
            print(f"Error checking active streams: {e}")
            
    def generate_test_tone(self):
        """Generate a test tone on TRUSDX sink"""
        print("\n=== Generating Test Tone ===")
        
        try:
            # Find TRUSDX output device
            devices = sd.query_devices()
            trusdx_device = None
            
            for i, device in enumerate(devices):
                if 'TRUSDX' in device['name'] and device['max_output_channels'] > 0 and 'monitor' not in device['name']:
                    trusdx_device = i
                    print(f"Found TRUSDX output at device index {i}")
                    break
                    
            if trusdx_device is None:
                print("❌ Could not find TRUSDX output device")
                return
                
            # Generate 1kHz test tone
            duration = 2.0
            sample_rate = 48000
            frequency = 1000
            t = np.linspace(0, duration, int(sample_rate * duration))
            tone = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            print(f"Playing 1kHz test tone for {duration} seconds...")
            sd.play(tone, sample_rate, device=trusdx_device)
            sd.wait()
            print("✅ Test tone complete")
            
        except Exception as e:
            print(f"Error generating test tone: {e}")
            
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("AUDIO ROUTING TEST SUMMARY")
        print("="*60)
        
        print(f"TRUSDX sink exists: {'✅' if self.test_results['trusdx_sink_exists'] else '❌'}")
        print(f"TRUSDX.monitor exists: {'✅' if self.test_results['trusdx_monitor_exists'] else '❌'}")
        print(f"Audio detected on monitor: {'✅' if self.test_results['audio_detected_on_monitor'] else '❌'}")
        print(f"Peak audio level: {self.test_results['audio_level_peak']:.4f}")
        print(f"Audio samples received: {self.test_results['audio_samples_received']}")
        
        if self.test_results['pw_connections']:
            print(f"\nPipeWire connections found: {len(self.test_results['pw_connections'])}")
        else:
            print("\n⚠️  No PipeWire connections found between JS8Call and TRUSDX")
            
        if self.test_results['active_streams']:
            print(f"\nActive audio streams: {len(self.test_results['active_streams'])}")
        else:
            print("\n⚠️  No active audio streams found")
            
        print("\n" + "="*60)
        
        # Recommendations
        print("\nRECOMMENDATIONS:")
        
        if not self.test_results['trusdx_sink_exists']:
            print("1. Run the TruSDX driver to create the TRUSDX audio device")
            
        if not self.test_results['audio_detected_on_monitor']:
            print("2. Ensure JS8Call is configured to output audio to 'TRUSDX'")
            print("3. Try transmitting a message in JS8Call during the test")
            
        if not self.test_results['pw_connections']:
            print("4. Check JS8Call audio settings:")
            print("   - Input: TRUSDX.monitor")
            print("   - Output: TRUSDX")
            
    def run(self):
        """Run all tests"""
        print("TruSDX Audio Routing Test")
        print("========================")
        print(f"Started at: {datetime.now()}")
        
        # Setup signal handler
        signal.signal(signal.SIGINT, lambda s, f: setattr(self, 'running', False))
        
        # Run tests
        self.check_audio_devices()
        self.check_pipewire_connections()
        self.check_active_streams()
        
        # Ask if user wants to monitor audio
        response = input("\nMonitor TRUSDX.monitor for audio? (y/n): ")
        if response.lower() == 'y':
            self.start_audio_monitoring()
            
        # Ask if user wants to generate test tone
        response = input("\nGenerate test tone on TRUSDX output? (y/n): ")
        if response.lower() == 'y':
            self.generate_test_tone()
            
        # Print summary
        self.print_summary()
        

if __name__ == "__main__":
    tester = AudioRoutingTester()
    tester.run()
