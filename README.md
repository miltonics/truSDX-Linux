# TruSDX Linux Driver for JS8Call

A Python-based CAT interface driver that enables seamless integration between the TruSDX QRP transceiver and JS8Call on Linux systems.

## Features

- **Automatic Frequency Detection**: Reads current radio frequency at startup
- **TX/RX Control**: Handles transmission switching for JS8Call
- **VU Meter Support**: Visual transmission feedback during operation  
- **CAT Command Forwarding**: Transparent command passing between JS8Call and radio
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

3. **Configure JS8Call:**
   - Set CAT control to use TCP/IP connection
   - Host: `localhost` 
   - Port: `4532`

## Requirements

- Python 3.6+
- TruSDX transceiver connected via USB
- JS8Call software
- Linux system with USB permissions

## Installation

See `INSTALL.txt` for detailed installation instructions.

## Usage

See `USAGE.md` for quick usage guide and troubleshooting tips.

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
