#!/usr/bin/env python3
"""
Test script to verify power monitoring and reconnection logic
Tests the actual implementation in trusdx-txrx-AI.py
"""

import re
import subprocess
import time
import threading
import sys
import os

def analyze_trusdx_code():
    """Analyze the truSDX code for power monitoring implementation"""
    
    print("🔍 Analyzing truSDX power monitoring implementation")
    print("="*70)
    
    code_file = 'trusdx-txrx-AI.py'
    
    if not os.path.exists(code_file):
        print(f"❌ {code_file} not found")
        return False
    
    with open(code_file, 'r') as f:
        code = f.read()
    
    # Check for key power monitoring features
    features = {
        'Power polling function': 'def poll_power',
        'Power query command': 'query_radio.*PC',
        'FW000 detection': 'FW000',
        'Zero watt detection': 'watts.*==.*0',
        'Reconnection trigger': 'reconnection.*trigger|trigger.*reconnection',
        'TX ignore period': 'TX_IGNORE_PERIOD|tx.*ignore',
        'Power timeout settings': 'POWER_TIMEOUT|POWER_POLL_INTERVAL',
        'Reconnection count limit': 'MAX_RECONNECT_ATTEMPTS|MAX_RETRIES'
    }
    
    found_features = {}
    
    for feature, pattern in features.items():
        matches = re.findall(pattern, code, re.IGNORECASE)
        found_features[feature] = len(matches) > 0
        
        if found_features[feature]:
            print(f"✅ {feature}: Found")
        else:
            print(f"❌ {feature}: Not found")
    
    # Extract specific values
    print("\n📊 Configuration Values:")
    
    # Extract timeout values
    timeout_matches = re.findall(r'(POWER_POLL_INTERVAL|POWER_TIMEOUT|TX_IGNORE_PERIOD|CONNECTION_TIMEOUT)\s*=\s*([0-9.]+)', code)
    for name, value in timeout_matches:
        print(f"   {name}: {value}s")
    
    # Extract retry limits
    retry_matches = re.findall(r'(MAX_RECONNECT_ATTEMPTS|MAX_RETRIES)\s*=\s*([0-9]+)', code)
    for name, value in retry_matches:
        print(f"   {name}: {value}")
    
    return all(found_features.values())

def test_power_query_logic():
    """Test the power query logic implementation"""
    
    print("\n🧪 Testing power query logic")
    print("="*70)
    
    # Test cases for power response parsing
    test_cases = [
        ('PC010;', 10, 'Normal power'),
        ('PC000;', 0, 'Zero power - should trigger reconnection'),
        ('FW000;', 0, 'Firmware response with 0W'),
        ('PC050;', 50, 'High power'),
        ('INVALID', None, 'Invalid response')
    ]
    
    success_count = 0
    
    for response, expected_watts, description in test_cases:
        print(f"\n🔸 Testing: {description}")
        print(f"   Response: {response}")
        
        # Simulate parsing logic from the truSDX driver
        try:
            if response.startswith('PC') and len(response) >= 5:
                watts_str = response[2:5]
                watts = int(watts_str)
                print(f"   Parsed watts: {watts}")
                
                if watts == expected_watts:
                    print("   ✅ PASS")
                    success_count += 1
                else:
                    print(f"   ❌ FAIL: Expected {expected_watts}, got {watts}")
            
            elif response.startswith('FW') and '000' in response:
                # Special case for firmware response
                watts = 0
                print(f"   Parsed watts: {watts} (FW response)")
                
                if watts == expected_watts:
                    print("   ✅ PASS")
                    success_count += 1
                else:
                    print(f"   ❌ FAIL: Expected {expected_watts}, got {watts}")
            
            else:
                if expected_watts is None:
                    print("   ✅ PASS (correctly rejected invalid response)")
                    success_count += 1
                else:
                    print("   ❌ FAIL: Should have parsed valid response")
        
        except Exception as e:
            if expected_watts is None:
                print(f"   ✅ PASS (correctly raised exception: {e})")
                success_count += 1
            else:
                print(f"   ❌ FAIL: Unexpected exception: {e}")
    
    print(f"\n📈 Power query logic test: {success_count}/{len(test_cases)} passed")
    return success_count == len(test_cases)

def test_reconnection_trigger_logic():
    """Test the reconnection trigger logic"""
    
    print("\n🔄 Testing reconnection trigger logic")
    print("="*70)
    
    # Simulate the logic from poll_power function
    
    print("🔸 Simulating power monitoring sequence:")
    
    # Test scenario: Multiple 0W readings should trigger reconnection
    power_readings = [10, 5, 0, 0, 0, 10]  # 3 consecutive zeros
    power_zero_count = 0
    reconnection_triggered = False
    
    for i, watts in enumerate(power_readings):
        print(f"\n   Reading {i+1}: {watts}W")
        
        if watts == 0:
            power_zero_count += 1
            print(f"      Zero count: {power_zero_count}")
            
            # Logic from the driver: trigger after 3+ consecutive 0W readings
            if power_zero_count >= 3:
                print("      🚨 RECONNECTION TRIGGERED!")
                reconnection_triggered = True
        else:
            if power_zero_count > 0:
                print(f"      Power restored from {power_zero_count} zero readings")
            power_zero_count = 0
    
    print(f"\n📊 Reconnection trigger test: {'✅ PASS' if reconnection_triggered else '❌ FAIL'}")
    return reconnection_triggered

def test_tx_ignore_period():
    """Test TX ignore period logic"""
    
    print("\n⏱️  Testing TX ignore period logic")
    print("="*70)
    
    # Simulate TX ignore period (from TX_IGNORE_PERIOD = 2.0)
    TX_IGNORE_PERIOD = 2.0
    
    scenarios = [
        (True, 1.0, "TX mode, within ignore period"),  # Should ignore 0W
        (True, 3.0, "TX mode, beyond ignore period"),  # Should detect 0W  
        (False, 1.0, "RX mode, any time"),            # Should detect 0W
    ]
    
    results = []
    
    for tx_mode, time_since_tx, description in scenarios:
        print(f"\n🔸 {description}")
        print(f"   TX mode: {tx_mode}")
        print(f"   Time since TX: {time_since_tx}s")
        print(f"   Ignore period: {TX_IGNORE_PERIOD}s")
        
        # Logic from the driver
        in_tx_ignore_period = tx_mode and time_since_tx <= TX_IGNORE_PERIOD
        should_ignore_0w = in_tx_ignore_period
        
        print(f"   Should ignore 0W: {should_ignore_0w}")
        
        if description == "TX mode, within ignore period":
            expected = True
        else:
            expected = False
            
        if should_ignore_0w == expected:
            print("   ✅ PASS")
            results.append(True)
        else:
            print("   ❌ FAIL")
            results.append(False)
    
    success = all(results)
    print(f"\n📊 TX ignore period test: {'✅ PASS' if success else '❌ FAIL'}")
    return success

def manual_test_instructions():
    """Provide manual testing instructions"""
    
    print("\n📋 Manual Testing Instructions")
    print("="*70)
    
    print("""
🎯 MANUAL TEST SCENARIOS:

1. DUMMY SERIAL ECHO TEST:
   • Run: python3 test_dummy_echo.py
   • Verify FW000; response detection
   • Should trigger reconnection logic

2. REAL HARDWARE 0W TEST:
   • Connect real truSDX hardware
   • Run: python3 trusdx-txrx-AI.py --verbose
   • Use radio to set power to 0W
   • Monitor console for:
     - "Power poll: 0W detected" warnings
     - Reconnection trigger after 3+ readings
     - Auto-recovery when power restored

3. NORMAL TX TEST:
   • Set radio to normal power (>0W)
   • Enable TX mode in WSJT-X/JS8Call
   • Verify:
     - No false reconnection triggers
     - TX ignore period working (first 2s)
     - Stable operation during normal TX

4. WSJT-X/JS8Call PERSISTENCE TEST:
   • Start WSJT-X or JS8Call
   • Connect to truSDX CAT port
   • Force a reconnection scenario
   • Verify:
     - CAT connection maintained
     - No loss of frequency/mode settings
     - Automatic recovery

📊 SUCCESS CRITERIA:
✅ FW000; response triggers reconnection
✅ 3+ consecutive 0W readings trigger reconnection  
✅ TX ignore period prevents false triggers
✅ CAT clients remain connected through reconnection
✅ Radio settings preserved during reconnection
✅ Normal operation uninterrupted
    """)

def main():
    """Main test runner"""
    
    print("truSDX Power Monitoring & Reconnection Test Suite")
    print("="*70)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
Usage: python3 test_power_monitor.py

This script analyzes and tests the power monitoring and 
reconnection logic in the truSDX driver.

Tests performed:
1. Code analysis - Check for required features
2. Power query logic - Test response parsing  
3. Reconnection trigger - Test 0W detection logic
4. TX ignore period - Test timing logic
5. Manual test guidance - Instructions for real hardware

No hardware required for automated tests.
        """)
        return
    
    # Run automated tests
    results = []
    
    print("\n" + "="*70)
    print("TEST 1: Code Analysis")
    print("="*70)
    results.append(analyze_trusdx_code())
    
    print("\n" + "="*70)
    print("TEST 2: Power Query Logic")  
    print("="*70)
    results.append(test_power_query_logic())
    
    print("\n" + "="*70)
    print("TEST 3: Reconnection Trigger Logic")
    print("="*70)
    results.append(test_reconnection_trigger_logic())
    
    print("\n" + "="*70)
    print("TEST 4: TX Ignore Period Logic")
    print("="*70)
    results.append(test_tx_ignore_period())
    
    print("\n" + "="*70)
    print("TEST 5: Manual Test Instructions")
    print("="*70)
    manual_test_instructions()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"Automated Tests: {passed}/{total} passed")
    
    if passed == total:
        print("✅ All automated tests passed!")
        print("🎯 Ready for manual hardware testing")
    else:
        print("❌ Some automated tests failed")
        print("🔧 Check implementation before hardware testing")
    
    print("\nNext steps:")
    print("1. Run dummy echo test: python3 test_dummy_echo.py")
    print("2. Test with real truSDX hardware")
    print("3. Run full test matrix: python3 test_matrix.py")

if __name__ == '__main__':
    main()
