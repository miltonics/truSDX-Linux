#!/usr/bin/env python3
"""
Main entry point for truSDX-AI driver.
Initializes and coordinates different modules for radio communication.
"""

import argparse
import threading
import json
import os
from audio_io import AudioManager
from cat_emulator import CATEmulator
from connection_manager import ConnectionManager
from logging_cfg import configure_logging, log
from ui import UserInterface

VERSION = "v1.1.6-pre-refactor-1-gcef88aa-dirty"
BUILD_DATE = "2025-07-09"
AUTHOR = "SQ3SWF, PE1NNZ, AI-Enhanced - MONITORING & RECONNECT"

COMPATIBLE_PROGRAMS = ["WSJT-X", "JS8Call", "FlDigi", "Winlink"]

PERSISTENT_PORTS = {
    'cat_port': '/tmp/trusdx_cat',
    'audio_device': 'TRUSDX'
}

CONFIG_FILE = os.path.expanduser('~/.config/trusdx-ai/config.json')
DEFAULT_CONFIG = {
    'callsign': 'N/A',
    'cat_port': '/tmp/trusdx_cat',
    'audio_device': 'TRUSDX'
}

def load_config():
    """Load configuration from file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        log(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()

def save_config(config_data):
    """Save configuration to file."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=2)
    except Exception as e:
        log(f"Error saving config: {e}")

def main():
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
    parser.add_argument("--logfile", type=str, help="Custom log file path (default: ~/.cache/trusdx/logs/trusdx.log)")
    parser.add_argument("--syslog", action="store_true", default=False, help="Enable syslog handler for systemd integration")
    args = parser.parse_args()
    config = vars(args)
    
    # Load persistent configuration
    persistent_config = load_config()
    
    # Override callsign if provided via command line
    if config.get('callsign'):
        persistent_config['callsign'] = config['callsign']
        save_config(persistent_config)
    
    # Update port info with any persistent configuration
    port_info = PERSISTENT_PORTS.copy()
    port_info.update(persistent_config)

    configure_logging(
        verbose=config['verbose'],
        log_file=config.get('logfile'),
        enable_syslog=config.get('syslog', False)
    )

    ui = UserInterface()
    conn_manager = ConnectionManager()
    cat_emulator = CATEmulator()
    audio_manager = AudioManager()

    if not config.get('no_header', False):
        ui.show_persistent_header(
            version=VERSION,
            build_date=BUILD_DATE,
            callsign=persistent_config.get('callsign', 'N/A'),
            port_info=port_info,
            power_info={'watts': 100},  # Example power info
            reconnect_status={'active': False}  # Example reconnect status
        )

    # Additional setup and threads can be orchestrated here
    # threading.Thread(target=conn_manager.monitor_connection, daemon=True).start()

if __name__ == '__main__':
    main()
