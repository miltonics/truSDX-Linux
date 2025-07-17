#!/usr/bin/env python3
"""
Test CAT driver for testing rigctl commands without hardware
Creates a virtual CAT port and handles TS-480 commands
"""

import os
import sys
import time
import threading
import serial
from unittest.mock import MagicMock

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("trusdx", "trusdx-txrx-AI.py")
trusdx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trusdx)

class TestCATDriver:
    def __init__(self):
        self.running = False
        self.master1 = None
        self.master2 = None
        self.cat_port = '/tmp/trusdx_cat'
        
        # Mock the config
        trusdx.config = {
            'verbose': True,
            'unmute': False
        }
        
        # Initialize radio state
        trusdx.radio_state = {
            'vfo_a_freq': '00014074000',  # 14.074 MHz
            'vfo_b_freq': '00014074000',  # 14.074 MHz
            'mode': '2',                  # USB
            'rx_vfo': '0',               # VFO A
            'tx_vfo': '0',               # VFO A
            'split': '0',                # Split off
            'rit': '0',                  # RIT off
            'xit': '0',                  # XIT off
            'rit_offset': '00000',       # No offset
            'power_on': '1',             # Power on
            'ai_mode': '2'               # Auto info on
        }
        
        # Mock serial port
        self.mock_ser = MagicMock()
        
        # Mock log function
        trusdx.log = lambda msg, level='INFO': print(f"[{level}] {msg}")
        
    def start(self):
        """Start the test CAT driver"""
        try:
            print("Starting Test CAT Driver...")
            
            # Create PTY pair
            master1, slave1 = os.openpty()
            master2, slave2 = os.openpty()
            
            # Open master ends
            self.master1 = os.fdopen(master1, 'rb+', 0)
            self.master2 = os.fdopen(master2, 'rb+', 0)
            
            # Get slave device names
            cat_serial_dev = os.ttyname(slave1)
            loopback_serial_dev = os.ttyname(slave2)
            
            # Create persistent symlink
            if os.path.exists(self.cat_port):
                os.remove(self.cat_port)
            os.symlink(cat_serial_dev, self.cat_port)
            
            print(f"Created CAT port: {self.cat_port} -> {cat_serial_dev}")
            print(f"Loopback port: {loopback_serial_dev}")
            
            # Start echo threads
            self.running = True
            threading.Thread(target=self.pty_echo, args=(self.master1, self.master2), daemon=True).start()
            threading.Thread(target=self.pty_echo, args=(self.master2, self.master1), daemon=True).start()
            
            # Start command handler
            threading.Thread(target=self.command_handler, daemon=True).start()
            
            print("Test CAT Driver ready!")
            print(f"Test with: rigctl -m 2028 -r {self.cat_port} <command>")
            print("Commands to test:")
            print("  rigctl -m 2028 -r /tmp/trusdx_cat V")
            print("  rigctl -m 2028 -r /tmp/trusdx_cat f")
            print("  rigctl -m 2028 -r /tmp/trusdx_cat vfo")
            print("  rigctl -m 2028 -r /tmp/trusdx_cat i")
            print("")
            
            return True
            
        except Exception as e:
            print(f"Error starting CAT driver: {e}")
            return False
    
    def pty_echo(self, fd1, fd2):
        """Echo data between PTY ends"""
        try:
            while self.running:
                try:
                    data = fd1.read(1)
                    if data:
                        fd2.write(data)
                        fd2.flush()
                except (OSError, IOError):
                    break
                except Exception as e:
                    print(f"PTY echo error: {e}")
                    break
        except Exception as e:
            print(f"PTY echo thread error: {e}")
    
    def command_handler(self):
        """Handle incoming CAT commands"""
        try:
            buffer = b''
            while self.running:
                try:
                    # Read from master1 (commands from rigctl)
                    data = self.master1.read(1)
                    if data:
                        buffer += data
                        print(f"Received: {repr(data)}")
                        
                        # Look for complete commands ending with ;
                        if b';' in buffer:
                            # Process all complete commands
                            commands = buffer.split(b';')
                            buffer = commands[-1]  # Keep incomplete command
                            
                            for cmd in commands[:-1]:
                                if cmd.strip():
                                    self.process_command(cmd + b';')
                
                except (OSError, IOError):
                    break
                except Exception as e:
                    print(f"Command handler error: {e}")
                    break
                    
        except Exception as e:
            print(f"Command handler thread error: {e}")
    
    def process_command(self, command):
        """Process a CAT command"""
        try:
            print(f"Processing command: {command}")
            
            # Handle the command using the trusdx handler
            response = trusdx.handle_ts480_command(command, self.mock_ser)
            
            if response:
                print(f"Sending response: {response}")
                # Send response back through master1
                self.master1.write(response)
                self.master1.flush()
            else:
                print("No response (forwarded to radio)")
                
        except Exception as e:
            print(f"Error processing command {command}: {e}")
    
    def stop(self):
        """Stop the test CAT driver"""
        self.running = False
        
        if self.master1:
            self.master1.close()
        if self.master2:
            self.master2.close()
        
        if os.path.exists(self.cat_port):
            os.remove(self.cat_port)
        
        print("Test CAT Driver stopped")

def main():
    driver = TestCATDriver()
    
    if driver.start():
        try:
            print("Press Ctrl+C to stop...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            driver.stop()
    else:
        print("Failed to start CAT driver")

if __name__ == '__main__':
    main()
