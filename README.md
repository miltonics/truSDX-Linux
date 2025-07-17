# TruSDX Linux Driver for JS8Call

A Python-based CAT interface driver that enables seamless integration between the TruSDX QRP transceiver and JS8Call on Linux systems.

## Features

- **Automatic Frequency Detection**: Reads current radio frequency at startup
- **TX/RX Control**: Handles transmission switching for JS8Call
- **VU Meter Support**: Visual transmission feedback during operation  
- **CAT Command Forwarding**: Transparent command passing between JS8Call and radio
- **RTS/DTR Driver Shim**: Neutralizes RTS/DTR flags to prevent hardware conflicts
- **Robust Error Handling**: Multiple retry attempts with comprehensive debugging
- **Auto-detection**: Automatically finds TruSDX USB device

## Quick Start

1. **Install dependencies:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Run the driver:**
   ```bash
   python3 trusdx-txrx-AI.py
   ```
   
   Or for verbose mode with device indices:
   ```bash
   python3 trusdx-txrx-AI.py --verbose
   ```

3. **Configure JS8Call:**
   
   **CAT Control:**
   - Radio: Kenwood TS-480
   - CAT Control Port: `/tmp/trusdx_cat`
   - Baud Rate: 115200
   - Data Bits: 8, Stop Bits: 1, Handshake: None
   - PTT Method: CAT
   
   **Audio Configuration:**
   - Audio Input (from radio): `TRUSDX.monitor`
   - Audio Output (to radio): `TRUSDX`
   
   The driver automatically creates the TRUSDX audio sink if missing.

## Requirements

- Python 3.6+
- TruSDX transceiver connected via USB
- JS8Call software
- Linux system with USB permissions

## Installation

See `INSTALL.txt` for detailed installation instructions.

## Usage

See `USAGE.md` for quick usage guide and troubleshooting tips.

### Audio Connection Utility

A helper script `trusdx-audio-connect.sh` is provided to manage audio connections:

```bash
# Interactive mode
./trusdx-audio-connect.sh

# Command line mode
./trusdx-audio-connect.sh connect js8call
./trusdx-audio-connect.sh verify
./trusdx-audio-connect.sh test
```

The utility provides:
- Automatic TRUSDX sink creation
- Application audio routing (JS8Call, WSJT-X, FLDigi)
- Connection verification
- Audio recording test with `parecord`

## RTS/DTR Driver Shim (New in v1.2.1)

The driver now includes an intelligent RTS/DTR neutralization system that prevents hardware conflicts:

- **Automatic Detection**: Monitors for RTS/DTR control signals from CAT software
- **Signal Neutralization**: Safely absorbs RTS/DTR flags before they reach hardware
- **Hardware Protection**: Prevents potential conflicts with TruSDX USB interface
- **Transparent Operation**: Works seamlessly with JS8Call, WSJT-X, and other CAT software
- **Backward Compatibility**: Maintains compatibility with existing configurations

**Benefits:**
- Eliminates need to manually disable RTS/DTR in client software
- Prevents "driver shim active" messages in system logs
- Ensures stable USB communication with TruSDX hardware
- Reduces potential for USB disconnections during operation

**Technical Details:**
The shim operates at the Python pyserial level, intercepting RTS/DTR property access and method calls. This approach is transparent to both the hardware and client software, providing a robust solution that works across different operating systems and CAT applications.

## Contributing

This project is open source and welcomes contributions! Feel free to:
- Report bugs and issues
- Submit feature requests
- Create pull requests
- Improve documentation

## Development

The project includes comprehensive testing and debugging tools. Development files are available in the repository history.

## Hardware Compatibility

Tested and working with:
- TruSDX QRP Transceiver
- Linux systems (Ubuntu, Mint, Debian)
- JS8Call v2.2+

## Support

If you encounter issues:
1. Check the troubleshooting section in `USAGE.md`
2. Review the detailed logs the script provides
3. Open an issue on GitHub with your configuration details

## Acknowledgments

Thanks to the amateur radio community and JS8Call developers for their excellent software that makes digital communications accessible to everyone.

---

**73 de Milton**
