#!/usr/bin/env python3
"""
Standalone test module for IF command format verification
Called by setup.sh to verify IF command format compatibility
"""

import sys
import os
import unittest

# Add the current directory to sys.path to import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("trusdx", "trusdx-txrx-AI.py")
trusdx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trusdx)

def test_if_command_format():
    """Test IF command format for setup verification"""
    try:
        # Mock serial port
        from unittest.mock import MagicMock
        mock_ser = MagicMock()
        
        # Set up config if not present
        if not hasattr(trusdx, 'config'):
            trusdx.config = {'verbose': False}
            
        # Set up basic radio state
        trusdx.radio_state.update({
            'vfo_a_freq': '00014074000',
            'vfo_b_freq': '00014074000',
            'mode': '2',
            'rx_vfo': '0',
            'tx_vfo': '0',
            'split': '0',
            'rit': '0',
            'xit': '0',
            'rit_offset': '00000',
            'power_on': '1',
            'ai_mode': '2'
        })
        
        # Test IF command
        command = b'IF;'
        response = trusdx.handle_ts480_command(command, mock_ser)
        
        if response is None:
            print("ERROR: IF command returned None")
            return False
            
        response_str = response.decode('utf-8')
        
        # Verify format
        if not response_str.startswith('IF'):
            print(f"ERROR: Response should start with 'IF', got: {response_str}")
            return False
            
        if not response_str.endswith(';'):
            print(f"ERROR: Response should end with ';', got: {response_str}")
            return False
            
        if len(response_str) != 40:
            print(f"ERROR: Response should be 40 chars, got {len(response_str)}: '{response_str}'")
            return False
            
        print(f"SUCCESS: IF command format verified: '{response_str}'")
        return True
        
    except Exception as e:
        print(f"ERROR: Exception during IF test: {e}")
        return False

if __name__ == '__main__':
    success = test_if_command_format()
    sys.exit(0 if success else 1)
