#!/usr/bin/env python3
"""
Test script to show JS8Call configuration for truSDX-AI driver
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ui import UserInterface
from main import VERSION, BUILD_DATE, PERSISTENT_PORTS, load_config

def show_js8call_config():
    """Display the configuration needed for JS8Call"""
    ui = UserInterface()
    config = load_config()
    
    print("=== JS8Call Configuration for truSDX-AI Driver ===")
    print(f"Driver Version: {VERSION}")
    print(f"Build Date: {BUILD_DATE}")
    print(f"Callsign: {config.get('callsign', 'N/A')}")
    print()
    
    print("=== JS8Call Radio Settings ===")
    print("Radio: Kenwood TS-480")
    print(f"Serial Port: {PERSISTENT_PORTS['cat_port']}")
    print("Baud Rate: 115200")
    print("Data Bits: 8")
    print("Stop Bits: 1") 
    print("Parity: None")
    print("Handshake: None")
    print("PTT Method: CAT")
    print()
    
    print("=== JS8Call Audio Settings ===")
    print(f"Input Device: {PERSISTENT_PORTS['audio_device']}")
    print(f"Output Device: {PERSISTENT_PORTS['audio_device']}")
    print("Sample Rate: 48000 Hz")
    print("Channels: 1 (Mono)")
    print()
    
    print("=== Setup Instructions ===")
    print("1. Start the truSDX-AI driver:")
    print("   python3 main.py")
    print()
    print("2. In JS8Call, configure:")
    print("   - Radio: Kenwood TS-480")
    print(f"   - Serial Port: {PERSISTENT_PORTS['cat_port']}")
    print("   - Baud Rate: 115200")
    print(f"   - Audio Input: {PERSISTENT_PORTS['audio_device']}")
    print(f"   - Audio Output: {PERSISTENT_PORTS['audio_device']}")
    print("   - PTT Method: CAT")
    print()
    
    print("=== Test Header Display ===")
    ui.show_persistent_header(
        version=VERSION,
        build_date=BUILD_DATE,
        callsign=config.get('callsign', 'N/A'),
        port_info=PERSISTENT_PORTS,
        power_info={'watts': 25},
        reconnect_status={'active': False}
    )

if __name__ == "__main__":
    show_js8call_config()
