#!/usr/bin/env python3
"""
Test rigctld response parsing to debug the IF command issue.
"""

import subprocess
import time
import threading
import socket
import sys

def start_rigctld():
    """Start rigctld in the background."""
    cmd = [
        'rigctld',
        '-m', '2028',  # Kenwood TS-480
        '-r', '/tmp/trusdx_cat',
        '-s', '115200',
        '-t', '4532',
        '-vvv'
    ]
    
    print(f"Starting rigctld: {' '.join(cmd)}")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    return process

def test_rigctld_commands():
    """Test commands via rigctld."""
    time.sleep(3)  # Give rigctld time to start
    
    try:
        # Connect to rigctld
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 4532))
        
        # Test commands
        commands = [
            'f',        # Get frequency
            'F 7074000', # Set frequency
            'f',        # Get frequency again
            'm',        # Get mode
            'v',        # Get VFO
        ]
        
        for cmd in commands:
            print(f"\nSending to rigctld: {cmd}")
            sock.send(f'{cmd}\n'.encode())
            
            # Read response
            response = sock.recv(1024)
            print(f"rigctld response: {response}")
            
            time.sleep(0.5)
        
        sock.close()
        
    except Exception as e:
        print(f"Error testing rigctld: {e}")

def monitor_rigctld_output(process):
    """Monitor rigctld output for debugging."""
    while True:
        line = process.stderr.readline()
        if not line:
            break
        print(f"rigctld stderr: {line.strip()}")

if __name__ == '__main__':
    print("rigctld Test")
    print("=" * 50)
    
    # Start rigctld
    process = start_rigctld()
    
    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_rigctld_output, args=(process,))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    try:
        # Test commands
        test_rigctld_commands()
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        # Stop rigctld
        process.terminate()
        process.wait()
        print("rigctld stopped")
