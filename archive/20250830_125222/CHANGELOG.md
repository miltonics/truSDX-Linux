# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.5] - 2025-01-20

### Fixed
- Fixed application crash issue

### Added
- Added *_app aliases for improved usability

## [1.2.3] - 2025-01-XX

### Added
- Time synchronization watcher for improved digital mode timing accuracy
- Automatic audio device connection on startup and reconnection
- Improved setup script with better error handling and user feedback
- Step-by-step Linux installation guide with screenshots
- Comprehensive troubleshooting FAQ section
- JS8Call configuration guide with detailed screenshots

### Fixed
- CAT VFO handling for better JS8Call compatibility
- VFO frequency management to prevent JS8Call lockups
- Audio device auto-reconnection after system sleep/suspend
- Setup script now properly handles missing dependencies

### Changed
- Enhanced documentation with clearer Linux-specific instructions
- Improved error messages for common setup issues
- Better handling of audio device disconnections

### Notes
- Windows functionality remains unchanged from v1.2.2
- All improvements in this release are Linux-specific enhancements

## [1.2.2] - 2025-07-09

### Added
- Comprehensive code-base audit and issue tracking system
- Enhanced CAT command processing with better error handling
- Improved VFO frequency management for JS8Call compatibility
- Better debugging output with color-coded messages
- Enhanced frequency validation and protection mechanisms
- Improved startup frequency detection with robust error handling
- Added comprehensive testing framework with multiple test scenarios

### Fixed
- Fixed CAT binary data corruption in VFO handling
- Improved VFO handling for better Hamlib compatibility
- Fixed frequency reading approach using CAT forwarding
- Resolved JS8Call default frequency conflicts (14.074 MHz blocking)
- Fixed TX0 usage and current frequency reading on startup
- Improved error handling in CAT command processing
- Fixed audio configuration issues with persistent header updates

### Changed
- Updated version tracking and build date management
- Enhanced connection monitoring and stability improvements
- Improved CAT command forwarding with better state management
- Refined frequency change validation logic
- Enhanced debugging and logging capabilities
- Improved documentation and setup instructions

### Security
- Added RTS/DTR driver shim for hardware protection
- Improved USB communication stability with TruSDX hardware
- Enhanced error handling to prevent system crashes

## [1.2.0] - 2024-12-XX

### Added
- AI-enhanced monitoring and reconnection features
- Hardware reconnection and monitoring system
- Automatic device detection and recovery
- Enhanced connection stability monitoring
- Improved error handling with retry mechanisms
- Connection manager with persistent monitoring
- Hardware status tracking and reporting
- Enhanced GUI integration and cross-platform compatibility
- Performance optimizations and documentation improvements
- pip installation support with setup.py

### Fixed
- Power monitoring stability issues
- TX instability problems
- Connection recovery mechanisms

## [1.1.6] - 2024-XX-XX

### Added
- CAT binary data corruption fixes
- VFO debugging and Hamlib compatibility improvements
- GUI requirements and --nogui flag support

### Fixed
- VFO handling for Hamlib compatibility
- Power monitoring disabled by default to prevent TX instability

## [1.1.0] - 2024-XX-XX

### Added
- Initial release with basic TruSDX integration
- JS8Call CAT interface support
- Frequency detection and TX/RX control
- VU meter support
- Basic error handling and debugging
