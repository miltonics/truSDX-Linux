#!/bin/bash
# ci_regression_test.sh - CI-friendly regression test for truSDX driver
# Designed for GitHub Actions, GitLab CI, Jenkins, etc.

set -e

# CI Environment Detection
CI_MODE=${CI:-false}
GITHUB_ACTIONS=${GITHUB_ACTIONS:-false}
GITLAB_CI=${GITLAB_CI:-false}

# Test configuration
TEST_DURATION=120  # 2 minutes
STREAM_CYCLES=3    # Reduced for CI (faster)
CYCLE_DURATION=5   # Shorter cycles for CI
LOG_DIR="./logs"
TEST_LOG="$LOG_DIR/ci_regression_test.log"
DRIVER_LOG="$LOG_DIR/ci_driver_test.log"
JUNIT_OUTPUT="$LOG_DIR/test_results.xml"

# Exit codes
EXIT_SUCCESS=0
EXIT_FAILURE=1
EXIT_SKIP=77  # Standard skip code

# Test results
TEST_PASSED=true
ERROR_COUNT=0
SUCCESS_COUNT=0
TEST_START_TIME=$(date +%s)

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$TEST_LOG"
}

# Function to check dependencies
check_dependencies() {
    local missing_deps=""
    
    # Check for required commands
    for cmd in python3 aplay arecord sox; do
        if ! command -v "$cmd" &> /dev/null; then
            missing_deps="$missing_deps $cmd"
        fi
    done
    
    if [ -n "$missing_deps" ]; then
        log_message "ERROR: Missing dependencies:$missing_deps"
        
        # Try to install missing dependencies in CI
        if [ "$CI_MODE" = "true" ] || [ "$GITHUB_ACTIONS" = "true" ]; then
            log_message "Attempting to install missing dependencies..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update -qq
                sudo apt-get install -y -qq python3 alsa-utils sox
            elif command -v yum &> /dev/null; then
                sudo yum install -y python3 alsa-utils sox
            fi
        else
            return 1
        fi
    fi
    
    # Check for Python modules
    if ! python3 -c "import serial" 2>/dev/null; then
        log_message "Installing pyserial..."
        pip3 install --quiet pyserial
    fi
    
    if ! python3 -c "import pyaudio" 2>/dev/null; then
        log_message "Installing pyaudio..."
        if [ "$CI_MODE" = "true" ] || [ "$GITHUB_ACTIONS" = "true" ]; then
            sudo apt-get install -y -qq portaudio19-dev
        fi
        pip3 install --quiet pyaudio
    fi
    
    return 0
}

# Function to setup ALSA loopback in CI
setup_alsa_ci() {
    log_message "Setting up ALSA loopback for CI..."
    
    # Load snd-aloop module
    if ! lsmod | grep -q snd_aloop; then
        log_message "Loading snd-aloop module..."
        sudo modprobe snd-aloop || {
            log_message "WARNING: Could not load snd-aloop, tests may fail"
            
            # In GitHub Actions, we might be in a container
            if [ "$GITHUB_ACTIONS" = "true" ]; then
                log_message "GitHub Actions detected - using dummy audio"
                export AUDIODEV=null
                return 0
            fi
        }
    fi
    
    # Verify loopback device
    if aplay -l 2>/dev/null | grep -q "Loopback"; then
        log_message "ALSA Loopback device available"
        return 0
    else
        log_message "WARNING: ALSA Loopback not available, using fallback"
        return 1
    fi
}

# Function to generate JUnit XML output
generate_junit_xml() {
    local test_time=$(($(date +%s) - TEST_START_TIME))
    local test_status="passed"
    local failure_message=""
    
    if [ "$TEST_PASSED" != "true" ] || [ $ERROR_COUNT -gt 0 ]; then
        test_status="failed"
        failure_message="<failure message=\"Test failed with $ERROR_COUNT errors\">
$(grep "ERROR:" "$TEST_LOG" | head -20)
</failure>"
    fi
    
    cat > "$JUNIT_OUTPUT" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="truSDX Regression Tests" tests="1" failures="$([[ $test_status == "failed" ]] && echo 1 || echo 0)" time="$test_time">
  <testsuite name="Audio Driver Regression" tests="1" failures="$([[ $test_status == "failed" ]] && echo 1 || echo 0)" time="$test_time">
    <testcase name="WSJT-X Simulation Test" classname="regression.audio" time="$test_time">
      $failure_message
      <system-out>
        Success Count: $SUCCESS_COUNT
        Error Count: $ERROR_COUNT
        Test Duration: ${test_time}s
      </system-out>
    </testcase>
  </testsuite>
</testsuites>
EOF
    
    log_message "JUnit XML report generated: $JUNIT_OUTPUT"
}

# Function to run minimal audio test
run_audio_test() {
    local driver_pid=""
    local aplay_pid=""
    local arecord_pid=""
    
    log_message "Starting minimal audio test..."
    
    # Generate test audio
    sox -n -r 48000 -c 1 -b 16 /tmp/ci_test.wav synth 10 sine 1000 gain -20 2>/dev/null || {
        log_message "WARNING: Could not generate test audio"
    }
    
    # Start driver
    if [ -f "./trusdx-txrx-AI.py" ]; then
        log_message "Starting driver..."
        timeout 60 python3 ./trusdx-txrx-AI.py > "$DRIVER_LOG" 2>&1 &
        driver_pid=$!
        sleep 5
        
        # Check if driver started
        if ! kill -0 "$driver_pid" 2>/dev/null; then
            log_message "ERROR: Driver failed to start"
            ERROR_COUNT=$((ERROR_COUNT + 1))
            
            # Show driver log
            if [ -f "$DRIVER_LOG" ]; then
                log_message "Driver log tail:"
                tail -20 "$DRIVER_LOG" | while read line; do
                    log_message "  $line"
                done
            fi
            
            return 1
        fi
        
        log_message "Driver started (PID: $driver_pid)"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        
        # Try to start dummy audio streams
        if [ -f /tmp/ci_test.wav ]; then
            # Use hw:Loopback if available, otherwise use null device
            if aplay -l 2>/dev/null | grep -q "Loopback"; then
                aplay -D hw:Loopback,1,0 -r 48000 /tmp/ci_test.wav 2>/dev/null &
                aplay_pid=$!
                arecord -D hw:Loopback,1,1 -r 48000 -d 10 /dev/null 2>/dev/null &
                arecord_pid=$!
            else
                # Fallback for CI environments without audio
                log_message "Using null audio devices"
            fi
        fi
        
        # Monitor driver for 30 seconds
        log_message "Monitoring driver stability..."
        local monitor_start=$(date +%s)
        local monitor_duration=30
        
        while [ $(($(date +%s) - monitor_start)) -lt $monitor_duration ]; do
            if ! kill -0 "$driver_pid" 2>/dev/null; then
                log_message "ERROR: Driver crashed during monitoring"
                ERROR_COUNT=$((ERROR_COUNT + 1))
                TEST_PASSED=false
                break
            fi
            
            # Check for critical errors
            if [ -f "$DRIVER_LOG" ]; then
                if grep -q "Device unavailable" "$DRIVER_LOG"; then
                    log_message "ERROR: 'Device unavailable' detected"
                    ERROR_COUNT=$((ERROR_COUNT + 1))
                    TEST_PASSED=false
                fi
                
                if grep -q "Traceback" "$DRIVER_LOG"; then
                    log_message "ERROR: Python traceback detected"
                    ERROR_COUNT=$((ERROR_COUNT + 1))
                    TEST_PASSED=false
                    
                    # Show traceback
                    grep -A 5 "Traceback" "$DRIVER_LOG" | tail -10 | while read line; do
                        log_message "  $line"
                    done
                fi
            fi
            
            sleep 2
        done
        
        if [ "$TEST_PASSED" = "true" ]; then
            log_message "Driver remained stable for $monitor_duration seconds"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        fi
        
        # Cleanup
        [ -n "$aplay_pid" ] && kill "$aplay_pid" 2>/dev/null
        [ -n "$arecord_pid" ] && kill "$arecord_pid" 2>/dev/null
        [ -n "$driver_pid" ] && kill "$driver_pid" 2>/dev/null
        
    else
        log_message "ERROR: Driver script not found"
        ERROR_COUNT=$((ERROR_COUNT + 1))
        return 1
    fi
    
    return 0
}

# Function to output CI-specific markers
output_ci_markers() {
    if [ "$GITHUB_ACTIONS" = "true" ]; then
        # GitHub Actions annotations
        if [ $ERROR_COUNT -gt 0 ]; then
            echo "::error::Regression test failed with $ERROR_COUNT errors"
        else
            echo "::notice::Regression test passed successfully"
        fi
    fi
    
    if [ "$GITLAB_CI" = "true" ]; then
        # GitLab CI markers
        if [ $ERROR_COUNT -gt 0 ]; then
            echo "REGRESSION_TEST=FAILED" >> ci_variables.env
        else
            echo "REGRESSION_TEST=PASSED" >> ci_variables.env
        fi
    fi
}

# Main CI test execution
main() {
    # Setup
    mkdir -p "$LOG_DIR"
    echo "=== CI Regression Test Log ===" > "$TEST_LOG"
    log_message "Starting CI regression test"
    log_message "CI Environment: CI=$CI, GITHUB_ACTIONS=$GITHUB_ACTIONS, GITLAB_CI=$GITLAB_CI"
    
    # Check dependencies
    log_message "Checking dependencies..."
    if ! check_dependencies; then
        log_message "ERROR: Missing required dependencies"
        if [ "$CI_MODE" = "true" ]; then
            # Skip test in CI if dependencies cannot be installed
            log_message "Skipping test due to missing dependencies"
            exit $EXIT_SKIP
        else
            exit $EXIT_FAILURE
        fi
    fi
    
    # Setup ALSA
    log_message "Setting up audio system..."
    setup_alsa_ci
    
    # Run test
    log_message "Running audio driver test..."
    run_audio_test
    
    # Generate reports
    log_message "Generating test reports..."
    generate_junit_xml
    
    # Output results
    log_message ""
    log_message "========================================="
    log_message "TEST RESULTS:"
    log_message "  Successful checks: $SUCCESS_COUNT"
    log_message "  Errors found: $ERROR_COUNT"
    log_message "  Test status: $([[ $TEST_PASSED == "true" ]] && echo "PASSED" || echo "FAILED")"
    log_message "========================================="
    
    # CI-specific output
    output_ci_markers
    
    # Set exit code
    if [ "$TEST_PASSED" = "true" ] && [ $ERROR_COUNT -eq 0 ]; then
        log_message "✅ CI REGRESSION TEST PASSED"
        exit $EXIT_SUCCESS
    else
        log_message "❌ CI REGRESSION TEST FAILED"
        
        # Output error summary
        if [ -f "$TEST_LOG" ]; then
            echo ""
            echo "Error Summary:"
            grep "ERROR:" "$TEST_LOG" | head -10
        fi
        
        exit $EXIT_FAILURE
    fi
}

# Run the test
main
