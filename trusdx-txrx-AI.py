#!/usr/bin/env python3
# de SQ3SWF, PE1NNZ 2023
# Enhanced AI version with Kenwood TS-480 CAT interface and persistent serial ports
# Version: 1.2.3 (2025-07-10)

# Linux:
# sudo apt install portaudio19-dev
# stty -F /dev/ttyUSB0 raw -echo -echoe -echoctl -echoke -hupcl 115200;
# pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"
# pavucontrol
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

import pyaudio
import serial
import serial.tools.list_ports
import threading
import time
import os
import datetime
import array
import argparse
import json
import configparser
from sys import platform
import sys

# Version information
VERSION = "1.2.3"
BUILD_DATE = "2025-07-10"
AUTHOR = "SQ3SWF, PE1NNZ, AI-Enhanced - MONITORING & RECONNECT"
COMPATIBLE_PROGRAMS = ["WSJT-X", "JS8Call", "FlDigi", "Winlink"]

audio_tx_rate_trusdx = 4800
audio_tx_rate = 11520  #11521
audio_rx_rate = 7812
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
    'hardware_disconnected': False
}

# Thread-safe locks for handle replacement and monitoring
handle_lock = threading.Lock()
monitor_lock = threading.Lock()

# Connection monitoring settings
CONNECTION_TIMEOUT = 3.0  # Seconds without data before considering connection lost (reduced for TX)
TX_CONNECTION_TIMEOUT = 1.5  # Faster detection for TX mode
RECONNECT_DELAY = 1.0     # Faster reconnection (reduced from 2.0)
MAX_RECONNECT_ATTEMPTS = 3 # Reduced attempts for faster recovery
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
    'audio_device': 'TRUSDX'
}

# Global logging configuration
LOG_FILE = None
LOG_LOCK = threading.Lock()

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
            except Exception as e:
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
    print(f"\033[1;35m  Audio:\033[0m {PERSISTENT_PORTS['audio_device']} (Input/Output) | \033[1;35mPTT:\033[0m CAT | \033[1;35mStatus:\033[0m Ready")
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
    print(f"\033[1;35m  Audio:\033[0m {PERSISTENT_PORTS['audio_device']} (Input/Output) | \033[1;35mPTT:\033[0m CAT | \033[1;35mStatus:\033[0m Ready")
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
    print(f"  Input Device: {PERSISTENT_PORTS['audio_device']}")
    print(f"  Output Device: {PERSISTENT_PORTS['audio_device']}")
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
    except Exception as e:
        log(f"Error loading config: {e}")
    return PERSISTENT_PORTS.copy()

def save_config(config_data):
    """Save persistent configuration"""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
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
    except Exception as e:
        log(f"Error creating persistent ports: {e}")
        return False

def check_audio_setup():
    """Check if TRUSDX audio device is properly configured"""
    try:
        # Check if TRUSDX sink exists
        result = os.popen('pactl list sinks | grep -c "Name: TRUSDX"').read().strip()
        if result == '0':
            print(f"\033[1;33m[AUDIO] TRUSDX sink not found, auto-loading module-null-sink...\033[0m")
            # Auto-load module-null-sink with TRUSDX name
            load_result = os.popen('pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"').read().strip()
            if load_result.isdigit():
                print(f"\033[1;32m[AUDIO] ✅ TRUSDX sink created successfully (module ID: {load_result})\033[0m")
                log(f"Loaded module-null-sink TRUSDX with module ID: {load_result}")
            else:
                print(f"\033[1;31m[AUDIO] ❌ Failed to create TRUSDX sink: {load_result}\033[0m")
                log(f"Failed to load module-null-sink: {load_result}")
                return False
            time.sleep(1)
        else:
            print(f"\033[1;32m[AUDIO] ✅ TRUSDX sink already exists\033[0m")
        
        # Verify it exists now and get its index
        sink_info = os.popen('pactl list sinks | grep -A 2 "Name: TRUSDX"').read()
        if 'TRUSDX' in sink_info:
            # Extract sink index if available
            lines = sink_info.split('\n')
            for i, line in enumerate(lines):
                if 'Sink #' in line:
                    sink_index = line.split('#')[1].strip()
                    print(f"\033[1;36m[AUDIO] TRUSDX sink index: {sink_index}\033[0m")
                    log(f"TRUSDX sink index: {sink_index}")
                    break
            return True
        else:
            print(f"\033[1;31m[AUDIO] ❌ TRUSDX sink verification failed\033[0m")
            return False
        
    except Exception as e:
        log(f"Audio setup error: {e}")
        print(f"\033[1;31m[AUDIO] Error during setup: {e}\033[0m")
        return False

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
    for i in range(pyaudio.PyAudio().get_device_count()):
        print(pyaudio.PyAudio().get_device_info_by_index(i))
    for i in range(pyaudio.PyAudio().get_host_api_count()):
        print(pyaudio.PyAudio().get_host_api_info_by_index(i))
        
def find_audio_device(name, occurance = 0):
    try:
        p = pyaudio.PyAudio()
        result = []
        trusdx_devices = []  # Specifically track TRUSDX devices
        
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = device_info['name']
            
            # Special handling for TRUSDX devices
            if 'TRUSDX' in device_name:
                if device_info['maxInputChannels'] > 0 and '.monitor' in device_name:
                    trusdx_devices.append((i, device_name, 'input'))
                    if config.get('verbose', False):
                        print(f"\033[1;36m[AUDIO] Found TRUSDX.monitor (input) - index: {i}, channels: {device_info['maxInputChannels']}\033[0m")
                elif device_info['maxOutputChannels'] > 0:
                    trusdx_devices.append((i, device_name, 'output'))
                    if config.get('verbose', False):
                        print(f"\033[1;36m[AUDIO] Found TRUSDX (output) - index: {i}, channels: {device_info['maxOutputChannels']}\033[0m")
            
            if name.lower() in device_name.lower():
                result.append(i)
                log(f"Found audio device: {device_name} (index {i})")
                if config.get('verbose', False):
                    print(f"\033[1;90m[AUDIO] Device {i}: {device_name} (in:{device_info['maxInputChannels']}, out:{device_info['maxOutputChannels']})\033[0m")
        
        p.terminate()
        
        # If looking for TRUSDX, use the specifically found devices
        if 'TRUSDX' in name:
            if name == 'TRUSDX.monitor':
                # Find input device (monitor)
                for idx, dev_name, dev_type in trusdx_devices:
                    if dev_type == 'input' and '.monitor' in dev_name:
                        log(f"Using TRUSDX.monitor device index {idx}")
                        print(f"\033[1;32m[AUDIO] Selected TRUSDX.monitor (index: {idx})\033[0m")
                        return idx
            else:
                # Find output device (sink)
                for idx, dev_name, dev_type in trusdx_devices:
                    if dev_type == 'output' and '.monitor' not in dev_name:
                        log(f"Using TRUSDX sink device index {idx}")
                        print(f"\033[1;32m[AUDIO] Selected TRUSDX sink (index: {idx})\033[0m")
                        return idx
        
        if len(result) > occurance:
            log(f"Using audio device index {result[occurance]} for '{name}'")
            return result[occurance]
        else:
            log(f"Audio device '{name}' not found, using default (-1)")
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
        
        if state['reconnect_count'] > MAX_RECONNECT_ATTEMPTS:
            print(f"\033[1;31m[RECONNECT] ❌ Max retries ({MAX_RECONNECT_ATTEMPTS}) exceeded. Setting hardware disconnected flag.\033[0m")
            log(f"FATAL: Maximum retry limit ({MAX_RECONNECT_ATTEMPTS}) exceeded. Unable to maintain stable connection.", "ERROR")
            state['reconnecting'] = False
            state['hardware_disconnected'] = True  # Set flag for main loop to exit and restart
            status[2] = False  # Stop all threads
            return
        
        log(f"Connection issue detected - attempting reconnection #{state['reconnect_count']}")
        print(f"\033[1;33m[RECONNECT] 🔄 Reconnection attempt #{state['reconnect_count']}/{MAX_RECONNECT_ATTEMPTS}...\033[0m")

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
            
            # Set up audio streams
            new_in_stream = pyaudio.PyAudio().open(
                frames_per_buffer=config['block_size'], 
                format=pyaudio.paInt16, 
                channels=1, 
                rate=audio_tx_rate, 
                input=True, 
                input_device_index=find_audio_device(platform_config['virtual_audio_dev_out']) if platform_config['virtual_audio_dev_out'] else -1
            )
            
            new_out_stream = pyaudio.PyAudio().open(
                frames_per_buffer=0, 
                format=pyaudio.paUInt8, 
                channels=1, 
                rate=audio_rx_rate, 
                output=True, 
                output_device_index=find_audio_device(platform_config['virtual_audio_dev_in']) if platform_config['virtual_audio_dev_in'] else -1
            )
            
            # Atomically replace handles
            state['ser'] = new_ser
            state['ser2'] = new_ser2
            state['in_stream'] = new_in_stream
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
            'virtual_audio_dev_out': "TRUSDX",         # Sink for output
            'virtual_audio_dev_in': "TRUSDX.monitor",  # Monitor for input
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
        while status[2]:
            try:
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
                    log(f"PTY device disconnected: {e}")
                    print(f"\033[1;33m[PTY] 🔌 Virtual device disconnected\033[0m")
                    break  # Exit gracefully
                elif e.errno == 25:  # Errno 25: Inappropriate ioctl for device (RTS/DTR related)
                    # Hamlib's ioctl will still fail in the C layer, so we trap the IOError
                    # in the PTY echo thread and just ignore it - keeps stderr clean without touching JS8Call
                    log(f"PTY ioctl error (RTS/DTR related) - ignoring: {e}")
                    time.sleep(0.001)
                    continue
                else:
                    log(f"PTY I/O error: {e}")
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
           # Use TRUSDX null-sink devices for audio
           virtual_audio_dev_out = "TRUSDX"         # Audio from WSJT-X/JS8Call to truSDX (sink)
           virtual_audio_dev_in  = "TRUSDX.monitor" # Audio from truSDX to WSJT-X/JS8Call (monitor)
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
           # Setup audio streams with proper device indices
           in_device_idx = find_audio_device(virtual_audio_dev_out) if virtual_audio_dev_out else -1
           out_device_idx = find_audio_device(virtual_audio_dev_in) if virtual_audio_dev_in else -1
           
           if config.get('verbose', False):
               print(f"\033[1;36m[AUDIO] Opening streams - Input device: {virtual_audio_dev_out} (index: {in_device_idx}), Output device: {virtual_audio_dev_in} (index: {out_device_idx})\033[0m")
           
           # in_stream receives audio from WSJT-X/JS8Call via TRUSDX sink
           in_stream = pyaudio.PyAudio().open(frames_per_buffer=config['block_size'], format = pyaudio.paInt16, channels = 1, rate = audio_tx_rate, input = True, input_device_index = in_device_idx)
           # out_stream sends audio to WSJT-X/JS8Call via TRUSDX.monitor
           out_stream = pyaudio.PyAudio().open(frames_per_buffer=0, format = pyaudio.paUInt8, channels = 1, rate = audio_rx_rate, output = True, output_device_index = out_device_idx)
           
           print(f"\033[1;32m[AUDIO] ✅ Audio streams opened successfully\033[0m")
        except Exception as e:
            if platform == "win32": print("VB-Audio CABLE not found: reinstall or enable")
            else:
                print("\033[1;31m[AUDIO] ❌ Audio device error: {e}\033[0m")
                print("\033[1;33m[AUDIO] The TRUSDX sink will be auto-created if missing\033[0m")
                print("\033[1;33m[AUDIO] Manual command: pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description=\"TRUSDX\"\033[0m")
            raise
 
        try:
            ser = serial.Serial(find_serial_device(trusdx_serial_dev), 115200, write_timeout = 0)
        except Exception as e:
            print("truSDX device not found")
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
        
        # Check and setup audio
        audio_status = check_audio_setup()
        if audio_status:
            print(f"\033[1;32m[AUDIO] TRUSDX audio device ready\033[0m")
        else:
            print(f"\033[1;33m[AUDIO] TRUSDX audio device needs setup - see instructions\033[0m")
        
        print(f"\033[1;36m[READY] Waiting for connections from WSJT-X/JS8Call...\033[0m")
        print()
        
        # Save current configuration
        save_config(PERSISTENT_PORTS)
        
        #ts = time.time()
        # Add debug tracking for main loop
        loop_count = 0
        header_refresh_count = 0
        while status[2]:    # wait and idle
            loop_count += 1
            print(f"\033[1;36m[DEBUG] Main loop iteration {loop_count}, status[2]={status[2]}\033[0m")
            
            # Check if hardware disconnection was detected
            if state.get('hardware_disconnected', False):
                log("Hardware disconnection detected in main loop - exiting to restart")
                print(f"\033[1;33m[MAIN] Hardware disconnection detected - triggering restart...\033[0m")
                status[2] = False  # Stop all threads
                break
            
            # Check thread status
            thread_count = threading.active_count()
            print(f"\033[1;36m[DEBUG] Active threads: {thread_count}\033[0m")
            
            # Refresh header every 30 seconds (30 iterations since we sleep 1 second)
            header_refresh_count += 1
            if header_refresh_count >= 30:
                header_refresh_count = 0
                if not config.get('no_header', False):
                    refresh_header_only()
                    print(f"\033[1;36m[HEADER] Periodic header refresh\033[0m")
            
            # display some stats every 1 seconds
            #log(f"{int(time.time()-ts)} buf: {len(buf)}")
            time.sleep(1)
    except Exception as e:
        log(e)
        status[2] = False
    except KeyboardInterrupt:
        print("Stopping")
        status[2] = False
        ser.write(b";UA0;")

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
        #in_stream.close()
        #out_stream.close()
        pyaudio.PyAudio().terminate()
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
    parser.add_argument("--direct", action="store_true", default=False, help="Use system audio devices (no loopback)")
    parser.add_argument("--no-rtsdtr", action="store_true", default=False, help="Disable RTS/DTR-triggered PTT")
    parser.add_argument("-B", "--block-size", type=int, default=512, help="RX Block size")
    parser.add_argument("-T", "--tx-block-size", type=int, default=48, help="TX Block size")
    parser.add_argument("--no-header", action="store_true", default=False, help="Skip initial version display")
    parser.add_argument("--no-power-monitor", action="store_true", default=True, help="Disable power monitoring feature")
    parser.add_argument("--logfile", type=str, help="Override default log file location")
    args = parser.parse_args()
    config = vars(args)
    
    # Setup logging before any other operations
    setup_logging()
    
    if config['verbose']: 
        print(config)
        log(f"Configuration loaded: {config}")

    main()

