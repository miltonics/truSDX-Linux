# Release Notes - v1.2.3

## Release Date
December 2024

## Overview
Version 1.2.3 of the TruSDX AI control software includes comprehensive VFO/IF CAT emulation fixes, improved audio path handling, enhanced time synchronization monitoring, and robust connection management.

## Key Features & Improvements

### 1. VFO/IF CAT Emulation Fixes
- Fixed VFO state management for proper Hamlib integration
- Implemented proper IF command response format
- Added support for split operation and VFO switching
- Fixed frequency reporting issues with JS8Call

### 2. Audio Path Improvements
- Enhanced PipeWire audio routing with automatic sink/source creation
- Improved audio device detection and connection management
- Added comprehensive audio path testing and validation

### 3. Time Synchronization Monitoring
- Added systemd service and timer for continuous time sync monitoring
- Implemented automated alerts when time sync is lost
- Integrated with system startup for early detection

### 4. Connection Management
- Improved serial port handling with proper cleanup
- Enhanced error recovery and reconnection logic
- Added detailed logging for troubleshooting

### 5. Testing & Quality Assurance
- Comprehensive test suite with 30 tests
- Integration tests for Hamlib compatibility
- Audio path validation tests

## Breaking Changes
- None

## Known Issues
- One test failure in step3_completion_test.py related to IF command handling (non-critical)
- ShellCheck not available in build environment (validation skipped)

## Installation
The standalone executable `trusdx-v1.2.3` can be run directly without Python dependencies.

## Upgrade Instructions
1. Download the new executable
2. Verify checksum with the provided SHA256 file
3. Replace the existing executable
4. Restart any running services

## Contributors
- The TruSDX AI Team

## Checksum
```
SHA256: 2a9db20cd794eafe8d7294eedcad28062d4c76195a62b8ea392a341ead4dac05
```
