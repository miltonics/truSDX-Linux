#!/usr/bin/env python3
"""
Hamlib Compatibility Test Suite for TruSDX-AI Driver
====================================================
Test suite to verify Hamlib/rigctl compatibility with the truSDX-AI driver

Version: 1.0.0 (2025-01-13)

Compatibility:
-------------
* Tested on: Linux Mint 21/22, Ubuntu 24.04, Fedora 40
* Requires: Python 3.12+
* Dependencies: hamlib (rigctl command)
* Hardware: TruSDX transceiver must be connected and powered

Quick-Start Commands:
--------------------
1. Ensure trusdx-txrx-AI.py is running:
   python trusdx-txrx-AI.py --port /dev/ttyUSB0

2. Run this test in another terminal:
   python test_hamlib_compat.py

3. Test individual rigctl commands manually:
   rigctl -m 2028 -r /tmp/trusdx_cat -s 115200 -vvv f  # Get frequency
   rigctl -m 2028 -r /tmp/trusdx_cat -s 115200 -vvv m  # Get mode
   rigctl -m 2028 -r /tmp/trusdx_cat -s 115200 -vvv t  # Get PTT status

Expected Results:
----------------
* All tests should pass (green checkmarks)
* Frequency, mode, and PTT operations should work correctly
* No CAT errors should appear in the logs

Troubleshooting:
---------------
* If tests fail, check that trusdx-txrx-AI.py is running
* Verify /tmp/trusdx_cat exists (created by the driver)
* Check logs/ directory for detailed debug information
* Ensure your truSDX is connected and powered on

Notes:
-----
* This test uses Kenwood TS-480 emulation (model 2028)
* The driver creates a virtual serial port at /tmp/trusdx_cat
* Tests include frequency, mode, VFO, and PTT operations
"""

import subprocess
import time
import os
import sys

def test_rigctl_commands():
    """Test various rigctl commands to ensure Hamlib compatibility"""
    
    # Check if rigctl is available
    try:
        subprocess.run(['rigctl', '--version'], capture_output=True, check=True)
    except FileNotFoundError:
        print("❌ rigctl not found. Please install hamlib.")
        return False
    except Exception as e:
        print(f"❌ Error checking rigctl: {e}")
        return False
    
    print("=== Testing Hamlib/rigctl compatibility with truSDX ===\n")
    
    # Common rigctl parameters for Kenwood TS-480
    rig_params = [
        '-m', '2028',           # Kenwood TS-480 model
        '-r', '/tmp/trusdx_cat', # CAT port
        '-s', '115200',         # Baud rate
        '-t', '80',             # Polling interval (ms)
        '-vvv'                  # Verbose output
    ]
    
    # Test commands
    tests = [
        {
            'name': 'Get Frequency',
            'cmd': ['rigctl'] + rig_params + ['f'],
            'expected': 'Should return frequency'
        },
        {
            'name': 'Get Mode',
            'cmd': ['rigctl'] + rig_params + ['m'],
            'expected': 'Should return mode (USB) and bandwidth'
        },
        {
            'name': 'Get VFO',
            'cmd': ['rigctl'] + rig_params + ['v'],
            'expected': 'Should return current VFO'
        },
        {
            'name': 'Get Info',
            'cmd': ['rigctl'] + rig_params + ['_'],
            'expected': 'Should return radio info'
        },
        {
            'name': 'PTT Test (Query)',
            'cmd': ['rigctl'] + rig_params + ['t'],
            'expected': 'Should return PTT status (0 = RX)'
        },
        {
            'name': 'Set Mode USB',
            'cmd': ['rigctl'] + rig_params + ['M', 'USB', '2400'],
            'expected': 'Should set mode to USB with 2400Hz bandwidth'
        },
        {
            'name': 'PTT On/Off Test',
            'cmd': None,  # Special handling below
            'expected': 'Should activate and deactivate PTT'
        }
    ]
    
    all_passed = True
    
    for test in tests:
        print(f"\n--- {test['name']} ---")
        
        if test['name'] == 'PTT On/Off Test':
            # Special handling for PTT test
            try:
                # PTT ON
                print("Activating PTT...")
                result = subprocess.run(
                    ['rigctl'] + rig_params + ['T', '1'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode != 0:
                    print(f"❌ PTT ON failed: {result.stderr}")
                    all_passed = False
                else:
                    print("✅ PTT ON command sent")
                    time.sleep(1)  # Hold PTT for 1 second
                    
                    # PTT OFF
                    print("Deactivating PTT...")
                    result = subprocess.run(
                        ['rigctl'] + rig_params + ['T', '0'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    
                    if result.returncode != 0:
                        print(f"❌ PTT OFF failed: {result.stderr}")
                        all_passed = False
                    else:
                        print("✅ PTT OFF command sent")
                
            except subprocess.TimeoutExpired:
                print("❌ Command timed out")
                all_passed = False
            except Exception as e:
                print(f"❌ Error: {e}")
                all_passed = False
            
            continue
        
        # Regular tests
        try:
            result = subprocess.run(
                test['cmd'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            print(f"Command: {' '.join(test['cmd'])}")
            print(f"Return code: {result.returncode}")
            
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
            
            if result.stderr:
                # Filter out common non-error messages
                error_lines = []
                for line in result.stderr.split('\n'):
                    if line and not any(skip in line for skip in ['rig:', 'Backend version:', 'Opened']):
                        error_lines.append(line)
                
                if error_lines:
                    print(f"Errors: {chr(10).join(error_lines)}")
            
            if result.returncode == 0:
                print(f"✅ {test['expected']}")
            else:
                print(f"❌ Command failed")
                all_passed = False
                
        except subprocess.TimeoutExpired:
            print("❌ Command timed out")
            all_passed = False
        except Exception as e:
            print(f"❌ Error running command: {e}")
            all_passed = False
    
    return all_passed

def main():
    print("=== Hamlib Compatibility Test for truSDX-AI ===")
    print("\nMake sure trusdx-txrx-AI.py is running before continuing!")
    print("Press Enter to start tests or Ctrl+C to cancel...")
    input()
    
    # Run the tests
    success = test_rigctl_commands()
    
    print("\n" + "="*50)
    if success:
        print("✅ All Hamlib tests passed!")
        print("\nYour truSDX-AI driver is properly configured for Hamlib.")
        print("You should be able to use it with WSJT-X, JS8Call, etc.")
    else:
        print("❌ Some tests failed.")
        print("\nTroubleshooting tips:")
        print("1. Ensure trusdx-txrx-AI.py is running")
        print("2. Check that /tmp/trusdx_cat exists")
        print("3. Verify your truSDX is connected and powered on")
        print("4. Check the logs in the logs/ directory")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
