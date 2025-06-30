#!/usr/bin/env python3
"""
truSDX-AI Driver Version Information

Centralized version, date, and author strings for reuse by scripts, setup, and docs.
"""

__version__ = "1.2.0"
__build_date__ = "2024-12-19"
__author__ = "SQ3SWF, PE1NNZ, AI-Enhanced"
__description__ = "truSDX-AI audio driver with Kenwood TS-480 CAT interface"

# Legacy compatibility
VERSION = __version__
BUILD_DATE = __build_date__
AUTHOR = __author__

# Program compatibility information
COMPATIBLE_PROGRAMS = ["WSJT-X", "JS8Call", "FlDigi", "Winlink"]

# Connection banner information
WSJT_X_CONNECTION_INFO = {
    'radio_model': 'Kenwood TS-480',
    'poll_interval': '80ms',
    'baud_rate': '115200',
    'data_bits': '8',
    'stop_bits': '1',
    'parity': 'None',
    'handshake': 'None',
    'ptt_method': 'CAT or RTS/DTR',
    'audio_device': 'TRUSDX',
    'sample_rate': '48000 Hz',
    'channels': '1 (Mono)'
}

def get_version_string():
    """Return formatted version string"""
    return f"truSDX-AI Driver v{__version__}"

def get_full_version_info():
    """Return complete version information"""
    return {
        'version': __version__,
        'build_date': __build_date__,
        'author': __author__,
        'description': __description__,
        'compatible_programs': COMPATIBLE_PROGRAMS
    }

def get_banner_info():
    """Return connection information for banner display"""
    return WSJT_X_CONNECTION_INFO

if __name__ == '__main__':
    print(f"Version: {__version__}")
    print(f"Build Date: {__build_date__}")
    print(f"Author: {__author__}")
