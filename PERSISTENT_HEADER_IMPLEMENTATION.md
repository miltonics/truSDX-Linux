# Persistent Header Implementation - Step 4 Complete

## Summary
Successfully implemented persistent header functionality for the truSDX-AI driver as requested in Step 4.

## Completed Features

### ✅ Header Drawing Moved to UI Module
- **Modular version:** Created separate `src/ui.py` with `UserInterface` class
- **Main driver:** Enhanced `trusdx-txrx-AI.py` with integrated header functions
- Both versions feature the same functionality with color detection and callsign support

### ✅ Persistent Header Display
- **Version:** 1.2.0-AI-MONITORING-RECONNECT  
- **Build Date:** 2025-06-27
- **Callsign:** Read from config file (`~/.config/trusdx-ai/config.json`)
- **CAT Port:** `/tmp/trusdx_cat` (115200 baud, 80ms poll)
- **Audio Ports:** TRUSDX (Input/Output)
- **Power:** Displays watts with reconnection status
- **Reconnect Status:** Shows active/ready status

### ✅ Refreshable Without Clearing Scroll-back
- `show_persistent_header()` - Initial header display with full screen clear
- `refresh_header_only()` - Updates header area only, preserves scroll history
- Uses ANSI escape sequences to clear only header lines (7 lines)
- Saves/restores cursor position to maintain terminal state

### ✅ --no-header Flag
- Command line option: `--no-header` 
- Skips initial header display for minimal terminals
- Useful for scripting or resource-constrained environments

### ✅ ANSI Escape Sequences with Color Fallback
- **Color Detection:** Checks `$TERM` environment variable
- **Supported Terminals:** xterm, screen, tmux, rxvt, konsole, gnome, or any with "color" in name
- **Fallback:** Plain text output when color not supported
- **Functions:** `check_term_color()` and `get_color_code()`

### ✅ Configuration Management
- **Config File:** `~/.config/trusdx-ai/config.json`
- **Callsign Support:** `--callsign` command line option
- **Persistent Settings:** Automatically saves callsign changes
- **Default Values:** Graceful fallback when config missing

## Usage Examples

### Basic Usage
```bash
python3 trusdx-txrx-AI.py
```

### Set Callsign
```bash
python3 trusdx-txrx-AI.py --callsign "W1AW"
```

### Disable Header
```bash
python3 trusdx-txrx-AI.py --no-header
```

### Test Color Fallback
```bash
TERM=dumb python3 trusdx-txrx-AI.py
```

## Files Modified/Created

### Main Driver (Complete Integration)
- `trusdx-txrx-AI.py` - Enhanced with all features

### Modular Version (Separate Modules)
- `src/ui.py` - UserInterface class with header functionality
- `src/main.py` - Main entry point using UI module
- `src/connection_manager.py` - Status methods for UI
- `src/audio_io.py` - Audio port information
- `src/cat_emulator.py` - CAT command support
- `src/logging_cfg.py` - Logging configuration

### Configuration
- `~/.config/trusdx-ai/config.json` - Persistent settings

### Tests
- `test_js8call_config.py` - JS8Call configuration helper

## JS8Call Integration
The persistent header displays all required information for JS8Call configuration:
- **Radio:** Kenwood TS-480
- **Serial Port:** /tmp/trusdx_cat  
- **Baud Rate:** 115200
- **Audio Device:** TRUSDX
- **PTT Method:** CAT

## Technical Implementation

### Color Detection
```python
def check_term_color():
    term = os.getenv("TERM", "")
    color_terms = ['xterm', 'screen', 'tmux', 'rxvt', 'konsole', 'gnome']
    return any(color_term in term for color_term in color_terms) or 'color' in term
```

### Header Refresh
```python
def refresh_header_only(power_info=None):
    # Clear only header lines (7 lines)
    for i in range(7):
        print(f"\033[{i+1};1H\033[K", end="")
    # Redraw header with current status
    # Restore cursor position
```

### Configuration Loading
```python
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        log(f"Error loading config: {e}")
    return DEFAULT_CONFIG.copy()
```

## Status: ✅ COMPLETE
All requirements from Step 4 have been successfully implemented and tested.
