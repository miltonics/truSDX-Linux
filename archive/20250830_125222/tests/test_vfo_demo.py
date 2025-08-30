#!/usr/bin/env python3
"""
Demo script to test VFO state machine using pyserial's loop:// functionality
This simulates a typical Hamlib<->truSDX interaction
"""

import serial
import time
import threading

def simulate_hamlib_client(port_name):
    """Simulate Hamlib client sending CAT commands"""
    # Open serial port
    ser = serial.serial_for_url(port_name, baudrate=115200, timeout=1)
    
    print("=== Hamlib Client Simulation ===")
    
    # Test sequence
    commands = [
        ("ID;", "Get radio ID"),
        ("IF;", "Get initial status"),
        ("FR;", "Get RX VFO"),
        ("FT;", "Get TX VFO"),
        ("FA;", "Get VFO A frequency"),
        ("FB;", "Get VFO B frequency"),
        ("FA00021074000;", "Set VFO A to 21.074 MHz"),
        ("FA;", "Confirm VFO A frequency"),
        ("FB00028074000;", "Set VFO B to 28.074 MHz"),
        ("FB;", "Confirm VFO B frequency"),
        ("FR0;", "Set RX to VFO A"),
        ("FT1;", "Set TX to VFO B"),
        ("IF;", "Check IF response - should show VFO B active"),
        ("FR1;", "Set RX to VFO B"),
        ("IF;", "Check IF response - should show VFO B"),
        ("TX;", "Query TX status"),
        ("AI0;", "Set AI mode off"),
        ("AI2;", "Set AI mode on"),
        ("AI;", "Query AI mode"),
        ("VD;", "Test unimplemented command"),
        ("XO;", "Test another unimplemented command")
    ]
    
    for cmd, desc in commands:
        print(f"\n[CLIENT] {desc}")
        print(f"[CLIENT] Sending: {cmd}")
        ser.write(cmd.encode())
        ser.flush()
        
        # Wait for response
        time.sleep(0.1)
        response = ser.read(100)
        if response:
            print(f"[CLIENT] Received: {response.decode('utf-8', errors='ignore').strip()}")
        else:
            print(f"[CLIENT] No response")
        
        time.sleep(0.5)
    
    ser.close()
    print("\n=== Hamlib Client Simulation Complete ===")

def simulate_trusdx_server(port_name):
    """Simulate truSDX server handling CAT commands"""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Import trusdx module
    import importlib.util
    spec = importlib.util.spec_from_file_location("trusdx", 
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        "trusdx-txrx-AI.py"))
    trusdx = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trusdx)
    
    # Initialize radio state
    trusdx.radio_state = {
        'vfo_a_freq': '00007074000',
        'vfo_b_freq': '00014074000',
        'mode': '2',
        'rx_vfo': '0',
        'tx_vfo': '0',
        'curr_vfo': 'A',
        'split': '0',
        'rit': '0',
        'xit': '0',
        'rit_offset': '00000',
        'power_on': '1',
        'ai_mode': '0'
    }
    
    trusdx.status = [False, False, True, True, False, False]
    trusdx.config = {'verbose': False, 'unmute': False}
    trusdx.log = lambda msg, level='INFO': None  # Disable logging
    
    # Open serial port
    ser = serial.serial_for_url(port_name, baudrate=115200, timeout=0.1)
    trusdx.handle_ts480_command = lambda cmd, ser: trusdx.handle_ts480_command(cmd, ser)
    
    print("=== truSDX Server Simulation ===")
    print("Initial state:")
    print(f"  VFO A: {float(trusdx.radio_state['vfo_a_freq'])/1000000:.3f} MHz")
    print(f"  VFO B: {float(trusdx.radio_state['vfo_b_freq'])/1000000:.3f} MHz")
    print(f"  Current VFO: {trusdx.radio_state['curr_vfo']}")
    
    buffer = b''
    
    while True:
        try:
            # Read data
            data = ser.read(100)
            if not data:
                continue
                
            buffer += data
            
            # Process complete commands
            while b';' in buffer:
                idx = buffer.find(b';')
                cmd = buffer[:idx + 1]
                buffer = buffer[idx + 1:]
                
                print(f"\n[SERVER] Received: {cmd.decode('utf-8', errors='ignore').strip()}")
                
                # Handle command
                response = trusdx.handle_ts480_command(cmd, mock_ser)
                
                if response:
                    print(f"[SERVER] Sending: {response.decode('utf-8', errors='ignore').strip()}")
                    ser.write(response)
                    ser.flush()
                else:
                    print(f"[SERVER] Command forwarded to hardware (no emulated response)")
                
                # Print state changes for certain commands
                if cmd.startswith(b'FA') or cmd.startswith(b'FB'):
                    print(f"[SERVER] State: VFO A={float(trusdx.radio_state['vfo_a_freq'])/1000000:.3f} MHz, "
                          f"VFO B={float(trusdx.radio_state['vfo_b_freq'])/1000000:.3f} MHz, "
                          f"Current={trusdx.radio_state['curr_vfo']}")
                elif cmd.startswith(b'FR') or cmd.startswith(b'FT'):
                    print(f"[SERVER] State: RX VFO={trusdx.radio_state['rx_vfo']}, "
                          f"TX VFO={trusdx.radio_state['tx_vfo']}, "
                          f"Current={trusdx.radio_state['curr_vfo']}")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            if "read operation" in str(e):
                break
            print(f"[SERVER] Error: {e}")
            continue
    
    ser.close()
    print("\n=== truSDX Server Simulation Complete ===")

def main():
    """Run the VFO state machine demo"""
    print("VFO State Machine Demo using pyserial loop://")
    print("=" * 50)
    
    # Create virtual serial port pair using loop://
    port_url = "loop://"
    
    # Start server thread
    server_thread = threading.Thread(target=simulate_trusdx_server, args=(port_url,))
    server_thread.daemon = True
    server_thread.start()
    
    # Give server time to start
    time.sleep(1)
    
    # Run client
    simulate_hamlib_client(port_url)
    
    # Give server time to finish
    time.sleep(1)
    
    print("\nDemo complete!")

if __name__ == "__main__":
    main()
