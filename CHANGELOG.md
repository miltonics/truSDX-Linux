# truSDX-AI Driver Changelog

## Version 1.2.0 (2024-12-19)

### 🚀 MAJOR ENHANCEMENTS - Production Ready Release

**This version introduces significant improvements for stability, usability, and documentation.**

### ✅ SCRIPT ENHANCEMENTS
• **Script Rename**: `trusdx-txrx-AI.py` → `trusdx-rxtx-AI.py` (corrected RX/TX order for clarity)
• **Backward Compatibility**: Maintained via symlink for existing configurations
• **Enhanced Setup Script**: Non-interactive installation with modular Hamlib 4.6.3 support
• **Improved Error Handling**: Better diagnostics and logging throughout setup process
• **Version Management**: Centralized version system via `version.py` module

### 🔧 SYSTEM INTEGRATION
• **CH341 Kernel Module**: Automatic detection and loading for truSDX USB-serial support
• **PulseAudio Integration**: Persistent TRUSDX sink creation with auto-configuration
• **Dialout Group**: Automatic user addition for serial port access permissions
• **Hamlib 4.6.3**: Optional modular installation for enhanced CAT control
• **Dependencies**: Streamlined Python package management with user-space installs

### 📚 DOCUMENTATION OVERHAUL
• **README.md**: Complete rewrite with current script names and system requirements
• **INSTALL.txt**: CLI-focused quick installation guide for end users
• **Troubleshooting**: Enhanced sections covering kernel modules, audio, and permissions
• **System Requirements**: Updated minimum requirements and compatibility matrix
• **Quick Start**: Streamlined setup process with current script references

### 🛠️ TECHNICAL IMPROVEMENTS
• **Persistent Banner**: Always-visible connection information for WSJT-X/JS8Call
• **Audio Architecture**: Improved virtual PulseAudio sink management
• **CAT Protocol**: Enhanced Kenwood TS-480 command compatibility (95+ commands)
• **Configuration**: JSON-based persistent settings with error recovery
• **Serial Ports**: Consistent `/tmp/trusdx_cat` port allocation

### 🔍 TROUBLESHOOTING ENHANCEMENTS
• **Kernel Module**: CH341 driver detection and manual loading instructions
• **Audio Issues**: PulseAudio sink verification and pavucontrol guidance
• **Permission Issues**: Dialout group membership and login requirements
• **CAT Control**: Poll interval optimization and baud rate troubleshooting
• **USB Detection**: Device enumeration and connection verification

### 📋 VERIFIED COMPATIBILITY
• **Operating Systems**: Ubuntu 20.04+, Debian 11+, Linux Mint 20+
• **Python**: 3.6+ with enhanced package management
• **Software**: WSJT-X 2.6+, JS8Call 2.2+, FLDigi 4.1+, Winlink
• **Hardware**: truSDX with CH341 USB-serial interface
• **Audio**: PulseAudio with virtual sink support

## Version 1.1.6-AI-VU-WORKING (2024-06-10)

### 🎉 MAJOR MILESTONE - CONTACT MADE!

**This version has been proven working with successful contacts made!**

### ✅ FIXED
- **Frequency Control**: Commands FA/FB now properly forward to truSDX hardware
- **Band Changes**: WSJT-X band/frequency changes now work correctly
- **VU Meter**: Audio levels display properly in WSJT-X
- **Audio Routing**: Stable audio streaming in both directions
- **CAT Stability**: Improved command handling and timing

### 🔧 TECHNICAL CHANGES
- Modified frequency command handling to forward FA/FB set commands to hardware
- Maintained local state for frequency read commands
- Enhanced error handling for serial communication
- Improved debug output for troubleshooting

### 📋 VERIFIED WORKING
- [x] Audio streaming (RX/TX)
- [x] VU meter functionality
- [x] Frequency/band control
- [x] PTT control (CAT and RTS/DTR)
- [x] Kenwood TS-480 CAT emulation
- [x] WSJT-X integration
- [x] Successful contacts made

### 🎯 DISTRIBUTION READY
- Created clean distribution package
- Added comprehensive setup script
- Included detailed documentation
- Verified all dependencies

## Previous Versions

### Version 1.1.5 (2024-06-09)
- Enhanced VU meter functionality
- Improved audio level detection
- Better ALSA error handling

### Version 1.1.0 (2024-06-08)
- Added persistent serial ports
- Implemented full TS-480 CAT emulation
- Enhanced audio device management

### Version 1.0.x (2024-06-07)
- Initial AI enhancements
- Improved error handling
- Added configuration persistence

---

**Status**: PRODUCTION READY ✅  
**Tested**: Linux Mint, Ubuntu  
**Verified**: Successful contacts made  
**Ready**: For forum distribution

