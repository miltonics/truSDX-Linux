# truSDX Driver Regression Testing

## Overview

This repository includes comprehensive regression testing for the truSDX audio driver, designed to simulate WSJT-X operation and verify driver stability under various conditions.

## Test Scripts

### 1. `regression_test.sh` - Full Interactive Test
- **Purpose**: Complete regression test with detailed output and visualization
- **Duration**: ~2 minutes for basic test, configurable
- **Features**:
  - Simulates WSJT-X audio streams using `arecord`/`aplay`
  - Tests driver stability over time
  - Verifies stream reconnection logic
  - Provides colored terminal output
  - Generates detailed logs

### 2. `ci_regression_test.sh` - CI/CD Optimized Test
- **Purpose**: Lightweight test for automated CI/CD pipelines
- **Duration**: ~1 minute
- **Features**:
  - GitHub Actions/GitLab CI compatible
  - JUnit XML output for test reporting
  - Automatic dependency installation in CI
  - Exit codes for CI integration
  - Minimal resource usage

## Running Tests Locally

### Prerequisites

1. **Install required packages**:
```bash
# Ubuntu/Debian
sudo apt-get install alsa-utils portaudio19-dev sox python3-pip

# Fedora/RHEL
sudo dnf install alsa-utils portaudio-devel sox python3-pip
```

2. **Install Python dependencies**:
```bash
pip3 install pyserial pyaudio
```

3. **Load ALSA loopback module**:
```bash
sudo modprobe snd-aloop
```

### Running the Full Test

```bash
# Make script executable (first time only)
chmod +x regression_test.sh

# Run the test
./regression_test.sh
```

### Running the CI Test

```bash
# Make script executable (first time only)
chmod +x ci_regression_test.sh

# Run the test
./ci_regression_test.sh
```

## Test Scenarios

The regression tests cover the following scenarios:

1. **Driver Startup**
   - Verifies driver initializes without errors
   - Checks for proper ALSA device detection
   - Validates serial port setup

2. **Audio Stream Simulation**
   - Launches dummy `arecord` (simulating WSJT-X RX)
   - Launches dummy `aplay` (simulating WSJT-X TX)
   - Uses `*_app` ALSA loopback devices

3. **Stability Testing**
   - Monitors driver for 2+ minutes
   - Checks for crashes or hangs
   - Detects "Device unavailable" errors
   - Identifies Python tracebacks

4. **Reconnection Logic**
   - Starts and stops audio streams repeatedly
   - Verifies driver handles disconnections gracefully
   - Tests recovery from stream interruptions

## CI/CD Integration

### GitHub Actions

The repository includes a GitHub Actions workflow (`.github/workflows/regression_test.yml`) that:
- Runs on push to main/develop branches
- Runs on pull requests
- Runs nightly at 2 AM UTC
- Tests multiple Python versions (3.9-3.12)
- Publishes test results
- Creates issues on failure

### GitLab CI

Example `.gitlab-ci.yml`:

```yaml
regression_test:
  stage: test
  image: ubuntu:latest
  before_script:
    - apt-get update -qq
    - apt-get install -y -qq python3 python3-pip alsa-utils sox
    - pip3 install pyserial pyaudio
  script:
    - ./ci_regression_test.sh
  artifacts:
    when: always
    paths:
      - logs/
    reports:
      junit: logs/test_results.xml
```

### Jenkins

Example Jenkinsfile:

```groovy
pipeline {
    agent any
    stages {
        stage('Test') {
            steps {
                sh 'chmod +x ci_regression_test.sh'
                sh './ci_regression_test.sh'
            }
        }
    }
    post {
        always {
            junit 'logs/test_results.xml'
            archiveArtifacts artifacts: 'logs/*.log', allowEmptyArchive: true
        }
    }
}
```

## Test Output

### Success Output
```
=== truSDX Driver Regression Test ===
✅ ALSA Loopback card available
✅ Found trusdx_tx_app device
✅ Found trusdx_rx_app device
✅ Dummy audio streams started
✅ Driver started successfully (PID: 12345)
✅ Driver healthy for 120 seconds
✅ Driver survived stream restart cycle 1
✅ Driver survived stream restart cycle 2
...
✅ ✅ ✅ REGRESSION TEST PASSED ✅ ✅ ✅
```

### Failure Output
```
=== truSDX Driver Regression Test ===
✅ ALSA Loopback card available
✅ Dummy audio streams started
❌ Driver failed to start
❌ Found 'Device unavailable' error in driver log
❌ ❌ ❌ REGRESSION TEST FAILED ❌ ❌ ❌

Error Summary:
  • ERROR: Driver failed to start
  • ERROR: Device unavailable detected
```

## Log Files

Tests generate the following logs in the `./logs/` directory:

- `regression_test_YYYYMMDD_HHMMSS.log` - Main test execution log
- `trusdx_driver_test.log` - Driver output during test
- `test_results.xml` - JUnit XML format results (CI test only)

## Troubleshooting

### ALSA Loopback Not Found

If the test reports "ALSA Loopback card not found":

1. Load the module manually:
```bash
sudo modprobe snd-aloop
```

2. Make it persistent:
```bash
echo "snd-aloop" | sudo tee -a /etc/modules
```

3. Verify it's loaded:
```bash
lsmod | grep snd_aloop
aplay -l | grep Loopback
```

### Permission Issues

If you get permission errors:

1. Add user to audio group:
```bash
sudo usermod -a -G audio $USER
```

2. Log out and back in for changes to take effect

### Driver Fails to Start

Check the driver log for details:
```bash
tail -100 logs/trusdx_driver_test.log
```

Common issues:
- Serial port not available
- Python dependencies missing
- ALSA configuration incorrect

## Customization

### Adjusting Test Duration

Edit the test scripts to modify duration:

```bash
# In regression_test.sh or ci_regression_test.sh
TEST_DURATION=300  # 5 minutes instead of 2
STREAM_CYCLES=10   # More reconnection cycles
```

### Adding Custom Checks

Add custom error patterns to check for:

```bash
# In check_driver_health() function
if grep -q "YOUR_ERROR_PATTERN" "$DRIVER_LOG"; then
    log_message "ERROR: Custom error detected"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi
```

## Contributing

When adding new features to the driver, ensure:

1. Regression tests still pass
2. Add new test cases if needed
3. Update this README with any new test scenarios
4. Test in CI environment before merging

## License

Same as the main truSDX project.
