#!/usr/bin/env python3
"""
Quick VU Meter Test
This script tests if the VU meter functionality is working
"""

import pyaudio
import array
import math
import time

def test_vu_meter():
    print("Testing VU meter functionality...")
    
    try:
        # Initialize PyAudio (same configuration as truSDX script)
        p = pyaudio.PyAudio()
        
        # Open input stream (same as truSDX)
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=11520,  # Same rate as truSDX
            input=True,
            frames_per_buffer=512
        )
        
        print("✅ Audio stream opened successfully")
        print("🎧 Listening for audio... (10 seconds)")
        print("VU Meter levels:")
        
        # Test for 10 seconds
        for i in range(100):  # 10 seconds at 0.1s intervals
            try:
                # Read audio data
                data = stream.read(512, exception_on_overflow=False)
                arr = array.array('h', data)
                
                # Calculate RMS level (same as truSDX VU meter)
                if len(arr) > 0:
                    rms = math.sqrt(sum(x*x for x in arr) / len(arr))
                    level = min(int(rms / 1000), 20)  # Scale to 0-20
                    
                    # Display VU meter
                    bar = "█" * level + "░" * (20 - level)
                    print(f"\r[{bar}] {level:2d}/20 RMS:{rms:6.0f}", end="", flush=True)
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\n❌ Error reading audio: {e}")
                break
        
        print("\n✅ VU meter test completed")
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        return True
        
    except Exception as e:
        print(f"❌ VU meter test failed: {e}")
        return False

if __name__ == "__main__":
    test_vu_meter()
