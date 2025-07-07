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

3. **Configure JS8Call:**
   - Set CAT control to use TCP/IP connection
   - Host: `localhost` 
   - Port: `4532`

## Requirements

- Python 3.6+
- TruSDX transceiver connected via USB
- JS8Call software
- Linux system with USB permissions

## GUI Requirements

- `python3-tk` - Tkinter GUI framework
- `python3-matplotlib` - Plotting library for VU meter and waterfall displays

Install GUI dependencies:
```bash
sudo apt install python3-tk python3-matplotlib
```

To run without GUI (headless mode):
```bash
python3 trusdx-txrx-AI.py --nogui
```

## Installation

See `INSTALL.txt` for detailed installation instructions.

## Usage

See `USAGE.md` for quick usage guide and troubleshooting tips.

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
