# Changelog

All notable changes to the truSDX-AI Driver project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

*Current build: v1.1.6-pre-refactor-dirty (2025-07-09)*

### Added
- TBD - Future features will be added here

### Changed
- TBD - Future changes will be documented here

## [1.2.0] - 2025-01-27

### Added
- Hardware reconnection and monitoring system
- Automatic device detection and recovery
- Enhanced connection stability monitoring
- Improved error handling with retry mechanisms
- Connection manager with persistent monitoring
- Hardware status tracking and reporting
- Enhanced error handling and recovery mechanisms
- Improved GUI integration
- Better cross-platform compatibility
- Performance optimizations
- Auto-update version & build date via git describe
- Pre-commit hook for version management

### Changed
- Updated version to 1.2.0-AI-MONITORING-RECONNECT
- Enhanced main loop with connection monitoring
- Improved thread management and cleanup
- Restructured project architecture for better maintainability
- Documentation package with Keep-a-Changelog format
- Enhanced troubleshooting documentation
- Improved testing documentation

### Fixed
- Hardware disconnection detection and recovery
- Connection stability issues during TX/RX operations
- Thread safety improvements
- Memory leaks in connection monitoring
- Race conditions in TX/RX switching

## [1.1.8] - 2024-06-23

### Added
- Comprehensive VFO debugging and Hamlib compatibility
- Enhanced frequency reading with robust radio state initialization
- Automatic frequency detection at startup
- Improved TX/RX control for JS8Call integration

### Fixed
- CAT binary data corruption issues
- VFO handling for better Hamlib compatibility
- Frequency synchronization between JS8Call and radio
- TX instability by disabling power monitoring by default

### Changed
- Enhanced debugging output for frequency operations
- Improved CAT command forwarding
- Better error handling for serial communications

## [1.1.7] - 2024-06-22

### Added
- Startup frequency reading from radio
- Persistent frequency header display
- Enhanced frequency debugging capabilities

### Fixed
- Frequency initialization issues
- JS8Call default frequency blocking (14.074 MHz)
- Radio frequency synchronization problems

## [1.1.6] - 2024-06-21

### Added
- GUI requirements and --nogui flag support
- Comprehensive testing framework
- Enhanced VU meter support
- Waterfall display improvements

### Fixed
- Audio configuration stability
- TX0 command handling
- Radio state persistence

### Changed
- Improved audio routing and setup
- Enhanced user experience with better feedback
- Streamlined installation process

## [1.1.5] - 2024-06-20

### Added
- Enhanced pull request documentation
- Comprehensive verification scripts
- Improved GitHub integration

### Fixed
- Audio configuration issues
- Serial port handling improvements
- Enhanced error recovery

## [1.1.0] - 2024-06-15

### Added
- Initial AI-enhanced version
- Kenwood TS-480 CAT interface emulation
- Persistent serial port configuration
- Comprehensive audio system integration
- VU meter and waterfall display support

### Features
- **Automatic Frequency Detection**: Reads current radio frequency at startup
- **TX/RX Control**: Handles transmission switching for JS8Call
- **VU Meter Support**: Visual transmission feedback during operation
- **CAT Command Forwarding**: Transparent command passing between JS8Call and radio
- **Robust Error Handling**: Multiple retry attempts with comprehensive debugging
- **Auto-detection**: Automatically finds TruSDX USB device

### Hardware Compatibility
- TruSDX QRP Transceiver
- Linux systems (Ubuntu, Mint, Debian)
- JS8Call v2.2+
- WSJT-X integration

### Installation
- Automated setup script with dependency management
- Hamlib 4.6.3 integration
- PulseAudio configuration for persistent audio devices
- Python 3.6+ compatibility

## [1.0.0] - 2024-06-10

### Added
- Initial project structure
- Basic CAT interface implementation
- Audio system integration
- Serial communication handling
- Linux-specific optimizations

### Technical Details
- Python-based implementation
- PyAudio for audio handling
- PySerial for CAT communication
- Hamlib integration for radio control
- PulseAudio virtual sink creation

---

## Development Notes

### Version History Summary
- **v1.2.0**: Current development version with monitoring and reconnection
- **v1.1.8**: Stable version with VFO and frequency fixes
- **v1.1.6**: Enhanced GUI and testing framework
- **v1.1.0**: Major AI-enhanced release
- **v1.0.0**: Initial working implementation

### Key Branches
- `main`: Current development branch (v1.2.0)
- `master`: Original stable branch
- `fix-tx0-and-init-frequency`: Frequency handling fixes

### Commit Statistics
- Total commits: 25+ with comprehensive feature development
- Major milestones: Initial commit, AI enhancement, frequency fixes, monitoring system
- Current HEAD: `8fc3c31` - Fix CAT binary data corruption and enhance VFO handling

---

*This changelog is maintained as part of the truSDX-AI Driver project. For detailed commit history, see `git log --oneline --graph --all`.*
