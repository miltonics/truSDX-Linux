# truSDX-AI Driver for Linux

**Version:** 1.2.0  
**Date:** 2024-12-19  
**Authors:** SQ3SWF, PE1NNZ, AI-Enhanced  
**Status:** ✅ PRODUCTION READY - Proven Working

## Overview

This is an enhanced AI-optimized driver for the truSDX transceiver that provides full Kenwood TS-480 CAT emulation and audio interface for Linux systems. It has been tested and proven working with successful contacts made.

## Features

- ✅ **Full Kenwood TS-480 CAT Emulation** - Perfect compatibility with WSJT-X, JS8Call, FLDigi
- ✅ **Working VU Meter** - Audio levels display correctly in WSJT-X
- ✅ **Frequency Control** - Band/frequency changes work correctly
- ✅ **PTT Control** - Both CAT and RTS/DTR PTT methods supported
- ✅ **Audio Streaming** - Bi-directional audio with proper routing
- ✅ **Persistent Ports** - Consistent `/tmp/trusdx_cat` port for easy setup
- ✅ **Auto-Configuration** - Automatic audio device setup

## Quick Start

1. **Connect your truSDX** via USB to your Linux computer

2. **Download and extract** this folder to your desired location

3. **Run the setup script:**
   ```bash
   cd "Trusdx Linux"
   chmod +x setup.sh
   ./setup.sh
   ```

4. **Start the driver:**
   ```bash
   ./trusdx-rxtx-AI.py
   ```

5. **Configure WSJT-X:**
   - Radio: **Kenwood TS-480**
   - Serial Port: **/tmp/trusdx_cat**
   - Baud Rate: **115200**
   - Audio Input: **Monitor of TRUSDX**
   - Audio Output: **TRUSDX**
   - PTT Method: **CAT**
   - Poll Interval: **80ms**

## System Requirements

### Minimum Requirements
- **Operating System**: Ubuntu 20.04+, Debian 11+, Linux Mint 20+, or compatible
- **Python**: Version 3.6 or higher
- **Audio System**: PulseAudio (standard on most desktop Linux)
- **USB**: Available USB 2.0+ port for truSDX connection
- **Memory**: 512MB RAM minimum, 1GB recommended
- **Storage**: 100MB free space for installation
- **Network**: Internet connection for initial dependency download

### Hardware Requirements
- **truSDX transceiver** with USB cable (CH341 USB-serial chip)
- **USB cable** (typically USB-A to USB-C or micro-USB)
- **Audio hardware** compatible with PulseAudio

### Software Compatibility
- **WSJT-X**: Version 2.6.0 or higher (recommended)
- **JS8Call**: Version 2.2.0 or higher
- **FLDigi**: Version 4.1.0 or higher  
- **Winlink**: Pat or other Linux-compatible Winlink clients

## USB-Serial Driver Support

The truSDX uses a CH341 USB-to-serial chip. On Linux, this is supported by the built-in `ch341` kernel module that loads automatically when the device is connected. No additional driver installation is required.

**For rare cases where the module doesn't auto-load:**
```bash
sudo modprobe ch341
```

**To verify the driver is loaded:**
```bash
lsmod | grep ch341
dmesg | grep ch341
```

## Supported Software

- WSJT-X (recommended)
- JS8Call
- FLDigi
- Winlink
- Any software supporting Kenwood TS-480 CAT protocol

## Command Line Options

```bash
./trusdx-txrx-AI.py [options]

Options:
  -v, --verbose         Enable verbose logging
  --vox                 Enable VOX (audio-triggered PTT)
  --unmute              Enable truSDX audio output
  --direct              Use system audio (no virtual devices)
  --no-rtsdtr           Disable RTS/DTR PTT
  -B N, --block-size N  Set RX block size (default: 512)
  -T N, --tx-block-size N Set TX block size (default: 48)
  --no-header           Skip version display on startup
```

## Troubleshooting

### Kernel Module Issues (CH341 USB-Serial)
- **Check if CH341 module is loaded:**
  ```bash
  lsmod | grep ch341
  ```
- **Manually load if needed:**
  ```bash
  sudo modprobe ch341
  ```
- **Verify USB device detection:**
  ```bash
  dmesg | grep -i ch341
  lsusb | grep -i ch341
  ```
- **Make module load permanent:**
  ```bash
  echo 'ch341' | sudo tee -a /etc/modules
  ```

### Audio Issues (PulseAudio Sink)
- **Verify TRUSDX sink exists:**
  ```bash
  pactl list sinks short | grep TRUSDX
  ```
- **Manually create sink if missing:**
  ```bash
  pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description="TRUSDX"
  ```
- **Run PulseAudio control panel:**
  ```bash
  pavucontrol
  ```
  - Recording tab: WSJT-X should use "Monitor of TRUSDX"
  - Playback tab: WSJT-X should use "TRUSDX"
- **If VU meter shows no activity:**
  - Restart the driver
  - Check audio routing in pavucontrol
  - Verify TRUSDX sink is not muted

### Permission Issues (Dialout Group)
- **Check current group membership:**
  ```bash
  groups $USER | grep dialout
  ```
- **Add user to dialout group:**
  ```bash
  sudo usermod -a -G dialout $USER
  ```
- **IMPORTANT:** Log out and log back in after group change
- **Verify permissions on USB device:**
  ```bash
  ls -l /dev/ttyUSB*
  ```
- **Never run the driver as root/sudo**

### Serial Port Issues
- **Ensure truSDX is connected via USB**
- **Check USB device detection:**
  ```bash
  dmesg | tail -20
  lsusb
  ```
- **Verify CAT port exists when driver runs:**
  ```bash
  ls -l /tmp/trusdx_cat
  ```
- **Try different USB ports or cables**
- **Check for conflicting software using serial ports:**
  ```bash
  sudo lsof /dev/ttyUSB*
  ```

### CAT Control Issues
- **Ensure Poll Interval is set to 80ms in WSJT-X**
- **Try different baud rates if needed:**
  - 115200 (recommended)
  - 57600 (fallback)
  - 38400 (legacy)
- **Check that no other software is using the CAT port**
- **Restart WSJT-X after driver is running**
- **Enable CAT control in WSJT-X settings**

## Technical Details

### Audio Architecture
- Creates virtual PulseAudio sink "TRUSDX"
- RX: truSDX → Driver → TRUSDX sink → WSJT-X
- TX: WSJT-X → TRUSDX sink → Driver → truSDX
- Sample rates: 11520 Hz TX, 7812 Hz RX

### CAT Protocol
- Emulates Kenwood TS-480 command set
- Handles 95+ CAT commands locally
- Forwards frequency/mode changes to hardware
- Maintains state consistency

### File Locations
- CAT Port: `/tmp/trusdx_cat`
- Config: `~/.config/trusdx-ai.json`
- PulseAudio: `~/.config/pulse/default.pa`

## Known Working Configurations

| Software | Version | Status | Notes |
|----------|---------|--------|---------|
| WSJT-X | 2.6.x | ✅ Working | Recommended settings above |
| JS8Call | 2.2.x | ✅ Working | Same as WSJT-X settings |
| FLDigi | 4.1.x | ✅ Working | Use Kenwood TS-480 profile |

## Version History

- **v1.1.6-AI-VU-WORKING** - Fixed frequency control, proven working with contacts
- **v1.1.5** - Enhanced VU meter functionality
- **v1.1.0** - Added persistent ports and improved CAT emulation
- **v1.0.x** - Initial AI enhancements

## Support

For issues, questions, or improvements:
1. Check this README first
2. Run with `--verbose` flag for detailed logging
3. Post on the truSDX forum with log output
4. Include your Linux distribution and software versions

## License

Based on original work by SQ3SWF and PE1NNZ. Enhanced with AI assistance.
Distributed under original license terms.

---

**Happy DXing! 73**

