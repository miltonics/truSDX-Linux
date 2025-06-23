#!/usr/bin/env python3
"""
Simple VU meter test script to monitor audio levels from TRUSDX sink
This simulates what WSJT-X would see for audio levels
"""

import pyaudio
import numpy as np
import time
import threading
import sys

def find_audio_device(name):
    """Find audio device by name"""
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if name.lower() in info['name'].lower():
            print(f"Found audio device: {info['name']} (index {i})")
            return i
    return -1

def vu_meter_monitor(device_index, duration=30):
    """Monitor audio levels and display VU meter"""
    p = pyaudio.PyAudio()
    
    # Audio parameters
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 48000
    
    try:
        stream = p.open(format=format,
                       channels=channels,
                       rate=rate,
                       input=True,
                       input_device_index=device_index,
                       frames_per_buffer=chunk)
        
        print(f"Monitoring audio levels for {duration} seconds...")
        print("VU Meter (0-100): ", end="", flush=True)
        
        start_time = time.time()
        max_level = 0
        sample_count = 0
        
        while time.time() - start_time < duration:
            try:
                data = stream.read(chunk, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate RMS level
                rms = np.sqrt(np.mean(audio_data**2))
                
                # Convert to dB and normalize to 0-100 scale
                if rms > 0:
                    db = 20 * np.log10(rms / 32768.0)  # 32768 is max for 16-bit
                    level = max(0, min(100, (db + 60) * 100 / 60))  # Normalize -60dB to 0dB as 0-100
                else:
                    level = 0
                
                max_level = max(max_level, level)
                sample_count += 1
                
                # Display VU meter every 10 samples
                if sample_count % 10 == 0:
                    bar_length = 50
                    filled_length = int(bar_length * level / 100)
                    bar = '█' * filled_length + '░' * (bar_length - filled_length)
                    print(f"\r[{bar}] {level:5.1f}% (max: {max_level:5.1f}%)", end="", flush=True)
                
            except Exception as e:
                print(f"\nError reading audio: {e}")
                break
                
        print(f"\nMonitoring complete. Maximum level detected: {max_level:.1f}%")
        
        if max_level < 1.0:
            print("⚠️  WARNING: Very low or no audio detected - VU meter appears silent!")
            return False
        else:
            print("✅ Audio levels detected - VU meter is working!")
            return True
            
    except Exception as e:
        print(f"Error opening audio stream: {e}")
        return False
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except:
            pass
        p.terminate()

def main():
    print("=== truSDX VU Meter Test ===")
    
    # Find TRUSDX audio device
    device_index = find_audio_device("TRUSDX")
    if device_index == -1:
        print("❌ TRUSDX audio device not found!")
        print("Available audio devices:")
        p = pyaudio.PyAudio()
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            print(f"  {i}: {info['name']}")
        p.terminate()
        return False
    
    # Monitor VU meter
    return vu_meter_monitor(device_index)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

