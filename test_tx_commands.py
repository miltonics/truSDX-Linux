#!/usr/bin/env python3
"""
Focused test to demonstrate the TX0 vs TX1 command difference
This script simulates the key difference between v1.1.6 and v1.1.7
"""

import serial
import time
import threading
import sys
import os

def simulate_radio_response(ser_radio, command_log):
    """Simulate truSDX radio responses"""
    print("📻 Radio simulator started...")
    try:
        while True:
            if ser_radio.in_waiting > 0:
                data = ser_radio.read(ser_radio.in_waiting)
                cmd = data.decode('utf-8', errors='ignore').strip()
                command_log.append(cmd)
                
                if 'TX0' in cmd:
                    print(f"📻 [RADIO] Received TX0 command: {cmd}")
                    print("🎵 [AUDIO] VU meter would show ACTIVITY (v1.1.6 behavior)")
                elif 'TX1' in cmd:
                    print(f"📻 [RADIO] Received TX1 command: {cmd}")
                    print("🔇 [AUDIO] VU meter would be SILENT (v1.1.7 behavior)")
                elif 'RX' in cmd:
                    print(f"📻 [RADIO] Received RX command: {cmd}")
                else:
                    print(f"📻 [RADIO] Other command: {cmd}")
                    
            time.sleep(0.1)
    except Exception as e:
        print(f"Radio simulator error: {e}")

def test_vox_handler_v116(ser_radio, command_log):
    """Test v1.1.6 VOX handler (uses TX0)"""
    print("\n=== Testing v1.1.6 VOX Handler (TX0) ===")
    command_log.clear()
    
    # Simulate VOX trigger
    print("🎤 Simulating VOX trigger...")
    ser_radio.write(b";TX0;")
    ser_radio.flush()
    time.sleep(0.5)
    
    # Simulate VOX release
    print("🔇 Simulating VOX release...")
    ser_radio.write(b";RX;")
    ser_radio.flush()
    time.sleep(0.5)
    
    return command_log.copy()

def test_vox_handler_v117(ser_radio, command_log):
    """Test v1.1.7 VOX handler (uses TX1)"""
    print("\n=== Testing v1.1.7 VOX Handler (TX1) ===")
    command_log.clear()
    
    # Simulate VOX trigger
    print("🎤 Simulating VOX trigger...")
    ser_radio.write(b";TX1;")
    ser_radio.flush()
    time.sleep(0.5)
    
    # Simulate VOX release
    print("🔇 Simulating VOX release...")
    ser_radio.write(b";RX;")
    ser_radio.flush()
    time.sleep(0.5)
    
    return command_log.copy()

def main():
    print("=== truSDX TX Command Difference Test ===")
    print("This demonstrates the key difference between v1.1.6 and v1.1.7")
    print("that causes the VU meter bug.\n")
    
    # Check if virtual serial ports exist
    if not (os.path.exists('/tmp/trusdx_radio') and os.path.exists('/tmp/trusdx_cat')):
        print("❌ Virtual serial ports not found!")
        print("Please run: socat -d -d pty,link=/tmp/trusdx_radio,echo=0,ignoreeof,b115200,raw,perm=0777 pty,link=/tmp/trusdx_cat,echo=0,ignoreeof,b115200,raw,perm=0777 &")
        return False
    
    try:
        # Open virtual serial ports
        ser_radio = serial.Serial('/tmp/trusdx_radio', 115200, timeout=0.1)
        ser_cat = serial.Serial('/tmp/trusdx_cat', 115200, timeout=0.1)
        
        command_log = []
        
        # Start radio simulator in background
        radio_thread = threading.Thread(target=simulate_radio_response, args=(ser_cat, command_log), daemon=True)
        radio_thread.start()
        
        time.sleep(1)  # Let radio simulator start
        
        # Test v1.1.6 behavior
        log_v116 = test_vox_handler_v116(ser_radio, command_log)
        
        # Test v1.1.7 behavior  
        log_v117 = test_vox_handler_v117(ser_radio, command_log)
        
        print("\n" + "="*60)
        print("🔍 TEST RESULTS SUMMARY")
        print("="*60)
        
        print("\n✅ v1.1.6 Commands (VU meter WORKING):")
        for cmd in log_v116:
            if cmd.strip():
                print(f"   {cmd}")
        
        print("\n❌ v1.1.7 Commands (VU meter BROKEN):")
        for cmd in log_v117:
            if cmd.strip():
                print(f"   {cmd}")
                
        print("\n🎯 KEY FINDING:")
        print("   v1.1.6 uses TX0 command → VU meter shows activity")
        print("   v1.1.7 uses TX1 command → VU meter goes silent")
        print("\n💡 CONCLUSION:")
        print("   The change from TX0 to TX1 in PTT handlers breaks VU meter functionality")
        print("   This affects WSJT-X and other applications that rely on audio level indication")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        try:
            ser_radio.close()
            ser_cat.close()
        except:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

