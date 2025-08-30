#!/usr/bin/env python3
"""
Simple CAT connection test to verify communication with truSDX driver
"""

import serial
import time

def test_cat_connection():
    """Test basic CAT connectivity"""
    print("=== CAT Connection Test ===")
    
    try:
        # Open connection to CAT port
        ser = serial.Serial('/tmp/trusdx_cat', 115200, timeout=1)
        print(f"✓ Connected to /tmp/trusdx_cat")
        
        # Test commands
        test_cmds = [
            ("ID;", "Get radio ID"),
            ("IF;", "Get radio status"),
            ("FA;", "Get VFO A frequency"),
            ("MD;", "Get mode"),
            ("FR;", "Get RX VFO"),
            ("FT;", "Get TX VFO"),
            ("AI;", "Get AI mode"),
            ("FW;", "Get filter width"),
        ]
        
        for cmd, desc in test_cmds:
            print(f"\n{desc}:")
            print(f"  Sending: {cmd}")
            
            # Clear any pending data
            ser.reset_input_buffer()
            
            # Send command
            ser.write(cmd.encode())
            ser.flush()
            
            # Wait for response
            time.sleep(0.1)
            
            # Read response
            response = ser.read(100)
            if response:
                print(f"  Response: {response.decode('utf-8', errors='ignore').strip()}")
                
                # Analyze IF response
                if cmd == "IF;" and len(response) >= 40:
                    resp_str = response.decode('utf-8')
                    if resp_str.startswith('IF'):
                        content = resp_str[2:-1]
                        freq = content[0:11]
                        freq_mhz = float(freq) / 1000000.0
                        mode = content[21]
                        vfo = content[22]
                        print(f"  Analysis:")
                        print(f"    Frequency: {freq_mhz:.3f} MHz")
                        print(f"    Mode: {mode} ({'LSB' if mode == '1' else 'USB' if mode == '2' else 'Other'})")
                        print(f"    VFO: {vfo} ({'A' if vfo == '0' else 'B'})")
            else:
                print(f"  No response!")
        
        # Test frequency setting
        print("\n\nTesting frequency change:")
        print("  Setting VFO A to 7.074 MHz...")
        ser.write(b"FA00007074000;")
        ser.flush()
        time.sleep(0.1)
        
        response = ser.read(100)
        if response:
            print(f"  Response: {response.decode('utf-8', errors='ignore').strip()}")
        
        # Verify frequency
        print("  Verifying frequency...")
        ser.write(b"FA;")
        ser.flush()
        time.sleep(0.1)
        
        response = ser.read(100)
        if response:
            print(f"  Response: {response.decode('utf-8', errors='ignore').strip()}")
        
        ser.close()
        print("\n✓ CAT connection test completed successfully!")
        
    except serial.SerialException as e:
        print(f"✗ Serial error: {e}")
        print("\nMake sure:")
        print("  1. trusdx-txrx-AI.py is running")
        print("  2. /tmp/trusdx_cat exists")
        print("  3. No other program is using the CAT port")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_cat_connection()
