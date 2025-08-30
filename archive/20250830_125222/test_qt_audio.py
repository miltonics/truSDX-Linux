#!/usr/bin/env python3
"""
Test script to check how Qt applications like JS8Call see audio devices
"""

import sys
import subprocess

# Test using ALSA directly
print("=" * 60)
print("ALSA PCM Devices (as seen by applications like JS8Call):")
print("=" * 60)

# Get list of PCM devices
result = subprocess.run(['aplay', '-L'], capture_output=True, text=True)
lines = result.stdout.split('\n')

trusdx_devices = []
current_device = None
for i, line in enumerate(lines):
    if line and not line.startswith(' '):
        current_device = line
    elif current_device and 'trusdx' in current_device.lower():
        desc = line.strip() if line.strip() else "No description"
        trusdx_devices.append((current_device, desc))
        current_device = None

print("\n✅ truSDX devices visible to applications:\n")
for device, desc in trusdx_devices:
    print(f"  Device: {device}")
    print(f"  Description: {desc}")
    print()

# Also check with arecord for capture devices
print("\n" + "=" * 60)
print("ALSA Capture Devices (for receiving audio):")
print("=" * 60)

result = subprocess.run(['arecord', '-L'], capture_output=True, text=True)
lines = result.stdout.split('\n')

capture_devices = []
for line in lines:
    if 'trusdx' in line.lower() and not line.startswith(' '):
        capture_devices.append(line)

print("\n✅ truSDX capture devices:")
for device in capture_devices:
    print(f"  • {device}")

print("\n" + "=" * 60)
print("Configuration for JS8Call:")
print("=" * 60)
print()
print("In JS8Call's Settings → Radio → Soundcard:")
print()
print("  Input (for receiving):")
print("    • Select: trusdx_rx")
print("    • Or: alsa:trusdx_rx")
print()
print("  Output (for transmitting):")
print("    • Select: trusdx_tx")
print("    • Or: alsa:trusdx_tx")
print()
print("Note: If you don't see these in JS8Call, try:")
print("  1. Restart JS8Call")
print("  2. Or select 'Refresh' in the audio device dropdown")
print("  3. Or manually type: alsa:trusdx_rx and alsa:trusdx_tx")
