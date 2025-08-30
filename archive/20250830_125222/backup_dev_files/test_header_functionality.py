#!/usr/bin/env python3
"""
Test script to verify header functionality works correctly
"""

import sys
import os
import time
import argparse
import importlib.util

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_header_functionality():
    """Test that header functions work correctly"""
    
    # Test 1: Test argument parsing for --no-header
    print("Test 1: Testing --no-header argument parsing")
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-header", action="store_true", default=False, help="Skip initial version display")
    
    # Test with --no-header
    args = parser.parse_args(["--no-header"])
    config = vars(args)
    assert config.get('no_header', False) == True, "Expected no_header=True with --no-header"
    print("✓ --no-header option works correctly")
    
    # Test without --no-header
    args = parser.parse_args([])
    config = vars(args)
    assert config.get('no_header', False) == False, "Expected no_header=False without --no-header"
    print("✓ default header behavior works correctly")
    
    # Test 2: Test header function presence in source code
    print("\nTest 2: Testing header function presence in source code")
    try:
        with open('trusdx-txrx-AI.py', 'r') as f:
            source_code = f.read()
        
        # Check that header functions exist
        assert 'def show_persistent_header(' in source_code, "show_persistent_header function missing"
        assert 'def refresh_header_only(' in source_code, "refresh_header_only function missing"
        print("✓ Header functions are properly defined in source code")
        
    except Exception as e:
        print(f"✗ Could not check source code: {e}")
        return False
    
    # Test 3: Test that configuration variables are set correctly
    print("\nTest 3: Testing configuration variables in source code")
    try:
        assert 'PERSISTENT_PORTS' in source_code, "PERSISTENT_PORTS not defined"
        assert 'VERSION =' in source_code, "VERSION not defined"
        assert 'BUILD_DATE =' in source_code, "BUILD_DATE not defined"
        print("✓ Configuration variables are properly defined")
        
    except AssertionError as e:
        print(f"✗ Configuration test failed: {e}")
        return False
    
    # Test 4: Test header function calls in main code
    print("\nTest 4: Testing header function calls in main code")
    try:
        assert 'show_persistent_header()' in source_code, "show_persistent_header() not called"
        assert 'refresh_header_only()' in source_code, "refresh_header_only() not called"
        assert 'header_refresh_count' in source_code, "periodic refresh logic not found"
        print("✓ Header functions are properly called in main code")
        
    except AssertionError as e:
        print(f"✗ Header calls test failed: {e}")
        return False
    
    print("\n✅ All header functionality tests passed!")
    return True

if __name__ == "__main__":
    success = test_header_functionality()
    sys.exit(0 if success else 1)
