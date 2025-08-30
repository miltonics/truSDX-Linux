#!/usr/bin/env python3
"""
Simple truSDX Bridge - Minimal stable driver for audio and CAT
"""

import serial
import pyaudio
import threading
import time
import sys

# Configuration
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200
AUDIO_TX_RATE = 11525
AUDIO_RX_RATE = 7820

# Global state
buf = []
tx_active = False
running = True

def receive_audio(ser):
    """Receive audio data from radio"""
    global buf, running
    while running:
        try:
            data = ser.read(500)
            if data:
                buf.append(data)
        except Exception as e:
            print(f"RX Error: {e}")
            time.sleep(0.1)

def play_audio(stream):
    """Play received audio"""
    global buf, running
    while running:
        try:
            if len(buf) < 2:
                time.sleep(0.01)
                continue
            stream.write(buf[0])
            buf.pop(0)
        except Exception as e:
            print(f"Play Error: {e}")
            time.sleep(0.1)

def transmit_audio(stream, ser):
    """Transmit audio to radio"""
    global tx_active, running
    while running:
        try:
            samples = stream.read(500, exception_on_overflow=False)
            if min(samples) != 128 and max(samples) != 128:
                if not tx_active:
                    tx_active = True
                    print("TX ON")
                    ser.write(b"UA1;TX0;")
                ser.write(samples)
            elif tx_active:
                time.sleep(0.1)
                ser.write(b";RX;")
                tx_active = False
                print("TX OFF")
        except Exception as e:
            if "Input overflowed" not in str(e):
                print(f"TX Error: {e}")
            time.sleep(0.1)

def main():
    global running
    
    print("Starting truSDX Simple Bridge...")
    
    # Open serial port
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)
        print(f"Serial port {SERIAL_PORT} opened")
    except Exception as e:
        print(f"Failed to open serial port: {e}")
        sys.exit(1)
    
    # Initialize PyAudio
    pa = pyaudio.PyAudio()
    
    # Find ALSA loopback devices
    loopback_out = None
    loopback_in = None
    
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        if "Loopback" in info['name']:
            if "hw:1,0,0" in info['name'] and info['maxOutputChannels'] > 0:
                loopback_out = i
                print(f"Found loopback output: {info['name']} (index {i})")
            elif "hw:1,1,0" in info['name'] and info['maxInputChannels'] > 0:
                loopback_in = i
                print(f"Found loopback input: {info['name']} (index {i})")
    
    # Open audio streams
    try:
        # Input from Loopback,1 (what JS8Call sends)
        if loopback_in is not None:
            in_stream = pa.open(format=pyaudio.paUInt8, 
                               channels=1, 
                               rate=AUDIO_TX_RATE, 
                               input=True,
                               input_device_index=loopback_in)
            print(f"TX audio: Reading from Loopback device {loopback_in}")
        else:
            in_stream = pa.open(format=pyaudio.paUInt8, 
                               channels=1, 
                               rate=AUDIO_TX_RATE, 
                               input=True)
            print("TX audio: Using default input")
        
        # Output to Loopback,0 (what JS8Call receives)
        if loopback_out is not None:
            out_stream = pa.open(format=pyaudio.paInt8, 
                                channels=1, 
                                rate=AUDIO_RX_RATE, 
                                output=True,
                                output_device_index=loopback_out)
            print(f"RX audio: Sending to Loopback device {loopback_out}")
        else:
            out_stream = pa.open(format=pyaudio.paInt8, 
                                channels=1, 
                                rate=AUDIO_RX_RATE, 
                                output=True)
            print("RX audio: Using default output")
            
        print("Audio streams opened")
        print("\nIMPORTANT: In JS8Call audio settings:")
        print("  Input: hw:Loopback,1,0 (or 'Loopback: PCM (hw:1,1)')")
        print("  Output: hw:Loopback,0,0 (or 'Loopback: PCM (hw:1,0)')")
        print("")
    except Exception as e:
        print(f"Failed to open audio streams: {e}")
        ser.close()
        sys.exit(1)
    
    # Initialize radio
    time.sleep(2)
    ser.write(b"UA1;")  # Enable audio streaming
    ser.write(b"FA00007074000;")  # Set to 7.074 MHz
    print("Radio initialized")
    
    # Start threads
    rx_thread = threading.Thread(target=receive_audio, args=(ser,))
    play_thread = threading.Thread(target=play_audio, args=(out_stream,))
    tx_thread = threading.Thread(target=transmit_audio, args=(in_stream, ser))
    
    rx_thread.daemon = True
    play_thread.daemon = True
    tx_thread.daemon = True
    
    rx_thread.start()
    play_thread.start()
    tx_thread.start()
    
    print("Bridge running. Press Ctrl+C to stop.")
    
    # Main loop - print status
    try:
        while True:
            print(f"Buffer: {len(buf)} | TX: {'ON' if tx_active else 'OFF'}")
            time.sleep(10)
    except KeyboardInterrupt:
        print("\nShutting down...")
        running = False
        ser.write(b"RX;")
        ser.close()
        in_stream.close()
        out_stream.close()
        pa.terminate()
        print("Shutdown complete")

if __name__ == "__main__":
    main()
