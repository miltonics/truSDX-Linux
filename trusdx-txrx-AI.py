#!/usr/bin/env python3
"""
TruSDX AI-Enhanced Transceiver Control Software
===============================================
Enhanced AI version with Kenwood TS-480 CAT interface and persistent serial ports

Authors: SQ3SWF, PE1NNZ 2023, AI-Enhanced 2025
Version: 1.2.4 (2025-01-13)

Compatibility:
-------------
* Tested on: Linux Mint 21/22, Ubuntu 24.04, Fedora 40
* Requires: Python 3.12+
* Hardware: TruSDX transceiver with USB connection
* Software: Compatible with WSJT-X, JS8Call, FlDigi, Winlink

Audio Devices (ALSA & PipeWire):
--------------------------------
* ALSA Loopback: Uses snd-aloop module to create trusdx_tx and trusdx_rx devices
* PipeWire: Setup script creates TRUSDX (sink) and TRUSDX.monitor (source) virtual devices
* Both backends work seamlessly - use whichever is available on your system
* In WSJT-X/JS8Call:
  - Output: Select "TRUSDX" (PipeWire) or "trusdx_tx" (ALSA)
  - Input: Select "TRUSDX.monitor" (PipeWire) or "trusdx_rx" (ALSA)

Quick-Start Commands:
--------------------
Linux:
  1. Run setup script (installs everything):
     ./setup.sh
  
  2. Run the driver:
     ./trusdx-txrx-AI.py
  
  That's it! The setup script handles all dependencies and configuration.
  
  Manual setup (if needed):
  - Configure serial port: stty -F /dev/ttyUSB0 raw -echo -echoe -echoctl -echoke -hupcl 115200
  - If `hw:Loopback` does not exist, run `sudo modprobe snd-aloop` and reboot
  - For PipeWire systems, the setup script creates TRUSDX virtual audio devices automatically
  - Test with Hamlib: python3 test_hamlib_compat.py

Windows:
  See detailed Windows setup instructions below in comments.

Dependencies:
------------
* pyserial >= 3.5 - Serial port communication
* pyaudio - Audio stream handling
* portaudio19-dev (Linux) - Audio library backend
* socat (optional) - Virtual serial port creation for testing

Notes:
-----
* Run ./setup.sh first to install all dependencies
* Logs are saved to ./logs/ directory for debugging  
* Configuration persists in ~/.config/trusdx-ai.json
* The driver will create persistent serial port symlinks for CAT control
* PipeWire virtual sinks (TRUSDX/TRUSDX.monitor) are created if PipeWire is detected
* ALSA loopback devices (trusdx_tx/trusdx_rx) are always configured as fallback
"""

# de SQ3SWF, PE1NNZ 2023
# Enhanced AI version with Kenwood TS-480 CAT interface and persistent serial ports
# Version: 1.2.4 (2025-01-13) - Python 3.12+ compatible

# Linux:
# sudo apt install portaudio19-dev
# stty -F /dev/ttyUSB0 raw -echo -echoe -echoctl -echoke -hupcl 115200;
# sudo modprobe snd-aloop  # Load ALSA loopback module for card 0
# Configure ALSA Loopback card 0 devices (done by setup.sh)
# If `hw:Loopback` does not exist, run `sudo modprobe snd-aloop` and reboot
###

# Windows 7:
# Install python3.6 (32 bits version)
# python -m pip install --upgrade pip
# python -m pip install pyaudio   # or download and install the matching version from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
# python -m pip install pyaudio
# Install, extract VB-Audio Virtual Audio Cable from https://download.vb-audio.com/
# Install VB-Audio by clicking right on x64 executable and select Run as Administrator, click install driver
# Download and extract com0com from https://sourceforge.net/projects/com0com/
# setup.exe /S /D=C:\Program Files\com0com
# Install x64 executable. In case of driver-signing issues: every-time reboot Windows by holding F8 (Win7) or Shift (Win8/10), select "Disable Driver Signature Enforcement" in Advanced Boot options
# Select Start > com0com > Setup Command Prompt, and enter: uninstall > enter: install PortName=COM8 PortName=COM9
# or open Command Prompt > cd C:\Program Files (x86)\com0com > setupc install PortName=COM8 PortName=COM9
# Select CABLE audio devices and COM8 in WSJT-X or any other HAM radio program

# Build: sudo apt install patchelf && python -m pip install -U nuitka
# python -m nuitka --standalone trusdx-txrx.py

# Setup_com0com_v3.0.0.0_W7_x64_signed.exe  /S /D=C:\Program Files\com0com
# cd "c:\Program Files\com0com"
# setupc.exe install PortName=COM8 PortName=COM9
# (as admin) VBCABLE_Setup_x64.exe

###
# socat -d -d pty,link=/tmp/ttyS0,echo=0,ignoreeof,b115200,raw,perm=0777 pty,link=/tmp/ttyS1,echo=0,ignoreeof,b115200,raw,perm=0777 &
# sudo modprobe snd-aloop

# Standard library imports first
import sys
import threading
import time
import os
import datetime
import array
import argparse
import json
import configparser
import subprocess
import atexit
from sys import platform

# Import required modules with helpful error messages
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("\033[1;31m[ERROR] pyserial not installed!\033[0m")
    print("Please run: ./setup.sh")
    print("Or manually: sudo pip3 install pyserial")
    sys.exit(1)

try:
    import pyaudio
except ImportError:
    print("\033[1;31m[ERROR] pyaudio not installed!\033[0m")
    print("Please run: ./setup.sh")
    print("Or manually: sudo apt install portaudio19-dev && sudo pip3 install pyaudio")
    sys.exit(1)

# Version information
VERSION = "1.2.4"
BUILD_DATE = "2025-01-13"
AUTHOR = "SQ3SWF, PE1NNZ, AI-Enhanced - Python 3.12+ Compatible"
COMPATIBLE_PROGRAMS = ["WSJT-X", "JS8Call", "FlDigi", "Winlink"]
MIN_PYTHON_VERSION = (3, 12)

# Audio rate constants - compatible with both ALSA loopback and PipeWire backends
audio_tx_rate_trusdx = 4800
audio_tx_rate = 48000  # Use standard 48kHz for ALSA Loopback/PipeWire compatibility
audio_rx_rate = 48000   # Use standard 48kHz for ALSA Loopback/PipeWire compatibility
buf = []    # buffer for received audio
urs = [0]   # underrun counter
status = [False, False, True, False, False, False]	# tx_state, cat_streaming_state, running, cat_active, keyed_by_rts_dtr, tx_connection_lost

# Global state dictionary for atomic handle replacement
state = {
    'ser': None,
    'ser2': None,
    'in_stream': None,
    'out_stream': None,
    'reconnecting': False,
    'connection_stable': True,
    'last_data_time': time.time(),
    'reconnect_count': 0,
    'hardware_disconnected': False,
    'pyaudio_instance': None  # Shared PyAudio instance
}

# Thread-safe locks for handle replacement and monitoring
handle_lock = threading.Lock()
monitor_lock = threading.Lock()

# Connection monitoring settings
CONNECTION_TIMEOUT = 3.0  # Seconds without data before considering connection lost (reduced for TX)
TX_CONNECTION_TIMEOUT = 1.5  # Faster detection for TX mode
RECONNECT_DELAY = 2.0     # Give hardware time to settle
MAX_RECONNECT_ATTEMPTS = 0 # 0 = infinite attempts (never give up)
MAX_RETRIES = 5           # Maximum retries before exiting with error

# Power monitoring settings
POWER_POLL_INTERVAL = 5.0  # Poll power every 5 seconds
POWER_TIMEOUT = 2.0       # Timeout for power queries
TX_IGNORE_PERIOD = 2.0    # Ignore 0-W detection during initial 2s of each TX

# Kenwood TS-480 CAT Command mapping
TS480_COMMANDS = {
    'FA': 'Set/Read VFO A frequency',
    'FB': 'Set/Read VFO B frequency', 
    'FR': 'Set/Read receive VFO',
    'FT': 'Set/Read transmit VFO',
    'ID': 'Read transceiver ID',
    'IF': 'Read transceiver status',
    'MD': 'Set/Read operating mode',
    'PS': 'Set/Read power on/off status',
    'TX': 'Set transmit mode',
    'RX': 'Set receive mode',
    'AI': 'Set/Read auto information mode',
    'AG': 'Set/Read AF gain',
    'RF': 'Set/Read RF gain',
    'SQ': 'Set/Read squelch level',
    'MG': 'Set/Read microphone gain',
    'PC': 'Set/Read output power',
    'VX': 'Set/Read VOX status',
    'IS': 'Set/Read IF shift',
    'NB': 'Set/Read noise blanker',
    'NR': 'Set/Read noise reduction',
    'NT': 'Set/Read notch filter',
    'PA': 'Set/Read preamp/attenuator',
    'RA': 'Set/Read RIT/XIT frequency',
    'RT': 'Set/Read RIT on/off',
    'XT': 'Set/Read XIT on/off',
    'RC': 'Clear RIT/XIT frequency',
    'FL': 'Set/Read IF filter',
    'EX': 'Set/Read menu settings',
    'MC': 'Read memory channel',
    'MW': 'Write memory channel'
}

# Configuration file for persistent settings
CONFIG_FILE = '/home/milton/.config/trusdx-ai.json'
PERSISTENT_PORTS = {
    'cat_port': '/tmp/trusdx_cat',
    'audio_device': 'ALSA Loopback card 0'
}

# Audio stream retry settings
AUDIO_RETRY_COUNT = 10  # Number of retries for device-busy errors
AUDIO_RETRY_DELAY = 0.5  # Delay in seconds between retries
AUDIO_RECHECK_INTERVAL = 2.0  # How often to recheck for stream availability

# Global logging configuration
LOG_FILE = None
LOG_LOCK = threading.Lock()

# Cleanup handlers registration
def cleanup_at_exit():
    """Clean up resources at exit to prevent Python 3.12 shutdown crashes"""
    global state
    
    try:
        print("\n\033[1;33m[CLEANUP] Shutting down gracefully...\033[0m")
        
        # Stop all threads
        status[2] = False
        time.sleep(0.5)  # Give threads time to stop
        
        # Close serial ports
        if state.get('ser'):
            try:
                state['ser'].write(b";UA0;")  # Mute radio before closing
                state['ser'].close()
                print("\033[1;32m[CLEANUP] ✅ Closed primary serial port\033[0m")
            except:
                pass
        
        if state.get('ser2') and state['ser2'] != state.get('ser'):
            try:
                state['ser2'].close()
                print("\033[1;32m[CLEANUP] ✅ Closed secondary serial port\033[0m")
            except:
                pass
        
        # Close audio streams
        if state.get('in_stream'):
            try:
                state['in_stream'].stop_stream()
                state['in_stream'].close()
                print("\033[1;32m[CLEANUP] ✅ Closed input audio stream\033[0m")
            except:
                pass
        
        if state.get('out_stream'):
            try:
                state['out_stream'].stop_stream()
                state['out_stream'].close()
                print("\033[1;32m[CLEANUP] ✅ Closed output audio stream\033[0m")
            except:
                pass
        
        # Terminate PyAudio instance
        if state.get('pyaudio_instance'):
            try:
                state['pyaudio_instance'].terminate()
                print("\033[1;32m[CLEANUP] ✅ Terminated PyAudio instance\033[0m")
            except:
                pass
        
        print("\033[1;32m[CLEANUP] ✅ Cleanup complete\033[0m")
    except Exception as e:
        print(f"\033[1;31m[CLEANUP] Error during cleanup: {e}\033[0m")

# Register cleanup handler
atexit.register(cleanup_at_exit)

def setup_logging():
    """Setup logging with file rotation per run"""
    global LOG_FILE
    
    # Create logs directory if it doesn't exist
    logs_dir = "logs"
    os.makedirs(logs_dir, exist_ok=True)
    
    # Generate log filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"trusdx-{timestamp}.log"
    
    # Use custom logfile if provided, otherwise use default in logs/
    if config.get('logfile'):
        LOG_FILE = config['logfile']
    else:
        LOG_FILE = os.path.join(logs_dir, log_filename)
    
    # Initialize log file with header
    with LOG_LOCK:
        try:
            with open(LOG_FILE, 'w') as f:
                f.write(f"truSDX-AI Driver v{VERSION} - Log started at {datetime.datetime.now()}\n")
                f.write(f"Build Date: {BUILD_DATE}\n")
                f.write(f"Platform: {platform}\n")
                f.write("=" * 80 + "\n")
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"Warning: Could not initialize log file {LOG_FILE}: {e}")
            LOG_FILE = None

def log(msg, level="INFO"):
    """Log message with optional level and formatting
    
    Args:
        msg: Message to log
        level: Log level ("INFO", "WARNING", "ERROR", "RECONNECT")
    """
    timestamp = datetime.datetime.utcnow()
    
    # Always log to file if enabled
    if LOG_FILE:
        with LOG_LOCK:
            try:
                with open(LOG_FILE, 'a') as f:
                    f.write(f"[{timestamp}] {level}: {msg}\n")
            except KeyboardInterrupt:
                raise
            except Exception:
                # Silently continue if file logging fails
                pass
    
    # Console output only if verbose mode is enabled
    if config.get('verbose', False):
        # Format based on level
        if level == "RECONNECT":
            # Bold color header for reconnection messages
            print(f"\033[1;33m[{timestamp}] {msg}\033[0m")
        elif level == "ERROR":
            print(f"\033[1;31m[{timestamp}] ERROR: {msg}\033[0m")
        elif level == "WARNING":
            print(f"\033[1;33m[{timestamp}] WARNING: {msg}\033[0m")
        else:
            print(f"{timestamp} {msg}")

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def show_persistent_header():
    """Display persistent header with version and connection info"""
    # Setup screen with scrolling region
    print("\033[2J", end="")  # Clear entire screen
    print("\033[H", end="")   # Move cursor to home position
    print("\033[1;32m" + "="*80 + "\033[0m")  # Green header line
    print(f"\033[1;36mtruSDX-AI Driver v{VERSION}\033[0m - \033[1;33m{BUILD_DATE}\033[0m")
    print(f"\033[1;37mConnections for WSJT-X/JS8Call:\033[0m")
    print(f"\033[1;35m  Radio:\033[0m Kenwood TS-480 | \033[1;35mPort:\033[0m {PERSISTENT_PORTS['cat_port']} | \033[1;35mBaud:\033[0m 115200 | \033[1;35mPoll:\033[0m 80ms")
    print(f"\033[1;35m  Audio:\033[0m ALSA trusdx_tx / trusdx_rx | \033[1;35mPTT:\033[0m CAT | \033[1;35mStatus:\033[0m Ready")
    print("\033[1;32m" + "="*80 + "\033[0m")  # Green header line
    print()
    # Set scrolling region to start after header (lines 7 onwards)
    print("\033[7;24r", end="")  # Set scrolling region from line 7 to 24
    print("\033[7;1H", end="")   # Move cursor to line 7

def refresh_header_only(power_info=None):
    """Refresh just the header without clearing screen
    
    Args:
        power_info: Dict with 'watts' and 'reconnecting' status for power display
    """
    # Save cursor position
    print("\033[s", end="")  # Save cursor position
    
    # Move to top and redraw header with power info
    print("\033[2J", end="")  # Clear entire screen
    print("\033[H", end="")   # Move cursor to home position

def open_audio_streams(platform_config, config, state, retry_on_busy=True):
    """Open audio input and output streams with retry logic for device-busy errors.
    
    Args:
        platform_config: Platform-specific configuration dict
        config: Main configuration dict
        state: Global state dict to store stream handles
        retry_on_busy: Whether to retry on -9985 device-busy errors
    
    Returns:
        tuple: (in_stream, out_stream) - Either or both may be None if unavailable
    """
    # Initialize shared PyAudio instance if not already created
    if not state.get('pyaudio_instance'):
        try:
            state['pyaudio_instance'] = pyaudio.PyAudio()
            log("[AUDIO] Created shared PyAudio instance")
        except Exception as e:
            log(f"[AUDIO] Failed to create PyAudio instance: {e}", "ERROR")
            print(f"\033[1;31m[AUDIO] ❌ Failed to initialize PyAudio: {e}\033[0m")
            return None, None
    
    # Get device indices
    virtual_audio_dev_out = platform_config.get('virtual_audio_dev_out')
    virtual_audio_dev_in = platform_config.get('virtual_audio_dev_in')
    in_device_idx = find_audio_device(virtual_audio_dev_out) if virtual_audio_dev_out else -1
    out_device_idx = find_audio_device(virtual_audio_dev_in) if virtual_audio_dev_in else -1
    
    if config.get('verbose', False):
        print(f"\033[1;36m[AUDIO] Opening streams - Input: {virtual_audio_dev_out} (idx: {in_device_idx}), Output: {virtual_audio_dev_in} (idx: {out_device_idx})\033[0m")
    
    in_stream = None
    out_stream = None
    
    # Try to open input stream with retry logic
    for attempt in range(AUDIO_RETRY_COUNT if retry_on_busy else 1):
        try:
            log(f"[AUDIO] Opening input stream, attempt {attempt + 1}/{AUDIO_RETRY_COUNT}")
            in_stream = state['pyaudio_instance'].open(
                frames_per_buffer=config['block_size'],
                format=pyaudio.paInt16,
                channels=1,
                rate=audio_tx_rate,
                input=True,
                input_device_index=in_device_idx
            )
            log(f"[AUDIO] ✅ Successfully opened input stream from '{virtual_audio_dev_out}'")
            print(f"\033[1;32m[AUDIO] ✅ Input stream opened successfully\033[0m")
            break
        except OSError as e:
            error_code = getattr(e, 'errno', None) or (e.args[0] if e.args else None)
            if error_code == -9985:  # Device unavailable/busy
                log(f"[AUDIO] Device busy error -9985 on input stream, attempt {attempt + 1}/{AUDIO_RETRY_COUNT}")
                if attempt < AUDIO_RETRY_COUNT - 1 and retry_on_busy:
                    # Check if WSJT-X/JS8Call might have released the device
                    print(f"\033[1;33m[AUDIO] Input device busy, waiting {AUDIO_RETRY_DELAY}s before retry {attempt + 2}/{AUDIO_RETRY_COUNT}...\033[0m")
                    time.sleep(AUDIO_RETRY_DELAY)
                    
                    # Periodically check if we can detect WSJT-X/JS8Call status
                    if attempt % 4 == 3:  # Every 4th attempt
                        print(f"\033[1;36m[AUDIO] Checking if WSJT-X/JS8Call released the audio device...\033[0m")
                        time.sleep(AUDIO_RECHECK_INTERVAL)
                else:
                    # Max retries reached or retry disabled
                    log(f"[AUDIO] Input device remains busy after {attempt + 1} attempts, continuing without input audio", "WARNING")
                    print(f"\033[1;33m[AUDIO] ⚠️ Input audio device busy - continuing without TX audio\033[0m")
                    print(f"\033[1;33m[AUDIO] The driver will continue running and retry when device becomes available\033[0m")
                    break
            else:
                # Non-9985 error, don't retry
                log(f"[AUDIO] Error opening input stream: {e}", "ERROR")
                print(f"\033[1;31m[AUDIO] ❌ Failed to open input stream: {e}\033[0m")
                break
        except Exception as e:
            log(f"[AUDIO] Unexpected error opening input stream: {e}", "ERROR")
            print(f"\033[1;31m[AUDIO] ❌ Unexpected error opening input stream: {e}\033[0m")
            break
    
    # Try to open output stream with retry logic
    for attempt in range(AUDIO_RETRY_COUNT if retry_on_busy else 1):
        try:
            log(f"[AUDIO] Opening output stream, attempt {attempt + 1}/{AUDIO_RETRY_COUNT}")
            out_stream = state['pyaudio_instance'].open(
                frames_per_buffer=512,  # Use proper buffer size instead of 0
                format=pyaudio.paInt16,  # Use 16-bit format for better compatibility
                channels=1,
                rate=audio_rx_rate,
                output=True,
                output_device_index=out_device_idx
            )
            log(f"[AUDIO] ✅ Successfully opened output stream to '{virtual_audio_dev_in}'")
            print(f"\033[1;32m[AUDIO] ✅ Output stream opened successfully\033[0m")
            break
        except OSError as e:
            error_code = getattr(e, 'errno', None) or (e.args[0] if e.args else None)
            if error_code == -9985:  # Device unavailable/busy
                log(f"[AUDIO] Device busy error -9985 on output stream, attempt {attempt + 1}/{AUDIO_RETRY_COUNT}")
                if attempt < AUDIO_RETRY_COUNT - 1 and retry_on_busy:
                    # Check if WSJT-X/JS8Call might have released the device
                    print(f"\033[1;33m[AUDIO] Output device busy, waiting {AUDIO_RETRY_DELAY}s before retry {attempt + 2}/{AUDIO_RETRY_COUNT}...\033[0m")
                    time.sleep(AUDIO_RETRY_DELAY)
                    
                    # Periodically check if we can detect WSJT-X/JS8Call status
                    if attempt % 4 == 3:  # Every 4th attempt
                        print(f"\033[1;36m[AUDIO] Checking if WSJT-X/JS8Call released the audio device...\033[0m")
                        time.sleep(AUDIO_RECHECK_INTERVAL)
                else:
                    # Max retries reached or retry disabled
                    log(f"[AUDIO] Output device remains busy after {attempt + 1} attempts, continuing without output audio", "WARNING")
                    print(f"\033[1;33m[AUDIO] ⚠️ Output audio device busy - continuing without RX audio\033[0m")
                    print(f"\033[1;33m[AUDIO] The driver will continue running and retry when device becomes available\033[0m")
                    break
            else:
                # Non-9985 error, don't retry
                log(f"[AUDIO] Error opening output stream: {e}", "ERROR")
                print(f"\033[1;31m[AUDIO] ❌ Failed to open output stream: {e}\033[0m")
                break
        except Exception as e:
            log(f"[AUDIO] Unexpected error opening output stream: {e}", "ERROR")
            print(f"\033[1;31m[AUDIO] ❌ Unexpected error opening output stream: {e}\033[0m")
            break
    
    # Log final status
    if in_stream and out_stream:
        log("[AUDIO] Both audio streams opened successfully")
        print(f"\033[1;32m[AUDIO] ✅ All audio streams ready\033[0m")
    elif in_stream or out_stream:
        log(f"[AUDIO] Partial audio streams: in={in_stream is not None}, out={out_stream is not None}", "WARNING")
        print(f"\033[1;33m[AUDIO] ⚠️ Partial audio available (TX: {in_stream is not None}, RX: {out_stream is not None})\033[0m")
    else:
        log("[AUDIO] No audio streams available, driver will continue without audio", "WARNING")
        print(f"\033[1;33m[AUDIO] ⚠️ No audio streams available - driver running in CAT-only mode\033[0m")
    
    return in_stream, out_stream
    print("\033[1;32m" + "="*80 + "\033[0m")  # Green header line
    print(f"\033[1;36mtruSDX-AI Driver v{VERSION}\033[0m - \033[1;33m{BUILD_DATE}\033[0m")
    print(f"\033[1;37mConnections for WSJT-X/JS8Call:\033[0m")
    
    # Build status line with power information
    status_line = f"\033[1;35m  Radio:\033[0m Kenwood TS-480 | \033[1;35mPort:\033[0m {PERSISTENT_PORTS['cat_port']} | \033[1;35mBaud:\033[0m 115200 | \033[1;35mPoll:\033[0m 80ms"
    
    # Add power status if provided
    if power_info:
        if power_info.get('reconnecting', False) or power_info.get('watts', 0) == 0:
            status_line += f" | \033[1;33mPower: {power_info.get('watts', 0)}W (reconnecting…)\033[0m"
        else:
            status_line += f" | \033[1;32mPower: {power_info.get('watts', 0)}W\033[0m"
    
    print(status_line)
    print(f"\033[1;35m  Audio:\033[0m ALSA trusdx_tx / trusdx_rx | \033[1;35mPTT:\033[0m CAT | \033[1;35mStatus:\033[0m Ready")
    print("\033[1;32m" + "="*80 + "\033[0m")  # Green header line
    print()
    
    # Set scrolling region to start after header (lines 7 onwards)
    print("\033[7;24r", end="")  # Set scrolling region from line 7 to 24
    print("\033[7;1H", end="")   # Move cursor to line 7
    
    # Restore cursor position
    print("\033[u", end="")  # Restore cursor position

def show_version_info():
    """Display version and configuration information for connecting programs"""
    print(f"\n=== truSDX-AI Driver v{VERSION} ===")
    print(f"Build Date: {BUILD_DATE}")
    print(f"Author: {AUTHOR}")
    print(f"Platform: {platform}")
    print("\n=== Connection Information for WSJT-X/JS8Call ===")
    print("Radio Configuration:")
    print("  Rig: Kenwood TS-480")
    print("  Poll Interval: 80ms")
    print(f"  CAT Serial Port: {PERSISTENT_PORTS['cat_port']}")
    print("  Baud Rate: 115200")
    print("  Data Bits: 8")
    print("  Stop Bits: 1")
    print("  Parity: None")
    print("  Handshake: None")
    print("  PTT Method: CAT or RTS/DTR")
    print("\nAudio Configuration:")
    print("  Input Device: ALSA trusdx_rx (Loopback card 0)")
    print("  Output Device: ALSA trusdx_tx (Loopback card 0)")
    print("  Sample Rate: 48000 Hz")
    print("  Channels: 1 (Mono)")
    print("\nSupported Programs:")
    for prog in COMPATIBLE_PROGRAMS:
        print(f"  - {prog}")
    print("\nCAT Commands Supported:")
    for cmd, desc in list(TS480_COMMANDS.items())[:10]:  # Show first 10
        print(f"  {cmd}: {desc}")
    print(f"  ... and {len(TS480_COMMANDS)-10} more commands")
    print("\n" + "="*50)

def load_config():
    """Load persistent configuration"""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        log(f"Error loading config: {e}")
    return PERSISTENT_PORTS.copy()

def save_config(config_data):
    """Save persistent configuration"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
    except KeyboardInterrupt:
        raise
    except Exception as e:
        log(f"Error saving config: {e}")

def create_persistent_serial_ports():
    """Create persistent serial port symlinks"""
    try:
        # Remove existing symlinks if they exist
        for port_name in [PERSISTENT_PORTS['cat_port']]:
            if os.path.islink(port_name):
                os.unlink(port_name)
        
        # Create directory if needed
        os.makedirs(os.path.dirname(PERSISTENT_PORTS['cat_port']), exist_ok=True)
        
        return True
    except KeyboardInterrupt:
        raise
    except Exception as e:
        log(f"Error creating persistent ports: {e}")
        return False

# check_audio_setup() removed - now using ALSA loopback directly

def query_radio(cmd, retries=3, timeout=0.2, ser_handle=None):
    """Query radio with command and retry logic
    
    Args:
        cmd: Command string (e.g., "FA", "MD")
        retries: Number of retry attempts (default: 3)
        timeout: Timeout in seconds to wait for response (default: 0.2)
        ser_handle: Serial handle to use (if None, uses state['ser'])
    
    Returns:
        bytes: Response from radio or None if failed
    """
    # Use provided handle or get from state
    ser = ser_handle or state.get('ser')
    if not ser:
        return None
    
    for attempt in range(retries):
        try:
            # Clear any existing data in buffer
            if ser.in_waiting > 0:
                ser.read(ser.in_waiting)
            
            # Send command
            command = f";{cmd};".encode('utf-8')
            ser.write(command)
            ser.flush()
            
            # Wait for response
            start_time = time.time()
            response = b''
            
            while time.time() - start_time < timeout:
                if ser.in_waiting > 0:
                    chunk = ser.read(ser.in_waiting)
                    response += chunk
                    
                    # Check if we have a complete response (ends with ';')
                    if b';' in response:
                        # Find the last complete response
                        responses = response.split(b';')
                        for resp in responses:
                            if resp and resp.startswith(cmd.encode('utf-8')):
                                return resp + b';'
                        break
                
                time.sleep(0.01)  # Small delay to avoid busy waiting
            
            # If we got here, no valid response was received
            if attempt < retries - 1:
                log(f"Query {cmd} attempt {attempt + 1} failed, retrying...")
                time.sleep(0.05)  # Small delay before retry
            
        except Exception as e:
            log(f"Error in query_radio({cmd}) attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                time.sleep(0.05)
    
    log(f"Query {cmd} failed after {retries} attempts")
    return None

# Radio state variables for consistent responses
radio_state = {
    'vfo_a_freq': '00007074000',  # Default to 40m (7.074 MHz) instead of 20m
    'vfo_b_freq': '00007074000',  # Default to 40m (7.074 MHz) instead of 20m
    'mode': '2',                  # Will be read from radio at startup
    'rx_vfo': '0',               # VFO A
    'tx_vfo': '0',               # VFO A
    'curr_vfo': 'A',             # Current VFO, initialized to VFOA
    'split': '0',                # Split off
    'rit': '0',                  # RIT off
    'xit': '0',                  # XIT off
    'rit_offset': '00000',       # No offset
    'power_on': '1',             # Power on
    'ai_mode': '2'               # Auto info on
}

def handle_ts480_command(cmd, ser):
    """Handle Kenwood TS-480 specific CAT commands with full emulation"""
    try:
        cmd_str = cmd.decode('utf-8').strip(';\r\n')
        log(f"Processing CAT command: {cmd_str}")
        
        # Empty command - ignore
        if not cmd_str:
            return None
            
        # ID command - return TS-480 ID
        if cmd_str == 'ID':
            return b'ID020;'
        
        # IF command - return current status (critical for Hamlib)
        elif cmd_str == 'IF':
            # Hamlib expects EXACTLY 37 characters (not including IF and ;)
            # Format: IF13-character content
            
            # Update VFO indicator
            vfo_indicator = '0' if radio_state['curr_vfo'] == 'A' else '1'
            radio_state['rx_vfo'] = vfo_indicator
            radio_state['tx_vfo'] = vfo_indicator
            # Total: IF + 37 chars + ; = 40 characters
            
            freq = radio_state['vfo_a_freq'][:11].ljust(11, '0')     # 11 digits
            rit_xit = radio_state['rit_offset'][:5].ljust(5, '0')    # 5 digits  
            rit = radio_state['rit'][:1].ljust(1, '0')               # 1 digit
            xit = radio_state['xit'][:1].ljust(1, '0')               # 1 digit
            bank = '00'                                              # 2 digits
            rxtx = '1' if status[0] else '0'                        # 1 digit (0=RX, 1=TX)
            mode = radio_state['mode'][:1].ljust(1, '2')             # 1 digit
            vfo = radio_state['rx_vfo'][:1].ljust(1, '0')            # 1 digit (0=VFO A, 1=VFO B)
            scan = '0'                                               # 1 digit
            split = radio_state['split'][:1].ljust(1, '0')           # 1 digit
            tone = '0'                                               # 1 digit
            tone_freq = '08'                                         # 2 digits
            ctcss = '00'                                             # 2 digits (missing!)
            
            # Total should be: 11+5+1+1+2+1+1+1+1+1+1+2+2 = 30 chars
            # We need 35 chars, so add 5 more padding
            padding = '00000'  # 5 digits padding
            
# Build response: IF + 35 characters + ;
            content = f'{freq}{rit_xit}{rit}{xit}{bank}{rxtx}{mode}{vfo}{scan}{split}{tone}{tone_freq}{ctcss}{padding}'
            
            # Ensure exactly 35 characters
            content = content[:35].ljust(35, '0')
            response = f'IF{content};'

            # Double-check length
            if len(response) != 38:
                # Known working 35-char format for TS-480
                response = 'IF0001407400000000000200000008000;'

            return response.encode('utf-8')
        
        # VFO query commands - critical for fixing "VFO None" error
        elif cmd_str == 'V':
            # Get current VFO - return VFO A
            return b'V0;'  # Always return VFO A as current
        
        elif cmd_str.startswith('V') and len(cmd_str) == 2 and cmd_str[1] in ['0', '1']:
            # Set VFO command (V0 or V1 only)
            vfo_val = cmd_str[1]
            radio_state['rx_vfo'] = vfo_val
            radio_state['tx_vfo'] = vfo_val
            radio_state['curr_vfo'] = 'A' if vfo_val == '0' else 'B'
            return None  # Forward to radio
        
        # AI command - auto information (critical for Hamlib)
        elif cmd_str.startswith('AI'):
            if len(cmd_str) > 2:
                # Set AI mode
                old_ai_mode = radio_state['ai_mode']
                radio_state['ai_mode'] = cmd_str[2]
                
                # If AI mode is being turned on (1 or 2), send unsolicited ID and IF
                if old_ai_mode == '0' and radio_state['ai_mode'] in ['1', '2']:
                    # Send unsolicited ID and IF when AI mode is enabled
                    try:
                        if status[3] and ser:
                            time.sleep(0.01)
                            ser.write(b'ID020;')
                            ser.flush()
                            time.sleep(0.01)
                            # Build IF response
                            freq = radio_state['vfo_a_freq'][:11].ljust(11, '0')
                            rit_xit = radio_state['rit_offset'][:5].ljust(5, '0')
                            rit = radio_state['rit'][:1].ljust(1, '0')
                            xit = radio_state['xit'][:1].ljust(1, '0')
                            bank = '00'
                            rxtx = '1' if status[0] else '0'  # Use status[0] for TX/RX indication
                            mode = radio_state['mode'][:1].ljust(1, '2')
                            vfo = '0' if radio_state['curr_vfo'] == 'A' else '1'
                            scan = '0'
                            split = radio_state['split'][:1].ljust(1, '0')
                            tone = '0'
                            tone_freq = '08'
                            ctcss = '00'
                            padding = '00000'
                            content = f'{freq}{rit_xit}{rit}{xit}{bank}{rxtx}{mode}{vfo}{scan}{split}{tone}{tone_freq}{ctcss}{padding}'[:35].ljust(35, '0')
                            ser.write(f'IF{content};'.encode('utf-8'))
                            ser.flush()
                            log("Sent unsolicited ID and IF for AI mode activation")
                    except Exception as e:
                        log(f"Error sending unsolicited AI responses: {e}")
                
                return cmd  # Echo back
            else:
                # Read AI mode
                return f'AI{radio_state["ai_mode"]};'.encode('utf-8')
        
        # Frequency commands
        elif cmd_str.startswith('FA'):
            if len(cmd_str) > 2:
                # Set VFO A frequency
                freq = cmd_str[2:13].ljust(11, '0')[:11]  # Ensure exactly 11 digits
                freq_mhz = float(freq) / 1000000.0
                
                print(f"\033[1;36m[DEBUG] JS8Call setting frequency: {freq} ({freq_mhz:.3f} MHz)\033[0m")
                
                # Only block the default 14.074 MHz when JS8Call first connects
                # Allow all other frequency changes
                if freq == '00014074000' and radio_state['vfo_a_freq'] != '00014074000':
                    print(f"\033[1;33m[CAT] Blocking JS8Call's default 14.074 MHz - keeping current frequency\033[0m")
                    # Return current frequency instead of accepting the default
                    current_freq = radio_state['vfo_a_freq'].ljust(11, '0')[:11]
                    current_mhz = float(current_freq) / 1000000.0
                    print(f"\033[1;32m[CAT] \u2705 Returning current frequency: {current_mhz:.3f} MHz\033[0m")
                    return f'FA{current_freq};'.encode('utf-8')
                else:
                    # Allow legitimate frequency changes
                    radio_state['curr_vfo'] = 'A'
                    print(f"\033[1;32m[CAT] \u2705 Allowing frequency change to {freq_mhz:.3f} MHz\033[0m")
                    radio_state['vfo_a_freq'] = freq
                    refresh_header_only()
                    # ACK with semicolon for FA setter
                    return b';'
            else:
                # Read VFO A frequency - return current state
                print(f"\033[1;36m[DEBUG] JS8Call requesting frequency\033[0m")
                freq = radio_state['vfo_a_freq'].ljust(11, '0')[:11]
                freq_mhz = float(freq) / 1000000.0
                print(f"\033[1;32m[CAT] ✅ Returning frequency: {freq_mhz:.3f} MHz\033[0m")
                return f'FA{freq};'.encode('utf-8')
                
        elif cmd_str.startswith('FB'):
            if len(cmd_str) > 2:
                # Set VFO B frequency - extract and validate 11-digit frequency
                freq = cmd_str[2:13].ljust(11, '0')[:11]  # Ensure exactly 11 digits
                radio_state['vfo_b_freq'] = freq
                radio_state['curr_vfo'] = 'B'
                # ACK with semicolon for FB setter
                return b';'
            else:
                # Read VFO B frequency
                freq = radio_state['vfo_b_freq'].ljust(11, '0')[:11]
                return f'FB{freq};'.encode('utf-8')
        
        # Mode commands
        elif cmd_str.startswith('MD'):
            if len(cmd_str) > 2:
                # Set mode - update state and echo back acknowledgment
                radio_state['mode'] = cmd_str[2]
                # Don't forward to radio, just acknowledge
                return b';'  # ACK
            else:
                # Read mode
                return f'MD{radio_state["mode"]};'.encode('utf-8')
        
        # Power status
        elif cmd_str.startswith('PS'):
            if len(cmd_str) > 2:
                # Set power (ignore for now)
                return cmd
            else:
                # Read power status
                return f'PS{radio_state["power_on"]};'.encode('utf-8')
        
        # VFO operations
        elif cmd_str.startswith('FR'):
            if len(cmd_str) > 2:
                # Set RX VFO
                vfo_char = cmd_str[2]
                if vfo_char == '0':
                    radio_state['curr_vfo'] = 'A'
                    radio_state['rx_vfo'] = '0'
                elif vfo_char == '1':
                    radio_state['curr_vfo'] = 'B'
                    radio_state['rx_vfo'] = '1'
                return b';'  # ACK
            else:
                # Read RX VFO
                vfo_code = '0' if radio_state['curr_vfo'] == 'A' else '1'
                return f'FR{vfo_code};'.encode('utf-8')
                
        elif cmd_str.startswith('FT'):
            if len(cmd_str) > 2:
                # Set TX VFO
                vfo_char = cmd_str[2]
                if vfo_char == '0':
                    radio_state['tx_vfo'] = '0'
                elif vfo_char == '1':
                    radio_state['tx_vfo'] = '1'
                return b';'  # ACK
            else:
                # Read TX VFO
                vfo_code = '0' if radio_state['curr_vfo'] == 'A' else '1'
                return f'FT{vfo_code};'.encode('utf-8')
        
        # Split operation
        elif cmd_str.startswith('SP'):
            if len(cmd_str) > 2:
                # Set split - forward to hardware
                radio_state['split'] = cmd_str[2]
                return None  # Forward to radio
            else:
                # Read split
                return f'SP{radio_state["split"]};'.encode('utf-8')
        
        # RIT operations
        elif cmd_str.startswith('RT'):
            if len(cmd_str) > 2:
                # Set RIT on/off - forward to hardware
                radio_state['rit'] = cmd_str[2]
                return None  # Forward to radio
            else:
                # Read RIT status
                return f'RT{radio_state["rit"]};'.encode('utf-8')
                
        elif cmd_str.startswith('XT'):
            if len(cmd_str) > 2:
                # Set XIT on/off - forward to hardware
                radio_state['xit'] = cmd_str[2]
                return None  # Forward to radio
            else:
                # Read XIT status
                return f'XT{radio_state["xit"]};'.encode('utf-8')
        
        # Memory operations
        elif cmd_str.startswith('MC'):
            # Memory channel read
            return b'MC000;'  # Channel 0
            
        # Gain controls (return reasonable defaults)
        elif cmd_str.startswith('AG'):
            if len(cmd_str) > 2:
                return cmd  # Echo back
            else:
                return b'AG0100;'  # AF gain 100
                
        elif cmd_str.startswith('RF'):
            if len(cmd_str) > 2:
                return cmd  # Echo back
            else:
                return b'RF0100;'  # RF gain 100
                
        elif cmd_str.startswith('SQ'):
            if len(cmd_str) > 2:
                return cmd  # Echo back
            else:
                return b'SQ0000;'  # Squelch 0
        
        # PTT operations - must forward to truSDX hardware
        elif cmd_str == 'TX':
            # Query TX status - TX0 = in TX mode, TX1 = in RX mode
            return b'TX0;' if status[0] else b'TX1;'
        elif cmd_str.startswith('TX'):
            # TX command with mode (TX1 = enter TX mode, TX0 = exit TX mode)
            if cmd_str == 'TX1' and not status[0]:
                # Starting transmission - need to unmute speaker first
                print("\033[1;33m[TX] Transmit mode\033[0m")
                # Return None to let main handler send UA1 before TX1
            return None  # Forward to truSDX hardware
        elif cmd_str == 'RX':
            # Set to receive mode
            return None  # Forward to truSDX hardware
            
        # Filter and other commands
        elif cmd_str.startswith('FL') or cmd_str.startswith('IS') or cmd_str.startswith('NB') or cmd_str.startswith('NR'):
            return cmd  # Echo back filter commands
        
        # FW command (firmware query or filter width) - return default
        elif cmd_str.startswith('FW'):
            if len(cmd_str) > 2:
                return cmd  # Echo back
            else:
                return b'FW0000;'  # Default filter width
        
        # Handle common Hamlib initialization commands
        elif cmd_str == 'KS':
            return b'KS020;'  # Keying speed (CW)
        elif cmd_str == 'EX':
            return b'EX;'     # Menu extension
        elif cmd_str.startswith('EX'):
            return cmd        # Echo back EX commands
        
        # UA command - audio control (mute/unmute speaker)
        elif cmd_str.startswith('UA'):
            if len(cmd_str) > 2:
                # Set audio mode - forward to radio to ensure speaker control
                return None  # Forward to radio
            else:
                # Read audio mode - return current setting
                if config['unmute']:
                    return b'UA1;'  # Unmuted
                else:
                    return b'UA2;'  # Muted
        
        # For unknown/unimplemented TS-480 commands, return ";" to avoid ERROR
        elif cmd_str:
            log(f"Unimplemented TS-480 command: {cmd_str} - returning ';'")
            # Return semicolon for unimplemented commands to avoid CAT errors
            return b';'
        
        # For unhandled commands, forward to radio
        return None
        
    except Exception as e:
        log(f"Error processing CAT command {cmd}: {e}")
        return None  # Don't send error responses

def show_audio_devices():
    # Use shared PyAudio instance or create temporary one
    p = state.get('pyaudio_instance')
    temp_instance = False
    if not p:
        p = pyaudio.PyAudio()
        temp_instance = True
    
    try:
        for i in range(p.get_device_count()):
            print(p.get_device_info_by_index(i))
        for i in range(p.get_host_api_count()):
            print(p.get_host_api_info_by_index(i))
    finally:
        if temp_instance:
            p.terminate()
        
def find_audio_device(name, occurance = 0):
    """Find audio device by name or ALSA PCM descriptor.
    
    This function searches PyAudio's device list for:
    - Exact matches of the provided name
    - ALSA PCM names like 'trusdx_tx', 'trusdx_rx'
    - ALSA hardware descriptors like 'hw:Loopback,0,0'
    - Devices containing 'Loopback' in their description
    
    Args:
        name: Device name to search for (e.g., 'trusdx_tx', 'hw:Loopback,0,0')
        occurance: Which matching device to return if multiple found (default: 0 = first)
    
    Returns:
        int: Device index or -1 if not found
    """
    log(f"[ALSA-AUDIT] Searching for audio device: '{name}'")
    
    # Special case for TRUSDX devices - map to correct Loopback hw devices
    # Support both naming conventions (Option #1 preferred, Option #2 legacy)
    if name in ["TRUSDX", "TRUSDX_monitor", "trusdx_tx", "trusdx_rx"]:
        try:
            p = state.get('pyaudio_instance')
            temp_instance = False
            if not p:
                p = pyaudio.PyAudio()
                temp_instance = True
            
            # Map device names to Loopback hw device patterns
            # Driver perspective:
            # TRUSDX / trusdx_tx: Driver reads TX audio from hw:1,0 (JS8Call writes to hw:1,0)
            # TRUSDX.monitor / trusdx_rx: Driver writes RX audio to hw:1,1 (JS8Call reads from hw:1,1)
            device_map = {
                "TRUSDX": "1,0",           # Option #1 (preferred) - TX audio input
                "TRUSDX_monitor": "1,1",   # Option #1 (preferred) - RX audio output
                "trusdx_tx": "1,0",        # Option #2 (legacy) - TX audio input
                "trusdx_rx": "1,1"         # Option #2 (legacy) - RX audio output
            }
            
            hw_pattern = device_map[name]
            
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                device_name = device_info['name']
                # Check if this is the correct Loopback device
                # PyAudio shows these as "Loopback: PCM (hw:0,0)" and "Loopback: PCM (hw:0,1)"
                if "Loopback" in device_name and hw_pattern in device_name:
                    log(f"[ALSA-AUDIT] Found {name} -> {device_name} (index {i})")
                    print(f"\033[1;32m[AUDIO] Mapped {name} to {device_name} (index: {i})\033[0m")
                    if temp_instance:
                        p.terminate()
                    return i
                    
            # If not found, log available Loopback devices for debugging
            log(f"[ALSA-AUDIT] Could not find {name} with pattern {hw_pattern}")
            log(f"[ALSA-AUDIT] Available Loopback devices:")
            for i in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(i)
                if "Loopback" in device_info['name']:
                    log(f"[ALSA-AUDIT]   {i}: {device_info['name']}")
                    
            if temp_instance:
                p.terminate()
        except Exception as e:
            log(f"Error in special trusdx device lookup: {e}")
    
    try:
        # Use shared PyAudio instance or create temporary one
        p = state.get('pyaudio_instance')
        temp_instance = False
        if not p:
            p = pyaudio.PyAudio()
            temp_instance = True
        
        result = []
        loopback_devices = []  # Track ALSA loopback devices
        
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = device_info['name']
            
            # Debug logging in verbose mode
            if config.get('verbose', False):
                print(f"\033[1;90m[AUDIO] Device {i}: {device_name} (in:{device_info['maxInputChannels']}, out:{device_info['maxOutputChannels']})\033[0m")
            
            # Check for exact match first
            if name == device_name:
                result.append(i)
                # Extract ALSA hw details if present
                alsa_info = ""
                if 'hw:' in device_name:
                    alsa_info = f" - ALSA descriptor: {device_name}"
                log(f"[ALSA-AUDIT] Found exact audio device match: {device_name} (index {i}){alsa_info}")
                if config.get('verbose', False):
                    print(f"\033[1;32m[AUDIO] Exact match found: {device_name} (index: {i})\033[0m")
                continue
            
            # Check if this is an ALSA hw: style descriptor match
            if name.startswith('hw:') and name in device_name:
                result.append(i)
                log(f"[ALSA-AUDIT] Found ALSA hw device: {device_name} (index {i}) - Requested: {name}")
                if config.get('verbose', False):
                    print(f"\033[1;32m[AUDIO] ALSA hw match: {device_name} (index: {i})\033[0m")
                continue
            
            # Check for ALSA PCM name matches (trusdx_tx, trusdx_rx)
            if 'trusdx_tx' in name.lower() or 'trusdx_rx' in name.lower():
                # Look for these specific PCM names in the device description
                if name.lower() in device_name.lower():
                    result.append(i)
                    # Parse ALSA card,device,subdevice from device name if present
                    alsa_details = ""
                    if 'hw:' in device_name:
                        alsa_details = f" - ALSA: {device_name}"
                    log(f"[ALSA-AUDIT] Found ALSA PCM device: {device_name} (index {i}) for '{name}'{alsa_details}")
                    if config.get('verbose', False):
                        print(f"\033[1;32m[AUDIO] ALSA PCM match: {device_name} (index: {i})\033[0m")
                    continue
            
            # Check for Loopback devices (fallback if custom names not found)
            if 'Loopback' in device_name or 'loopback' in device_name.lower():
                # Determine if it's input or output based on channels
                if device_info['maxInputChannels'] > 0:
                    loopback_devices.append((i, device_name, 'input'))
                    if config.get('verbose', False):
                        print(f"\033[1;36m[AUDIO] Found Loopback input device: {device_name} (index: {i})\033[0m")
                if device_info['maxOutputChannels'] > 0:
                    loopback_devices.append((i, device_name, 'output'))
                    if config.get('verbose', False):
                        print(f"\033[1;36m[AUDIO] Found Loopback output device: {device_name} (index: {i})\033[0m")
            
            # General substring match (case-insensitive)
            if name.lower() in device_name.lower():
                result.append(i)
                log(f"Found audio device (substring): {device_name} (index {i})")
        
        if temp_instance:
            p.terminate()
        
        # If we found exact/substring matches, use them
        if len(result) > occurance:
            selected_idx = result[occurance]
            # Get more details about the selected device
            if not temp_instance:
                p = state.get('pyaudio_instance')
            device_info = p.get_device_info_by_index(selected_idx)
            device_name = device_info['name']
            
            # Parse ALSA info if present
            alsa_mapping = ""
            if 'hw:' in device_name:
                # Extract card, device, subdevice from names like "hw:Loopback,0,0"
                import re
                match = re.search(r'hw:(\w+),(\d+),(\d+)', device_name)
                if match:
                    card_name, device_num, subdev_num = match.groups()
                    alsa_mapping = f" -> ALSA hw:{card_name},{device_num},{subdev_num}"
                else:
                    # Try simpler pattern for "hw:Loopback,0" format
                    match = re.search(r'hw:(\w+),(\d+)', device_name)
                    if match:
                        card_name, device_num = match.groups()
                        alsa_mapping = f" -> ALSA hw:{card_name},{device_num}"
            elif 'trusdx_tx' in name.lower():
                # This is using the ALSA PCM alias which maps to hw:Loopback,0,0
                alsa_mapping = " -> ALSA PCM 'trusdx_tx' (mapped to hw:Loopback,0,subdevice)"
            elif 'trusdx_rx' in name.lower():
                # This is using the ALSA PCM alias which maps to hw:Loopback,1,0  
                alsa_mapping = " -> ALSA PCM 'trusdx_rx' (mapped to hw:Loopback,1,subdevice)"
            
            log(f"[ALSA-AUDIT] SELECTED: Using audio device index {selected_idx} for '{name}' - Device: '{device_name}'{alsa_mapping}")
            return selected_idx
        
        # NO FALLBACK - only use exact device names specified
        # This prevents accidentally grabbing .1 sub-devices or wrong Loopback devices
        if not result:
            log(f"[ALSA-AUDIT] STRICT MODE: Device '{name}' not found - NO FALLBACK to generic Loopback devices")
            if config.get('verbose', False):
                print(f"\033[1;33m[AUDIO] Device '{name}' not found - strict mode, no fallback\033[0m")
        
        # No device found
        log(f"Audio device '{name}' not found, using default (-1)")
        if config.get('verbose', False):
            print(f"\033[1;31m[AUDIO] Device '{name}' not found, will use default\033[0m")
        return -1
        
    except Exception as e:
        log(f"Error finding audio device '{name}': {e}")
        return -1

def show_serial_devices():
    for port in serial.tools.list_ports.comports():
        print(port)

def find_serial_device(name, occurance = 0):
    result = [port.device for port in serial.tools.list_ports.comports() if name in port.description]
    return result[occurance] if len(result) else "" # return n-th matching device to name, "" for no match

def handle_rx_audio(ser, cat, pastream, d):
    if status[1]:
        #log(f"stream: {d}")
        if not status[0]: buf.append(d)                   # in CAT streaming mode: fwd to audio buf
        #if not status[0]: pastream.write(d)  #  in CAT streaming mode: directly fwd to audio
        if d[-1] == ord(';'):
            status[1] = False           # go to CAT cmd mode when data ends with ';'
            #log("***CAT mode")
    else:
        if d.startswith(b'US'):
            #log("***US mode")
            status[1] = True            # go to CAT stream mode when data starts with US
        else:
            if status[3]:               # only send something to cat port, when active
                try:
                    # Synchronize radio response transmission with same protection as emulated responses
                    cat.reset_output_buffer()
                    time.sleep(0.001)  # Brief pause to ensure buffer is actually clear
                    cat.write(d)
                    cat.flush()
                    
                    if config.get('verbose', False):
                        print(f"\033[1;35m[RADIO] Forwarded radio response: {d}\033[0m")
                        
                except Exception as cat_error:
                    log(f"CAT radio response write error: {cat_error}")
                    print(f"\033[1;31m[CAT ERROR] Failed to forward radio response: {cat_error}\033[0m")
                    
                log(f"O: {d}")  # in CAT command mode
            else:
                log("Skip CAT response, as CAT is not active.")

def receive_serial_audio(ser, cat, pastream):
    try:
        log("receive_serial_audio")
        bbuf = b''  # rest after ';' that cannot be handled
        while status[2]:
            try:
                if False and status[0]:  # WORKAROUND: special case for TX; this is a workaround to handle CAT responses properly during TX
                    if(ser.in_waiting < 1): time.sleep(0.001)
                    else:
                        d = ser.read()
                        #log(f"Q: {d}")  # in TX CAT command mode
                        #cat.write(d)
                        #cat.flush()
                        handle_rx_audio(ser, cat, pastream, d)
                # below implements: d = ser.read_until(b';', 32)  #read until CAT end or enough in buf but only up to 32 bytes to keep response
                #elif(ser.in_waiting < config['tx_block_size']): time.sleep(0.001)   #normal case for RX
                elif(ser.in_waiting == 0): 
                    time.sleep(0.001)   #normal case for RX
                    continue  # Skip the rest of the loop when no data is waiting
                else:
                    #d = bbuf + ser.read(config['tx_block_size'])
                    d = bbuf + ser.read(ser.in_waiting)
                    x = d.split(b';', maxsplit=1)
                    cat_delim = (len(x) == 2)
                    bbuf = x[1] if cat_delim else b''
                    if not cat_delim and len(x[0]) < config['tx_block_size']:
                        bbuf = x[0]
                        continue
                    d = x[0] + b';' if cat_delim else x[0]
                    handle_rx_audio(ser, cat, pastream, d)
                # Update data timestamp for connection monitoring
                update_data_timestamp()
            except (serial.serialutil.SerialException, OSError) as e:
                error_msg = str(e)
                log(f"Serial disconnection detected: {error_msg}")
                print(f"\033[1;33m[SERIAL] 🔌 Hardware disconnected: {error_msg}\033[0m")
                
                # Set hardware disconnection flag
                state['hardware_disconnected'] = True
                state['connection_stable'] = False
                
                # Trigger immediate reconnection if not already in progress
                if not state.get('reconnecting', False):
                    print(f"\033[1;31m[SERIAL] 🔄 Triggering immediate reconnection due to hardware disconnect...\033[0m")
                    threading.Thread(target=safe_reconnect, daemon=True).start()
                
                # Stop this thread
                status[2] = False
                break
            except Exception as e:
                log(f"Unexpected error in receive_serial_audio: {e}")
                time.sleep(0.1)  # Brief pause before continuing
                continue
                
    except Exception as e:
        log(f"Fatal error in receive_serial_audio: {e}")
        status[2] = False
        if config['verbose']: raise

def play_receive_audio(pastream):
    try:
        log("play_receive_audio")
        while status[2]:
            if len(buf) < 2:
                #log(f"UNDERRUN #{urs[0]} - refilling")
                urs[0] += 1
                while len(buf) < 10:
                    time.sleep(0.001)
            if not status[0]: pastream.write(buf[0])
            buf.remove(buf[0])
    except Exception as e:
        log(e)
        status[2] = False
        if config['verbose']: raise

def tx_cat_delay(ser):
    #ser.reset_output_buffer() # because trusdx TX buffers can be full, empty host buffers (but reset_output_buffer does not seem to work)
    ser.flush()  # because trusdx TX buffers can be full, wait until all buffers are empty
    #time.sleep(0.003 + config['block_size']/audio_tx_rate) # time.sleep(0.01) and wait a bit before interrupting TX stream for a CAT cmd
    #time.sleep(0.0005 + 32/audio_tx_rate_trusdx) # and wait until trusdx buffers are read
    time.sleep(0.010) # and wait a bit before interrupting TX stream for a CAT cmd

def send_cat(cmd, ser, pre_delay=0.003, post_delay=0.010):
    """Send CAT command with proper timing and buffer management.
    
    Args:
        cmd: The command bytes to send
        ser: Serial port object
        pre_delay: Delay before sending command (default 0.003s)
        post_delay: Delay after sending command (default 0.010s)
    """
    ser.flush()
    time.sleep(pre_delay)
    ser.write(cmd)
    ser.flush()
    time.sleep(post_delay)

def disable_cat_audio(ser):
    """Ensure audio stream to CAT is disabled after TX ends (UA0)."""
    state['cat_audio_enabled'] = False
    try:
        ser.write(b";UA0;")
        ser.flush()
        time.sleep(0.05)  # small settling delay
        log("Sent UA0 after TX", "DEBUG")
    except Exception as e:
        log(f"UA0 send error: {e}", "ERROR")

def enable_cat_audio(ser):
    """Send UA1; to truSDX to enable CAT-audio ahead of TX"""
    try:
        # First ensure we're in USB mode (MD2)
        send_cat(b'MD2;', ser, post_delay=0.050)  # Set USB mode first
        log('Sent MD2; (USB mode)', 'INFO')
        
        # Then enable CAT audio with longer delay
        send_cat(b'UA1;', ser, post_delay=0.100)  # Increased delay from 30ms to 100ms
        log('Sent UA1; (enable CAT-audio)', 'INFO')
        
        # Additional settling time for truSDX hardware
        time.sleep(0.050)  # Extra 50ms for hardware to stabilize
        
        # Set output power to maximum (100W) - truSDX might need this
        send_cat(b'PC100;', ser, post_delay=0.050)  # Set power to 100W
        log('Sent PC100; (set power to 100W)', 'INFO')
    except Exception as e:
        log(f'UA1 send failed: {e}', 'ERROR')

def handle_vox(samples8, ser):
    if (128 - min(samples8)) == 64 and (max(samples8) - 127) == 64: # if does contain very loud signal
        if not status[0]:
            if not state.get('cat_audio_enabled', False):
                log("TX sequence start – enabling CAT-audio", level='RECONNECT')
                enable_cat_audio(ser)
                state['cat_audio_enabled'] = True
            status[0] = True  # Set TX state BEFORE entering TX mode
            log("UA1 → TX0", level='RECONNECT')
            send_cat(b";TX0;", ser)  # TX0 = enter TX mode for truSDX
    elif status[0]:  # in TX and no audio detected (silence)
        tx_cat_delay(ser)  # Call delay BEFORE RX command
        log("TX0 → audio-stream → RX", level='RECONNECT')
        send_cat(b";RX;", ser)  # RX = exit TX mode for truSDX
        log("TX sequence end – disabling CAT-audio", level='RECONNECT')
        disable_cat_audio(ser)  # Send UA0 after exiting TX
        log("RX → UA0", level='RECONNECT')
        status[0] = False  # Clear TX state after exiting

def handle_rts_dtr(ser, cat):
    if not status[4] and (cat.cts or cat.dsr):
        if not state.get('cat_audio_enabled', False):
            enable_cat_audio(ser)
            state['cat_audio_enabled'] = True
        status[4] = True    # keyed by RTS/DTR
        status[0] = True    # Set TX state BEFORE entering TX mode
        #log("***TX mode - entering with TX1")
        send_cat(b";TX1;", ser)  # TX1 = enter TX mode
    elif status[4] and not (cat.cts or cat.dsr):  #if keyed by RTS/DTR
        tx_cat_delay(ser)  # Call delay BEFORE TX0 command
        send_cat(b";TX0;", ser)  # TX0 = exit TX mode
        disable_cat_audio(ser)  # Send UA0 after exiting TX
        status[4] = False
        status[0] = False  # Clear TX state after exiting
        #log("***RX mode - exited with TX0")
    
def handle_cat(pastream, ser, cat):
    if(cat.inWaiting()):
        if not status[3]:
            status[3] = True
            log("CAT interface active")
            print("\033[1;32m[CAT] Interface activated\033[0m")
        
        try:
            # Read all available data
            raw_data = cat.read(cat.inWaiting())
            if not raw_data:
                return
                
            print(f"\033[1;36m[DEBUG] Raw CAT data: {raw_data}\033[0m")
            
            # Handle partial commands and buffering
            if not hasattr(handle_cat, 'buffer'):
                handle_cat.buffer = b''
            
            # Add new data to buffer
            handle_cat.buffer += raw_data
            
            # Process complete commands (ending with ;)
            while b';' in handle_cat.buffer:
                # Find the first complete command
                cmd_end = handle_cat.buffer.find(b';')
                cmd_data = handle_cat.buffer[:cmd_end]
                handle_cat.buffer = handle_cat.buffer[cmd_end + 1:]
                
                if not cmd_data.strip():
                    continue
                
                d = cmd_data + b';'
                print(f"\033[1;35m[CMD] Processing: {d}\033[0m")
                
                # Try to handle TS-480 command locally first
                ts480_response = handle_ts480_command(d, ser)
                if ts480_response:
                    print(f"\033[1;34m[CAT] \033[0m{d.decode('utf-8', errors='ignore').strip()} \033[1;32m→\033[0m {ts480_response.decode('utf-8', errors='ignore').strip()}")
                    
                    # Synchronize CAT response transmission
                    try:
                        # Ensure buffer is clear and wait for any ongoing transmission to complete
                        cat.reset_output_buffer()
                        time.sleep(0.001)  # Brief pause to ensure buffer is actually clear
                        
                        # Write response in a single atomic operation
                        cat.write(ts480_response)
                        cat.flush()
                        
                        # Verify the response was sent cleanly
                        if config.get('verbose', False):
                            print(f"\033[1;36m[DEBUG] Sent clean CAT response: {ts480_response}\033[0m")
                            
                    except Exception as cat_error:
                        log(f"CAT write error: {cat_error}")
                        print(f"\033[1;31m[CAT ERROR] Failed to send response: {cat_error}\033[0m")
                    
                    log(f"I: {d}")
                    log(f"O: {ts480_response} (TS-480 emu)")
                    
                    # Small delay to prevent overwhelming the CAT interface
                    time.sleep(0.005)  # Increased delay for better synchronization
                    continue
                
                # Handle TX1 command - must send UA1 BEFORE forwarding TX1
                if d.startswith(b"TX1"):
                    # Need to unmute speaker before TX1
                    if not state.get('cat_audio_enabled', False):
                        print("\033[1;33m[TX] Enabling CAT audio (UA1) before TX1...\033[0m")
                        enable_cat_audio(ser)
                        state['cat_audio_enabled'] = True
                        
                        # Wait for hardware to process UA1 before sending TX1
                        time.sleep(0.2)  # Increased from 0.1 to 0.2
                        print("\033[1;36m[TX] CAT audio enabled, proceeding with TX1...\033[0m")
                        
                        # Query power to check if hardware is ready
                        power_response = query_radio('PC', retries=1, timeout=0.5, ser_handle=ser)
                        if power_response:
                            power_str = power_response.decode('utf-8').strip(';')
                            print(f"\033[1;36m[TX DEBUG] Power query before TX1: {power_str}\033[0m")
                        else:
                            print(f"\033[1;33m[TX DEBUG] No power response before TX1\033[0m")
                    
                    status[0] = True  # Set TX state BEFORE sending TX command
                    print("\033[1;31m[TX] Transmit mode\033[0m")
                    pastream.stop_stream()
                    pastream.start_stream()
                    time.sleep(0.1)  # Ensure stream is stable before reading
                
                # Forward to radio if not handled locally
                if status[0]:
                    tx_cat_delay(ser)
                    ser.write(b";")  # in TX mode, interrupt CAT stream by sending ; before issuing CAT cmd
                    ser.flush()
                
                log(f"I: {d}")
                ser.write(d)                # fwd data on CAT port to trx
                ser.flush()
                print(f"\033[1;33m[FWD] \033[0m{d.decode('utf-8', errors='ignore').strip()} \033[1;31m→ truSDX\033[0m")
                
                # For frequency queries, we need to wait for and capture the response
                if d.startswith(b"FA") and len(d) == 4:  # Frequency query (not set)
                    # Read the response from the radio
                    time.sleep(0.1)  # Give radio time to respond
                    if ser.in_waiting > 0:
                        response = ser.read(ser.in_waiting)
                        if response.startswith(b"FA") and len(response) >= 15:
                            new_freq = response[2:-1].decode().ljust(11,'0')[:11]
                            radio_state['vfo_a_freq'] = new_freq
                            freq_mhz = float(new_freq) / 1000000.0
                            print(f"\033[1;32m[FREQ] ✅ Updated frequency: {freq_mhz:.3f} MHz\033[0m")
                            refresh_header_only()
                            # Forward the response to CAT client
                            cat.write(response)
                            cat.flush()
                        else:
                            print(f"\033[1;33m[FREQ] No valid response from radio\033[0m")
                
                if d.startswith(b"TX0") or d.startswith(b"RX"):
                    # TX0 or RX command - exit TX mode
                    # Note: tx_cat_delay was already called above if status[0] was True
                    # So we don't need to call it again here
                    if state.get('cat_audio_enabled', False):
                        print("\033[1;33m[RX] Disabling CAT audio (UA0) after TX...\033[0m")
                        disable_cat_audio(ser)
                        state['cat_audio_enabled'] = False
                    status[0] = False  # Clear TX state after sending command
                    print("\033[1;32m[RX] Receive mode\033[0m")
                    pastream.stop_stream()
                    pastream.start_stream()
               
        except Exception as e:
            log(f"CAT error: {e}")
            print(f"\033[1;31m[CAT ERROR] {e}\033[0m")

def transmit_audio_via_serial(pastream, ser, cat):
    try:
        log("transmit_audio_via_serial_cat")
        while status[2]:
            handle_cat(pastream, ser, cat)
            if(platform == "win32" and not config['no_rtsdtr']): handle_rts_dtr(ser, cat)
            if (status[0] or config['vox']) and pastream.get_read_available() > 0:    # in TX mode, and audio available
                samples = pastream.read(config['block_size'], exception_on_overflow = False)
                arr = array.array('h', samples)
                samples8 = bytearray([128 + x//256 for x in arr])  # was //512 because with //256 there is 5dB too much signal. Win7 only support 16 bits input audio -> convert to 8 bits
                
                # Conservative filtering to prevent corruption of CAT responses
                # Only filter the most critical CAT command delimiter
                samples8 = samples8.replace(b'\x3b', b'\x3a')      # filter ; of stream (essential)
                
                if status[0]: ser.write(samples8)
                if config['vox']: handle_vox(samples8, ser)
            else:
                time.sleep(0.001)
    except (serial.SerialException, OSError) as e:
        log(f"Serial error in transmit_audio_via_serial: {e}")
        print(f"\033[1;33m[TX] 📡 Serial disconnection detected during transmission\033[0m")
        
        # Set disconnection flag and trigger reconnection
        state['hardware_disconnected'] = True
        state['connection_stable'] = False
        
        # Trigger reconnection if not already in progress
        if not state.get('reconnecting', False):
            print(f"\033[1;31m[TX] 🔄 Triggering reconnection from TX thread...\033[0m")
            threading.Thread(target=safe_reconnect, daemon=True).start()
        
        status[2] = False
        if config['verbose']: raise e
    except Exception as e:
        log(f"Unexpected error in transmit_audio_via_serial: {e}")
        status[2] = False
        if config['verbose']: raise

def poll_power():
    """Poll radio power output and detect watts=0 for reconnection feedback"""
    if config.get('no_power_monitor', False):
        log("Power monitoring disabled via CLI")
        return
    try:
        # Wait a bit for the system to stabilize before starting power polling
        time.sleep(5)
        
        log("Power monitor started", "INFO")
        print("\033[1;32m[POWER] Power monitoring active\033[0m")
        
        last_power_check = time.time()
        power_zero_count = 0
        tx_start_time = None
        
        while status[2]:
            try:
                current_time = time.time()
                
                # Poll power every POWER_POLL_INTERVAL seconds
                if current_time - last_power_check >= POWER_POLL_INTERVAL:
                    try:
                        # Only query power if we have a stable connection and ser is available
                        if (state.get('ser') and 
                            not state.get('reconnecting', False) and 
                            state.get('connection_stable', True)):
                            
                            power_response = query_radio('PC', retries=1, timeout=POWER_TIMEOUT)
                            
                            if power_response:
                                # Parse power response (format: PC<nnn>; where nnn is power in watts)
                                # Also handle FW000; firmware response indicating 0W
                                power_str = power_response.decode('utf-8').strip(';')
                                
                                # Handle both PC<nnn> and FW000 responses
                                if power_str.startswith('PC') and len(power_str) >= 5:
                                    try:
                                        watts = int(power_str[2:5])  # Extract 3-digit power value
                                    except ValueError:
                                        watts = 0
                                elif power_str.startswith('FW') and '000' in power_str:
                                    # FW000 firmware response indicates 0W - trigger reconnection logic
                                    watts = 0
                                    if config.get('verbose', False):
                                        log(f"FW000 firmware response detected - treating as 0W", "WARNING")
                                else:
                                    watts = 0
                                    if config.get('verbose', False):
                                        log(f"Invalid power response format: {power_str}", "WARNING")
                                
                                # Process the watts reading regardless of source (PC or FW)
                                if watts == 0:
                                    power_zero_count += 1
                                    # Log verbose message for watts=0
                                    if config.get('verbose', False):
                                        log(f"Power poll: 0W detected (count: {power_zero_count})", "WARNING")
                                    
                                    # Check if we are in TX mode and within the ignore period
                                    time_since_last_data = current_time - state['last_data_time']
                                    in_tx_ignore_period = status[0] and time_since_last_data <= TX_IGNORE_PERIOD
                                    
                                    if in_tx_ignore_period:
                                        if config.get('verbose', False):
                                            log(f"Ignoring 0W detection during TX ignore period ({time_since_last_data:.1f}s <= {TX_IGNORE_PERIOD}s)", "INFO")
                                        power_zero_count = 0  # Reset count during ignore period
                                    else:
                                        # Update header to show reconnecting status after multiple 0W readings
                                        if power_zero_count >= 3:  # Only after consistent 0W readings
                                            refresh_header_only({'watts': 0, 'reconnecting': True})
                                            print(f"\033[1;33m[POWER] Persistent 0W detected - connection may be unstable\033[0m")
                                else:
                                    # Reset count when we get valid power reading
                                    if power_zero_count > 0:
                                        log(f"Power restored: {watts}W", "INFO")
                                        print(f"\033[1;32m[POWER] ✅ Power restored: {watts}W\033[0m")
                                        refresh_header_only({'watts': watts, 'reconnecting': False})
                                    power_zero_count = 0
                            else:
                                # No response to power query - don't spam logs
                                if config.get('verbose', False):
                                    log("No response to power query", "WARNING")
                        
                        last_power_check = current_time
                        
                    except Exception as e:
                        if config.get('verbose', False):
                            log(f"Error in power polling iteration: {e}", "ERROR")
                
                time.sleep(2.0)  # Check every 2 seconds (less frequent to avoid issues)
                
            except Exception as e:
                if config.get('verbose', False):
                    log(f"Error in power polling loop: {e}", "ERROR")
                time.sleep(5.0)  # Wait longer on errors
            
    except Exception as e:
        log(f"Power monitor error: {e}", "ERROR")
        print(f"\033[1;31m[POWER ERROR] {e}\033[0m")

def monitor_connection():
    """Monitor connection health and trigger reconnection if needed"""
    try:
        log("Connection monitor started")
        print("\033[1;32m[MONITOR] Connection monitoring active\033[0m")
        
        while status[2]:
            with monitor_lock:
                current_time = time.time()
                time_since_data = current_time - state['last_data_time']
                
                # Use different timeouts based on TX status
                timeout_threshold = TX_CONNECTION_TIMEOUT if status[0] else CONNECTION_TIMEOUT
                
                # Check if we haven't received data for too long
                if time_since_data > timeout_threshold and state['connection_stable']:
                    tx_mode_str = "(TX MODE)" if status[0] else ""
                    print(f"\033[1;33m[MONITOR] ⚠️ No data for {time_since_data:.1f}s {tx_mode_str}- connection unstable\033[0m")
                    state['connection_stable'] = False
                    
                    # Log reconnection message with bold color header
                    log("Connection lost - initiating reconnection sequence", "RECONNECT")
                    
                    # Flag TX connection lost if in TX mode
                    if status[0]:
                        status[5] = True
                        print("\033[1;31m[MONITOR] 🚨 TX CONNECTION LOST - Priority reconnection!\033[0m")
                    
                    # Trigger reconnection if not already in progress
                    if not state['reconnecting']:
                        print("\033[1;31m[MONITOR] 🔄 Triggering automatic reconnection...\033[0m")
                        threading.Thread(target=safe_reconnect, daemon=True).start()
                
                # Reset connection status if we've received recent data
                elif time_since_data <= 1.0 and not state['connection_stable']:
                    state['connection_stable'] = True
                    state['reconnect_count'] = 0
                    log("Connection restored successfully", "RECONNECT")
                    print("\033[1;32m[MONITOR] ✅ Connection restored\033[0m")
            
            time.sleep(1.0)  # Check every second
            
    except Exception as e:
        log(f"Connection monitor error: {e}")
        print(f"\033[1;31m[MONITOR ERROR] {e}\033[0m")

def update_data_timestamp():
    """Update the timestamp when data is received"""
    with monitor_lock:
        state['last_data_time'] = time.time()
        was_unstable = not state['connection_stable'] or status[5]
        if was_unstable:
            state['connection_stable'] = True
            status[5] = False  # Clear TX connection lost flag
            print("\033[1;32m[MONITOR] ✅ Data received - connection and TX stable\033[0m")

def safe_reconnect():
    """Safely reconnect hardware with atomic handle replacement"""
    global status
    
    with handle_lock:
        if state['reconnecting']:
            print("\033[1;33m[RECONNECT] Already reconnecting, skipping...\033[0m")
            return

        state['reconnecting'] = True
        state['reconnect_count'] += 1
        
        # Only limit reconnections if MAX_RECONNECT_ATTEMPTS > 0
        if MAX_RECONNECT_ATTEMPTS > 0:
            if state['reconnect_count'] > MAX_RECONNECT_ATTEMPTS:
                print(f"\033[1;33m[RECONNECT] ⚠️ Max retries ({MAX_RECONNECT_ATTEMPTS}) exceeded. Waiting 10s before resetting counter...\033[0m")
                log(f"Max reconnect attempts reached, waiting before retry", "WARNING")
                time.sleep(10)
                state['reconnect_count'] = 0  # Reset counter and try again
                print(f"\033[1;33m[RECONNECT] 🔄 Resetting counter and continuing reconnection attempts...\033[0m")
        else:
            # Infinite reconnection mode
            if state['reconnect_count'] % 10 == 0 and state['reconnect_count'] > 0:
                print(f"\033[1;36m[RECONNECT] ℹ️ Reconnection attempt #{state['reconnect_count']} (infinite mode)\033[0m")
        
        log(f"Connection issue detected - attempting reconnection #{state['reconnect_count']}")
        
        if MAX_RECONNECT_ATTEMPTS > 0:
            print(f"\033[1;33m[RECONNECT] 🔄 Reconnection attempt #{state['reconnect_count']}/{MAX_RECONNECT_ATTEMPTS}...\033[0m")
        else:
            print(f"\033[1;33m[RECONNECT] 🔄 Reconnection attempt #{state['reconnect_count']} (infinite mode)...\033[0m")

        # Preserve radio state (frequency, mode) and TX status
        preserved_freq = radio_state['vfo_a_freq']
        preserved_mode = radio_state['mode']
        preserved_state = radio_state.copy()
        was_transmitting = status[0]  # Remember if we were transmitting
        
        # Stop threads and audio
        old_status = status[2]
        status[2] = False
        time.sleep(0.5)  # Allow threads to stop
        
        # Close old handles
        try:
            if state['ser']:
                state['ser'].close()
                log("Closed ser")
            if state['ser2']:
                state['ser2'].close()
                log("Closed ser2")
            if state['in_stream']:
                state['in_stream'].close()
                log("Closed in_stream")
            if state['out_stream']:
                state['out_stream'].close()
                log("Closed out_stream")
        except Exception as e:
            log(f"Error closing handles: {e}")

        print(f"\033[1;33m[RECONNECT] Waiting {RECONNECT_DELAY}s before reinitializing...\033[0m")
        time.sleep(RECONNECT_DELAY)

        # Reinitialize hardware
        try:
            # Reinitialize using the same logic as the original run() function
            platform_config = get_platform_config()
            
            new_ser = serial.Serial(
                find_serial_device(platform_config['trusdx_serial_dev']), 
                115200, 
                write_timeout=0
            )
            
            # Set up serial port 2
            if platform_config['loopback_serial_dev']:
                new_ser2 = serial.Serial(
                    port=platform_config['loopback_serial_dev'], 
                    baudrate=115200, 
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                    write_timeout=1,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False
                )
            else:
                new_ser2 = new_ser  # Use the same port if no loopback
            
            # Use the open_audio_streams function with retry logic during reconnection
            log(f"[RECONNECT] Attempting to reopen audio streams...")
            new_in_stream, new_out_stream = open_audio_streams(platform_config, config, state, retry_on_busy=True)
            
            if not new_in_stream and not new_out_stream:
                log(f"[RECONNECT] No audio streams could be reopened, continuing without audio", "WARNING")
                print(f"\033[1;33m[RECONNECT] ⚠️ No audio streams available - continuing in CAT-only mode\033[0m")
            elif not new_in_stream:
                log(f"[RECONNECT] TX audio stream unavailable, continuing with RX only", "WARNING")
                print(f"\033[1;33m[RECONNECT] ⚠️ TX audio unavailable - continuing in RX-only mode\033[0m")
            elif not new_out_stream:
                log(f"[RECONNECT] RX audio stream unavailable, continuing with TX only", "WARNING")
                print(f"\033[1;33m[RECONNECT] ⚠️ RX audio unavailable - continuing in TX-only mode\033[0m")
            else:
                log(f"[RECONNECT] Both audio streams reopened successfully")
                print(f"\033[1;32m[RECONNECT] ✅ Audio streams restored\033[0m")
            
            # Atomically replace handles (only if successfully opened)
            state['ser'] = new_ser
            state['ser2'] = new_ser2
            if new_in_stream:
                state['in_stream'] = new_in_stream
            if new_out_stream:
                state['out_stream'] = new_out_stream
            
            # Reset CAT buffer in handle_cat
            if hasattr(handle_cat, 'buffer'):
                handle_cat.buffer = b''
                log("CAT buffer reset after reconnection")
            
            # Initialize radio with proper commands - send separately with delays
            new_ser.write(b";MD2;")  # Set USB mode first
            new_ser.flush()
            time.sleep(0.2)  # Give hardware time to process mode change
            
            # Then set audio mute state
            audio_cmd = b";UA2;" if not config['unmute'] else b";UA1;"
            new_ser.write(audio_cmd)
            new_ser.flush()
            time.sleep(0.3)
            
            # Initialize radio - send commands separately with delays
            time.sleep(2)  # Wait for device to stabilize
            
            # Set USB mode first
            new_ser.write(b";MD2;")
            new_ser.flush()
            time.sleep(0.3)  # Wait for mode change to process
            
            # Then set audio mute state
            audio_cmd = b";UA2;" if not config['unmute'] else b";UA1;"
            new_ser.write(audio_cmd)
            new_ser.flush()
            time.sleep(0.5)
            
            # Speaker-mute guarantee on reconnection - send unconditionally
            try:
                if config['unmute']:
                    new_ser.write(b";UA1;")
                    new_ser.flush()
                    log("Speaker unmuted")
                    print(f"\033[1;33m[RECONNECT] ✅ Speaker unmuted (UA1)\033[0m")
                else:
                    new_ser.write(b";UA2;")
                    new_ser.flush()
                    log("Speaker muted")
                    print(f"\033[1;32m[RECONNECT] ✅ Speaker muted (UA2)\033[0m")
                time.sleep(0.2)  # Give radio time to process
            except Exception as mute_error:
                log(f"Error setting speaker mute state during reconnection: {mute_error}")
                print(f"\033[1;31m[RECONNECT] Error setting speaker mute state: {mute_error}\033[0m")
            
        except Exception as e:
            log(f"Error during hardware re-init: {e}")
            print(f"\033[1;31m[RECONNECT] ❌ Reinitialization failed: {e}\033[0m")
            state['reconnecting'] = False
            return

        # Restore radio state values and re-apply them if necessary
        radio_state.update(preserved_state)
        
        # Re-apply frequency and mode to radio
        try:
            if state['ser']:
                # Re-apply frequency
                freq_cmd = f";FA{preserved_freq};"
                state['ser'].write(freq_cmd.encode('utf-8'))
                state['ser'].flush()
                time.sleep(0.1)
                
                # Re-apply mode
                mode_cmd = f";MD{preserved_mode};"
                state['ser'].write(mode_cmd.encode('utf-8'))
                state['ser'].flush()
                time.sleep(0.1)
                
                # If we were transmitting before disconnection, restart TX
                if was_transmitting and status[5]:
                    print("\033[1;31m[RECONNECT] 🔄 Restoring TX mode after connection lost...\033[0m")
                    send_cat(b";TX1;", state['ser'])  # TX1 = enter TX mode
                    status[0] = True  # Restore TX state
                
                freq_mhz = float(preserved_freq) / 1000000.0
                log(f"Re-applied radio settings: freq={freq_mhz:.3f}MHz, mode={preserved_mode}")
                print(f"\033[1;36m[RECONNECT] 📻 Restored frequency: {freq_mhz:.3f} MHz, mode: {preserved_mode}\033[0m")
                
        except Exception as e:
            log(f"Error re-applying radio settings: {e}")
            print(f"\033[1;33m[RECONNECT] ⚠️ Warning: Could not restore radio settings: {e}\033[0m")

        # Restart threads
        status[2] = True
        threading.Thread(target=receive_serial_audio, args=(state['ser'], state['ser2'], state['out_stream']), daemon=True).start()
        threading.Thread(target=play_receive_audio, args=(state['out_stream'],), daemon=True).start()
        threading.Thread(target=transmit_audio_via_serial, args=(state['in_stream'], state['ser'], state['ser2']), daemon=True).start()
        
        # Restart connection monitoring
        threading.Thread(target=monitor_connection, daemon=True).start()
        
        # Reset flags
        status[0] = False
        status[1] = False
        status[3] = False
        status[4] = False
        
        # Update timestamps
        state['last_data_time'] = time.time()
        state['connection_stable'] = True
        state['reconnecting'] = False
        
        log("Reconnection completed successfully")
        print("\033[1;32m[RECONNECT] ✅ Reconnection completed successfully!\033[0m")
        
        # Reset hardware disconnected flag after successful reconnection
        state['hardware_disconnected'] = False

def get_platform_config():
    """Get platform-specific configuration"""
    if platform == "linux" or platform == "linux2":
        return {
            # IMPORTANT: These are from the driver's perspective:
            # - virtual_audio_dev_out: Audio OUTPUT from driver to WSJT-X (RX audio)
            # - virtual_audio_dev_in: Audio INPUT to driver from WSJT-X (TX audio)
            'virtual_audio_dev_out': "TRUSDX_monitor",  # RX audio output to WSJT-X (Option #1 - preferred)
            'virtual_audio_dev_in': "TRUSDX",           # TX audio input from WSJT-X (Option #1 - preferred)
            'trusdx_serial_dev': "USB Serial",
            'loopback_serial_dev': "",
            'cat_serial_dev': "",
            'alt_cat_serial_dev': PERSISTENT_PORTS['cat_port']
        }
    elif platform == "win32":
        return {
            'virtual_audio_dev_out': "CABLE Output",
            'virtual_audio_dev_in': "CABLE Input",
            'trusdx_serial_dev': "CH340",
            'loopback_serial_dev': "COM9",
            'cat_serial_dev': "COM8"
        }
    else:  # darwin
        return {
            'virtual_audio_dev_out': "BlackHole 2ch",
            'virtual_audio_dev_in': "BlackHole 2ch",
            'trusdx_serial_dev': "USB Serial",
            'loopback_serial_dev': "",
            'cat_serial_dev': ""
        }

def pty_echo(fd1, fd2):
    try:
        log("pty_echo")
        initial_wait = True
        while status[2]:
            try:
                # Give the system time to establish connections on startup
                if initial_wait:
                    time.sleep(1.0)  # Wait 1 second before starting to prevent immediate disconnection
                    initial_wait = False
                    log("PTY echo thread ready")
                    
                c1 = fd1.read(1)
                if not c1:  # EOF or device disconnected
                    time.sleep(0.001)
                    continue
                fd2.write(c1)
                # Update data timestamp when we see activity
                update_data_timestamp()
                #print(f'{datetime.datetime.utcnow()} {threading.current_thread().ident} > ', c1)
            except (OSError, IOError) as e:
                if e.errno in [5, 9]:  # Errno 5: I/O error, Errno 9: Bad file descriptor
                    # Don't exit immediately - this might be a temporary condition
                    if initial_wait:
                        # Still in initial phase, just wait
                        time.sleep(0.1)
                        continue
                    log(f"PTY I/O error (may be temporary): {e}")
                    time.sleep(0.5)  # Wait before retrying
                    continue  # Don't break, keep trying
                elif e.errno == 25:  # Errno 25: Inappropriate ioctl for device (RTS/DTR related)
                    # Hamlib's ioctl will still fail in the C layer, so we trap the IOError
                    # in the PTY echo thread and just ignore it - keeps stderr clean without touching JS8Call
                    log(f"PTY ioctl error (RTS/DTR related) - ignoring: {e}")
                    time.sleep(0.001)
                    continue
                else:
                    log(f"PTY I/O error (errno {e.errno}): {e}")
                    time.sleep(0.1)
                    continue
            except Exception as e:
                log(f"Unexpected error in pty_echo: {e}")
                time.sleep(0.1)
                continue
                
    except Exception as e:
        log(f"Fatal error in pty_echo: {e}")
        status[2] = False
        if config['verbose']: raise
    
    log("pty_echo thread exiting gracefully")

# https://stackoverflow.com/questions/7088672/pyaudio-working-but-spits-out-error-messages-each-time
def run():
    try:
        status[0] = False
        status[1] = False
        status[2] = True
        status[3] = False
        status[4] = False

        # Load persistent configuration
        persistent_config = load_config()
        PERSISTENT_PORTS.update(persistent_config)
        
        # Create persistent serial ports
        create_persistent_serial_ports()

        if platform == "linux" or platform == "linux2":
           # Use ALSA loopback devices for audio (Option #1 - PREFERRED)
           # IMPORTANT: These are from the perspective of WSJT-X/JS8Call:
           # - TRUSDX.monitor receives audio FROM the radio (RX audio for WSJT-X to decode)
           # - TRUSDX sends audio TO the radio (TX audio from WSJT-X)
           virtual_audio_dev_out = "TRUSDX_monitor"  # RX audio FROM radio (goes OUT to WSJT-X)
           virtual_audio_dev_in  = "TRUSDX"          # TX audio TO radio (comes IN from WSJT-X)
           trusdx_serial_dev     = "USB Serial"
           loopback_serial_dev   = ""
           cat_serial_dev        = ""
           alt_cat_serial_dev    = PERSISTENT_PORTS['cat_port']
        elif platform == "win32":
           virtual_audio_dev_out = "CABLE Output"
           virtual_audio_dev_in  = "CABLE Input"
           trusdx_serial_dev     = "CH340"
           loopback_serial_dev   = "COM9"
           cat_serial_dev        = "COM8"
        elif platform == "darwin":
           virtual_audio_dev_out = "BlackHole 2ch"
           virtual_audio_dev_in  = "BlackHole 2ch"
           trusdx_serial_dev     = "USB Serial"
           loopback_serial_dev   = ""
           cat_serial_dev        = ""

        if config['direct']:
           virtual_audio_dev_out = "" # default audio device
           virtual_audio_dev_in  = "" # default audio device

        if config['verbose']:
            show_audio_devices()
            print("Audio device = ", find_audio_device(virtual_audio_dev_in), find_audio_device(virtual_audio_dev_out) )
            show_serial_devices()
            print("Serial device = ", find_serial_device(trusdx_serial_dev) )
            print("Serial loopback = ", find_serial_device(loopback_serial_dev) )
        
        if platform == "win32":
            if find_serial_device(loopback_serial_dev):
                print(f"Conflict on COM port {loopback_serial_dev}: Go to Device Manager, select CH340 device and change in advanced settings COM port other than 8 or 9.")
                time.sleep(1)
            if find_serial_device(cat_serial_dev):
                print(f"Conflict on COM port {cat_serial_dev}: Go to Device Manager, select CH340 device and change in advanced settings COM port other than 8 or 9.")
                time.sleep(1)

        if platform != "win32":  # skip for Windows as we have com0com there
           _master1, slave1 = os.openpty()  # make a tty <-> tty device where one end is opened as serial device, other end by CAT app
           _master2, slave2 = os.openpty()
           master1 = os.fdopen(_master1, 'rb+', 0)
           master2 = os.fdopen(_master2, 'rb+', 0)
           threading.Thread(target=pty_echo, args=(master1,master2)).start()
           threading.Thread(target=pty_echo, args=(master2,master1)).start()
           cat_serial_dev = os.ttyname(slave1)
           
           # Create persistent symlink
           if os.path.exists(alt_cat_serial_dev): 
               os.remove(alt_cat_serial_dev)
           os.symlink(cat_serial_dev, alt_cat_serial_dev)
           print(f"Created persistent CAT port: {alt_cat_serial_dev} -> {cat_serial_dev}")
           
           loopback_serial_dev = os.ttyname(slave2)
        try:
            # Configure serial port with proper settings for Hamlib
            ser2 = serial.Serial(
                port=loopback_serial_dev, 
                baudrate=115200, 
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                write_timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            
            # Emulate RTS/DTR success inside the Python driver
            # Before opening ser2 (the PTY side), monkey-patch RTS/DTR methods
            if hasattr(ser2, "setRTS"):  # pyserial ≥3
                ser2.setRTS = lambda x: None
                ser2.setDTR = lambda x: None
            
            # Monkey-patch serial.Serial.rts/dtr properties to harmless no-ops
            # This prevents Hamlib's ioctl calls from raising exceptions in Python layer
            original_rts_fget = serial.Serial.rts.fget if hasattr(serial.Serial.rts, 'fget') else None
            original_rts_fset = serial.Serial.rts.fset if hasattr(serial.Serial.rts, 'fset') else None
            original_dtr_fget = serial.Serial.dtr.fget if hasattr(serial.Serial.dtr, 'fget') else None
            original_dtr_fset = serial.Serial.dtr.fset if hasattr(serial.Serial.dtr, 'fset') else None
            
            def noop_rts_get(self): return True  # Always report RTS as active
            def noop_rts_set(self, value): pass  # Do nothing when setting RTS
            def noop_dtr_get(self): return True  # Always report DTR as active  
            def noop_dtr_set(self, value): pass  # Do nothing when setting DTR
            
            # Apply monkey patches
            serial.Serial.rts = property(noop_rts_get, noop_rts_set)
            serial.Serial.dtr = property(noop_dtr_get, noop_dtr_set)
            print(f"\033[1;32m[SERIAL] CAT port configured: {loopback_serial_dev}\033[0m")
        except Exception as e:
            if platform == "win32":
                print("VSPE virtual com port not found: reinstall or enable")
            else:
                print(f"\033[1;31m[ERROR] /dev/pts/x device not found: {e}\033[0m")
        
        try:
           # Use the new open_audio_streams function with retry logic
           platform_config = {
               'virtual_audio_dev_out': virtual_audio_dev_out,
               'virtual_audio_dev_in': virtual_audio_dev_in
           }
           
           # Open audio streams with retry logic for device-busy errors
           in_stream, out_stream = open_audio_streams(platform_config, config, state, retry_on_busy=True)
           
           # Check if we got at least one stream
           if not in_stream and not out_stream:
               print(f"\033[1;31m[AUDIO] ❌ Failed to open any audio streams\033[0m")
               if platform == "win32":
                   print("VB-Audio CABLE not found: reinstall or enable")
               else:
                   print("\033[1;33m[AUDIO] ALSA loopback devices not found\033[0m")
                   print("\033[1;33m[AUDIO] Run setup.sh to configure ALSA loopback devices (trusdx_tx, trusdx_rx)\033[0m")
               # Don't raise an error - continue running in CAT-only mode
           elif not in_stream:
               print(f"\033[1;33m[AUDIO] ⚠️ TX audio unavailable - continuing in RX-only mode\033[0m")
           elif not out_stream:
               print(f"\033[1;33m[AUDIO] ⚠️ RX audio unavailable - continuing in TX-only mode\033[0m")
        except Exception as e:
            if platform == "win32": print("VB-Audio CABLE not found: reinstall or enable")
            else:
                print(f"\033[1;31m[AUDIO] ❌ Audio device error: {e}\033[0m")
                print("\033[1;33m[AUDIO] ALSA loopback devices not found\033[0m")
                print("\033[1;33m[AUDIO] Run setup.sh to configure ALSA loopback devices (trusdx_tx, trusdx_rx)\033[0m")
            raise
 
        try:
            # Try to find the truSDX device
            trusdx_port = find_serial_device(trusdx_serial_dev)
            if not trusdx_port:
                # Fallback: try common USB serial ports
                for fallback_port in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']:
                    if os.path.exists(fallback_port):
                        print(f"\033[1;33m[SERIAL] Using fallback port: {fallback_port}\033[0m")
                        trusdx_port = fallback_port
                        break
                
                if not trusdx_port:
                    raise Exception("No USB serial device found. Is the truSDX connected?")
            else:
                print(f"\033[1;32m[SERIAL] Found truSDX on: {trusdx_port}\033[0m")
            
            ser = serial.Serial(trusdx_port, 115200, write_timeout = 0)
            print(f"\033[1;32m[SERIAL] ✅ Connected to truSDX on {trusdx_port}\033[0m")
        except Exception as e:
            print(f"\033[1;31m[ERROR] truSDX device not found: {e}\033[0m")
            print(f"\033[1;33m[HINT] Make sure the truSDX is connected via USB\033[0m")
            print(f"\033[1;33m[HINT] You may need to be in the 'dialout' group: sudo usermod -a -G dialout $USER\033[0m")
            raise
            
        #ser.dtr = True
        #ser.rts = False
        time.sleep(3) # wait for device to start after opening serial port
        
        # Initialize radio with basic commands like the working 1.1.6 version
        print(f"\033[1;33m[INIT] Initializing radio communication...\033[0m")
        try:
            # Send basic initialization commands (like working 1.1.6)
            # UA2 = muted speaker, UA1 = unmuted speaker
            # Send commands separately with delays for better hardware compatibility
            ser.write(b";MD2;")  # Set USB mode first
            ser.flush()
            time.sleep(0.3)  # Give hardware time to process mode change

            # Retry setting audio mute/unmute state
            retries = 3
            for attempt in range(retries):
                audio_cmd = b";UA2;" if not config['unmute'] else b";UA1;"
                ser.write(audio_cmd)
                ser.flush()
                time.sleep(0.5)  # Give radio time to process

                # Capture response for logging
                response = ser.read(ser.in_waiting)
                log(f"Attempt {attempt + 1}/{retries}: Sent {audio_cmd.decode()} - received: {response}")
                
                # Assuming success response end with ';'
                if response.endswith(b';'):
                    break
                else:
                    time.sleep(0.2)  # Additional delay before retry
            
            # Ensure speaker is muted by sending explicit mute command
            if not config['unmute']:
                ser.write(b";UA2;")  # Explicitly mute the speaker
                ser.flush() 
                time.sleep(0.2)
                print(f"\033[1;32m[INIT] ✅ Radio speaker muted (UA2)\033[0m")
            else:
                print(f"\033[1;33m[INIT] ✅ Radio speaker unmuted (UA1) - use --unmute flag to enable\033[0m")
                
            print(f"\033[1;32m[INIT] ✅ Radio initialized with basic commands\033[0m")
        except Exception as e:
            print(f"\033[1;31m[INIT] Error initializing radio: {e}\033[0m")
        
        # CRITICAL: Read actual frequency from radio BEFORE JS8Call connects
        print(f"\033[1;33m[INIT] Reading actual frequency from radio...\033[0m")
        
        freq_success = False
        for attempt in range(3):  # Try 3 times with different delays
            try:
                print(f"\033[1;36m[INIT] Frequency reading attempt {attempt + 1}/3...\033[0m")
                
                # Clear any pending data
                if ser.in_waiting > 0:
                    old_data = ser.read(ser.in_waiting)
                    print(f"\033[1;33m[DEBUG] Cleared old data: {old_data}\033[0m")
                
                # Send frequency query
                ser.write(b";FA;")
                ser.flush()
                print(f"\033[1;36m[DEBUG] Sent FA command to radio\033[0m")
                
                # Wait with increasing delay
                wait_time = 0.5 + (attempt * 0.3)  # 0.5s, 0.8s, 1.1s
                time.sleep(wait_time)
                
                # Check for response
                if ser.in_waiting > 0:
                    response = ser.read(ser.in_waiting)
                    print(f"\033[1;36m[DEBUG] Raw radio response: {response}\033[0m")
                    
                    # Look for FA response in the data
                    if b'FA' in response:
                        # Find FA response
                        fa_start = response.find(b'FA')
                        fa_data = response[fa_start:]
                        
                        # Look for the semicolon that ends the command
                        if b';' in fa_data:
                            fa_end = fa_data.find(b';')
                            fa_response = fa_data[:fa_end + 1]
                            print(f"\033[1;36m[DEBUG] Extracted FA response: {fa_response}\033[0m")
                            
                            if len(fa_response) >= 13:  # FA + 11 digits + ;
                                try:
                                    actual_freq = fa_response[2:-1].decode().ljust(11,'0')[:11]
                                    if actual_freq != '00000000000' and actual_freq.isdigit():
                                        radio_state['vfo_a_freq'] = actual_freq
                                        freq_mhz = float(actual_freq) / 1000000.0
                                        print(f"\033[1;32m[INIT] ✅ Successfully read frequency: {freq_mhz:.3f} MHz\033[0m")
                                        freq_success = True
                                        break
                                    else:
                                        print(f"\033[1;33m[INIT] Invalid frequency data: {actual_freq}\033[0m")
                                except Exception as decode_error:
                                    print(f"\033[1;31m[INIT] Error decoding frequency: {decode_error}\033[0m")
                            else:
                                print(f"\033[1;33m[INIT] FA response too short: {fa_response}\033[0m")
                        else:
                            print(f"\033[1;33m[INIT] No semicolon found in FA data: {fa_data}\033[0m")
                    else:
                        print(f"\033[1;33m[INIT] No FA command found in response: {response}\033[0m")
                else:
                    print(f"\033[1;33m[INIT] No response from radio (attempt {attempt + 1})\033[0m")
                    
            except Exception as e:
                print(f"\033[1;31m[INIT] Error in frequency reading attempt {attempt + 1}: {e}\033[0m")
            
            if not freq_success and attempt < 2:
                print(f"\033[1;33m[INIT] Retrying in 1 second...\033[0m")
                time.sleep(1)
        
        if not freq_success:
            print(f"\033[1;31m[INIT] ❌ Failed to read frequency after 3 attempts\033[0m")
            print(f"\033[1;33m[INIT] Using fallback frequency: {float(radio_state['vfo_a_freq'])/1000000:.3f} MHz\033[0m")
        
        # Show what frequency we'll report to JS8Call
        current_freq = float(radio_state['vfo_a_freq']) / 1000000.0
        print(f"\033[1;36m[INIT] Will report {current_freq:.3f} MHz to CAT clients\033[0m")
        #status[1] = True
        
        # Speaker-mute guarantee on startup - send unconditionally
        try:
            if config['unmute']:
                ser.write(b";UA1;")
                ser.flush()
                log("Speaker unmuted")
                print(f"\033[1;33m[INIT] ✅ Speaker unmuted (UA1)\033[0m")
            else:
                ser.write(b";UA2;")
                ser.flush()
                log("Speaker muted")
                print(f"\033[1;32m[INIT] ✅ Speaker muted (UA2)\033[0m")
            time.sleep(0.2)  # Give radio time to process
        except Exception as e:
            log(f"Error setting speaker mute state: {e}")
            print(f"\033[1;31m[INIT] Error setting speaker mute state: {e}\033[0m")

        # Store handles in state dictionary for monitoring and reconnection
        with handle_lock:
            state['ser'] = ser
            state['ser2'] = ser2
            state['in_stream'] = in_stream
            state['out_stream'] = out_stream
        
        print(f"\033[1;36m[DEBUG] Starting receive_serial_audio thread...\033[0m")
        threading.Thread(target=receive_serial_audio, args=(ser,ser2,out_stream), daemon=True).start()
        time.sleep(0.1)
        print(f"\033[1;36m[DEBUG] Starting play_receive_audio thread...\033[0m")
        threading.Thread(target=play_receive_audio, args=(out_stream,), daemon=True).start()
        time.sleep(0.1)
        print(f"\033[1;36m[DEBUG] Starting transmit_audio_via_serial thread...\033[0m")
        threading.Thread(target=transmit_audio_via_serial, args=(in_stream,ser,ser2), daemon=True).start()
        time.sleep(0.1)
        
        # Start connection monitoring after initialization stabilizes
        def delayed_connection_monitoring():
            time.sleep(5)  # Wait 5 seconds for system to stabilize
            # Initialize timestamp before monitoring starts
            state['last_data_time'] = time.time()
            monitor_connection()
        
        threading.Thread(target=delayed_connection_monitoring, daemon=True).start()
        
        # Start power polling for reconnection feedback after initial stabilization
        # Wait for main initialization to complete before starting power monitoring
        def delayed_power_polling():
            time.sleep(10)  # Wait 10 seconds for system to fully stabilize
            poll_power()
        
        threading.Thread(target=delayed_power_polling, daemon=True).start()

        clear_screen()
        if not config.get('no_header', False):
            show_persistent_header()
        print(f"\033[1;32m[INIT] truSDX-AI Driver v{VERSION} started successfully!\033[0m")
        print(f"\033[1;37m[INFO] Available devices:\033[0m [{virtual_audio_dev_in}, {virtual_audio_dev_out}, {cat_serial_dev}]")
        print(f"\033[1;37m[INFO] Persistent CAT port:\033[0m {alt_cat_serial_dev}")
        
        # Audio devices are now using ALSA loopback (no PulseAudio setup needed)
        print(f"\033[1;32m[AUDIO] Using ALSA loopback devices (Option #1):\033[0m")
        print(f"\033[1;36m  • {virtual_audio_dev_in} → TX audio from WSJT-X to radio\033[0m")
        print(f"\033[1;36m  • {virtual_audio_dev_out} → RX audio from radio to WSJT-X\033[0m")
        
        print(f"\033[1;36m[READY] Waiting for connections from WSJT-X/JS8Call...\033[0m")
        print()
        
        # Save current configuration
        save_config(PERSISTENT_PORTS)
        
        #ts = time.time()
        # Add debug tracking for main loop
        loop_count = 0
        header_refresh_count = 0
        shutdown_requested = False
        
        while status[2]:    # wait and idle
            loop_count += 1
            
            # Only print debug messages in verbose mode
            if config.get('verbose', False) and loop_count % 60 == 0:
                print(f"\033[1;36m[DEBUG] Main loop iteration {loop_count}, running normally\033[0m")
            
            # Check if hardware disconnection was detected
            if state.get('hardware_disconnected', False):
                # Don't exit, just trigger reconnection
                if not state.get('reconnecting', False):
                    log("Hardware disconnection detected in main loop - triggering reconnection")
                    print(f"\033[1;33m[MAIN] Hardware disconnection detected - attempting reconnection...\033[0m")
                    threading.Thread(target=safe_reconnect, daemon=True).start()
                    state['hardware_disconnected'] = False  # Clear flag
                time.sleep(1)
                continue
            
            # Check thread status
            if config.get('verbose', False) and loop_count % 120 == 0:
                thread_count = threading.active_count()
                print(f"\033[1;36m[DEBUG] Active threads: {thread_count}\033[0m")
            
            # Refresh header every 30 seconds (30 iterations since we sleep 1 second)
            header_refresh_count += 1
            if header_refresh_count >= 30:
                header_refresh_count = 0
                if not config.get('no_header', False):
                    refresh_header_only()
            
            # display some stats every 1 seconds
            #log(f"{int(time.time()-ts)} buf: {len(buf)}")
            time.sleep(1)
            
            # Check for keyboard interrupt or shutdown request
            if shutdown_requested:
                print("\033[1;33m[MAIN] Shutdown requested, cleaning up...\033[0m")
                status[2] = False
                break
    except Exception as e:
        log(e)
        status[2] = False
    except KeyboardInterrupt:
        print("\n\033[1;33m[MAIN] Keyboard interrupt - shutting down gracefully...\033[0m")
        status[2] = False
        # Ensure speaker is muted before exit
        if ser:
            try:
                ser.write(b";UA2;")  # Mute speaker
                ser.flush()
            except:
                pass
        shutdown_requested = True

    try:
        # clean-up
        log("Closing")
        time.sleep(1)   
        if platform != "win32":  # Linux
           #master1.close()
           #master2.close()
           #os.close(_master1)           
           os.close(slave1)
           #os.close(_master2)
           os.close(slave2)
           log("fd closed")
        ser2.close()
        ser.close()
        if in_stream:
            in_stream.stop_stream()
            in_stream.close()
        if out_stream:
            out_stream.stop_stream()
            out_stream.close()
        # Note: PyAudio instance will be terminated by atexit handler
        log("Closed")
    except Exception as e:
        log(e)
        pass	

def check_js8call_ini():
    """Check JS8Call.ini for RTS/DTR settings and warn user once if still enabled"""
    js8call_ini_paths = [
        os.path.expanduser("~/.config/JS8Call.ini"),
        os.path.expanduser("~/.config/js8call/JS8Call.ini"),
        os.path.expanduser("~/AppData/Local/JS8Call/JS8Call.ini"),
        os.path.expanduser("~/Library/Preferences/JS8Call.ini")
    ]
    
    for ini_path in js8call_ini_paths:
        if os.path.exists(ini_path):
            try:
                config_parser = configparser.ConfigParser()
                config_parser.read(ini_path)
                
                # Check for RTS/DTR settings in Configuration section
                if 'Configuration' in config_parser:
                    cat_force_rts = config_parser.get('Configuration', 'CATForceRTS', fallback='false').lower()
                    cat_force_dtr = config_parser.get('Configuration', 'CATForceDTR', fallback='false').lower()
                    
                    if cat_force_rts == 'true' or cat_force_dtr == 'true':
                        print(f"\033[1;33m[CONFIG] ⚠️  JS8Call.ini still has RTS/DTR enabled ({ini_path})\033[0m")
                        print(f"\033[1;33m[CONFIG] ℹ️  This is now safely absorbed by the driver's monkey-patch\033[0m")
                        print(f"\033[1;33m[CONFIG] 💡 Consider disabling RTS/DTR in JS8Call settings for cleaner operation\033[0m")
                        return  # Only show warning once, even if multiple settings are true
                        
                break  # Found and processed the file, no need to check other paths
                
            except Exception as e:
                if config.get('verbose', False):
                    print(f"\033[1;33m[CONFIG] Could not parse {ini_path}: {e}\033[0m")
                continue

def main():
    # Python version check
    if sys.version_info < MIN_PYTHON_VERSION:
        print(f"ERROR: Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]} or higher is required.")
        print(f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        sys.exit(1)
    
    if not config.get('no_header', False):
        show_version_info()
        log("Starting truSDX-AI Driver...", "INFO")
    
    # Check JS8Call.ini for RTS/DTR settings and warn if needed
    check_js8call_ini()
    
    max_restart_attempts = 5
    restart_count = 0
    
    while restart_count < max_restart_attempts:
        try:
            # Reset global state for fresh start
            state['hardware_disconnected'] = False
            state['connection_stable'] = True
            state['reconnecting'] = False
            state['reconnect_count'] = 0
            
            run()  # Main execution
            
            # If run() exits normally, check if it was due to hardware disconnection
            if state.get('hardware_disconnected', False):
                restart_count += 1
                log(f"[RESTART] Hardware disconnection detected - attempting restart #{restart_count}/{max_restart_attempts} in 3 seconds...", "WARNING")
                
                if restart_count >= max_restart_attempts:
                    log(f"[FATAL] Maximum restart attempts ({max_restart_attempts}) exceeded after hardware disconnections. Exiting.", "ERROR")
                    break
                    
                time.sleep(3)
                continue  # Restart the main loop
            else:
                # Normal exit - break the loop
                log("[EXIT] truSDX-AI Driver exiting normally", "INFO")
                break
            
        except Exception as e:
            restart_count += 1
            log(f"Main loop error (attempt {restart_count}/{max_restart_attempts}): {e}")
            log(f"[ERROR] Main loop failed (attempt {restart_count}/{max_restart_attempts}): {e}", "ERROR")
            
            if restart_count >= max_restart_attempts:
                log(f"[FATAL] Maximum restart attempts ({max_restart_attempts}) exceeded. Exiting.", "ERROR")
                break
            
            # Check if it was a hardware disconnection
            if state.get('hardware_disconnected', False):
                log("[RESTART] Hardware disconnection detected - attempting restart in 3 seconds...", "WARNING")
                time.sleep(3)
            else:
                # Wait before retrying to prevent rapid restart loops
                log("[RESTART] Unexpected error - retrying in 5 seconds...", "WARNING")
                time.sleep(5)
    
    log("[EXIT] truSDX-AI Driver exiting gracefully", "INFO")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f"truSDX-AI audio driver v{VERSION}", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="increase verbosity")
    parser.add_argument("--vox", action="store_true", default=False, help="VOX audio-triggered PTT (Linux only)")
    parser.add_argument("--unmute", action="store_true", default=False, help="Enable (tr)usdx audio")
    parser.add_argument("--direct", action="store_true", default=False, help="Use system audio devices directly (bypasses ALSA Loopback card 0)")
    parser.add_argument("--no-rtsdtr", action="store_true", default=False, help="Disable RTS/DTR-triggered PTT")
    parser.add_argument("-B", "--block-size", type=int, default=512, help="RX Block size")
    parser.add_argument("-T", "--tx-block-size", type=int, default=48, help="TX Block size")
    parser.add_argument("--no-header", action="store_true", default=False, help="Skip initial version display")
    parser.add_argument("--no-power-monitor", action="store_true", default=False, help="Disable power monitoring feature")
    parser.add_argument("--logfile", type=str, help="Override default log file location")
    args = parser.parse_args()
    config = vars(args)
    
    # Setup logging before any other operations
    setup_logging()
    
    if config['verbose']: 
        print(config)
        log(f"Configuration loaded: {config}")

    main()

