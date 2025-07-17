#!/usr/bin/env python3
"""
Simple Audio Routing Test for JS8Call and TruSDX Driver
Tests audio flow between JS8Call and the TruSDX driver using system commands
"""

import subprocess
import time
import sys
from datetime import datetime

class SimpleAudioRoutingTester:
    def __init__(self):
        self.test_results = {
            'trusdx_sink_exists': False,
            'trusdx_monitor_exists': False,
            'pw_connections': [],
            'active_streams': [],
            'audio_activity': []
        }
        
    def run_command(self, cmd):
        """Run a command and return output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1
            
    def check_audio_devices(self):
        """Check if TRUSDX audio devices exist"""
        print("\n=== Checking Audio Devices ===")
        
        # Check PulseAudio sinks
        stdout, stderr, rc = self.run_command('pactl list short sinks')
        if 'TRUSDX' in stdout:
            self.test_results['trusdx_sink_exists'] = True
            print("✅ TRUSDX sink found in PulseAudio")
            for line in stdout.strip().split('\n'):
                if 'TRUSDX' in line:
                    print(f"   {line}")
        else:
            print("❌ TRUSDX sink not found in PulseAudio")
            
        # Check sources (monitors)
        stdout, stderr, rc = self.run_command('pactl list short sources')
        if 'TRUSDX.monitor' in stdout:
            self.test_results['trusdx_monitor_exists'] = True
            print("✅ TRUSDX.monitor source found in PulseAudio")
            for line in stdout.strip().split('\n'):
                if 'TRUSDX.monitor' in line:
                    print(f"   {line}")
        else:
            print("❌ TRUSDX.monitor source not found in PulseAudio")
            
        # List all TRUSDX-related devices
        print("\n--- PipeWire Devices ---")
        stdout, stderr, rc = self.run_command('pw-cli list-objects | grep -A5 -B5 TRUSDX')
        if stdout:
            print(stdout)
            
    def check_pipewire_connections(self):
        """Check PipeWire connections"""
        print("\n=== Checking PipeWire Connections ===")
        
        # Get all links
        stdout, stderr, rc = self.run_command('pw-link -l')
        if stdout:
            lines = stdout.strip().split('\n')
            connections = []
            
            # Parse connections
            i = 0
            while i < len(lines):
                line = lines[i]
                if 'TRUSDX' in line or 'JS8Call' in line:
                    # Found a relevant connection
                    output_port = line.strip()
                    # Look for the arrow and input port
                    if i + 1 < len(lines) and '->' in lines[i + 1]:
                        arrow_line = lines[i + 1]
                        if i + 2 < len(lines):
                            input_port = lines[i + 2].strip()
                            connections.append({
                                'output': output_port,
                                'input': input_port
                            })
                            print(f"Found: {output_port} -> {input_port}")
                i += 1
                
            self.test_results['pw_connections'] = connections
            
            if not connections:
                print("No TRUSDX/JS8Call connections found in PipeWire")
                print("\nAll PipeWire links:")
                print(stdout)
        else:
            print("Could not get PipeWire links")
            
    def check_active_streams(self):
        """Check for active audio streams"""
        print("\n=== Checking Active Audio Streams ===")
        
        # Check source outputs (recording from sources)
        stdout, stderr, rc = self.run_command('pactl list short source-outputs')
        if stdout:
            print("Active source outputs (applications recording):")
            for line in stdout.strip().split('\n'):
                if line:
                    print(f"  {line}")
                    self.test_results['active_streams'].append(('source-output', line))
        else:
            print("No active source outputs")
                    
        # Check sink inputs (playing to sinks)
        stdout, stderr, rc = self.run_command('pactl list short sink-inputs')
        if stdout:
            print("\nActive sink inputs (applications playing):")
            for line in stdout.strip().split('\n'):
                if line:
                    print(f"  {line}")
                    self.test_results['active_streams'].append(('sink-input', line))
        else:
            print("No active sink inputs")
            
    def monitor_audio_levels(self, duration=10):
        """Monitor audio levels using parec"""
        print(f"\n=== Monitoring Audio Levels ({duration}s) ===")
        print("This will show if audio is flowing through TRUSDX.monitor...")
        
        # Start monitoring in background
        proc = subprocess.Popen(
            ['parec', '--device=TRUSDX.monitor', '--format=float32le', '--channels=1', '--latency=100'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print("\nMonitoring... (transmit in JS8Call to see activity)")
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # Read a small chunk
                data = proc.stdout.read(4096)
                if data:
                    # Simple activity detection
                    activity = sum(abs(b) for b in data) / len(data)
                    if activity > 0.1:
                        bar_length = min(int(activity), 50)
                        bar = '█' * bar_length + '░' * (50 - bar_length)
                        print(f"\rAudio Activity: [{bar}]", end='', flush=True)
                        self.test_results['audio_activity'].append(activity)
                    else:
                        print(f"\rAudio Activity: [{'░' * 50}] (silent)", end='', flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nMonitoring interrupted")
        finally:
            proc.terminate()
            proc.wait()
            
        print("\n✅ Monitoring complete")
        
    def generate_test_tone(self):
        """Generate a test tone using paplay"""
        print("\n=== Generating Test Tone ===")
        
        # Generate a simple WAV file using sox if available
        stdout, stderr, rc = self.run_command('which sox')
        if rc == 0:
            print("Generating 1kHz test tone...")
            self.run_command('sox -n -r 48000 -c 1 test_tone.wav synth 2 sine 1000')
            
            print("Playing test tone to TRUSDX...")
            stdout, stderr, rc = self.run_command('paplay --device=TRUSDX test_tone.wav')
            if rc == 0:
                print("✅ Test tone played successfully")
            else:
                print(f"❌ Error playing test tone: {stderr}")
                
            # Clean up
            self.run_command('rm -f test_tone.wav')
        else:
            print("Sox not installed. Trying speaker-test...")
            print("Playing white noise to TRUSDX for 2 seconds...")
            self.run_command('timeout 2 speaker-test -D pulse:TRUSDX -c 1 -t wav')
            
    def check_js8call_config(self):
        """Check JS8Call configuration if possible"""
        print("\n=== JS8Call Configuration Hints ===")
        
        # Look for JS8Call config
        stdout, stderr, rc = self.run_command('ls ~/.config/JS8Call.ini 2>/dev/null')
        if rc == 0:
            print("JS8Call configuration found")
            
            # Check audio settings in config
            stdout, stderr, rc = self.run_command('grep -i "audio\\|sound" ~/.config/JS8Call.ini | head -10')
            if stdout:
                print("\nJS8Call audio settings:")
                print(stdout)
        else:
            print("JS8Call configuration not found at ~/.config/JS8Call.ini")
            
        print("\nEnsure JS8Call is configured with:")
        print("  - Audio Input: TRUSDX.monitor")
        print("  - Audio Output: TRUSDX")
        
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("AUDIO ROUTING TEST SUMMARY")
        print("="*60)
        
        print(f"TRUSDX sink exists: {'✅' if self.test_results['trusdx_sink_exists'] else '❌'}")
        print(f"TRUSDX.monitor exists: {'✅' if self.test_results['trusdx_monitor_exists'] else '❌'}")
        
        if self.test_results['pw_connections']:
            print(f"\nPipeWire connections found: {len(self.test_results['pw_connections'])}")
            for conn in self.test_results['pw_connections']:
                print(f"  {conn['output']} -> {conn['input']}")
        else:
            print("\n⚠️  No PipeWire connections found between JS8Call and TRUSDX")
            
        if self.test_results['active_streams']:
            print(f"\nActive audio streams: {len(self.test_results['active_streams'])}")
        else:
            print("\n⚠️  No active audio streams found")
            
        if self.test_results['audio_activity']:
            print(f"\nAudio activity detected: ✅ (peak: {max(self.test_results['audio_activity']):.2f})")
        else:
            print("\nAudio activity detected: ❌")
            
        print("\n" + "="*60)
        
        # Recommendations
        print("\nRECOMMENDATIONS:")
        
        if not self.test_results['trusdx_sink_exists']:
            print("1. Ensure the TruSDX driver is running")
            
        if not self.test_results['audio_activity'] and self.test_results['trusdx_monitor_exists']:
            print("2. Transmit a message in JS8Call during monitoring")
            
        if not self.test_results['pw_connections']:
            print("3. Check JS8Call audio settings and ensure it's running")
            print("4. You may need to manually connect audio using:")
            print("   pw-link JS8Call:output_FL TRUSDX:playback_FL")
            print("   pw-link TRUSDX.monitor:capture_FL JS8Call:input_FL")
            
    def run_interactive(self):
        """Run tests interactively"""
        print("TruSDX Audio Routing Test")
        print("========================")
        print(f"Started at: {datetime.now()}")
        
        # Basic checks
        self.check_audio_devices()
        self.check_pipewire_connections()
        self.check_active_streams()
        self.check_js8call_config()
        
        # Interactive tests
        print("\n" + "-"*60)
        response = input("\nMonitor TRUSDX.monitor for audio activity? (y/n): ")
        if response.lower() == 'y':
            duration = input("How many seconds to monitor? (default 10): ")
            try:
                duration = int(duration) if duration else 10
            except:
                duration = 10
            self.monitor_audio_levels(duration)
            
        response = input("\nGenerate test tone on TRUSDX output? (y/n): ")
        if response.lower() == 'y':
            self.generate_test_tone()
            
        # Final summary
        self.print_summary()
        

if __name__ == "__main__":
    tester = SimpleAudioRoutingTester()
    tester.run_interactive()
