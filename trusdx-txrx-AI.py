#!/usr/bin/env python3
# de SQ3SWF, PE1NNZ 2023
# Enhanced AI version with Kenwood TS-480 CAT interface and persistent serial ports
# Version: 1.1.8-AI-TX0-FREQ-FIXED (2025-06-23)

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
import math
from sys import platform

# Version information
VERSION = "1.2.0-AI-MONITORING-RECONNECT"
BUILD_DATE = "2025-06-27"
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

def log(msg, level="INFO"):
    """Log message with optional level and formatting
    
    Args:
        msg: Message to log
        level: Log level ("INFO", "WARNING", "ERROR", "RECONNECT")
    """
    if config['verbose']:
        timestamp = datetime.datetime.utcnow()
        
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

def check_term_color():
    """Check if terminal supports color based on TERM environment variable."""
    term = os.getenv("TERM", "")
    # Check for common color-capable terminals
    color_terms = ['xterm', 'screen', 'tmux', 'rxvt', 'konsole', 'gnome']
    return any(color_term in term for color_term in color_terms) or 'color' in term

def get_color_code(color_code):
    """Return color code if terminal supports color, otherwise empty string."""
    return color_code if check_term_color() else ""

def show_persistent_header():
    """Display persistent header with version and connection info"""
    # Colors with fallback
    clr_green = get_color_code("\033[1;32m")
    clr_cyan = get_color_code("\033[1;36m")
    clr_yellow = get_color_code("\033[1;33m")
    clr_white = get_color_code("\033[1;37m")
    clr_magenta = get_color_code("\033[1;35m")
    reset = get_color_code("\033[0m")
    
    # Setup screen with scrolling region
    print("\033[2J", end="")  # Clear entire screen
    print("\033[H", end="")   # Move cursor to home position
    print(clr_green + "="*80 + reset)  # Green header line
    print(f"{clr_cyan}truSDX-AI Driver v{VERSION}{reset} - {clr_yellow}{BUILD_DATE}{reset}")
    
    # Load config to get callsign
    persistent_config = load_config()
    callsign = persistent_config.get('callsign', 'N/A')
    print(f"{clr_white}Callsign: {callsign}{reset}")
    
    print(f"{clr_magenta}  Radio:{reset} Kenwood TS-480 | {clr_magenta}Port:{reset} {PERSISTENT_PORTS['cat_port']} | {clr_magenta}Baud:{reset} 115200 | {clr_magenta}Poll:{reset} 80ms")
    print(f"{clr_magenta}  Audio:{reset} {PERSISTENT_PORTS['audio_device']} (Input/Output) | {clr_magenta}PTT:{reset} CAT | {clr_magenta}Status:{reset} Ready")
    print(clr_green + "="*80 + reset)  # Green header line
    print()
    # Set scrolling region to start after header (lines 7 onwards)
    print("\033[7;24r", end="")  # Set scrolling region from line 7 to 24
    print("\033[7;1H", end="")   # Move cursor to line 7

def refresh_header_only(power_info=None):
    """Refresh just the header without clearing screen
    
    Args:
        power_info: Dict with 'watts' and 'reconnecting' status for power display
    """
    # Colors with fallback
    clr_green = get_color_code("\033[1;32m")
    clr_cyan = get_color_code("\033[1;36m")
    clr_yellow = get_color_code("\033[1;33m")
    clr_white = get_color_code("\033[1;37m")
    clr_magenta = get_color_code("\033[1;35m")
    reset = get_color_code("\033[0m")
    
    # Save cursor position
    print("\033[s", end="")  # Save cursor position
    
    # Move to header area and redraw
    print("\033[1;1H", end="")  # Move to top-left
    
    # Clear header area only (7 lines)
    for i in range(7):
        print(f"\033[{i+1};1H\033[K", end="")  # Clear each header line
    
    # Redraw header
    print("\033[1;1H", end="")  # Back to top
    print(clr_green + "="*80 + reset)  # Green header line
    print(f"{clr_cyan}truSDX-AI Driver v{VERSION}{reset} - {clr_yellow}{BUILD_DATE}{reset}")
    
    # Load config to get callsign
    persistent_config = load_config()
    callsign = persistent_config.get('callsign', 'N/A')
    print(f"{clr_white}Callsign: {callsign}{reset}")
    
    # Build status line with power information
    status_line = f"{clr_magenta}  Radio:{reset} Kenwood TS-480 | {clr_magenta}Port:{reset} {PERSISTENT_PORTS['cat_port']} | {clr_magenta}Baud:{reset} 115200 | {clr_magenta}Poll:{reset} 80ms"
    
    # Add power status if provided
    if power_info:
        if power_info.get('reconnecting', False) or power_info.get('watts', 0) == 0:
            status_line += f" | {clr_yellow}Power: {power_info.get('watts', 0)}W (reconnecting...){reset}"
        else:
            status_line += f" | {clr_green}Power: {power_info.get('watts', 0)}W{reset}"
    
    print(status_line)
    print(f"{clr_magenta}  Audio:{reset} {PERSISTENT_PORTS['audio_device']} (Input/Output) | {clr_magenta}PTT:{reset} CAT | {clr_magenta}Status:{reset} Ready")
    print(clr_green + "="*80 + reset)  # Green header line
    print()
    
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
            print(f"\033[1;33m[AUDIO] Creating TRUSDX audio device...\033[0m")
            os.system('pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"')
            time.sleep(1)
        
        # Verify it exists now
        result = os.popen('pactl list sinks | grep -c "Name: TRUSDX"').read().strip()
        return result == '1'
        
    except Exception as e:
        log(f"Audio setup error: {e}")
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
            # Hamlib/rigctld expects EXACTLY 37 characters (not including IF and ;)
            # Real TS-480 format: IF<11-digit freq><5-digit RIT/XIT><RIT><XIT><Bank><RX/TX><Mode><VFO><Scan><Split><Tone><ToneFreq><CTCSS>;
            # Total: IF + 37 chars + ; = 40 characters
            
            # Build IF response matching real TS-480 format
            freq = radio_state['vfo_a_freq'][:11].ljust(11, '0')     # 11 digits - frequency
            rit_xit = '00000'                                        # 5 digits - RIT/XIT offset (always 00000)
            rit = '0'                                                # 1 digit - RIT off
            xit = '0'                                                # 1 digit - XIT off
            bank = '00'                                              # 2 digits - memory bank
            rxtx = '0'                                               # 1 digit - RX/TX status (0=RX)
            mode = '2'                                               # 1 digit - mode (2=USB)
            vfo = '0'                                                # 1 digit - VFO selection (0=VFO A)
            scan = '0'                                               # 1 digit - scan status
            split = '0'                                              # 1 digit - split status
            tone = '0'                                               # 1 digit - tone status
            tone_freq = '08'                                         # 2 digits - tone frequency
            ctcss = '0'                                              # 1 digit - CTCSS status
            
            # Calculate remaining padding to reach exactly 37 characters
            # Current: 11+5+1+1+2+1+1+1+1+1+1+2+1 = 29 chars
            # Need: 37 - 29 = 8 more chars
            padding = '00000000'  # 8 digits padding
            
            # Build response with exactly 37 characters
            content = f'{freq}{rit_xit}{rit}{xit}{bank}{rxtx}{mode}{vfo}{scan}{split}{tone}{tone_freq}{ctcss}{padding}'
            
            # Ensure exactly 37 characters - this is critical for rigctld
            if len(content) != 37:
                log(f"Warning: IF content length {len(content)} != 37, fixing")
                content = content[:37].ljust(37, '0')
            
            response = f'IF{content};'
            
            # Final verification
            if len(response) != 40:
                log(f"Error: IF response length {len(response)} != 40: {response}")
                # Use fallback response
                response = f'IF{freq}00000000200000080000000;'
            
            log(f"IF response: {response} (total: {len(response)}, content: {len(content)})")
            return response.encode('utf-8')
        
        # AI command - auto information (critical for Hamlib)
        elif cmd_str.startswith('AI'):
            if len(cmd_str) > 2:
                # Set AI mode
                radio_state['ai_mode'] = cmd_str[2]
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
                    print(f"\033[1;32m[CAT] \u2705 Allowing frequency change to {freq_mhz:.3f} MHz\033[0m")
                    radio_state['vfo_a_freq'] = freq
                    refresh_header_only()
                    return None  # Forward to radio
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
                return None  # Forward to radio
            else:
                # Read VFO B frequency
                freq = radio_state['vfo_b_freq'].ljust(11, '0')[:11]
                return f'FB{freq};'.encode('utf-8')
        
        # Mode commands
        elif cmd_str.startswith('MD'):
            if len(cmd_str) > 2:
                # Set mode - forward to hardware and update state
                radio_state['mode'] = cmd_str[2]
                return None  # Forward to radio
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
        
        # VFO operations - critical for Hamlib VFO handling
        elif cmd_str.startswith('FR'):
            if len(cmd_str) > 2:
                # Set RX VFO - validate and update state
                vfo_val = cmd_str[2]
                if vfo_val in ['0', '1']:  # 0=VFO A, 1=VFO B
                    radio_state['rx_vfo'] = vfo_val
                    log(f"Set RX VFO to {vfo_val} ({'A' if vfo_val == '0' else 'B'})")
                    return None  # Forward to radio
                else:
                    log(f"Invalid VFO value: {vfo_val}")
                    return None
            else:
                # Read RX VFO
                return f'FR{radio_state["rx_vfo"]};'.encode('utf-8')
                
        elif cmd_str.startswith('FT'):
            if len(cmd_str) > 2:
                # Set TX VFO - validate and update state
                vfo_val = cmd_str[2]
                if vfo_val in ['0', '1']:  # 0=VFO A, 1=VFO B
                    radio_state['tx_vfo'] = vfo_val
                    log(f"Set TX VFO to {vfo_val} ({'A' if vfo_val == '0' else 'B'})")
                    return None  # Forward to radio
                else:
                    log(f"Invalid VFO value: {vfo_val}")
                    return None
            else:
                # Read TX VFO
                return f'FT{radio_state["tx_vfo"]};'.encode('utf-8')
        
        # VFO selection commands (specific to Kenwood)
        elif cmd_str == 'VS':
            # VFO swap
            log("VFO swap command - not implemented")
            return None
        
        elif cmd_str.startswith('VS'):
            if len(cmd_str) > 2:
                # Set VFO - this might be the command causing issues
                vfo_val = cmd_str[2]
                if vfo_val in ['0', '1']:  # 0=VFO A, 1=VFO B
                    radio_state['rx_vfo'] = vfo_val
                    radio_state['tx_vfo'] = vfo_val
                    log(f"Set current VFO to {vfo_val} ({'A' if vfo_val == '0' else 'B'})")
                    return f'VS{vfo_val};'.encode('utf-8')
                else:
                    log(f"Invalid VFO selection: {vfo_val}")
                    return None
            else:
                # Read current VFO
                return f'VS{radio_state["rx_vfo"]};'.encode('utf-8')
        
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
        elif cmd_str.startswith('TX') or cmd_str == 'RX':
            return None  # Don't handle locally - forward to truSDX
        
        # Generic commands that should just be acknowledged
        elif cmd_str in ['TX', 'RX']:
            return cmd
            
        # Filter and other commands
        elif cmd_str.startswith('FL') or cmd_str.startswith('IS') or cmd_str.startswith('NB') or cmd_str.startswith('NR'):
            return cmd  # Echo back filter commands
        
        # Handle common Hamlib initialization commands
        elif cmd_str == 'KS':
            return b'KS020;'  # Keying speed (CW)
        elif cmd_str == 'EX':
            return b'EX;'     # Menu extension
        elif cmd_str.startswith('EX'):
            return cmd        # Echo back EX commands
        
        # For unknown commands, don't return error - just ignore
        elif cmd_str:
            log(f"Unknown CAT command: {cmd_str} - ignoring")
            # Don't return anything for unknown commands
            return None
        
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
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            device_name = device_info['name']
            if name.lower() in device_name.lower():
                result.append(i)
                log(f"Found audio device: {device_name} (index {i})")
        p.terminate()
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
                cat.write(d)
                cat.flush()
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

def monitor_audio_levels(samples8, arr, source="unknown"):
    """Monitor audio levels for VU meter debugging and diagnostics"""
    if not samples8 or not arr:
        return
    
    # Calculate various audio level metrics
    min_8bit = min(samples8)
    max_8bit = max(samples8)
    avg_8bit = sum(samples8) / len(samples8)
    
    # Calculate 16-bit metrics
    min_16bit = min(arr) if arr else 0
    max_16bit = max(arr) if arr else 0
    rms_16bit = int((sum(x*x for x in arr) / len(arr)) ** 0.5) if arr else 0
    
    # Calculate dynamic range and signal strength
    range_8bit = max_8bit - min_8bit
    signal_strength_8bit = max(abs(128 - min_8bit), abs(max_8bit - 128))
    
    # VU meter equivalent calculation (approximation)
    # VU meter typically shows RMS levels with some peak response
    vu_level_db = 20 * math.log10(rms_16bit / 32767.0) if rms_16bit > 0 else -60
    
    # Only log if there's significant signal or if verbose debugging is enabled
    if signal_strength_8bit > 10 or config.get('verbose', False):
        log(f"Audio levels [{source}] - 8bit: min={min_8bit}, max={max_8bit}, avg={avg_8bit:.1f}, range={range_8bit}, strength={signal_strength_8bit}")
        log(f"Audio levels [{source}] - 16bit: min={min_16bit}, max={max_16bit}, rms={rms_16bit}, vu_db={vu_level_db:.1f}dB")
        
        # Warning if signal levels are too low for VU meter
        if signal_strength_8bit < 5:
            log(f"WARNING: Very low audio signal strength ({signal_strength_8bit}) - VU meter may bounce to zero", "WARNING")


def handle_vox(samples8, ser):
    # Updated VOX detection logic for improved audio levels
    # With the new division by 128, we need to adjust the thresholds
    
    if len(samples8) > 0:
        min_val = min(samples8)
        max_val = max(samples8)
        
        # Calculate signal range from center (128)
        signal_range = max(abs(128 - min_val), abs(max_val - 128))
        
        # Improved VOX threshold - trigger on significant signal deviation
        # Adjusted for the new audio scaling (division by 128 instead of 256)
        vox_threshold = 32  # Equivalent to about 25% of full scale
        
        if signal_range > vox_threshold:  # if contains loud signal
            if not status[0]:
                status[0] = True
                if config.get('verbose', False):
                    log(f"VOX triggered - signal range: {signal_range}, threshold: {vox_threshold}")
                ser.write(b";TX0;")
                ser.flush()
        elif status[0]:  # in TX and no audio detected (silence)
            tx_cat_delay(ser)
            ser.write(b";RX;")
            ser.flush()
            status[0] = False
            if config.get('verbose', False):
                log(f"VOX released - signal range: {signal_range}, threshold: {vox_threshold}")

def handle_rts_dtr(ser, cat):
    if not status[4] and (cat.cts or cat.dsr):
        status[4] = True    # keyed by RTS/DTR
        status[0] = True
        #log("***TX mode")
        ser.write(b";TX0;")
        ser.flush()
    elif status[4] and not (cat.cts or cat.dsr):  #if keyed by RTS/DTR
        tx_cat_delay(ser)
        ser.write(b";RX;")
        ser.flush()
        status[4] = False
        status[0] = False
        #log("***RX mode")
    
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
                    cat.write(ts480_response)
                    cat.flush()
                    log(f"I: {d}")
                    log(f"O: {ts480_response} (TS-480 emu)")
                    
                    # Small delay to prevent overwhelming the CAT interface
                    time.sleep(0.001)
                    continue
                
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
                
                if d.startswith(b"TX"):
                   status[0] = True
                   print("\033[1;31m[TX] Transmit mode\033[0m")
                   pastream.stop_stream()
                   pastream.start_stream()
                   pastream.read(config['block_size'], exception_on_overflow = False)
                if d.startswith(b"RX"):
                   status[0] = False
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
                
                # Improved audio level calculation to prevent VU meter bouncing to zero
                # Scale 16-bit signed audio (-32768 to 32767) to 8-bit unsigned (0 to 255)
                # Using division by 128 instead of 256 to maintain proper signal levels
                # This gives us approximately 20dB louder signal level as requested
                samples8 = bytearray([min(255, max(0, 128 + x//128)) for x in arr])
                
                # Monitor audio levels for VU meter debugging
                # This helps identify if the VU meter is bouncing to zero due to low signal levels
                if len(samples8) > 0:
                    # Use the dedicated audio level monitoring function
                    monitor_audio_levels(samples8, arr, "TX_AUDIO")
                
                samples8 = samples8.replace(b'\x3b', b'\x3a')      # filter ; of stream
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
            
            # Initialize radio with proper commands
            # UA2 = mute speaker (default and when --mute-speaker is set)
            # UA1 = unmute speaker (only when --unmute is set and --mute-speaker is not set)
            if config.get('mute_speaker', False):
                init_cmd = b";MD2;UA2;"  # Force mute speaker while keeping VU meter active
            elif config.get('unmute', False):
                init_cmd = b";MD2;UA1;"  # Enable speaker audio
            else:
                init_cmd = b";MD2;UA2;"  # Default: mute speaker
            new_ser.write(init_cmd)
            new_ser.flush()
            time.sleep(0.3)
            
            # Initialize radio
            time.sleep(2)  # Wait for device to stabilize
            # Apply the same logic for the second initialization
            if config.get('mute_speaker', False):
                init_cmd = b";MD2;UA2;"  # Force mute speaker while keeping VU meter active
            elif config.get('unmute', False):
                init_cmd = b";MD2;UA1;"  # Enable speaker audio
            else:
                init_cmd = b";MD2;UA2;"  # Default: mute speaker
            new_ser.write(init_cmd)
            new_ser.flush()
            time.sleep(0.5)
            
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
                    state['ser'].write(b";TX0;")
                    state['ser'].flush()
                    status[0] = True  # Restore TX state
                    time.sleep(0.2)
                
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
            'virtual_audio_dev_out': "",
            'virtual_audio_dev_in': "",
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
           # Use empty string for default audio devices - this is what worked in 1.1.6
           virtual_audio_dev_out = ""#"TRUSDX"
           virtual_audio_dev_in  = ""#"TRUSDX"
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
            print(f"\033[1;32m[SERIAL] CAT port configured: {loopback_serial_dev}\033[0m")
        except Exception as e:
            if platform == "win32":
                print("VSPE virtual com port not found: reinstall or enable")
            else:
                print(f"\033[1;31m[ERROR] /dev/pts/x device not found: {e}\033[0m")
        
        try:
           #in_stream = pyaudio.PyAudio().open(frames_per_buffer=0, format = pyaudio.paInt16, channels = 1, rate = audio_tx_rate, input = True, input_device_index = find_audio_device(virtual_audio_dev_out) if virtual_audio_dev_out else -1)
           in_stream = pyaudio.PyAudio().open(frames_per_buffer=config['block_size'], format = pyaudio.paInt16, channels = 1, rate = audio_tx_rate, input = True, input_device_index = find_audio_device(virtual_audio_dev_out) if virtual_audio_dev_out else -1)
           out_stream = pyaudio.PyAudio().open(frames_per_buffer=0, format = pyaudio.paUInt8, channels = 1, rate = audio_rx_rate, output = True, output_device_index = find_audio_device(virtual_audio_dev_in) if virtual_audio_dev_in else -1)
        except Exception as e:
            if platform == "win32": print("VB-Audio CABLE not found: reinstall or enable")
            else:
                print("port audio device not found: ")
                print("  run in terminal: pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description=\"TRUSDX\" && pavucontrol  (hint: sudo modprobe snd-aloop)")
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
            # UA2 = mute speaker (default and when --mute-speaker is set)
            # UA1 = unmute speaker (only when --unmute is set and --mute-speaker is not set)
            if config.get('mute_speaker', False):
                init_cmd = b";MD2;UA2;"  # Force mute speaker while keeping VU meter active
                print(f"\033[1;33m[INIT] Mute speaker enabled (--mute-speaker)\033[0m")
            elif config.get('unmute', False):
                init_cmd = b";MD2;UA1;"  # Enable speaker audio
                print(f"\033[1;33m[INIT] Speaker audio enabled (--unmute)\033[0m")
            else:
                init_cmd = b";MD2;UA2;"  # Default: mute speaker
                print(f"\033[1;33m[INIT] Speaker muted (default)\033[0m")
            ser.write(init_cmd)  # enable audio streaming, set USB mode
            ser.flush()
            time.sleep(0.5)  # Give radio time to process
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

def main():
    if not config.get('no_header', False):
        show_version_info()
        print("\nStarting truSDX-AI Driver...")
    
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
                print(f"\033[1;33m[RESTART] Hardware disconnection detected - attempting restart #{restart_count}/{max_restart_attempts} in 3 seconds...\033[0m")
                
                if restart_count >= max_restart_attempts:
                    print(f"\033[1;31m[FATAL] Maximum restart attempts ({max_restart_attempts}) exceeded after hardware disconnections. Exiting.\033[0m")
                    break
                    
                time.sleep(3)
                continue  # Restart the main loop
            else:
                # Normal exit - break the loop
                print(f"\033[1;32m[EXIT] truSDX-AI Driver exiting normally\033[0m")
                break
            
        except Exception as e:
            restart_count += 1
            log(f"Main loop error (attempt {restart_count}/{max_restart_attempts}): {e}")
            print(f"\033[1;31m[ERROR] Main loop failed (attempt {restart_count}/{max_restart_attempts}): {e}\033[0m")
            
            if restart_count >= max_restart_attempts:
                print(f"\033[1;31m[FATAL] Maximum restart attempts ({max_restart_attempts}) exceeded. Exiting.\033[0m")
                break
            
            # Check if it was a hardware disconnection
            if state.get('hardware_disconnected', False):
                print(f"\033[1;33m[RESTART] Hardware disconnection detected - attempting restart in 3 seconds...\033[0m")
                time.sleep(3)
            else:
                # Wait before retrying to prevent rapid restart loops
                print(f"\033[1;33m[RESTART] Unexpected error - retrying in 5 seconds...\033[0m")
                time.sleep(5)
    
    print(f"\033[1;32m[EXIT] truSDX-AI Driver exiting gracefully\033[0m")

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
    parser.add_argument("--mute-speaker", action="store_true", default=False, help="Mute speaker output while keeping VU meter active")
    parser.add_argument("--callsign", type=str, help="Set callsign (overrides config file)")
    args = parser.parse_args()
    config = vars(args)
    
    # Load persistent configuration
    persistent_config = load_config()
    
    # Override callsign if provided via command line
    if config.get('callsign'):
        persistent_config['callsign'] = config['callsign']
        save_config(persistent_config)
    
    # Update port info with any persistent configuration
    PERSISTENT_PORTS.update(persistent_config)
    if config['verbose']: print(config)

    main()

