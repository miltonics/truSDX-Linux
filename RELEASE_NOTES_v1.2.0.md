# truSDX-AI Driver v1.2.0 Release Notes

## Overview
This is a major release of the truSDX-AI Driver, introducing comprehensive monitoring and reconnection capabilities for improved reliability and user experience.

## New Features

### 🔗 Hardware Monitoring & Reconnection
- **Automatic Device Detection**: Driver now automatically detects and recovers from hardware disconnections
- **Connection Stability Monitoring**: Continuous monitoring of serial and audio connections
- **Intelligent Reconnection**: Automated reconnection with exponential backoff and retry logic
- **Hardware Status Tracking**: Real-time tracking and reporting of device status

### 🖥️ Enhanced User Interface
- **Persistent Header Display**: Shows version, callsign, connection status, and power information
- **Dynamic Status Updates**: Real-time updates of connection and power status
- **Improved Color Support**: Better terminal color detection and fallback support
- **Enhanced Error Reporting**: More informative error messages and recovery suggestions

### 📊 Performance Improvements
- **Optimized Connection Handling**: Reduced reconnection time and improved stability
- **Better Thread Management**: Enhanced thread safety and cleanup
- **Memory Leak Fixes**: Resolved memory leaks in connection monitoring
- **Reduced CPU Usage**: More efficient polling and monitoring algorithms

### 🛠️ Development & Testing
- **Comprehensive Test Suite**: Added extensive integration and unit tests
- **Automated Version Management**: Git-based version and build date management
- **Enhanced Documentation**: Complete API documentation and troubleshooting guides
- **Pip Installation Support**: Full setuptools integration for easy installation

## Installation

### From Source
```bash
git clone https://github.com/milton-tanaka/trusdx-ai.git
cd trusdx-ai
pip install -e .
```

### Using Pre-built Binaries
Download the appropriate binary for your system from the release assets.

## System Requirements
- Python 3.6 or higher
- Linux (Ubuntu, Debian, Mint, etc.)
- TruSDX QRP Transceiver
- USB connection to radio
- PyAudio and PySerial libraries

## Compatibility
- **JS8Call**: v2.2+
- **WSJT-X**: All supported versions
- **FlDigi**: Compatible
- **Winlink**: Compatible

## Breaking Changes
- Configuration file location changed to `~/.config/trusdx-ai/config.json`
- Some command-line arguments have been reorganized
- Pre-commit hooks now automatically update version information

## Bug Fixes
- Fixed CAT binary data corruption issues
- Resolved VFO handling for better Hamlib compatibility
- Fixed frequency synchronization between JS8Call and radio
- Improved TX stability by disabling power monitoring by default during transmission
- Fixed race conditions in TX/RX switching
- Resolved thread safety issues in connection monitoring

## Known Issues
- Some terminals may not display colors correctly (fallback to plain text)
- First-time setup requires proper audio device configuration
- Windows compatibility is limited (Linux-focused release)

## Migration Guide
If upgrading from v1.1.x:
1. Backup your existing configuration
2. Update your installation using the new pip method
3. Verify audio device configuration
4. Test connection with your preferred digital mode software

## Contributing
We welcome contributions! Please see the CONTRIBUTING.md file for guidelines.

## Support
- GitHub Issues: https://github.com/milton-tanaka/trusdx-ai/issues
- Documentation: https://github.com/milton-tanaka/trusdx-ai/blob/main/README.md
- Amateur Radio Community Forums

## Acknowledgments
Special thanks to the amateur radio community, JS8Call developers, and all contributors who helped make this release possible.

---

**73 de Milton**  
*SQ3SWF, PE1NNZ, AI-Enhanced Development Team*
