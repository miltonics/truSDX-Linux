#!/usr/bin/env python3
"""
GUI Dependencies Audit Script
This script verifies that tkinter and matplotlib import cleanly
and checks that the default matplotlib backend is TkAgg.
"""

import sys

def test_tkinter():
    """Test tkinter import"""
    try:
        import tkinter
        print("✓ tkinter import successful")
        return True
    except ImportError as e:
        print(f"✗ tkinter import failed: {e}")
        return False

def test_matplotlib():
    """Test matplotlib import and backend"""
    try:
        import matplotlib
        print("✓ matplotlib import successful")
        
        # Get the current backend
        backend = matplotlib.get_backend()
        print(f"  Current backend: {backend}")
        
        # Check if it's TkAgg
        if backend == 'TkAgg':
            print("✓ Default backend is TkAgg")
            return True
        else:
            print(f"! Default backend is {backend}, not TkAgg")
            return False
            
    except ImportError as e:
        print(f"✗ matplotlib import failed: {e}")
        return False

def test_matplotlib_with_tk():
    """Test matplotlib with TkAgg backend specifically"""
    try:
        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as plt
        print("✓ matplotlib with TkAgg backend works")
        return True
    except Exception as e:
        print(f"✗ matplotlib with TkAgg backend failed: {e}")
        return False

def main():
    print("=== GUI Dependencies Audit ===")
    print()
    
    # Test imports
    tkinter_ok = test_tkinter()
    matplotlib_ok = test_matplotlib()
    matplotlib_tk_ok = test_matplotlib_with_tk()
    
    print()
    print("=== Summary ===")
    
    if tkinter_ok and matplotlib_ok and matplotlib_tk_ok:
        print("✓ All GUI dependencies are working correctly!")
        print("✓ System is ready for GUI applications")
        return 0
    else:
        print("✗ Some GUI dependencies have issues")
        if not tkinter_ok:
            print("  - tkinter needs to be fixed")
        if not matplotlib_ok:
            print("  - matplotlib needs to be fixed")
        if not matplotlib_tk_ok:
            print("  - matplotlib TkAgg backend needs to be fixed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
