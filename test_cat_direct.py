#!/usr/bin/env python3
"""
Direct CAT port test script to debug communication issues.
"""

import serial
import time
import sys

def test_cat_port():
    """Test direct communication with CAT port."""
    cat_port = "/tmp/trusdx_cat"
    
    try:
        print(f"Testing CAT port: {cat_port}")
        
        # Open the CAT port
        with serial.Serial(cat_port, 115200, timeout=2) as ser:
            print(f"Opened CAT port successfully")
            
            # Test commands
            commands = [
                b'ID;',
                b'AI;',
                b'IF;',
                b'FA;',
                b'MD;',
                b'FR;',
                b'FT;',
            ]
            
            for cmd in commands:
                try:
                    print(f"\nSending: {cmd.decode('utf-8')}")
                    
                    # Clear any existing data
                    if ser.in_waiting > 0:
                        old_data = ser.read(ser.in_waiting)
                        print(f"Cleared old data: {old_data}")
                    
                    # Send command
                    ser.write(cmd)
                    ser.flush()
                    
                    # Wait for response
                    time.sleep(0.1)
                    
                    # Read response
                    if ser.in_waiting > 0:
                        response = ser.read(ser.in_waiting)
                        print(f"Response: {response}")
                        try:
                            response_str = response.decode('utf-8')
                            print(f"Response (decoded): {response_str}")
                        except:
                            print(f"Response (hex): {response.hex()}")
                    else:
                        print("No response received")
                        
                except Exception as e:
                    print(f"Error with command {cmd}: {e}")
                    
    except Exception as e:
        print(f"Error opening CAT port: {e}")
        return False
    
    return True

def test_cat_with_rigctld():
    """Test CAT port with rigctld."""
    try:
        import subprocess
        
        print("\nTesting with rigctld...")
        
        # Start rigctld
        cmd = [
            'rigctld',
            '-m', '2014',  # Kenwood TS-480
            '-r', '/tmp/trusdx_cat',
            '-s', '115200',
            '-vvv'  # Very verbose
        ]
        
        print(f"Starting rigctld: {' '.join(cmd)}")
        
        # Start rigctld in background
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait a bit for it to start
        time.sleep(2)
        
        # Check if it's running
        if process.poll() is None:
            print("rigctld started successfully")
            
            # Test some commands via rigctld
            try:
                # Connect to rigctld
                with serial.Serial('localhost', 4532, timeout=2) as rig:
                    # Test get frequency
                    rig.write(b'f\n')
                    response = rig.read(100)
                    print(f"rigctld frequency response: {response}")
                    
            except Exception as e:
                print(f"Error connecting to rigctld: {e}")
            
            # Stop rigctld
            process.terminate()
            process.wait()
        else:
            # rigctld failed to start
            stdout, stderr = process.communicate()
            print(f"rigctld failed to start:")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            
    except Exception as e:
        print(f"Error testing rigctld: {e}")

if __name__ == '__main__':
    print("CAT Port Direct Test")
    print("=" * 50)
    
    if test_cat_port():
        print("\nDirect CAT test completed")
    else:
        print("\nDirect CAT test failed")
        sys.exit(1)
    
    # Uncomment to test with rigctld
    # test_cat_with_rigctld()
