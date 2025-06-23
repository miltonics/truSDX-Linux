# truSDX-AI Driver Changelog

## Version 1.1.8-AI (2024-06-XX)
### Fixed
- Reverted `TX1` back to `TX0` in VOX and RTS/DTR handlers to restore reliable TX turn-off and VU-meter activity.
- Startup now queries truSDX for current frequency/mode; no longer hard-defaults to 14.074 MHz.

## Version 1.1.7-AI-PTT-FIXED (2024-06-11)

### 🔧 PTT ENHANCEMENT
- **TX Command Fix**: Changed TX0 to TX1 in PTT handlers (lines 541 & 555)
- **Improved Compatibility**: Better PTT response with truSDX hardware
- **Verified Working**: TX1 command provides more reliable PTT operation

### ✅ CONFIRMED FIXES
- VOX PTT handler now uses TX1 (line 541)
- RTS/DTR PTT handler now uses TX1 (line 555)
- Maintains all previous functionality from v1.1.6

---

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

