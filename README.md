# TruSDX Linux Driver for JS8Call

🎉 **New Release: v1.2.0 Available!** 🎉

A Python-based CAT interface driver that enables seamless integration between the TruSDX QRP transceiver and JS8Call on Linux systems.

## 🚀 What's New in v1.2.0

- **🔗 Hardware Monitoring & Reconnection**: Automatic device detection and recovery from disconnections
- **🖥️ Enhanced User Interface**: Persistent header display with real-time status updates
- **📊 Performance Improvements**: Optimized connection handling and reduced CPU usage
- **🛠️ Development & Testing**: Comprehensive test suite and automated version management
- **📦 Easy Installation**: Full pip installation support with setuptools integration

[📋 View Full Release Notes](RELEASE_NOTES_v1.2.0.md) | [📥 Download Binaries](https://github.com/milton-tanaka/trusdx-ai/releases/tag/v1.2.0)

## Features

- **Automatic Frequency Detection**: Reads current radio frequency at startup
- **TX/RX Control**: Handles transmission switching for JS8Call
- **VU Meter Support**: Visual transmission feedback during operation  
- **CAT Command Forwarding**: Transparent command passing between JS8Call and radio
- **Robust Error Handling**: Multiple retry attempts with comprehensive debugging
- **Auto-detection**: Automatically finds TruSDX USB device

## Quick Start

### Method 1: Pip Installation (Recommended)

1. **Install from source:**
   ```bash
   git clone https://github.com/milton-tanaka/trusdx-ai.git
   cd trusdx-ai
   pip install -e .
   ```

2. **Run the driver:**
   ```bash
   trusdx-ai
   ```

### Method 2: Manual Installation

1. **Install dependencies:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

2. **Run the driver:**
   ```bash
   python3 trusdx-txrx-AI.py
   ```

### Method 3: Pre-built Binaries

1. **Download the binary** from the [releases page](https://github.com/milton-tanaka/trusdx-ai/releases/tag/v1.2.0)
2. **Make it executable:**
   ```bash
   chmod +x trusdx-ai-v1.2.0
   ./trusdx-ai-v1.2.0
   ```

### Configuration

**Configure JS8Call:**
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

## Windows vs. Linux Feature Comparison

| Feature | Windows Implementation | Linux Implementation | Notes |
|---------|----------------------|--------------------|---------|
| **Audio Routing** | VB-Audio Virtual Audio Cable | PulseAudio null-sink | Linux uses native audio subsystem |
| **CAT Bridging** | com0com virtual COM ports | PTY (pseudo-terminal) | Linux uses native device files |
| **PTT Control** | Manual virtual device setup | Integrated CAT/VOX | Linux has built-in support |
| **Installation** | Multiple manual driver installs | Single setup script | Linux requires fewer dependencies |
| **Virtual Devices** | Third-party drivers required | Native OS support | Linux advantage |
| **Audio Latency** | Dependent on VB-Audio | Direct PulseAudio access | Linux potentially lower latency |
| **System Integration** | External dependencies | Native integration | Linux more tightly integrated |

### Windows-Only Dependencies (Not applicable on Linux)

- **VB-Audio Virtual Audio Cable**: Linux uses PulseAudio null-sink instead
- **com0com**: Linux uses PTY for virtual serial ports  
- **Driver signing workarounds**: Not needed on Linux
- **Manual COM port configuration**: Linux auto-configures device files

### Linux Equivalents for Windows Features

- **Audio routing**: `pactl load-module module-null-sink` replaces VB-Audio
- **Virtual serial ports**: `socat` and PTY replace com0com
- **Device permissions**: `udev` rules replace Windows driver installation
- **Audio control**: PulseAudio mixer replaces Windows audio control panel

---

**73 de Milton**
