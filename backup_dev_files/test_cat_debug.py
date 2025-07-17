#!/usr/bin/env python3
"""
Debug script to test CAT commands manually
"""

import sys
import os

# Add the parent directory to sys.path  
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("trusdx", "trusdx-txrx-AI.py")
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

# Mock serial
class MockSer:
    def write(self, data):
        print(f"  [HARDWARE] Would send to radio: {data}")
    def flush(self):
        pass

mock_ser = MockSer()

# Test commands
test_commands = [
    b'ID;',
    b'IF;',
    b'FR;',
    b'FT;', 
    b'FA;',
    b'FB;',
    b'V;',
    b'AI;',
    b'MD;',
    b'FA00014074000;',
    b'FR0;',
    b'FR1;',
    b'FT0;',
    b'FT1;',
    b'TX;',
    b'RX;',
    b'AI2;',
    b'VD;',  # Unimplemented command test
]

print("=== CAT Command Debug Test ===\n")

for cmd in test_commands:
    print(f"Command: {cmd.decode('utf-8').strip()}")
    response = trusdx.handle_ts480_command(cmd, mock_ser)
    
    if response:
        resp_str = response.decode('utf-8')
        print(f"  Response: {resp_str.strip()}")
        
        # Special analysis for IF command
        if cmd == b'IF;':
            print(f"  IF Response Analysis:")
            print(f"    Total length: {len(resp_str)} chars")
            print(f"    Content length: {len(resp_str) - 3} chars (excluding 'IF' and ';')")
            
            if len(resp_str) >= 40:
                content = resp_str[2:-1]  # Remove IF and ;
                print(f"    Frequency: {content[0:11]} ({float(content[0:11])/1000000:.3f} MHz)")
                print(f"    RIT/XIT: {content[11:16]}")
                print(f"    RIT: {content[16]}")
                print(f"    XIT: {content[17]}")
                print(f"    Bank: {content[18:20]}")
                print(f"    RX/TX: {content[20]}")
                print(f"    Mode: {content[21]}")
                print(f"    VFO: {content[22]} ({'A' if content[22] == '0' else 'B'})")
                print(f"    Split: {content[24]}")
                
                # Check byte 38 position (0-indexed)
                # IF=2 chars, then position 22 in content is byte 24 overall, so byte 38 would be at position 36 in content
                if len(content) >= 37:
                    print(f"    Byte at position 38: content[36] = '{content[36] if len(content) > 36 else 'N/A'}'")
    else:
        print(f"  Response: None (forwarded to hardware)")
    
    # Show state changes for certain commands
    if cmd.startswith(b'F'):
        print(f"  State: curr_vfo={trusdx.radio_state['curr_vfo']}, "
              f"rx_vfo={trusdx.radio_state['rx_vfo']}, "
              f"tx_vfo={trusdx.radio_state['tx_vfo']}")
    
    print()

print("\n=== Summary ===")
print(f"Final VFO state: {trusdx.radio_state['curr_vfo']}")
print(f"VFO A freq: {float(trusdx.radio_state['vfo_a_freq'])/1000000:.3f} MHz")
print(f"VFO B freq: {float(trusdx.radio_state['vfo_b_freq'])/1000000:.3f} MHz")
