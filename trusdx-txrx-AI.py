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
from sys import platform

# Version information
VERSION = "1.1.8-AI-TX0-FREQ-FIXED"
BUILD_DATE = "2025-06-23"
AUTHOR = "SQ3SWF, PE1NNZ, AI-Enhanced - TX0 & FREQ FIXED"
COMPATIBLE_PROGRAMS = ["WSJT-X", "JS8Call", "FlDigi", "Winlink"]

audio_tx_rate_trusdx = 4800
audio_tx_rate = 11520  #11521
audio_rx_rate = 7812
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
    if config['verbose']: print(f"{datetime.datetime.utcnow()} {msg}")

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

def refresh_header_only():
    """Refresh just the header without clearing screen"""
    # Save cursor position
    print("\033[s", end="")  # Save cursor position
    # Move to top and redraw header
    show_persistent_header()
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

def query_radio(cmd, retries=3, timeout=0.2):
    """Query radio with command and retry logic
    
    Args:
        cmd: Command string (e.g., "FA", "MD")
        retries: Number of retry attempts (default: 3)
        timeout: Timeout in seconds to wait for response (default: 0.2)
    
    Returns:
        bytes: Response from radio or None if failed
    """
    global ser
    
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
            init_cmd = b";MD2;UA2;" if not config['unmute'] else b";MD2;UA1;"
            ser.write(init_cmd)  # enable audio streaming, set USB mode
            ser.flush()
            time.sleep(0.5)  # Give radio time to process
            print(f"\033[1;32m[INIT] ✅ Radio initialized with basic commands\033[0m")
        except Exception as e:
            print(f"\033[1;31m[INIT] Error initializing radio: {e}\033[0m")
        
        # CRITICAL: Read actual frequency from radio BEFORE JS8Call connects
        print(f"\033[1;33m[INIT] Reading actual frequency from radio...\033[0m")
        try:
            # Clear any pending data
            if ser.in_waiting > 0:
                ser.read(ser.in_waiting)
            
            # Query frequency from radio
            ser.write(b";FA;")
            ser.flush()
            time.sleep(0.5)  # Wait longer for response
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"\033[1;36m[DEBUG] Raw radio response: {response}\033[0m")
                
                if response.startswith(b"FA") and len(response) >= 15:
                    actual_freq = response[2:-1].decode().ljust(11,'0')[:11]
                    if actual_freq != '00000000000':  # Valid frequency
                        radio_state['vfo_a_freq'] = actual_freq
                        freq_mhz = float(actual_freq) / 1000000.0
                        print(f"\033[1;32m[INIT] ✅ Read actual frequency: {freq_mhz:.3f} MHz\033[0m")
                    else:
                        print(f"\033[1;33m[INIT] Radio returned invalid frequency: {actual_freq}\033[0m")
                else:
                    print(f"\033[1;33m[INIT] Invalid frequency response: {response}\033[0m")
            else:
                print(f"\033[1;33m[INIT] No response from radio to frequency query\033[0m")
                
        except Exception as e:
            print(f"\033[1;31m[INIT] Error reading frequency: {e}\033[0m")
        
        # Show what frequency we'll report to JS8Call
        current_freq = float(radio_state['vfo_a_freq']) / 1000000.0
        print(f"\033[1;36m[INIT] Will report {current_freq:.3f} MHz to CAT clients\033[0m")
        #status[1] = True

        threading.Thread(target=receive_serial_audio, args=(ser,ser2,out_stream)).start()
        threading.Thread(target=play_receive_audio, args=(out_stream,)).start()
        threading.Thread(target=transmit_audio_via_serial, args=(in_stream,ser,ser2)).start()

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
    parser = argparse.ArgumentParser(description=f"truSDX-AI audio driver v{VERSION}", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbose", action="store_true", default=False, help="increase verbosity")
    parser.add_argument("--vox", action="store_true", default=False, help="VOX audio-triggered PTT (Linux only)")
    parser.add_argument("--unmute", action="store_true", default=False, help="Enable (tr)usdx audio")
    parser.add_argument("--direct", action="store_true", default=False, help="Use system audio devices (no loopback)")
    parser.add_argument("--no-rtsdtr", action="store_true", default=False, help="Disable RTS/DTR-triggered PTT")
    parser.add_argument("-B", "--block-size", type=int, default=512, help="RX Block size")
    parser.add_argument("-T", "--tx-block-size", type=int, default=48, help="TX Block size")
    parser.add_argument("--no-header", action="store_true", default=False, help="Skip initial version display")
    args = parser.parse_args()
    config = vars(args)
    if config['verbose']: print(config)

    main()

