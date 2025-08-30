#!/usr/bin/env python3
"""
Test script to verify Step 3 completion:
- REQUIRED_PIP list at top
- Automatic dependency installation in venv
- Shared PyAudio instance
- atexit cleanup handlers
"""

import ast
import sys
import os

def check_step3_completion(filepath):
    """Check if all Step 3 requirements are implemented"""
    
    print("=" * 80)
    print("STEP 3 COMPLETION TEST")
    print("=" * 80)
    
    results = {
        'required_pip': False,
        'auto_install': False,
        'shared_pyaudio': False,
        'atexit_handlers': False,
        'graceful_fail': False
    }
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            
        # Parse the Python file
        tree = ast.parse(content)
        
        # 1. Check for REQUIRED_PIP at top
        print("\n1. Checking for REQUIRED_PIP list...")
        if 'REQUIRED_PIP = ["pyserial>=3.5", "pyaudio"]' in content:
            print("   ✅ REQUIRED_PIP list found with correct packages")
            results['required_pip'] = True
        else:
            print("   ❌ REQUIRED_PIP list not found or incorrect")
        
        # 2. Check for automatic installation function
        print("\n2. Checking for automatic dependency installation...")
        if 'check_and_install_dependencies' in content:
            if 'subprocess.check_call([sys.executable, "-m", "pip", "install"' in content:
                print("   ✅ Automatic pip install functionality found")
                results['auto_install'] = True
                
                # Check for virtual environment detection
                if 'hasattr(sys, \'real_prefix\')' in content or 'sys.base_prefix' in content:
                    print("   ✅ Virtual environment detection implemented")
                else:
                    print("   ⚠️  Virtual environment detection not found")
            else:
                print("   ❌ subprocess.check_call for pip not found")
        else:
            print("   ❌ check_and_install_dependencies function not found")
        
        # 3. Check for graceful failure handling
        print("\n3. Checking for graceful failure handling...")
        if 'response == \'y\'' in content or 'Installation declined' in content:
            print("   ✅ User choice handling implemented")
            results['graceful_fail'] = True
        else:
            print("   ❌ User choice handling not found")
        
        # 4. Check for shared PyAudio instance
        print("\n4. Checking for shared PyAudio instance...")
        if "'pyaudio_instance': None" in content:
            print("   ✅ pyaudio_instance in state dictionary")
            
            # Count PyAudio() instantiations
            pyaudio_creates = content.count('pyaudio.PyAudio()')
            shared_creates = content.count("state['pyaudio_instance'] = pyaudio.PyAudio()")
            shared_uses = content.count("state['pyaudio_instance']")
            
            print(f"   📊 Found {pyaudio_creates} total PyAudio() calls")
            print(f"   📊 Found {shared_creates} shared instance creations")
            print(f"   📊 Found {shared_uses} shared instance uses")
            
            if shared_uses > 5:  # Should be used multiple times
                print("   ✅ Shared PyAudio instance properly implemented")
                results['shared_pyaudio'] = True
            else:
                print("   ⚠️  Shared instance may not be fully utilized")
        else:
            print("   ❌ pyaudio_instance not in state dictionary")
        
        # 5. Check for atexit handlers
        print("\n5. Checking for atexit cleanup handlers...")
        if 'import atexit' in content:
            print("   ✅ atexit module imported")
            
            if 'atexit.register' in content:
                print("   ✅ atexit.register() called")
                
                if 'cleanup_at_exit' in content:
                    print("   ✅ cleanup_at_exit function defined")
                    
                    # Check cleanup operations
                    cleanup_ops = [
                        ("Serial port closing", "state['ser'].close()"),
                        ("Audio stream closing", "state['in_stream'].close()"),
                        ("PyAudio termination", "state['pyaudio_instance'].terminate()"),
                        ("Thread stopping", "status[2] = False")
                    ]
                    
                    for op_name, op_code in cleanup_ops:
                        if op_code in content or op_code.replace("'", '"') in content:
                            print(f"   ✅ {op_name} in cleanup")
                        else:
                            print(f"   ⚠️  {op_name} not found in cleanup")
                    
                    results['atexit_handlers'] = True
                else:
                    print("   ❌ cleanup_at_exit function not found")
            else:
                print("   ❌ atexit.register() not called")
        else:
            print("   ❌ atexit module not imported")
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        
        total_passed = sum(results.values())
        total_tests = len(results)
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name.ljust(20)}: {status}")
        
        print(f"\nTotal: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests:
            print("\n🎉 SUCCESS: All Step 3 requirements are implemented!")
            return True
        else:
            print(f"\n⚠️  WARNING: {total_tests - total_passed} requirements still need implementation")
            return False
            
    except FileNotFoundError:
        print(f"❌ ERROR: File not found: {filepath}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    # Get the path to the main script
    script_path = "/home/milton/Desktop/Trusdx Linux/trusdx-txrx-AI.py"
    
    if len(sys.argv) > 1:
        script_path = sys.argv[1]
    
    print(f"Testing: {script_path}")
    success = check_step3_completion(script_path)
    
    sys.exit(0 if success else 1)
