# truSDX-AI Driver for Linux

**Version:** 1.1.7-AI-PTT-FIXED  
**Date:** 2024-06-11
**Authors:** SQ3SWF, PE1NNZ, AI-Enhanced  
**Status:** ✅ PROVEN WORKING - Contact Made!

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
   ./trusdx-txrx-AI.py
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

- Linux (tested on Ubuntu, Debian, Mint)
- Python 3.6+
- PulseAudio
- USB port for truSDX connection
- Internet connection for initial setup

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

### Audio Issues
- Run `pavucontrol` to verify TRUSDX devices exist
- Check Recording tab: WSJT-X should use "Monitor of TRUSDX"
- Check Playbook tab: WSJT-X should use "TRUSDX"
- If VU meter shows no activity, restart the driver

### Serial Port Issues
- Ensure truSDX is connected via USB
- Check `dmesg | tail` for USB device detection
- Verify `/tmp/trusdx_cat` exists when driver is running
- Try unplugging/reconnecting truSDX

### Permission Issues
- Add user to dialout group: `sudo usermod -a -G dialout $USER`
- Log out and back in after group change
- Don't run the driver as root/sudo

### CAT Control Issues
- Ensure Poll Interval is set to 80ms in WSJT-X
- Try different baud rates if needed (38400, 57600, 115200)
- Check that no other software is using the CAT port

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

