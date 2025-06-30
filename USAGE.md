# TruSDX Linux Script - Quick Usage Guide

## What's in this folder:
- `trusdx-txrx-AI.py` - The main script that interfaces your TruSDX radio with JS8Call
- `README.md` - Detailed documentation and background information
- `INSTALL.txt` - Installation instructions
- `requirements.txt` - Python dependencies
- `setup.sh` - Automated setup script

## Quick Start:

1. **First time setup:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Run the script:**
   ```bash
   python3 trusdx-txrx-AI.py
   ```

3. **What it does:**
   - Reads your radio's current frequency at startup
   - Controls TX/RX switching for JS8Call
   - Shows VU meter during transmission
   - Forwards CAT commands between JS8Call and your radio

## Configuration:
The script will auto-detect your radio's USB device. If you need to specify a different device, edit the script and change the `DEVICE_PATH` variable.

## Troubleshooting:
- Make sure your TruSDX is connected via USB
- Ensure JS8Call is configured to use the script's CAT port (usually 4532)
- Check that you have permissions to access the USB device

## For more details:
See `README.md` for complete documentation and technical details.

---
*All development files, tests, and documentation have been moved to `/home/milton/Desktop/old/` to keep this folder clean.*
