#!/usr/bin/env python3
# de SQ3SWF, PE1NNZ 2023
# Enhanced AI version with Kenwood TS-480 CAT interface and persistent serial ports
# Now using centralized version management - see version.py

# Import centralized version information
from version import (
    __version__, __build_date__, __author__, __description__,
    VERSION, BUILD_DATE, AUTHOR, COMPATIBLE_PROGRAMS,
    get_version_string, get_banner_info
)

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
import subprocess
import atexit
from sys import platform

# Version information now imported from version.py
# This ensures consistency across all scripts and documentation

audio_tx_rate_trusdx = 4800
audio_tx_rate = 11520  #11521
audio_rx_rate = 7812

# Audio sink management for hardening
sink_created_by_script = False
PULSE_CONFIG_PATH = os.path.expanduser("~/.config/pulse/default.pa")
buf = []    # buffer for received audio
urs = [0]   # underrun counter
status = [False, False, True, False, False]	# tx_state, cat_streaming_state, running, cat_active, keyed_by_rts_dtr

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

def log(msg):
    try:
        if config['verbose']: print(f"{datetime.datetime.utcnow()} {msg}")
    except (NameError, KeyError):
        # Handle case where config is not defined (e.g., in tests)
        pass

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name == 'posix' else 'cls')

def show_persistent_header():
    """Display persistent header with version and connection info - ALWAYS VISIBLE"""
    banner_info = get_banner_info()
    
    # Clear screen but immediately redraw persistent header
    clear_screen()
    
    # Persistent banner that stays on screen
    print("\033[1;32m" + "═"*80 + "\033[0m")  # Double line for persistence
    print(f"\033[1;36m{get_version_string()}\033[0m - \033[1;33m{BUILD_DATE}\033[0m \033[1;37m[PERSISTENT]\033[0m")
    print("\033[1;37m📡 WSJT-X/JS8Call Connection Settings:\033[0m")
    print(f"\033[1;35m  Radio Model:\033[0m {banner_info['radio_model']} | \033[1;35mCAT Port:\033[0m {PERSISTENT_PORTS['cat_port']}")
    print(f"\033[1;35m  Baud Rate:\033[0m {banner_info['baud_rate']} | \033[1;35mPoll Interval:\033[0m {banner_info['poll_interval']} | \033[1;35mPTT:\033[0m {banner_info['ptt_method']}")
    print(f"\033[1;35m  Audio Device:\033[0m {banner_info['audio_device']} | \033[1;35mSample Rate:\033[0m {banner_info['sample_rate']} | \033[1;35mChannels:\033[0m {banner_info['channels']}")
    print("\033[1;32m" + "═"*80 + "\033[0m")  # Double line for persistence
    print("\033[1;33m⚠️  This banner remains visible during operation for quick reference\033[0m")
    print()
    
    # Force terminal to keep this banner visible by not clearing it
    # This creates a "sticky" header that persists throughout operation

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

# Radio state variables for consistent responses
radio_state = {
    'vfo_a_freq': '00014074000',  # 14.074 MHz
    'vfo_b_freq': '00014074000',  # 14.074 MHz
    'mode': '2',                  # USB
    'rx_vfo': '0',               # VFO A
    'tx_vfo': '0',               # VFO A
    'split': '0',                # Split off
    'rit': '0',                  # RIT off
    'xit': '0',                  # XIT off
    'rit_offset': '00000',       # No offset
    'power_on': '1',             # Power on
    'ai_mode': '2',              # Auto info on
    'cw_speed': '020',           # CW speed 20 WPM
    'filter_width': '2400',      # Filter width 2.4 kHz
    'filter_high': '25',         # High cut filter 2.5 kHz
    'filter_low': '03',          # Low cut filter 300 Hz
    'preamp': '0',               # Preamp off
    'rit_freq': '00000',         # RIT frequency offset
    'xit_freq': '00000'          # XIT frequency offset
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
            # Format: IF<11-digit freq><5-digit RIT/XIT><RIT><XIT><Bank><RX/TX><Mode><VFO><Scan><Split><Tone><ToneFreq>;
            # Total: IF + 37 chars + ; = 40 characters
            
            freq = radio_state['vfo_a_freq'][:11].ljust(11, '0')     # 11 digits
            rit_xit = radio_state['rit_offset'][:5].ljust(5, '0')    # 5 digits  
            rit = radio_state['rit'][:1].ljust(1, '0')               # 1 digit
            xit = radio_state['xit'][:1].ljust(1, '0')               # 1 digit
            bank = '00'                                              # 2 digits
            rxtx = '0'                                               # 1 digit
            mode = radio_state['mode'][:1].ljust(1, '2')             # 1 digit
            vfo = '0'                                                # 1 digit
            scan = '0'                                               # 1 digit
            split = radio_state['split'][:1].ljust(1, '0')           # 1 digit
            tone = '0'                                               # 1 digit
            tone_freq = '08'                                         # 2 digits
            ctcss = '00'                                             # 2 digits (missing!)
            
            # Total should be: 11+5+1+1+2+1+1+1+1+1+1+2+2 = 30 chars
            # We need 37 chars, so add 7 more padding
            padding = '0000000'  # 7 digits padding
            
            # Build response: IF + 37 characters + ;
            content = f'{freq}{rit_xit}{rit}{xit}{bank}{rxtx}{mode}{vfo}{scan}{split}{tone}{tone_freq}{ctcss}{padding}'
            
            # Ensure exactly 37 characters
            content = content[:37].ljust(37, '0')
            response = f'IF{content};'
            
            # Double-check length
            if len(response) != 40:
                # Known working 37-char format for TS-480
                response = 'IF000140740000000000020000000800000;'
            
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
                # Set VFO A frequency - extract and validate 11-digit frequency
                freq = cmd_str[2:13].ljust(11, '0')[:11]  # Ensure exactly 11 digits
                radio_state['vfo_a_freq'] = freq
                return None  # Forward to radio
            else:
                # Read VFO A frequency
                freq = radio_state['vfo_a_freq'].ljust(11, '0')[:11]
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
        
        # VFO operations
        elif cmd_str.startswith('FR'):
            if len(cmd_str) > 2:
                # Set RX VFO - forward to hardware
                radio_state['rx_vfo'] = cmd_str[2]
                return None  # Forward to radio
            else:
                # Read RX VFO
                return f'FR{radio_state["rx_vfo"]};'.encode('utf-8')
                
        elif cmd_str.startswith('FT'):
            if len(cmd_str) > 2:
                # Set TX VFO - forward to hardware
                radio_state['tx_vfo'] = cmd_str[2]
                return None  # Forward to radio
            else:
                # Read TX VFO
                return f'FT{radio_state["tx_vfo"]};'.encode('utf-8')
        
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
        
        # S-meter reading
        elif cmd_str.startswith('SM'):
            if len(cmd_str) > 2:
                # Set S-meter (not applicable)
                return cmd
            else:
                # Return S-meter reading (0-30 range, simulate S9+20dB)
                return b'SM0200;'  # S9+20dB signal strength
        
        # CW operations
        elif cmd_str.startswith('KS'):
            if len(cmd_str) > 2:
                # Set CW speed
                radio_state['cw_speed'] = cmd_str[2:5]
                return None  # Forward to radio
            else:
                # Read CW speed
                return f'KS{radio_state["cw_speed"]};'.encode('utf-8')
        
        elif cmd_str.startswith('CW'):
            # CW memory send (forward to radio)
            return None
        
        # Additional filter controls
        elif cmd_str.startswith('FW'):
            if len(cmd_str) > 2:
                # Set filter width
                radio_state['filter_width'] = cmd_str[2:6]
                return None  # Forward to radio
            else:
                # Read filter width
                return f'FW{radio_state["filter_width"]};'.encode('utf-8')
        
        elif cmd_str.startswith('SH'):
            if len(cmd_str) > 2:
                # Set high cut filter
                radio_state['filter_high'] = cmd_str[2:4]
                return None  # Forward to radio
            else:
                # Read high cut filter
                return f'SH{radio_state["filter_high"]};'.encode('utf-8')
        
        elif cmd_str.startswith('SL'):
            if len(cmd_str) > 2:
                # Set low cut filter
                radio_state['filter_low'] = cmd_str[2:4]
                return None  # Forward to radio
            else:
                # Read low cut filter
                return f'SL{radio_state["filter_low"]};'.encode('utf-8')
        
        # Preamp/Attenuator
        elif cmd_str.startswith('PA'):
            if len(cmd_str) > 2:
                # Set preamp/attenuator
                radio_state['preamp'] = cmd_str[2]
                return None  # Forward to radio
            else:
                # Read preamp/attenuator
                return f'PA{radio_state["preamp"]};'.encode('utf-8')
        
        # RIT/XIT frequency offset
        elif cmd_str.startswith('RC'):
            # Clear RIT/XIT frequency
            radio_state['rit_freq'] = '00000'
            radio_state['xit_freq'] = '00000'
            return None  # Forward to radio
        
        elif cmd_str.startswith('RD'):
            if len(cmd_str) > 2:
                # Set RIT frequency offset
                radio_state['rit_freq'] = cmd_str[2:7]
                return None  # Forward to radio
            else:
                # Read RIT frequency offset
                return f'RD{radio_state["rit_freq"]};'.encode('utf-8')
        
        elif cmd_str.startswith('XO'):
            if len(cmd_str) > 2:
                # Set XIT frequency offset
                radio_state['xit_freq'] = cmd_str[2:7]
                return None  # Forward to radio
            else:
                # Read XIT frequency offset
                return f'XO{radio_state["xit_freq"]};'.encode('utf-8')
        
        # VFO A/B swap
        elif cmd_str == 'SV':
            # Swap VFO A and B
            temp_freq = radio_state['vfo_a_freq']
            radio_state['vfo_a_freq'] = radio_state['vfo_b_freq']
            radio_state['vfo_b_freq'] = temp_freq
            return None  # Forward to radio
        
        # Handle common Hamlib initialization commands
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
    if platform == "linux" or platform == "linux2": return -1  # not supported
    result = [i for i in range(pyaudio.PyAudio().get_device_count()) if name in (pyaudio.PyAudio().get_device_info_by_index(i)['name']) ]
    return result[occurance] if len(result) else -1 # return n-th matching device to name, -1 for no match

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
            elif(ser.in_waiting == 0): time.sleep(0.001)   #normal case for RX
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
    except Exception as e:
        log(e)
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

def handle_vox(samples8, ser):
    if (128 - min(samples8)) == 64 and (max(samples8) - 127) == 64: # if does contain very loud signal
        if not status[0]:
            status[0] = True
            #log("***TX mode")
            ser.write(b";TX0;")
            ser.flush()
    elif status[0]:  # in TX and no audio detected (silence)
        tx_cat_delay(ser)
        ser.write(b";RX;")
        ser.flush()
        status[0] = False
        #log("***RX mode")

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
                samples8 = bytearray([128 + x//256 for x in arr])  # was //512 because with //256 there is 5dB too much signal. Win7 only support 16 bits input audio -> convert to 8 bits
                samples8 = samples8.replace(b'\x3b', b'\x3a')      # filter ; of stream
                if status[0]: ser.write(samples8)
                if config['vox']: handle_vox(samples8, ser)
            else:
                time.sleep(0.001)
    except Exception as e:
        log(e)
        status[2] = False
        if config['verbose']: raise

def pty_echo(fd1, fd2):
    try:
        log("pty_echo")
        while status[2]:
            c1 = fd1.read(1)
            fd2.write(c1)
            #print(f'{datetime.datetime.utcnow()} {threading.current_thread().ident} > ', c1)
    except Exception as e:
        log(e)
        status[2] = False
        if config['verbose']: raise

def check_trusdx_sink_exists():
    """Check if TRUSDX null-sink exists in PulseAudio"""
    try:
        result = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True)
        return 'Name: TRUSDX' in result.stdout
    except Exception as e:
        log(f"Error checking TRUSDX sink: {e}")
        return False

def create_trusdx_sink():
    """Create TRUSDX null-sink if it doesn't exist"""
    global sink_created_by_script
    
    if not check_trusdx_sink_exists():
        try:
            log("Creating TRUSDX null-sink...")
            print(f"\033[1;33m[AUDIO] Creating TRUSDX null-sink...\033[0m")
            result = subprocess.run([
                'pactl', 'load-module', 'module-null-sink', 
                'sink_name=TRUSDX', 
                'sink_properties=device.description="TRUSDX"'
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                log("TRUSDX sink created successfully")
                print(f"\033[1;32m[AUDIO] TRUSDX sink created successfully\033[0m")
                sink_created_by_script = True
                return True
            else:
                log(f"Failed to create TRUSDX sink: {result.stderr}")
                print(f"\033[1;31m[AUDIO] Failed to create TRUSDX sink: {result.stderr}\033[0m")
                return False
        except Exception as e:
            log(f"Error creating TRUSDX sink: {e}")
            print(f"\033[1;31m[AUDIO] Error creating TRUSDX sink: {e}\033[0m")
            return False
    else:
        log("TRUSDX sink already exists")
        print(f"\033[1;32m[AUDIO] TRUSDX sink already exists\033[0m")
        return True

def persist_trusdx_sink():
    """Add TRUSDX sink to PulseAudio default.pa for persistence"""
    try:
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(PULSE_CONFIG_PATH), exist_ok=True)
        
        # Check if already configured
        sink_line = 'load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"'
        
        if os.path.exists(PULSE_CONFIG_PATH):
            with open(PULSE_CONFIG_PATH, 'r') as f:
                content = f.read()
                if 'sink_name=TRUSDX' in content:
                    log("TRUSDX sink already configured for persistence")
                    print(f"\033[1;32m[AUDIO] TRUSDX sink already configured for persistence\033[0m")
                    return True
        
        # Add to config file
        with open(PULSE_CONFIG_PATH, 'a') as f:
            f.write(f"\n# TruSDX Audio Sink\n{sink_line}\n")
        
        log(f"TRUSDX sink added to {PULSE_CONFIG_PATH} for persistence")
        print(f"\033[1;32m[AUDIO] TRUSDX sink added to {PULSE_CONFIG_PATH} for persistence\033[0m")
        return True
        
    except Exception as e:
        log(f"Error persisting TRUSDX sink: {e}")
        print(f"\033[1;31m[AUDIO] Error persisting TRUSDX sink: {e}\033[0m")
        return False

def cleanup_trusdx_sink():
    """Remove TRUSDX sink only if it was created by this script"""
    global sink_created_by_script
    
    if sink_created_by_script and check_trusdx_sink_exists():
        try:
            log("Removing TRUSDX sink created by script...")
            print(f"\033[1;33m[AUDIO] Removing TRUSDX sink created by script...\033[0m")
            # Get the module ID
            result = subprocess.run(['pactl', 'list', 'modules'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            
            module_id = None
            for i, line in enumerate(lines):
                if 'Module #' in line and 'module-null-sink' in lines[i+1] if i+1 < len(lines) else False:
                    # Check if this is our TRUSDX sink
                    for j in range(i+2, min(i+10, len(lines))):
                        if 'sink_name=TRUSDX' in lines[j]:
                            module_id = line.split('#')[1].split()[0]
                            break
                    if module_id:
                        break
            
            if module_id:
                subprocess.run(['pactl', 'unload-module', module_id], check=True)
                log(f"TRUSDX sink module {module_id} unloaded")
                print(f"\033[1;32m[AUDIO] TRUSDX sink module {module_id} unloaded\033[0m")
            else:
                log("Could not find TRUSDX module ID")
                print(f"\033[1;33m[AUDIO] Could not find TRUSDX module ID\033[0m")
                
        except Exception as e:
            log(f"Error removing TRUSDX sink: {e}")
            print(f"\033[1;31m[AUDIO] Error removing TRUSDX sink: {e}\033[0m")

def verify_sample_rates():
    """Verify and display sample rate information"""
    log(f"Audio configuration:")
    log(f"  TX sample rate: {config.get('tx_rate', audio_tx_rate)} Hz")
    log(f"  RX sample rate: {config.get('rx_rate', audio_rx_rate)} Hz")
    log(f"  TruSDX internal rate: {audio_tx_rate_trusdx} Hz")
    
    print(f"\033[1;36m[AUDIO] Audio configuration:\033[0m")
    print(f"\033[1;37m  TX sample rate: {config.get('tx_rate', audio_tx_rate)} Hz\033[0m")
    print(f"\033[1;37m  RX sample rate: {config.get('rx_rate', audio_rx_rate)} Hz\033[0m")
    print(f"\033[1;37m  TruSDX internal rate: {audio_tx_rate_trusdx} Hz\033[0m")
    
    # Check for potential sample rate conversion issues
    tx_rate = config.get('tx_rate', audio_tx_rate)
    rx_rate = config.get('rx_rate', audio_rx_rate)
    
    if tx_rate != audio_tx_rate:
        log(f"Warning: TX rate mismatch - using {tx_rate} Hz instead of default {audio_tx_rate} Hz")
        print(f"\033[1;33m[WARNING] TX rate mismatch - using {tx_rate} Hz instead of default {audio_tx_rate} Hz\033[0m")
    if rx_rate != audio_rx_rate:
        log(f"Warning: RX rate mismatch - using {rx_rate} Hz instead of default {audio_rx_rate} Hz")
        print(f"\033[1;33m[WARNING] RX rate mismatch - using {rx_rate} Hz instead of default {audio_rx_rate} Hz\033[0m")

def setup_audio_architecture():
    """Setup complete audio architecture with hardening"""
    if platform not in ["linux", "linux2"]:
        log("Audio architecture hardening only supported on Linux")
        print(f"\033[1;33m[AUDIO] Audio architecture hardening only supported on Linux\033[0m")
        return True
    
    if config.get('direct', False):
        log("Direct audio mode - bypassing virtual sink")
        print(f"\033[1;33m[AUDIO] Direct audio mode - bypassing virtual sink\033[0m")
        return True
    
    print(f"\033[1;36m[AUDIO] Setting up audio architecture with hardening...\033[0m")
    
    # Check, create, and persist TRUSDX sink
    if not create_trusdx_sink():
        return False
    
    if not persist_trusdx_sink():
        log("Warning: Could not persist TRUSDX sink configuration")
        print(f"\033[1;33m[WARNING] Could not persist TRUSDX sink configuration\033[0m")
    
    verify_sample_rates()
    return True

def graceful_shutdown():
    """Perform graceful shutdown and cleanup"""
    log("Performing graceful shutdown...")
    print(f"\033[1;33m[SHUTDOWN] Performing graceful shutdown...\033[0m")
    cleanup_trusdx_sink()

# https://stackoverflow.com/questions/7088672/pyaudio-working-but-spits-out-error-messages-each-time
def run():
    try:
        status[0] = False
        status[1] = False
        status[2] = True
        status[3] = False
        status[4] = False

        # Setup audio architecture with hardening
        if not setup_audio_architecture():
            log("Failed to setup audio architecture")
            return

        # Use custom sample rates if provided
        global audio_tx_rate, audio_rx_rate
        audio_tx_rate = config.get('tx_rate', audio_tx_rate)
        audio_rx_rate = config.get('rx_rate', audio_rx_rate)
        
        # Load persistent configuration
        persistent_config = load_config()
        PERSISTENT_PORTS.update(persistent_config)
        
        # Create persistent serial ports
        create_persistent_serial_ports()

        if platform == "linux" or platform == "linux2":
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
            # Check if /tmp/trusdx_cat exists, if not, create it
            if platform != "win32":
                cat_link = "/tmp/trusdx_cat"
                if not os.path.exists(cat_link):
                    print(f"\033[1;33m[BRIDGE] Creating serial bridge at {cat_link}\033[0m")
                    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "create_serial_bridge.sh")
                    subprocess.run(["/bin/bash", script_path], check=True)
                    print(f"\033[1;32m[BRIDGE] Serial bridge created successfully\033[0m")
                else:
                    print(f"\033[1;32m[BRIDGE] Serial bridge already exists at {cat_link}\033[0m")

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
        ser.write(b";MD2;UA2;" if not config['unmute'] else b";MD2;UA1;") # enable audio streaming, mute trusdx
        #status[1] = True

        threading.Thread(target=receive_serial_audio, args=(ser,ser2,out_stream)).start()
        threading.Thread(target=play_receive_audio, args=(out_stream,)).start()
        threading.Thread(target=transmit_audio_via_serial, args=(in_stream,ser,ser2)).start()

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
        while status[2]:    # wait and idle
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
    while 1:
        run();

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f"truSDX-AI audio driver v{VERSION} with audio architecture hardening", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="increase verbosity")
    parser.add_argument("--vox", action="store_true", default=False, help="VOX audio-triggered PTT (Linux only)")
    parser.add_argument("--unmute", action="store_true", default=False, help="Enable (tr)usdx audio")
    parser.add_argument("--direct", action="store_true", default=False, help="Bypass virtual sink - use system audio devices directly")
    parser.add_argument("--no-rtsdtr", action="store_true", default=False, help="Disable RTS/DTR-triggered PTT")
    parser.add_argument("-B", "--block-size", type=int, default=512, help="RX Block size")
    parser.add_argument("-T", "--tx-block-size", type=int, default=48, help="TX Block size")
    parser.add_argument("--tx-rate", type=int, default=audio_tx_rate, help=f"TX sample rate in Hz (default: {audio_tx_rate})")
    parser.add_argument("--rx-rate", type=int, default=audio_rx_rate, help=f"RX sample rate in Hz (default: {audio_rx_rate})")
    parser.add_argument("--no-header", action="store_true", default=False, help="Skip initial version display")
    args = parser.parse_args()
    config = vars(args)
    
    # Register graceful shutdown
    atexit.register(graceful_shutdown)
    
    if config['verbose']: 
        print(config)
        print(f"\033[1;36m[AUDIO] Audio architecture hardening enabled (Linux only)\033[0m")
        print(f"\033[1;36m[AUDIO] TRUSDX sink detection and persistence: {'Enabled' if not config['direct'] else 'Bypassed (--direct mode)'}\033[0m")
        print(f"\033[1;36m[AUDIO] Sample rates - TX: {config['tx_rate']} Hz, RX: {config['rx_rate']} Hz\033[0m")

    try:
        main()
    except KeyboardInterrupt:
        print("\n\033[1;33m[SHUTDOWN] Shutdown requested...\033[0m")
        graceful_shutdown()
    except Exception as e:
        print(f"\033[1;31m[ERROR] {e}\033[0m")
        graceful_shutdown()
        time.sleep(3)

