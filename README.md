# TruSDX Linux Driver

## A Kenwood TS-480 CAT Emulator for (tr)uSDX Transceivers

A comprehensive Python-based CAT interface driver that enables seamless integration between (tr)uSDX QRP transceivers and popular ham radio software on Linux systems. This driver emulates the Kenwood TS-480 protocol while providing audio streaming capabilities for digital modes.

## 🎯 Features

### Core Functionality
- **Kenwood TS-480 CAT Emulation**: Full compatibility with WSJT-X, JS8Call, FlDigi, and Winlink
- **Automatic Device Detection**: Finds and connects to (tr)uSDX hardware automatically
- **Dual Audio Backend Support**: Works with both ALSA loopback and PipeWire virtual devices
- **CAT Audio Streaming**: Native (tr)uSDX audio streaming over USB (UA0/UA1/UA2 commands)
- **Persistent Connection Management**: Automatic reconnection on hardware disconnect
- **Real-time Frequency Synchronization**: Maintains accurate frequency display between radio and software

### Advanced Features
- **RTS/DTR Hardware Protection**: Intelligent signal neutralization prevents USB conflicts
- **TX/RX State Management**: Smooth transition handling with audio buffering
- **VU Meter Display**: Visual feedback during transmission
- **Comprehensive Logging**: Detailed debug logs for troubleshooting
- **Virtual Serial Port Creation**: Provides `/tmp/trusdx_cat` for CAT control
- **Multi-rate Audio Support**: Handles different sample rates for RX (7825 Hz) and TX (11520 Hz)

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
   - Audio Input (from radio): `ALSA Loopback card 0` (or `hw:Loopback,1,0`)
   - Audio Output (to radio): `ALSA Loopback card 0` (or `hw:Loopback,0,0`)
   
   The driver uses ALSA Loopback devices for audio routing.

## 📋 Requirements

### Hardware Requirements
- **(tr)uSDX Transceiver**: Any variant of the truSDX or uSDX QRP transceiver
- **USB Connection**: CH340/CH341 USB-to-serial converter (built into most (tr)uSDX units)
- **Computer**: Linux PC with available USB port

### Software Requirements
- **Python**: Version 3.12 or higher (tested with 3.12+)
- **Operating System**: Linux (tested on Ubuntu 24.04, Linux Mint 21/22, Fedora 40)
- **Ham Radio Software**: WSJT-X, JS8Call, FlDigi, or Winlink (optional)

### Python Dependencies
- `pyserial>=3.5` - Serial port communication
- `pyaudio>=0.2.11` - Audio stream handling

### System Dependencies
- `portaudio19-dev` - Audio library backend
- `pulseaudio-utils` or `pipewire` - Audio system
- `socat` (optional) - Virtual serial port creation for testing

## 📦 Installation

### Quick Install (Recommended)
```bash
# Clone the repository
git clone https://github.com/miltonics/truSDX-Linux.git
cd truSDX-Linux

# Run the setup script (handles everything)
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Install all system dependencies
- Set up Python virtual environment
- Configure ALSA loopback devices
- Create PipeWire virtual audio devices (if available)
- Set up udev rules for USB permissions
- Create necessary symlinks

### Manual Installation
If you prefer manual setup:
```bash
# Install system dependencies
sudo apt update
sudo apt install python3 python3-pip python3-venv portaudio19-dev

# Install Python packages
pip3 install --user pyserial pyaudio

# Load ALSA loopback module
sudo modprobe snd-aloop
echo "snd-aloop" | sudo tee -a /etc/modules

# Configure serial port
stty -F /dev/ttyUSB0 raw -echo -echoe -echoctl -echoke -hupcl 115200
```

## 📡 Supported CAT Commands

The (tr)uSDX supports a subset of the Kenwood TS-480 CAT interface, plus custom extensions for audio streaming.

### Standard TS-480 Commands
| Command | Description | Example |
|---------|-------------|---------||
| `FA;` | Get frequency | Returns: `FA00014195000;` |
| `FA[freq];` | Set frequency in Hz | `FA00014195000;` (14.195 MHz) |
| `MD;` | Get mode | Returns: `MD2;` (USB) |
| `MD[n];` | Set mode | `MD1;` (LSB), `MD2;` (USB), `MD3;` (CW), `MD4;` (FM), `MD5;` (AM) |
| `IF;` | Get transceiver status | Returns frequency and mode |
| `TX0;` | Set PTT ON (transmit) | Start transmission |
| `TX1;` | Set PTT ON (alternate) | Start transmission |
| `TX2;` | Set TUNE mode | CW tune (mode must be CW) |
| `RX;` | Set PTT OFF (receive) | Stop transmission |
| `ID;` | Get transceiver ID | Returns: `ID020;` (TS-480) |
| `PS;` `PS1;` | Power status | Power on status |
| `AI;` `AI0;` | Auto information | Disable auto info |
| `AG0;` | Audio gain | Get/set audio gain |
| `XT1;` `RT1;` | XIT/RIT control | Transmit/receive incremental tuning |
| `RC;` | Clear RIT | Clear receive incremental tuning |
| `FL0;` | Filter | Get filter settings |
| `RS;` | Reset | Reset transceiver |
| `VX;` | VOX status | Voice operated switch status |

### CAT Audio Streaming Extensions
| Command | Description | Details |
|---------|-------------|---------||
| `UA0;` | Disable CAT streaming | CAT control only (default) |
| `UA1;` | Enable streaming + speaker | CAT control + audio with speaker ON |
| `UA2;` | Enable streaming - speaker | CAT control + audio with speaker OFF |
| `US[data];` | Audio stream data | U8 format audio until ';' character |

**Audio Streaming Notes:**
- RX Sample Rate: 7825 Hz (8-bit unsigned)
- TX Sample Rate: 11520 Hz (8-bit unsigned)
- Dynamic Range: 46 dB (8-bit limitation)
- Stream can be interrupted with CAT commands starting with ';'

## 💻 Configuration for Ham Radio Applications

### WSJT-X Configuration
1. **Radio Tab:**
   - Rig: Kenwood TS-480
   - Serial Port: `/tmp/trusdx_cat`
   - Baud Rate: 115200
   - Data/Stop Bits: 8/1
   - Handshake: None
   - PTT Method: CAT

2. **Audio Tab:**
   - Input: `trusdx_rx` (ALSA) or `TRUSDX.monitor` (PipeWire)
   - Output: `trusdx_tx` (ALSA) or `TRUSDX` (PipeWire)

### JS8Call Configuration
1. **Settings → Radio:**
   - Radio: Kenwood TS-480
   - CAT Control: `/tmp/trusdx_cat`
   - Baud Rate: 115200
   - PTT: CAT

2. **Settings → Audio:**
   - Capture: `hw:Loopback,1,0` or PipeWire source
   - Playback: `hw:Loopback,0,0` or PipeWire sink

### FlDigi Configuration
1. **Configure → Rig Control → Hamlib:**
   - Rig: Kenwood TS-480
   - Device: `/tmp/trusdx_cat`
   - Baud: 115200
   - PTT: Use Hamlib

2. **Configure → Sound Card:**
   - Capture: ALSA Loopback or PipeWire
   - Playback: ALSA Loopback or PipeWire

## 🛠️ Usage

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
- ALSA Loopback device configuration
- Application audio routing (JS8Call, WSJT-X, FLDigi)
- Connection verification
- Audio recording test

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
1. Check the troubleshooting section below
2. Review the detailed logs the script provides
3. If `hw:Loopback` does not exist, run `sudo modprobe snd-aloop` and reboot
4. Open an issue on GitHub with your configuration details

## Troubleshooting

### ALSA Loopback Not Found
If you get errors about `hw:Loopback` not existing:
1. Load the ALSA loopback module: `sudo modprobe snd-aloop`
2. Make it persistent: `echo "snd-aloop" | sudo tee -a /etc/modules`
3. Reboot your system for the changes to take full effect
4. Verify the device exists: `aplay -l | grep Loopback`

## 👥 Credits & Acknowledgments

### Original Authors
- **SQ3SWF** - Original truSDX driver development (2023)
- **PE1NNZ** - Core protocol implementation and hardware interface
- **AI-Enhanced Version** (2025) - Extended CAT support, audio streaming, connection management

### Contributors
- **Milton (miltonics)** - Linux port maintainer, testing, documentation
- The amateur radio community for testing and feedback

### Special Thanks
- JS8Call developers for their excellent digital mode software
- WSJT-X team for pioneering weak signal communication
- The (tr)uSDX hardware community for creating affordable QRP transceivers

## 📄 License

This project is released under the MIT License. See [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2023-2025 SQ3SWF, PE1NNZ, and contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

## 📡 Contact & Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/miltonics/truSDX-Linux/issues)
- **Discussions**: [Join the conversation](https://github.com/miltonics/truSDX-Linux/discussions)

---

**73 de Milton and the truSDX Linux Driver Team** 📡
