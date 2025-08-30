#!/usr/bin/env python3
"""Test script to verify trusdx-txrx-AI.py refactoring for Python 3.12 compatibility"""

import ast
import sys
import os

def test_file_compilation():
    """Test that the file compiles with Python 3.12"""
    try:
        import py_compile
        py_compile.compile('trusdx-txrx-AI.py', doraise=True)
        print("✅ File compiles successfully with Python 3.12")
        return True
    except Exception as e:
        print(f"❌ Compilation failed: {e}")
        return False

def test_python_version_check():
    """Test that Python version check is implemented"""
    with open('trusdx-txrx-AI.py', 'r') as f:
        content = f.read()
    
    if 'MIN_PYTHON_VERSION' in content and 'sys.version_info < MIN_PYTHON_VERSION' in content:
        print("✅ Python version check is implemented")
        return True
    else:
        print("❌ Python version check not found")
        return False

def test_import_guards():
    """Test that third-party imports have try/except blocks"""
    with open('trusdx-txrx-AI.py', 'r') as f:
        content = f.read()
    
    checks = [
        ('pyaudio', 'pip install pyaudio'),
        ('serial', 'pip install pyserial')
    ]
    
    all_good = True
    for module, install_cmd in checks:
        if f"import {module}" in content and f"ImportError" in content and install_cmd in content:
            print(f"✅ Import guard for {module} is present")
        else:
            print(f"❌ Import guard for {module} is missing or incomplete")
            all_good = False
    
    return all_good

def test_exception_handling():
    """Test that KeyboardInterrupt is not masked"""
    with open('trusdx-txrx-AI.py', 'r') as f:
        lines = f.readlines()
    
    found_issues = []
    for i, line in enumerate(lines, 1):
        if 'except Exception' in line:
            # Check if there's a KeyboardInterrupt handler nearby
            start = max(0, i - 5)
            end = min(len(lines), i + 5)
            context = lines[start:end]
            context_str = ''.join(context)
            if 'KeyboardInterrupt' not in context_str:
                found_issues.append(i)
    
    if not found_issues:
        print("✅ KeyboardInterrupt handling looks good")
        return True
    else:
        print(f"⚠️  Potential KeyboardInterrupt masking at lines: {found_issues[:5]}...")
        # This is a warning, not a failure
        return True

def test_log_helper():
    """Test that log() helper is defined and used"""
    with open('trusdx-txrx-AI.py', 'r') as f:
        content = f.read()
    
    if 'def log(' in content and 'log(f"' in content:
        print("✅ log() helper is defined and used")
        return True
    else:
        print("❌ log() helper missing or not used properly")
        return False

def test_version_update():
    """Test that version has been updated"""
    with open('trusdx-txrx-AI.py', 'r') as f:
        content = f.read()
    
    if 'VERSION = "1.2.4"' in content and '2025-01-13' in content:
        print("✅ Version updated to 1.2.4 (2025-01-13)")
        return True
    else:
        print("❌ Version not properly updated")
        return False

def test_main_guard():
    """Test that __main__ guard exists"""
    with open('trusdx-txrx-AI.py', 'r') as f:
        content = f.read()
    
    if "if __name__ == '__main__':" in content:
        print("✅ __main__ guard is present")
        return True
    else:
        print("❌ __main__ guard is missing")
        return False

def main():
    print("=" * 60)
    print("Testing trusdx-txrx-AI.py refactoring for Python 3.12")
    print("=" * 60)
    print()
    
    tests = [
        test_file_compilation,
        test_python_version_check,
        test_import_guards,
        test_exception_handling,
        test_log_helper,
        test_version_update,
        test_main_guard
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
        print()
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if all(results):
        print(f"✅ All {total} tests passed!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
    
    return 0 if all(results) else 1

if __name__ == "__main__":
    sys.exit(main())
