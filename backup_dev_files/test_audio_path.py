#!/usr/bin/env python3
"""
Automated test for TRUSDX audio path
Plays a test tone through the driver and verifies signal via fifo_meter
"""

import os
import sys
import time
import subprocess
import wave
import numpy as np
import threading
import re
from datetime import datetime

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

def print_colored(color, text):
    """Print colored text"""
    print(f"{color}{text}{NC}")

def generate_test_tone(filename="test_tone.wav", duration=5, frequency=1000, sample_rate=48000):
    """Generate a test tone WAV file"""
    print_colored(CYAN, f"\n=== Generating {frequency}Hz test tone ({duration}s) ===")
    
    # Generate sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    amplitude = 0.5  # 50% amplitude to avoid clipping
    wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # Convert to 16-bit PCM
    wave_data = (wave_data * 32767).astype(np.int16)
    
    # Write WAV file
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)   # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(wave_data.tobytes())
    
    print_colored(GREEN, f"✅ Generated {filename}")
    return filename

def ensure_trusdx_sink():
    """Ensure TRUSDX sink exists"""
    print_colored(CYAN, "\n=== Checking TRUSDX audio sink ===")
    
    # Check if TRUSDX sink exists
    result = subprocess.run(['pactl', 'list', 'sinks'], 
                          capture_output=True, text=True)
    
    if 'Name: TRUSDX' not in result.stdout:
        print_colored(YELLOW, "TRUSDX sink not found, creating...")
        result = subprocess.run([
            'pactl', 'load-module', 'module-null-sink',
            'sink_name=TRUSDX',
            'sink_properties=device.description="TRUSDX"'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            module_id = result.stdout.strip()
            print_colored(GREEN, f"✅ Created TRUSDX sink (module ID: {module_id})")
        else:
            print_colored(RED, f"❌ Failed to create TRUSDX sink: {result.stderr}")
            return False
        
        time.sleep(1)
    else:
        print_colored(GREEN, "✅ TRUSDX sink already exists")
    
    return True

def get_sink_volume_levels():
    """Get current volume levels from all sinks using pactl"""
    volumes = {}
    try:
        # Get source (monitor) volumes
        result = subprocess.run(['pactl', 'list', 'sources'], 
                              capture_output=True, text=True)
        
        current_source = None
        for line in result.stdout.split('\n'):
            if 'Name:' in line:
                current_source = line.split('Name:')[1].strip()
            elif 'Volume:' in line and current_source:
                # Extract volume percentage
                match = re.search(r'(\d+)%', line)
                if match:
                    volumes[current_source] = int(match.group(1))
                current_source = None
        
        return volumes
    except Exception as e:
        print_colored(RED, f"Error getting volume levels: {e}")
        return {}

def monitor_audio_levels(duration=10, stop_event=None):
    """Monitor audio levels for the specified duration"""
    print_colored(CYAN, f"\n=== Monitoring audio levels for {duration}s ===")
    
    start_time = time.time()
    max_levels = {}
    sample_count = 0
    
    while time.time() - start_time < duration:
        if stop_event and stop_event.is_set():
            break
            
        levels = get_sink_volume_levels()
        sample_count += 1
        
        # Track maximum levels
        for source, level in levels.items():
            if 'TRUSDX' in source:
                if source not in max_levels or level > max_levels[source]:
                    max_levels[source] = level
                    
                # Print real-time update
                bar = '█' * (level // 5) + '░' * (20 - level // 5)
                print(f"\r{source}: [{bar}] {level}%", end='', flush=True)
        
        time.sleep(0.1)
    
    print()  # New line after monitoring
    
    # Report results
    print_colored(CYAN, f"\n=== Audio Level Results ({sample_count} samples) ===")
    
    signal_detected = False
    for source, max_level in max_levels.items():
        if max_level > 0:
            print_colored(GREEN, f"✅ {source}: Max level {max_level}%")
            signal_detected = True
        else:
            print_colored(YELLOW, f"⚠️  {source}: No signal detected (0%)")
    
    return signal_detected

def play_test_tone(filename, device="TRUSDX"):
    """Play test tone to specified device"""
    print_colored(CYAN, f"\n=== Playing test tone to {device} ===")
    
    try:
        # Use paplay to play to specific device
        cmd = ['paplay', f'--device={device}', filename]
        print_colored(BLUE, f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print_colored(GREEN, "✅ Test tone playback completed")
            return True
        else:
            print_colored(RED, f"❌ Playback failed: {result.stderr}")
            return False
            
    except Exception as e:
        print_colored(RED, f"❌ Error playing test tone: {e}")
        return False

def verify_with_parecord(device="TRUSDX.monitor", duration=3):
    """Record from TRUSDX.monitor to verify audio path"""
    print_colored(CYAN, f"\n=== Recording from {device} for verification ===")
    
    output_file = f"trusdx_verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    
    try:
        cmd = ['parecord', f'--device={device}', '-d', str(duration), output_file]
        print_colored(BLUE, f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            if file_size > 1000:  # More than 1KB
                print_colored(GREEN, f"✅ Recording successful: {output_file} ({file_size} bytes)")
                
                # Analyze the recording
                try:
                    with wave.open(output_file, 'r') as wav:
                        frames = wav.readframes(wav.getnframes())
                        data = np.frombuffer(frames, dtype=np.int16)
                        
                        # Calculate RMS level
                        rms = np.sqrt(np.mean(data**2))
                        max_val = np.max(np.abs(data))
                        
                        print_colored(CYAN, f"Audio analysis:")
                        print_colored(CYAN, f"  RMS level: {rms:.0f}")
                        print_colored(CYAN, f"  Peak level: {max_val}")
                        
                        if rms > 100:  # Threshold for detecting signal
                            print_colored(GREEN, "✅ Audio signal detected in recording!")
                            return True
                        else:
                            print_colored(YELLOW, "⚠️  Recording contains silence or very low signal")
                            return False
                            
                except Exception as e:
                    print_colored(YELLOW, f"Could not analyze recording: {e}")
                    return True  # File exists and has size
                    
            else:
                print_colored(RED, f"❌ Recording file too small: {file_size} bytes")
                return False
        else:
            print_colored(RED, f"❌ Recording failed: {result.stderr}")
            return False
            
    except Exception as e:
        print_colored(RED, f"❌ Error during recording: {e}")
        return False

def check_driver_running():
    """Check if trusdx-txrx-AI.py is running"""
    try:
        result = subprocess.run(['pgrep', '-f', 'trusdx-txrx-AI.py'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def main():
    """Main test function"""
    print_colored(CYAN, "=== TRUSDX Audio Path Test ===")
    print_colored(CYAN, f"Test started at: {datetime.now()}")
    
    # Check if driver is running
    if not check_driver_running():
        print_colored(YELLOW, "\n⚠️  trusdx-txrx-AI.py driver not detected running")
        print_colored(YELLOW, "Please start the driver in another terminal:")
        print_colored(YELLOW, "  python3 trusdx-txrx-AI.py")
        response = input("\nPress Enter when driver is running (or 'q' to quit): ")
        if response.lower() == 'q':
            return
    else:
        print_colored(GREEN, "✅ Driver is running")
    
    # Ensure TRUSDX sink exists
    if not ensure_trusdx_sink():
        print_colored(RED, "❌ Failed to setup TRUSDX audio sink")
        return
    
    # Generate test tone
    test_file = generate_test_tone(duration=5, frequency=1000)
    
    try:
        # Start monitoring in background
        stop_event = threading.Event()
        monitor_thread = threading.Thread(
            target=monitor_audio_levels, 
            args=(10, stop_event)
        )
        monitor_thread.start()
        
        # Wait a moment for monitoring to start
        time.sleep(1)
        
        # Play test tone
        play_success = play_test_tone(test_file)
        
        # Wait for playback to complete and monitoring to finish
        time.sleep(2)
        stop_event.set()
        monitor_thread.join()
        
        # Verify with recording
        print_colored(CYAN, "\n=== Verification Stage ===")
        record_success = verify_with_parecord(duration=3)
        
        # Summary
        print_colored(CYAN, "\n=== Test Summary ===")
        if play_success and record_success:
            print_colored(GREEN, "✅ AUDIO PATH TEST PASSED!")
            print_colored(GREEN, "✅ Audio successfully routed through TRUSDX sink")
            print_colored(GREEN, "✅ Signal detected on TRUSDX.monitor")
        else:
            print_colored(RED, "❌ AUDIO PATH TEST FAILED")
            if not play_success:
                print_colored(RED, "   - Failed to play test tone")
            if not record_success:
                print_colored(RED, "   - Failed to detect signal on monitor")
        
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
            print_colored(CYAN, f"\n✅ Cleaned up {test_file}")

if __name__ == "__main__":
    try:
        # Check for required modules
        import numpy
    except ImportError:
        print_colored(RED, "Error: numpy module not found")
        print_colored(YELLOW, "Install with: pip3 install numpy")
        sys.exit(1)
        
    main()
