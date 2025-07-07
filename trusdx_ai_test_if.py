#!/usr/bin/env python3
"""
Unit test for truSDX AI IF command response format validation
Ensures Hamlib compatibility with exactly 37 payload characters
"""

import sys
import os
import importlib.util

def load_trusdx_module():
    """Load the trusdx-txrx-AI.py module"""
    spec = importlib.util.spec_from_file_location("trusdx_ai", "trusdx-txrx-AI.py")
    trusdx_ai = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(trusdx_ai)
    return trusdx_ai

def test_if_response_format():
    """Test IF command response format for Hamlib compatibility"""
    print("Testing IF command response format...")
    
    try:
        # Load the main module
        trusdx_ai = load_trusdx_module()
        
        # Set up required global variables for testing
        trusdx_ai.config = {'verbose': False}  # Mock config
        trusdx_ai.status = [False, False, True, False]  # Mock status
        
        # Test with VFO A (default)
        trusdx_ai.radio_state = {
            'vfo_a_freq': '00007074000',  
            'vfo_b_freq': '00007074000',
            'mode': '2',                 
            'rx_vfo': '0',              # VFO A
            'tx_vfo': '0',
            'split': '0',
            'rit': '0',
            'xit': '0',
            'rit_offset': '00000',
            'power_on': '1',
            'ai_mode': '2'
        }
        
        # Create mock serial object (not used in IF command)
        class MockSerial:
            pass
        
        mock_ser = MockSerial()
        
        # Test IF command
        if_command = b'IF'
        response = trusdx_ai.handle_ts480_command(if_command, mock_ser)
        
        if response is None:
            print("❌ FAIL: IF command returned None")
            return False
            
        response_str = response.decode('utf-8')
        print(f"IF Response: {response_str}")
        
        # Test 1: Total length should be 40 (IF + 37 chars + ;)
        if len(response_str) != 40:
            print(f"❌ FAIL: Response length is {len(response_str)}, expected 40")
            print(f"   Response: '{response_str}'")
            return False
        
        # Test 2: Should start with 'IF' and end with ';'
        if not response_str.startswith('IF') or not response_str.endswith(';'):
            print(f"❌ FAIL: Response should start with 'IF' and end with ';'")
            print(f"   Response: '{response_str}'")
            return False
            
        # Test 3: Payload should be exactly 37 characters
        payload = response_str[2:-1]  # Remove 'IF' and ';'
        if len(payload) != 37:
            print(f"❌ FAIL: Payload length is {len(payload)}, expected 37")
            print(f"   Payload: '{payload}'")
            return False
        
        # Test 4: VFO selector (position 30, 0-indexed position 29) should be '0' or '1'
        vfo_selector = payload[29]  # Position 30 (0-indexed 29)
        if vfo_selector not in ['0', '1']:
            print(f"❌ FAIL: VFO selector at position 30 is '{vfo_selector}', expected '0' or '1'")
            print(f"   Payload: '{payload}'")
            print(f"   Position: {''.join([str(i%10) for i in range(37)])}")
            print(f"             {''.join([str(i//10) for i in range(37)])}")
            return False
        
        # Test 5: All characters should be valid (digits, letters, specific symbols)
        valid_chars = set('0123456789ABCDEF ')
        for i, char in enumerate(payload):
            if char not in valid_chars:
                print(f"❌ FAIL: Invalid character '{char}' at position {i+1}")
                return False
        
        print("✅ PASS: IF command response format is correct")
        print(f"   Length: {len(response_str)} (40 total: IF + 37 payload + ;)")
        print(f"   Payload: {len(payload)} characters")
        print(f"   VFO selector (pos 30): '{vfo_selector}'")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: Exception during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("truSDX AI IF Command Format Test")
    print("=" * 40)
    
    if not os.path.exists("trusdx-txrx-AI.py"):
        print("❌ FAIL: trusdx-txrx-AI.py not found in current directory")
        sys.exit(1)
    
    if test_if_response_format():
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
