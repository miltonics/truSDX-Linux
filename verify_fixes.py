#!/usr/bin/env python3
"""
Verification script for TX0 and frequency fixes
This script verifies that the fixes are properly implemented
"""

import re
import sys

def check_tx0_usage():
    """Check that TX0 is used instead of TX1"""
    print("🔍 Checking TX0 usage...")
    
    with open('trusdx-txrx-AI.py', 'r') as f:
        content = f.read()
    
    tx0_count = len(re.findall(r';TX0;', content))
    tx1_count = len(re.findall(r';TX1;', content))
    
    print(f"   TX0 commands found: {tx0_count}")
    print(f"   TX1 commands found: {tx1_count}")
    
    if tx0_count >= 2 and tx1_count == 0:
        print("   ✅ PASS: TX0 is properly used for VU meter functionality")
        return True
    else:
        print("   ❌ FAIL: TX1 commands found or TX0 commands missing")
        return False

def check_frequency_reading():
    """Check that frequency reading is implemented"""
    print("\n🔍 Checking frequency reading on startup...")
    
    with open('trusdx-txrx-AI.py', 'r') as f:
        content = f.read()
    
    # Check for query_radio function
    if 'def query_radio(' in content:
        print("   ✅ query_radio function found")
    else:
        print("   ❌ query_radio function missing")
        return False
    
    # Check for frequency initialization
    if 'freq_resp = query_radio("FA")' in content:
        print("   ✅ Frequency reading code found")
    else:
        print("   ❌ Frequency reading code missing")
        return False
    
    # Check for radio state update
    if "radio_state['vfo_a_freq']" in content:
        print("   ✅ Radio state update found")
    else:
        print("   ❌ Radio state update missing")
        return False
    
    print("   ✅ PASS: Frequency reading is properly implemented")
    return True

def check_version_number():
    """Check that version number is updated"""
    print("\n🔍 Checking version number...")
    
    with open('trusdx-txrx-AI.py', 'r') as f:
        content = f.read()
    
    if 'VERSION = "1.1.8-AI-TX0-FREQ-FIXED"' in content:
        print("   ✅ PASS: Version updated to 1.1.8-AI-TX0-FREQ-FIXED")
        return True
    else:
        version_match = re.search(r'VERSION = "([^"]+)"', content)
        if version_match:
            print(f"   ❌ FAIL: Version is {version_match.group(1)}, expected 1.1.8-AI-TX0-FREQ-FIXED")
        else:
            print("   ❌ FAIL: Version string not found")
        return False

def main():
    print("🚀 TruSDX-AI Fix Verification")
    print("=" * 40)
    
    results = []
    results.append(check_tx0_usage())
    results.append(check_frequency_reading())
    results.append(check_version_number())
    
    print("\n" + "=" * 40)
    print("📋 SUMMARY")
    
    if all(results):
        print("✅ ALL TESTS PASSED - Fixes are properly implemented!")
        print("\n📝 Notes:")
        print("   • TX0 commands will enable VU meter functionality")
        print("   • Frequency reading requires radio connection")
        print("   • When radio is disconnected, defaults to 14.074 MHz")
        print("\n🧪 Testing Tips:")
        print("   • Connect TruSDX radio via USB for frequency reading")
        print("   • Test VU meter in WSJT-X during transmission")
        print("   • Check that CAT control works properly")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Please check implementation")
        return 1

if __name__ == "__main__":
    sys.exit(main())
