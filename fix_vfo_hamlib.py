#!/usr/bin/env python3
"""
Fix script for VFO handling issues with Hamlib.
Addresses the "unsupported VFO None" error by ensuring proper VFO state management.
"""

import sys
import os
import time
import subprocess
import serial
import re
from typing import Optional, Dict, Any

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def fix_if_command_response():
    """Fix the IF command response format to be Hamlib compatible."""
    
    cat_emulator_path = os.path.join(os.path.dirname(__file__), 'src', 'cat_emulator.py')
    
    if not os.path.exists(cat_emulator_path):
        print("Error: CAT emulator file not found")
        return False
    
    # Read the current file
    with open(cat_emulator_path, 'r') as f:
        content = f.read()
    
    # Fix the IF command response to ensure proper VFO field
    old_if_response = '''    def _build_if_response(self) -> bytes:
        """Build IF response for Hamlib compatibility."""
        # Hamlib expects EXACTLY 37 characters (not including IF and ;)
        # Format: IF<11-digit freq><5-digit RIT/XIT><RIT><XIT><Bank><RX/TX><Mode><VFO><Scan><Split><Tone><ToneFreq><CTCSS>;
        # Total: IF + 37 chars + ; = 40 characters
        
        # Build IF response matching real TS-480 format
        freq = self.radio_state.vfo_a_freq[:11].ljust(11, '0')     # 11 digits - frequency
        rit_xit = '00000'                                        # 5 digits - RIT/XIT offset (always 00000)
        rit = '0'                                                # 1 digit - RIT off
        xit = '0'                                                # 1 digit - XIT off
        bank = '00'                                              # 2 digits - memory bank
        rxtx = '0'                                               # 1 digit - RX/TX status (0=RX)
        mode = '2'                                               # 1 digit - mode (2=USB)
        vfo = '0'                                                # 1 digit - VFO selection (0=VFO A)
        scan = '0'                                               # 1 digit - scan status
        split = '0'                                              # 1 digit - split status
        tone = '0'                                               # 1 digit - tone status
        tone_freq = '08'                                         # 2 digits - tone frequency
        ctcss = '0'                                              # 1 digit - CTCSS status
        
        # Calculate remaining padding to reach exactly 37 characters
        # Current: 11+5+1+1+2+1+1+1+1+1+1+2+1 = 29 chars
        # Need: 37 - 29 = 8 more chars
        padding = '00000000'  # 8 digits padding
        
        # Build response with exactly 37 characters
        content = f'{freq}{rit_xit}{rit}{xit}{bank}{rxtx}{mode}{vfo}{scan}{split}{tone}{tone_freq}{ctcss}{padding}'
        
        # Ensure exactly 37 characters - this is critical for rigctld
        if len(content) != 37:
            log(f"Warning: IF content length {len(content)} != 37, fixing")
            content = content[:37].ljust(37, '0')
        
        response = f'IF{content};'
        
        # Final verification
        if len(response) != 40:
            log(f"Error: IF response length {len(response)} != 40: {response}")
            # Use fallback response
            response = f'IF{freq}00000000200000080000000;'
        
        log(f"IF response: {response} (total: {len(response)}, content: {len(content)})")
        return response.encode('utf-8')'''
    
    # New IF response that ensures proper VFO handling
    new_if_response = '''    def _build_if_response(self) -> bytes:
        """Build IF response for Hamlib compatibility with proper VFO handling."""
        # Hamlib expects EXACTLY 37 characters (not including IF and ;)
        # Format: IF<11-digit freq><5-digit RIT/XIT><RIT><XIT><Bank><RX/TX><Mode><VFO><Scan><Split><Tone><ToneFreq><CTCSS>;
        # 
        # CRITICAL: The VFO field must be set correctly for Hamlib to work
        # VFO field values: 0=VFO A, 1=VFO B, 2=Memory
        
        # Ensure frequency is properly formatted
        freq = self.radio_state.vfo_a_freq[:11].ljust(11, '0')
        
        # Build IF response components
        rit_xit_offset = '00000'                                 # 5 digits - RIT/XIT offset
        rit_status = self.radio_state.rit                        # 1 digit - RIT status
        xit_status = self.radio_state.xit                        # 1 digit - XIT status  
        memory_bank = '00'                                       # 2 digits - memory bank
        tx_rx_status = '0'                                       # 1 digit - RX/TX (0=RX, 1=TX)
        mode = self.radio_state.mode                             # 1 digit - operating mode
        current_vfo = self.radio_state.rx_vfo                    # 1 digit - CURRENT VFO (critical!)
        scan_status = '0'                                        # 1 digit - scan status
        split_status = self.radio_state.split                    # 1 digit - split status
        tone_status = '0'                                        # 1 digit - tone status
        tone_number = '08'                                       # 2 digits - tone number
        ctcss_status = '0'                                       # 1 digit - CTCSS status
        
        # Build the 37-character content string
        # Order is critical for Hamlib parsing
        content = (
            f'{freq}'           # 11 chars: frequency
            f'{rit_xit_offset}' # 5 chars: RIT/XIT offset
            f'{rit_status}'     # 1 char: RIT on/off
            f'{xit_status}'     # 1 char: XIT on/off
            f'{memory_bank}'    # 2 chars: memory bank
            f'{tx_rx_status}'   # 1 char: TX/RX status
            f'{mode}'           # 1 char: mode
            f'{current_vfo}'    # 1 char: current VFO (CRITICAL!)
            f'{scan_status}'    # 1 char: scan status
            f'{split_status}'   # 1 char: split status
            f'{tone_status}'    # 1 char: tone status
            f'{tone_number}'    # 2 chars: tone number
            f'{ctcss_status}'   # 1 char: CTCSS status
        )
        
        # Ensure exactly 37 characters with padding if needed
        if len(content) < 37:
            content = content.ljust(37, '0')
        elif len(content) > 37:
            content = content[:37]
        
        # Build final response
        response = f'IF{content};'
        
        # Verify total length is exactly 40 characters
        if len(response) != 40:
            log(f"ERROR: IF response length {len(response)} != 40", "ERROR")
            # Emergency fallback to ensure Hamlib compatibility
            fallback_content = f'{freq}000000020000000080000000'[:37].ljust(37, '0')
            response = f'IF{fallback_content};'
        
        log(f"IF response: {response} (len={len(response)}, vfo={current_vfo})")
        return response.encode('utf-8')'''
    
    # Replace the old IF response method
    if old_if_response in content:
        content = content.replace(old_if_response, new_if_response)
        
        # Write the updated content back
        with open(cat_emulator_path, 'w') as f:
            f.write(content)
        
        print("✅ IF command response fixed for Hamlib compatibility")
        return True
    else:
        print("⚠️  Could not find IF command response to fix")
        return False

def add_vfo_command_handlers():
    """Add proper VFO command handlers to prevent 'unsupported VFO None' errors."""
    
    cat_emulator_path = os.path.join(os.path.dirname(__file__), 'src', 'cat_emulator.py')
    
    if not os.path.exists(cat_emulator_path):
        print("Error: CAT emulator file not found")
        return False
    
    # Read the current file
    with open(cat_emulator_path, 'r') as f:
        content = f.read()
    
    # Add VFO command handlers after the existing command handlers
    vfo_handlers = '''
    def _handle_vfo_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle VFO selection commands for Hamlib compatibility."""
        if cmd_str == 'VS':
            # VFO swap command
            # Swap VFO A and B frequencies
            temp_freq = self.radio_state.vfo_a_freq
            self.radio_state.vfo_a_freq = self.radio_state.vfo_b_freq
            self.radio_state.vfo_b_freq = temp_freq
            return None  # Forward to radio
        elif cmd_str == 'VX':
            # VFO exchange command (similar to swap)
            return self._handle_vfo_command('VS')
        elif cmd_str.startswith('VF'):
            # VFO frequency command
            return self._handle_fa_command(cmd_str.replace('VF', 'FA'))
        else:
            log(f"Unknown VFO command: {cmd_str}")
            return None
    
    def _handle_current_vfo(self, cmd_str: str) -> Optional[bytes]:
        """Handle current VFO queries that Hamlib needs."""
        # Always return VFO A as current VFO to prevent 'None' errors
        return b'VFOA;'
    
    def _ensure_vfo_state(self):
        """Ensure VFO state is never None for Hamlib compatibility."""
        if not hasattr(self.radio_state, 'current_vfo') or self.radio_state.current_vfo is None:
            self.radio_state.current_vfo = '0'  # Default to VFO A
        
        # Ensure RX/TX VFO fields are set
        if not hasattr(self.radio_state, 'rx_vfo') or self.radio_state.rx_vfo is None:
            self.radio_state.rx_vfo = '0'  # Default to VFO A
        
        if not hasattr(self.radio_state, 'tx_vfo') or self.radio_state.tx_vfo is None:
            self.radio_state.tx_vfo = '0'  # Default to VFO A
'''
    
    # Find where to insert the VFO handlers (after the existing handlers)
    insertion_point = content.find('    def _handle_pa_command(self, cmd_str: str)')
    if insertion_point == -1:
        insertion_point = content.find('    def get_supported_commands(self)')
    
    if insertion_point != -1:
        # Insert the VFO handlers before the insertion point
        content = content[:insertion_point] + vfo_handlers + '\n' + content[insertion_point:]
        
        # Also add VFO command handling to the main command handler
        main_handler_addition = '''
            # VFO commands for Hamlib compatibility
            elif cmd_str.startswith('VS') or cmd_str.startswith('VX') or cmd_str.startswith('VF'):
                return self._handle_vfo_command(cmd_str)
            
            # Current VFO query
            elif cmd_str == 'CV':
                return self._handle_current_vfo(cmd_str)
            
            # Ensure VFO state is valid before all operations
            self._ensure_vfo_state()
'''
        
        # Find the main command handler and add VFO handling
        main_handler_pos = content.find('            # Unknown commands - ignore')
        if main_handler_pos != -1:
            content = content[:main_handler_pos] + main_handler_addition + '\n' + content[main_handler_pos:]
        
        # Write the updated content
        with open(cat_emulator_path, 'w') as f:
            f.write(content)
        
        print("✅ VFO command handlers added for Hamlib compatibility")
        return True
    else:
        print("⚠️  Could not find insertion point for VFO handlers")
        return False

def fix_radio_state_initialization():
    """Fix radio state initialization to prevent None VFO values."""
    
    cat_emulator_path = os.path.join(os.path.dirname(__file__), 'src', 'cat_emulator.py')
    
    if not os.path.exists(cat_emulator_path):
        print("Error: CAT emulator file not found")
        return False
    
    # Read the current file
    with open(cat_emulator_path, 'r') as f:
        content = f.read()
    
    # Find the RadioState __init__ method
    init_start = content.find('    def __init__(self):')
    if init_start != -1:
        # Find the end of the __init__ method
        init_end = content.find('\n    def ', init_start + 1)
        if init_end == -1:
            init_end = content.find('\n\nclass ', init_start + 1)
        
        if init_end != -1:
            # Extract the current __init__ method
            init_method = content[init_start:init_end]
            
            # Add VFO initialization if not present
            if 'current_vfo' not in init_method:
                vfo_init = '''
        # Current VFO tracking (critical for Hamlib)
        self.current_vfo = '0'          # Current VFO (0=A, 1=B, 2=Memory)
        '''
                
                # Insert before the end of the __init__ method
                init_method = init_method.rstrip() + vfo_init + '\n'
                
                # Replace the old __init__ method
                content = content[:init_start] + init_method + content[init_end:]
                
                # Write the updated content
                with open(cat_emulator_path, 'w') as f:
                    f.write(content)
                
                print("✅ Radio state initialization fixed for VFO handling")
                return True
    
    print("⚠️  Could not find RadioState __init__ method to fix")
    return False

def test_vfo_fix():
    """Test if the VFO fix is working."""
    
    try:
        # Import the fixed CAT emulator
        from src.cat_emulator import CATEmulator
        
        # Create emulator instance
        emulator = CATEmulator()
        
        # Test IF command response
        if_response = emulator.handle_ts480_command(b'IF;', None)
        
        if if_response:
            response_str = if_response.decode('utf-8')
            print(f"IF Response: {response_str}")
            
            # Verify response format
            if len(response_str) == 40 and response_str.startswith('IF') and response_str.endswith(';'):
                print("✅ IF command response format is correct")
                
                # Extract VFO field (position 23 in the response)
                vfo_field = response_str[23]  # Position 23 is the VFO field
                if vfo_field in ['0', '1', '2']:
                    print(f"✅ VFO field is valid: {vfo_field}")
                    return True
                else:
                    print(f"❌ VFO field is invalid: {vfo_field}")
                    return False
            else:
                print(f"❌ IF response format is incorrect: {response_str}")
                return False
        else:
            print("❌ No IF response received")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

def main():
    """Main function to apply VFO fixes."""
    
    print("VFO Fix Script for Hamlib Compatibility")
    print("="*50)
    
    # Apply fixes
    fixes_applied = 0
    
    print("\n1. Fixing IF command response format...")
    if fix_if_command_response():
        fixes_applied += 1
    
    print("\n2. Adding VFO command handlers...")
    if add_vfo_command_handlers():
        fixes_applied += 1
    
    print("\n3. Fixing radio state initialization...")
    if fix_radio_state_initialization():
        fixes_applied += 1
    
    print(f"\n{fixes_applied}/3 fixes applied successfully")
    
    # Test the fixes
    print("\n4. Testing VFO fixes...")
    if test_vfo_fix():
        print("\n✅ VFO fixes are working correctly!")
        print("\nYou can now run trusdx-txrx-AI.py and it should work with Hamlib without VFO errors.")
    else:
        print("\n❌ VFO fixes may not be working correctly.")
        print("Please check the error messages above and try running the script again.")
    
    print("\n" + "="*50)
    print("VFO Fix Script Complete")

if __name__ == "__main__":
    main()
