#!/usr/bin/env python3

import pyaudio

# Initialize PyAudio
p = pyaudio.PyAudio()

print("\n=== PyAudio Device List ===\n")

# List all devices
for i in range(p.get_device_count()):
    device_info = p.get_device_info_by_index(i)
    device_name = device_info['name']
    
    print(f"Device {i}: {device_name}")
    print(f"  Max Input Channels: {device_info['maxInputChannels']}")
    print(f"  Max Output Channels: {device_info['maxOutputChannels']}")
    print(f"  Default Sample Rate: {device_info['defaultSampleRate']}")
    
    # Check if this is a Loopback device
    if "Loopback" in device_name:
        print(f"  *** This is a LOOPBACK device ***")
        if "0,0" in device_name:
            print(f"  --> Should map to trusdx_tx (TX audio from WSJT-X)")
        elif "0,1" in device_name:
            print(f"  --> Should map to trusdx_rx (RX audio to WSJT-X)")
    print()

# Test mapping function
def find_trusdx_device(name):
    """Test the device mapping logic"""
    device_map = {
        "trusdx_tx": "0,0",  # TX audio from WSJT-X (hw:0,0)
        "trusdx_rx": "0,1"   # RX audio to WSJT-X (hw:0,1)
    }
    
    if name not in device_map:
        return -1
    
    hw_pattern = device_map[name]
    
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        device_name = device_info['name']
        if "Loopback" in device_name and hw_pattern in device_name:
            return i
    
    return -1

print("\n=== Testing Device Mapping ===\n")

tx_idx = find_trusdx_device("trusdx_tx")
rx_idx = find_trusdx_device("trusdx_rx")

if tx_idx >= 0:
    print(f"✅ trusdx_tx mapped to device {tx_idx}: {p.get_device_info_by_index(tx_idx)['name']}")
else:
    print("❌ trusdx_tx not found")

if rx_idx >= 0:
    print(f"✅ trusdx_rx mapped to device {rx_idx}: {p.get_device_info_by_index(rx_idx)['name']}")
else:
    print("❌ trusdx_rx not found")

# Cleanup
p.terminate()
