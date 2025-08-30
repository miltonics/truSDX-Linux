#!/usr/bin/env python3
"""
Direct test of handle_ts480_command function
"""

import sys
import os
from unittest.mock import MagicMock

# Import the main module
import importlib.util
spec = importlib.util.spec_from_file_location("trusdx", "trusdx-txrx-AI.py")
trusdx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trusdx)

# Mock config
trusdx.config = {'verbose': True}

# Mock serial
mock_ser = MagicMock()

def test_commands():
    """Test various CAT commands"""
    print("Testing CAT commands directly...")
    
    # Test V command
    print("\n1. Testing V command (get current VFO):")
    cmd = b'V;'
    response = trusdx.handle_ts480_command(cmd, mock_ser)
    print(f"  Command: {cmd}")
    print(f"  Response: {response}")
    print(f"  Decoded: {response.decode('utf-8') if response else 'None'}")
    
    # Test IF command
    print("\n2. Testing IF command (get status):")
    cmd = b'IF;'
    response = trusdx.handle_ts480_command(cmd, mock_ser)
    print(f"  Command: {cmd}")
    print(f"  Response: {response}")
    print(f"  Decoded: {response.decode('utf-8') if response else 'None'}")
    if response:
        decoded = response.decode('utf-8')
        print(f"  Length: {len(decoded)}")
        if len(decoded) == 40:
            print("  ✅ Correct length (40 chars)")
        else:
            print(f"  ❌ Wrong length (expected 40, got {len(decoded)})")
    
    # Test AI command
    print("\n3. Testing AI command (auto info):")
    cmd = b'AI;'
    response = trusdx.handle_ts480_command(cmd, mock_ser)
    print(f"  Command: {cmd}")
    print(f"  Response: {response}")
    print(f"  Decoded: {response.decode('utf-8') if response else 'None'}")
    
    # Test FA command
    print("\n4. Testing FA command (frequency A):")
    cmd = b'FA;'
    response = trusdx.handle_ts480_command(cmd, mock_ser)
    print(f"  Command: {cmd}")
    print(f"  Response: {response}")
    print(f"  Decoded: {response.decode('utf-8') if response else 'None'}")
    
    # Test ID command
    print("\n5. Testing ID command (radio ID):")
    cmd = b'ID;'
    response = trusdx.handle_ts480_command(cmd, mock_ser)
    print(f"  Command: {cmd}")
    print(f"  Response: {response}")
    print(f"  Decoded: {response.decode('utf-8') if response else 'None'}")
    
    # Test PS command
    print("\n6. Testing PS command (power status):")
    cmd = b'PS;'
    response = trusdx.handle_ts480_command(cmd, mock_ser)
    print(f"  Command: {cmd}")
    print(f"  Response: {response}")
    print(f"  Decoded: {response.decode('utf-8') if response else 'None'}")
    
    print("\n" + "="*50)
    print("Current radio state:")
    for key, value in trusdx.radio_state.items():
        print(f"  {key}: {value}")

if __name__ == '__main__':
    test_commands()
