# Testing Guide

This guide provides comprehensive testing procedures for the truSDX-AI Driver project.

## Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Unit Tests](#unit-tests)
4. [Integration Tests](#integration-tests)
5. [Hardware Tests](#hardware-tests)
6. [Performance Tests](#performance-tests)
7. [Automated Testing](#automated-testing)
8. [Test Data and Fixtures](#test-data-and-fixtures)
9. [Continuous Integration](#continuous-integration)
10. [Manual Testing Procedures](#manual-testing-procedures)

## Overview

The truSDX-AI Driver project includes comprehensive testing to ensure reliability, compatibility, and performance across different configurations.

### Test Categories

- **Unit Tests**: Individual component functionality
- **Integration Tests**: Component interaction testing
- **Hardware Tests**: Physical device interaction
- **Performance Tests**: System performance and resource usage
- **Compatibility Tests**: Software integration testing

## Test Environment Setup

### Prerequisites

```bash
# Install testing dependencies
sudo apt install python3 python3-pip portaudio19-dev pulseaudio-utils
pip3 install --user -r requirements.txt

# Install additional testing tools
pip3 install --user pytest pytest-cov pytest-mock memory-profiler
```

### Test Hardware

- TruSDX QRP Transceiver (connected via USB)
- Linux system with PulseAudio
- Audio loopback capability
- Network connectivity for CAT testing

### Environment Variables

```bash
export TRUSDX_TEST_MODE=1
export TRUSDX_TEST_DEVICE="/dev/ttyUSB0"  # Adjust as needed
export TRUSDX_TEST_VERBOSE=1
```

## Unit Tests

### Audio System Tests

#### Test Audio Device Detection

```bash
python3 test_audio_handling.py
```

**Purpose**: Verify audio device enumeration and configuration
**Expected Result**: Lists available audio devices including TruSDX

#### Test Audio I/O Operations

```bash
python3 test_vu_meter.py
```

**Purpose**: Validate VU meter functionality and audio processing
**Expected Result**: VU meter responds to audio input

#### Test Audio Routing

```bash
python3 test_vu_waterfall.py
```

**Purpose**: Test audio routing and waterfall display
**Expected Result**: Audio signal properly routed and displayed

### CAT Interface Tests

#### Test CAT Emulation

```bash
python3 test_cat_emulation.py
```

**Purpose**: Verify CAT command processing and response
**Expected Result**: Proper command parsing and response generation

#### Test Direct CAT Communication

```bash
python3 test_cat_direct.py
```

**Purpose**: Test direct serial communication with TruSDX
**Expected Result**: Successful command transmission and response

#### Test TS-480 Compatibility

```bash
python3 test_cat_ts480_comprehensive.py
```

**Purpose**: Validate Kenwood TS-480 command compatibility
**Expected Result**: All supported commands work correctly

### Connection Management Tests

#### Test Connection Manager

```bash
python3 test_connection_manager.py
```

**Purpose**: Verify connection establishment and monitoring
**Expected Result**: Successful connection and reconnection handling

#### Test Hardware Detection

```bash
python3 test_rigctld.py
```

**Purpose**: Test rigctld integration and compatibility
**Expected Result**: Proper rigctld communication established

### Logging System Tests

#### Test Logging Configuration

```bash
python3 test_logging.py
```

**Purpose**: Verify logging system functionality
**Expected Result**: Proper log file creation and message formatting

## Integration Tests

### JS8Call Integration

#### Test JS8Call Configuration

```bash
python3 test_js8call_config.py
```

**Purpose**: Validate JS8Call integration and configuration
**Expected Result**: Successful JS8Call connection and communication

**Test Steps**:
1. Start truSDX-AI driver
2. Connect JS8Call to localhost:4532
3. Verify frequency synchronization
4. Test TX/RX switching
5. Validate audio routing

### WSJT-X Integration

#### Test WSJT-X Compatibility

```bash
python3 test_wsjt_integration.py
```

**Purpose**: Verify WSJT-X compatibility and operation
**Expected Result**: Successful WSJT-X integration

### End-to-End Testing

#### Test Complete System

```bash
python3 run_test_matrix.py
```

**Purpose**: Comprehensive system testing with multiple configurations
**Expected Result**: All test cases pass successfully

## Hardware Tests

### TruSDX Communication Tests

#### Test Hardware Detection

```bash
python3 -c "
from src.connection_manager import ConnectionManager
cm = ConnectionManager()
print(f'TruSDX detected: {cm.detect_trusdx()}')
"
```

#### Test Serial Communication

```bash
python3 test_id_command.py
```

**Purpose**: Test basic serial communication with TruSDX
**Expected Result**: Successful ID command execution

#### Test Power Monitoring

```bash
python3 test_power_monitor.py
```

**Purpose**: Validate power monitoring functionality
**Expected Result**: Accurate power readings during TX

### TX/RX Testing

#### Test TX0 Command

```bash
python3 test_cat_direct.py
```

**Purpose**: Verify TX0 command handling and radio response
**Expected Result**: Proper TX/RX switching

#### Test Frequency Control

```bash
python3 test_frequency_control.py
```

**Purpose**: Test frequency setting and reading
**Expected Result**: Accurate frequency control

## Performance Tests

### Memory Usage Testing

#### Test Memory Leaks

```bash
python3 -m memory_profiler trusdx-txrx-AI.py
```

**Purpose**: Identify memory leaks during operation
**Expected Result**: Stable memory usage over time

#### Test Resource Usage

```bash
python3 test_performance.py
```

**Purpose**: Monitor CPU and memory usage under load
**Expected Result**: Resource usage within acceptable limits

### Stress Testing

#### Test Connection Stability

```bash
python3 test_connection_stress.py
```

**Purpose**: Test system stability under stress conditions
**Expected Result**: Stable operation without crashes

## Automated Testing

### Test Runner Script

```bash
#!/bin/bash
# run_all_tests.sh

echo "Running truSDX-AI Driver Test Suite..."

# Set test environment
export TRUSDX_TEST_MODE=1

# Unit tests
echo "Running unit tests..."
python3 test_audio_handling.py
python3 test_cat_emulation.py
python3 test_connection_manager.py
python3 test_logging.py

# Integration tests
echo "Running integration tests..."
python3 test_js8call_config.py
python3 run_test_matrix.py

# Hardware tests (if hardware available)
if [ -e "/dev/ttyUSB0" ]; then
    echo "Running hardware tests..."
    python3 test_cat_direct.py
    python3 test_id_command.py
    python3 test_power_monitor.py
fi

echo "Test suite completed."
```

### Test Matrix

```bash
python3 run_test_matrix.py
```

**Test Matrix Includes**:
- Multiple audio configurations
- Different CAT command sets
- Various system configurations
- Error condition handling

## Test Data and Fixtures

### Audio Test Data

- Sample audio files for testing
- Frequency sweep signals
- Noise patterns for VU meter testing

### CAT Command Test Data

- Known good command sequences
- Error condition test cases
- Frequency control test patterns

### Configuration Test Data

- Valid configuration files
- Invalid configuration test cases
- Edge case configurations

## Continuous Integration

### Pre-commit Hooks

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit tests..."

# Run basic tests
python3 test_audio_handling.py
python3 test_cat_emulation.py
python3 test_logging.py

# Check code style
python3 -m flake8 src/
python3 -m mypy src/

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi

echo "Pre-commit tests passed."
```

### GitHub Actions Workflow

```yaml
name: CI Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.8
    
    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev pulseaudio-utils
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: |
        python3 test_audio_handling.py
        python3 test_cat_emulation.py
        python3 test_connection_manager.py
        python3 test_logging.py
```

## Manual Testing Procedures

### Basic Functionality Test

1. **Start the driver**:
   ```bash
   python3 trusdx-txrx-AI.py --verbose
   ```

2. **Verify startup sequence**:
   - Check TruSDX detection
   - Verify audio device initialization
   - Confirm CAT interface startup

3. **Test JS8Call connection**:
   - Start JS8Call
   - Configure CAT control (localhost:4532)
   - Verify frequency synchronization
   - Test TX/RX switching

### Audio Testing

1. **Test VU meter**:
   ```bash
   python3 trusdx-txrx-AI.py --unmute
   ```

2. **Verify audio routing**:
   - Check PulseAudio sources
   - Test audio loopback
   - Validate waterfall display

3. **Test audio quality**:
   - Listen for distortion
   - Check audio levels
   - Verify frequency response

### CAT Interface Testing

1. **Test CAT commands**:
   ```bash
   telnet localhost 4532
   ```

2. **Test command sequences**:
   - FA command (frequency read)
   - TX0/TX1 commands
   - ID command

3. **Test error handling**:
   - Invalid commands
   - Timeout conditions
   - Connection drops

### Performance Testing

1. **Monitor resource usage**:
   ```bash
   top -p $(pgrep -f trusdx-txrx-AI.py)
   ```

2. **Test stability**:
   - Run for extended periods
   - Monitor memory usage
   - Check for thread leaks

3. **Test under load**:
   - Multiple applications connected
   - High audio activity
   - Frequent TX/RX switching

## Test Results Documentation

### Test Report Template

```
# Test Report
Date: [DATE]
Version: [VERSION]
Tester: [NAME]

## Test Environment
- OS: [OS_VERSION]
- Python: [PYTHON_VERSION]
- Hardware: [HARDWARE_INFO]

## Test Results
- Unit Tests: [PASS/FAIL]
- Integration Tests: [PASS/FAIL]
- Hardware Tests: [PASS/FAIL]
- Performance Tests: [PASS/FAIL]

## Issues Found
- [ISSUE_DESCRIPTION]
- [RESOLUTION/WORKAROUND]

## Recommendations
- [RECOMMENDATIONS]
```

### Test Coverage

Current test coverage goals:
- Unit tests: >90%
- Integration tests: >80%
- Hardware tests: >70%
- Performance tests: >60%

## Troubleshooting Test Issues

### Common Test Failures

1. **Audio device not found**:
   - Check PulseAudio service
   - Verify device permissions
   - Test audio system independently

2. **CAT communication failure**:
   - Verify serial port access
   - Check device permissions
   - Test hardware connection

3. **Performance test failures**:
   - Reduce system load
   - Check for background processes
   - Verify test environment

### Test Environment Issues

1. **Permission errors**:
   ```bash
   sudo usermod -a -G dialout $USER
   ```

2. **Missing dependencies**:
   ```bash
   pip3 install --user -r requirements.txt
   ```

3. **Hardware not available**:
   - Use test mode
   - Mock hardware interfaces
   - Skip hardware-dependent tests

## Best Practices

### Writing Tests

1. **Test isolation**: Each test should be independent
2. **Mock external dependencies**: Use mocks for hardware interfaces
3. **Clear assertions**: Use descriptive assertion messages
4. **Test edge cases**: Include boundary conditions and error cases

### Running Tests

1. **Clean environment**: Start with fresh test environment
2. **Consistent hardware**: Use same hardware configuration
3. **Document results**: Keep detailed test logs
4. **Regression testing**: Re-run tests after changes

### Debugging Test Failures

1. **Enable verbose logging**: Use `--verbose` flag
2. **Isolate failures**: Run individual test components
3. **Check dependencies**: Verify all prerequisites are met
4. **Review logs**: Analyze error messages and stack traces

---

*Last updated: 2025-01-27*
*Version: 1.2.0-AI-MONITORING-RECONNECT*
