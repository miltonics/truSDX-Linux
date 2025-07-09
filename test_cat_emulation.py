#!/usr/bin/env python3
"""
Test script to verify CAT emulation compatibility with Hamlib.
Tests the IF command response format and VFO handling.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cat_emulator import CATEmulator

def test_if_command():
    """Test IF command response format."""
    print("Testing IF command response format...")
    
    emulator = CATEmulator()
    
    # Test IF command
    response = emulator.handle_ts480_command(b'IF;', None)
    
    if response:
        response_str = response.decode('utf-8')
        print(f"IF Response: {response_str}")
        print(f"Response length: {len(response_str)}")
        
        # Verify format
        if len(response_str) == 40:
            print("✅ Response length is correct (40 characters)")
        else:
            print(f"❌ Response length is incorrect (expected 40, got {len(response_str)})")
        
        if response_str.startswith('IF') and response_str.endswith(';'):
            print("✅ Response format is correct (starts with IF, ends with ;)")
        else:
            print("❌ Response format is incorrect")
        
        # Extract components
        content = response_str[2:-1]  # Remove IF and ;
        if len(content) == 37:
            print("✅ Content length is correct (37 characters)")
            
            # Parse components
            freq = content[:11]
            rit_xit = content[11:16]
            rit = content[16]
            xit = content[17]
            bank = content[18:20]
            rxtx = content[20]
            mode = content[21]
            vfo = content[22]
            scan = content[23]
            split = content[24]
            tone = content[25]
            tone_freq = content[26:28]
            ctcss = content[28]
            padding = content[29:]
            
            print(f"  Frequency: {freq}")
            print(f"  RIT/XIT: {rit_xit}")
            print(f"  RIT: {rit}")
            print(f"  XIT: {xit}")
            print(f"  Bank: {bank}")
            print(f"  RX/TX: {rxtx}")
            print(f"  Mode: {mode}")
            print(f"  VFO: {vfo}")
            print(f"  Scan: {scan}")
            print(f"  Split: {split}")
            print(f"  Tone: {tone}")
            print(f"  Tone Freq: {tone_freq}")
            print(f"  CTCSS: {ctcss}")
            print(f"  Padding: {padding}")
            
        else:
            print(f"❌ Content length is incorrect (expected 37, got {len(content)})")
    else:
        print("❌ No response received")

def test_vfo_commands():
    """Test VFO command handling."""
    print("\nTesting VFO command handling...")
    
    emulator = CATEmulator()
    
    # Test VFO A frequency query
    response = emulator.handle_ts480_command(b'FA;', None)
    if response:
        print(f"FA Response: {response.decode('utf-8')}")
    
    # Test VFO A frequency set
    response = emulator.handle_ts480_command(b'FA00007074000;', None)
    if response:
        print(f"FA Set Response: {response.decode('utf-8')}")
    
    # Test RX VFO query
    response = emulator.handle_ts480_command(b'FR;', None)
    if response:
        print(f"FR Response: {response.decode('utf-8')}")
    
    # Test TX VFO query
    response = emulator.handle_ts480_command(b'FT;', None)
    if response:
        print(f"FT Response: {response.decode('utf-8')}")

def test_mode_commands():
    """Test mode command handling."""
    print("\nTesting mode command handling...")
    
    emulator = CATEmulator()
    
    # Test mode query
    response = emulator.handle_ts480_command(b'MD;', None)
    if response:
        print(f"MD Response: {response.decode('utf-8')}")
    
    # Test mode set
    response = emulator.handle_ts480_command(b'MD2;', None)
    if response:
        print(f"MD Set Response: {response.decode('utf-8')}")

def test_ai_command():
    """Test AI (auto information) command."""
    print("\nTesting AI command handling...")
    
    emulator = CATEmulator()
    
    # Test AI query
    response = emulator.handle_ts480_command(b'AI;', None)
    if response:
        print(f"AI Response: {response.decode('utf-8')}")
    
    # Test AI set
    response = emulator.handle_ts480_command(b'AI2;', None)
    if response:
        print(f"AI Set Response: {response.decode('utf-8')}")

def test_id_command():
    """Test ID command."""
    print("\nTesting ID command handling...")
    
    emulator = CATEmulator()
    
    # Test ID query
    response = emulator.handle_ts480_command(b'ID;', None)
    if response:
        print(f"ID Response: {response.decode('utf-8')}")
        if response == b'ID020;':
            print("✅ ID response is correct (TS-480 ID)")
        else:
            print("❌ ID response is incorrect")

def test_hamlib_sequence():
    """Test typical Hamlib initialization sequence."""
    print("\nTesting Hamlib initialization sequence...")
    
    emulator = CATEmulator()
    
    # Typical Hamlib sequence
    commands = [
        b'ID;',      # Get radio ID
        b'AI;',      # Get auto info mode
        b'AI2;',     # Set auto info mode
        b'IF;',      # Get radio status
        b'FA;',      # Get VFO A frequency
        b'MD;',      # Get mode
        b'FR;',      # Get RX VFO
        b'FT;',      # Get TX VFO
    ]
    
    for cmd in commands:
        response = emulator.handle_ts480_command(cmd, None)
        if response:
            print(f"{cmd.decode('utf-8')} → {response.decode('utf-8')}")
        else:
            print(f"{cmd.decode('utf-8')} → No response")

if __name__ == '__main__':
    print("CAT Emulation Test Suite")
    print("=" * 50)
    
    test_if_command()
    test_vfo_commands()
    test_mode_commands()
    test_ai_command()
    test_id_command()
    test_hamlib_sequence()
    
    print("\n" + "=" * 50)
    print("Test complete!")
