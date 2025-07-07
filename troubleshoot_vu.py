#!/usr/bin/env python3
"""
VU Meter Troubleshooting Script for truSDX-AI
This script helps diagnose VU meter issues after long periods of operation
"""

import pyaudio
import serial
import serial.tools.list_ports
import time
import sys
import os

def check_audio_devices():
    """Check audio device availability and status"""
    print("=== Audio Device Status ===")
    try:
        p = pyaudio.PyAudio()
        print(f"PyAudio initialized successfully. Found {p.get_device_count()} audio devices.")
        
        # Look for TRUSDX device
        trusdx_found = False
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = device_info['name']
            if 'TRUSDX' in device_name or 'trusdx' in device_name.lower():
                trusdx_found = True
                print(f"✅ Found TRUSDX device: {device_name} (index {i})")
                print(f"   Max Input Channels: {device_info['maxInputChannels']}")
                print(f"   Max Output Channels: {device_info['maxOutputChannels']}")
                print(f"   Default Sample Rate: {device_info['defaultSampleRate']}")
        
        if not trusdx_found:
            print("❌ TRUSDX audio device not found!")
            print("Available devices:")
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                print(f"   {i}: {device_info['name']}")
        
        p.terminate()
        return trusdx_found
        
    except Exception as e:
        print(f"❌ Error checking audio devices: {e}")
        return False

def check_serial_devices():
    """Check serial device availability"""
    print("\n=== Serial Device Status ===")
    try:
        ports = list(serial.tools.list_ports.comports())
        usb_serial_found = False
        
        for port in ports:
            print(f"Found: {port.device} - {port.description}")
            if 'USB Serial' in port.description or 'CH340' in port.description:
                usb_serial_found = True
                print(f"✅ truSDX-compatible device: {port.device}")
        
        if not usb_serial_found:
            print("❌ No USB Serial device found!")
        
        return usb_serial_found
        
    except Exception as e:
        print(f"❌ Error checking serial devices: {e}")
        return False

def test_audio_streaming():
    """Test audio streaming capability"""
    print("\n=== Audio Streaming Test ===")
    try:
        p = pyaudio.PyAudio()
        
        # Try to create a test stream
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=48000,
            input=True,
            frames_per_buffer=512
        )
        
        print("✅ Audio input stream created successfully")
        
        # Test reading audio data
        for i in range(5):
            try:
                data = stream.read(512, exception_on_overflow=False)
                print(f"   Read {len(data)} bytes of audio data (test {i+1}/5)")
                time.sleep(0.1)
            except Exception as e:
                print(f"❌ Error reading audio data: {e}")
                break
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        print("✅ Audio streaming test completed")
        return True
        
    except Exception as e:
        print(f"❌ Audio streaming test failed: {e}")
        return False

def test_serial_communication():
    """Test serial communication"""
    print("\n=== Serial Communication Test ===")
    try:
        # Find USB Serial device
        ports = list(serial.tools.list_ports.comports())
        usb_port = None
        
        for port in ports:
            if 'USB Serial' in port.description or 'CH340' in port.description:
                usb_port = port.device
                break
        
        if not usb_port:
            print("❌ No USB Serial device found for testing")
            return False
        
        print(f"Testing communication with {usb_port}")
        
        # Try to open serial connection
        ser = serial.Serial(usb_port, 115200, timeout=2)
        print("✅ Serial port opened successfully")
        
        # Test basic communication
        ser.write(b";ID;")
        ser.flush()
        time.sleep(0.5)
        
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"✅ Received response: {response}")
        else:
            print("⚠️  No response from radio (this might be normal)")
        
        ser.close()
        print("✅ Serial communication test completed")
        return True
        
    except Exception as e:
        print(f"❌ Serial communication test failed: {e}")
        return False

def check_system_resources():
    """Check system resource usage"""
    print("\n=== System Resource Check ===")
    try:
        # Check memory usage
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            
        for line in meminfo.split('\n'):
            if 'MemTotal:' in line:
                total_mem = int(line.split()[1]) // 1024  # Convert to MB
                print(f"Total Memory: {total_mem} MB")
            elif 'MemAvailable:' in line:
                avail_mem = int(line.split()[1]) // 1024  # Convert to MB
                print(f"Available Memory: {avail_mem} MB")
                
                if avail_mem < 100:  # Less than 100MB available
                    print("⚠️  Low memory warning!")
                else:
                    print("✅ Memory usage looks OK")
        
        # Check CPU load
        with open('/proc/loadavg', 'r') as f:
            load = f.read().strip().split()
            load_1min = float(load[0])
            print(f"CPU Load (1min): {load_1min}")
            
            if load_1min > 2.0:
                print("⚠️  High CPU load detected!")
            else:
                print("✅ CPU load looks OK")
                
        return True
        
    except Exception as e:
        print(f"❌ Error checking system resources: {e}")
        return False

def check_pulseaudio_setup():
    """Check PulseAudio/PipeWire setup"""
    print("\n=== Audio System Check ===")
    try:
        # Check if TRUSDX sink exists
        result = os.popen('pactl list sinks | grep -c "Name: TRUSDX"').read().strip()
        
        if result == '1':
            print("✅ TRUSDX audio sink exists")
        else:
            print("❌ TRUSDX audio sink not found!")
            print("Creating TRUSDX audio sink...")
            os.system('pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"')
            time.sleep(1)
            
            # Check again
            result = os.popen('pactl list sinks | grep -c "Name: TRUSDX"').read().strip()
            if result == '1':
                print("✅ TRUSDX audio sink created successfully")
            else:
                print("❌ Failed to create TRUSDX audio sink")
                return False
        
        # Check for active audio streams
        streams = os.popen('pactl list source-outputs').read()
        if 'js8call' in streams:
            print("✅ JS8Call is connected to audio system")
        else:
            print("⚠️  JS8Call not detected in audio streams")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking audio system: {e}")
        return False

def main():
    """Main troubleshooting routine"""
    print("truSDX-AI VU Meter Troubleshooting Tool")
    print("=" * 50)
    
    # Run all diagnostic tests
    tests = [
        ("Audio Devices", check_audio_devices),
        ("Serial Devices", check_serial_devices),
        ("Audio Streaming", test_audio_streaming),
        ("Serial Communication", test_serial_communication),
        ("System Resources", check_system_resources),
        ("Audio System Setup", check_pulseaudio_setup)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "="*50)
    print("TROUBLESHOOTING SUMMARY")
    print("="*50)
    
    all_passed = True
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
        if not result:
            all_passed = False
    
    print("\nRECOMMENDATIONS:")
    if all_passed:
        print("✅ All tests passed! VU meter should be working.")
        print("   If VU meter still not working, try restarting the truSDX script.")
    else:
        print("❌ Some tests failed. Here are potential solutions:")
        
        if not results.get("Audio Devices", True):
            print("   • Check if TRUSDX audio device was created properly")
            print("   • Try: pactl load-module module-null-sink sink_name=TRUSDX")
        
        if not results.get("Serial Devices", True):
            print("   • Check USB connection to truSDX radio")
            print("   • Check if user is in 'dialout' group")
            print("   • Try: sudo usermod -a -G dialout $USER")
        
        if not results.get("Audio Streaming", True):
            print("   • Audio system may be overloaded")
            print("   • Try restarting PulseAudio: pulseaudio -k")
        
        if not results.get("Serial Communication", True):
            print("   • Radio may not be responding to CAT commands")
            print("   • Check radio power and CAT settings")
        
        if not results.get("System Resources", True):
            print("   • System may be low on resources")
            print("   • Close unnecessary applications")
        
        print("\n   • Try restarting the truSDX-AI script")
        print("   • If problems persist, reboot the system")

if __name__ == "__main__":
    main()
