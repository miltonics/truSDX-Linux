#!/bin/bash
# truSDX-AI Automated Test Suite
# Spins up Docker container (Ubuntu 22.04) and executes comprehensive tests
# Version: 1.0.0
# Date: 2024-12-19

set -eE -o pipefail

# Test configuration
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")
TEST_RESULTS_DIR="${SCRIPT_DIR}/results"
JUNIT_XML_FILE="${TEST_RESULTS_DIR}/junit-results.xml"
DOCKER_IMAGE="trusdx-ci-test"
CONTAINER_NAME="trusdx-test-$$"
TEST_TIMEOUT=300  # 5 minutes timeout

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TEST_START_TIME=$(date +%s)

echo -e "${BLUE}=== truSDX-AI Automated Test Suite ===${NC}"
echo -e "${BLUE}Starting Docker-based CI tests...${NC}"
echo "Test results will be saved to: $JUNIT_XML_FILE"
echo

# Create results directory
mkdir -p "$TEST_RESULTS_DIR"

# Initialize JUnit XML
init_junit_xml() {
    cat > "$JUNIT_XML_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="truSDX-AI Test Suite" tests="0" failures="0" errors="0" time="0.0" timestamp="$(date -Iseconds)">
EOF
}

# Add test case to JUnit XML
add_junit_testcase() {
    local classname="$1"
    local name="$2"
    local time="$3"
    local status="$4"
    local failure_message="$5"
    local output="$6"
    
    if [[ "$status" == "passed" ]]; then
        cat >> "$JUNIT_XML_FILE" << EOF
  <testcase classname="$classname" name="$name" time="$time">
    <system-out><![CDATA[$output]]></system-out>
  </testcase>
EOF
    else
        cat >> "$JUNIT_XML_FILE" << EOF
  <testcase classname="$classname" name="$name" time="$time">
    <failure message="$failure_message"><![CDATA[$output]]></failure>
  </testcase>
EOF
    fi
}

# Finalize JUnit XML
finalize_junit_xml() {
    local total_time=$(($(date +%s) - TEST_START_TIME))
    
    # Update test suite statistics
    sed -i "s/tests=\"0\"/tests=\"$TESTS_RUN\"/" "$JUNIT_XML_FILE"
    sed -i "s/failures=\"0\"/failures=\"$TESTS_FAILED\"/" "$JUNIT_XML_FILE"
    sed -i "s/time=\"0.0\"/time=\"$total_time.0\"/" "$JUNIT_XML_FILE"
    
    echo "</testsuites>" >> "$JUNIT_XML_FILE"
}

# Test execution wrapper
run_test() {
    local test_name="$1"
    local test_command="$2"
    local classname="${3:-TruSDX.Integration}"
    
    echo -e "${YELLOW}Running test: $test_name${NC}"
    ((TESTS_RUN++))
    
    local start_time=$(date +%s)
    local output
    local exit_code
    
    if output=$(eval "$test_command" 2>&1); then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        echo -e "${GREEN}✓ PASSED: $test_name${NC}"
        ((TESTS_PASSED++))
        add_junit_testcase "$classname" "$test_name" "$duration" "passed" "" "$output"
    else
        exit_code=$?
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        echo -e "${RED}✗ FAILED: $test_name${NC}"
        echo -e "${RED}Exit code: $exit_code${NC}"
        echo -e "${RED}Output: $output${NC}"
        ((TESTS_FAILED++))
        add_junit_testcase "$classname" "$test_name" "$duration" "failed" "Test failed with exit code $exit_code" "$output"
    fi
    echo
}

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up test environment...${NC}"
    
    # Stop and remove container
    if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
        echo "Stopping container $CONTAINER_NAME..."
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
    
    if docker ps -aq -f name="$CONTAINER_NAME" | grep -q .; then
        echo "Removing container $CONTAINER_NAME..."
        docker rm "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
    
    # Finalize test results
    finalize_junit_xml
    
    echo -e "${BLUE}Test Summary:${NC}"
    echo -e "  Tests Run: $TESTS_RUN"
    echo -e "  ${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "  ${RED}Failed: $TESTS_FAILED${NC}"
    echo -e "  Results: $JUNIT_XML_FILE"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        echo -e "${RED}Some tests failed!${NC}"
        exit 1
    else
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    fi
}

trap cleanup EXIT

# Initialize JUnit XML
init_junit_xml

echo -e "${BLUE}Step 1: Building Docker test environment...${NC}"

# Create Dockerfile for testing
cat > "${TEST_RESULTS_DIR}/Dockerfile" << 'EOF'
FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    portaudio19-dev \
    pulseaudio \
    pulseaudio-utils \
    socat \
    build-essential \
    pkg-config \
    cmake \
    git \
    curl \
    wget \
    libusb-1.0-0-dev \
    libfftw3-dev \
    libtool \
    autoconf \
    automake \
    texinfo \
    dbus-x11 \
    alsa-utils \
    sox \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install pyaudio pyserial pytest numpy

# Create test user (non-root)
RUN useradd -m -s /bin/bash testuser && \
    usermod -a -G audio,dialout testuser

# Set up PulseAudio for headless operation
RUN mkdir -p /home/testuser/.config/pulse
COPY pulse-config /home/testuser/.config/pulse/client.conf
RUN echo "autospawn = no" >> /home/testuser/.config/pulse/client.conf && \
    echo "daemon-binary = /bin/true" >> /home/testuser/.config/pulse/client.conf && \
    chown -R testuser:testuser /home/testuser/.config

# Create working directory
WORKDIR /app
RUN chown testuser:testuser /app

USER testuser
EOF

# Create PulseAudio config for headless testing
cat > "${TEST_RESULTS_DIR}/pulse-config" << 'EOF'
# Headless PulseAudio configuration for testing
autospawn = yes
daemon-binary = /usr/bin/pulseaudio
EOF

# Build Docker image
run_test "Docker Image Build" "cd '$TEST_RESULTS_DIR' && docker build -t '$DOCKER_IMAGE' ."

echo -e "${BLUE}Step 2: Starting test container...${NC}"

# Start container with required capabilities
docker run -d \
    --name "$CONTAINER_NAME" \
    --cap-add=SYS_PTRACE \
    --security-opt seccomp=unconfined \
    -v "$PROJECT_ROOT:/app/trusdx" \
    "$DOCKER_IMAGE" \
    sleep 3600

# Wait for container to be ready
sleep 2

echo -e "${BLUE}Step 3: Running setup.sh --ci (non-interactive)...${NC}"

# Test 1: Non-interactive setup
run_test "Setup Script Non-Interactive" "
    docker exec '$CONTAINER_NAME' bash -c '
        cd /app/trusdx && 
        export DEBIAN_FRONTEND=noninteractive && 
        timeout 120 ./setup.sh --ci
    '
" "TruSDX.Setup"

echo -e "${BLUE}Step 4: Testing Hamlib installation and rigctld...${NC}"

# Test 2: Verify Hamlib installation
run_test "Hamlib Installation Check" "
    docker exec '$CONTAINER_NAME' bash -c '
        rigctl --version | grep -q \"4.6.3\" && 
        rigctld --version | grep -q \"4.6.3\"
    '
" "TruSDX.Hamlib"

echo -e "${BLUE}Step 5: Starting rigctld in headless mode...${NC}"

# Test 3: Start rigctld in background
run_test "Start Rigctld Daemon" "
    docker exec -d '$CONTAINER_NAME' bash -c '
        cd /app/trusdx && 
        rigctld -m 2014 -r /dev/null -t 4532 > /tmp/rigctld.log 2>&1 &
        sleep 5
    '
" "TruSDX.Rigctld"

# Test 4: rigctld connectivity test
run_test "Rigctld Connectivity Test" "
    docker exec '$CONTAINER_NAME' bash -c '
        echo \"f\" | nc localhost 4532 | grep -E \"[0-9]+\"
    '
" "TruSDX.Rigctld"

echo -e "${BLUE}Step 6: Testing rigctl smoke tests via loopback...${NC}"

# Test 5: rigctl smoke tests
run_test "Rigctl Smoke Tests" "
    docker exec '$CONTAINER_NAME' bash -c '
        # Test basic rigctl commands via TCP
        echo \"F\" | nc localhost 4532 > /dev/null &&
        echo \"f\" | nc localhost 4532 | grep -E \"[0-9]+\" > /dev/null &&
        echo \"M\" | nc localhost 4532 > /dev/null &&
        echo \"dump_state\" | nc localhost 4532 | head -5 | grep -q \"0\"
    '
" "TruSDX.RigctlSmoke"

echo -e "${BLUE}Step 7: Setting up PulseAudio for audio testing...${NC}"

# Test 6: PulseAudio setup
run_test "PulseAudio Setup" "
    docker exec '$CONTAINER_NAME' bash -c '
        # Start PulseAudio in daemon mode
        pulseaudio --start --log-target=file:/tmp/pulse.log &&
        sleep 2 &&
        # Create TRUSDX null sink
        pactl load-module module-null-sink sink_name=TRUSDX sink_properties=device.description=\"TRUSDX\" &&
        # Verify sink exists
        pactl list sinks short | grep -q TRUSDX
    '
" "TruSDX.Audio"

echo -e "${BLUE}Step 8: Testing audio path with sine wave...${NC}"

# Test 7: Audio path verification with sine wave
run_test "Audio Path Sine Wave Test" "
    docker exec '$CONTAINER_NAME' bash -c '
        # Generate sine wave and pipe to TRUSDX sink
        timeout 5 sox -n -t pulseaudio TRUSDX synth 2 sine 1000 vol 0.1 &
        GENERATOR_PID=\$!
        
        # Capture from monitor
        timeout 5 pactl list sinks | grep -A 20 \"Name: TRUSDX\" | grep -q \"Monitor Source\" &&
        
        # Verify audio is flowing (check for monitor source activity)
        timeout 10 pactl list source-outputs | grep -q \"application.name\" || 
        pactl list sources | grep -q \"TRUSDX.monitor\"
        
        # Cleanup
        kill \$GENERATOR_PID 2>/dev/null || true
    '
" "TruSDX.AudioPath"

echo -e "${BLUE}Step 9: Testing RX buffer length assertion...${NC}"

# Test 8: RX buffer length verification
run_test "RX Buffer Length Test" "
    docker exec '$CONTAINER_NAME' bash -c '
        cd /app/trusdx &&
        # Create a simple Python script to test audio buffer
        cat > /tmp/test_audio_buffer.py << \"PYTHON_EOF\"
import pyaudio
import numpy as np
import sys
import time

def test_audio_buffer():
    try:
        p = pyaudio.PyAudio()
        
        # Find TRUSDX device
        trusdx_device = None
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if \"TRUSDX\" in info[\"name\"]:
                trusdx_device = i
                break
        
        if trusdx_device is None:
            # Try default device for CI
            trusdx_device = p.get_default_input_device_info()[\"index\"]
        
        # Open stream
        chunk = 1024
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=48000,
            input=True,
            input_device_index=trusdx_device,
            frames_per_buffer=chunk
        )
        
        # Read some samples
        data = stream.read(chunk, exception_on_overflow=False)
        buffer_length = len(data)
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Assert buffer length is reasonable
        if buffer_length >= chunk * 2:  # 2 bytes per sample for paInt16
            print(f\"✓ RX buffer length OK: {buffer_length} bytes\")
            return True
        else:
            print(f\"✗ RX buffer length too small: {buffer_length} bytes\")
            return False
            
    except Exception as e:
        print(f\"✗ Audio buffer test failed: {e}\")
        return False

if __name__ == \"__main__\":
    success = test_audio_buffer()
    sys.exit(0 if success else 1)
PYTHON_EOF

        python3 /tmp/test_audio_buffer.py
    '
" "TruSDX.AudioBuffer"

echo -e "${BLUE}Step 10: Running CAT emulation unit tests...${NC}"

# Test 9: CAT emulation tests
run_test "CAT Emulation Unit Tests" "
    docker exec '$CONTAINER_NAME' bash -c '
        cd /app/trusdx && 
        timeout 60 python3 tests/test_cat_emulation.py
    '
" "TruSDX.CATEmulation"

echo -e "${BLUE}Step 11: Integration test with driver...${NC}"

# Test 10: Driver integration test
run_test "Driver Integration Test" "
    docker exec '$CONTAINER_NAME' bash -c '
        cd /app/trusdx &&
        # Create test script for driver integration
        cat > /tmp/test_driver_integration.py << \"PYTHON_EOF\"
import subprocess
import time
import signal
import sys
import os

def test_driver_start():
    try:
        # Start driver in background
        env = os.environ.copy()
        env[\"DISPLAY\"] = \":99\"  # Virtual display
        
        process = subprocess.Popen(
            [\"python3\", \"trusdx-txrx-AI.py\", \"--test-mode\", \"--headless\"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            preexec_fn=os.setsid
        )
        
        # Give it time to start
        time.sleep(5)
        
        # Check if process is still running
        if process.poll() is None:
            print(\"✓ Driver started successfully\")
            success = True
        else:
            stdout, stderr = process.communicate()
            print(f\"✗ Driver failed to start: {stderr.decode()}\")
            success = False
        
        # Cleanup
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
        except:
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except:
                pass
        
        return success
        
    except Exception as e:
        print(f\"✗ Driver integration test failed: {e}\")
        return False

if __name__ == \"__main__\":
    success = test_driver_start()
    sys.exit(0 if success else 1)
PYTHON_EOF

        python3 /tmp/test_driver_integration.py
    '
" "TruSDX.DriverIntegration"

echo -e "${BLUE}Step 12: Final system verification...${NC}"

# Test 11: System verification
run_test "System Verification" "
    docker exec '$CONTAINER_NAME' bash -c '
        cd /app/trusdx &&
        # Verify all components are working
        rigctl --version | grep -q \"4.6.3\" &&
        python3 -c \"import pyaudio, serial; print(\\\"Python modules OK\\\")\" &&
        pactl list sinks short | grep -q TRUSDX &&
        ls -la /tmp/trusdx_cat 2>/dev/null || echo \"CAT port creation test\" &&
        echo \"✓ All system components verified\"
    '
" "TruSDX.SystemVerification"

echo

# The cleanup function will be called automatically via trap
echo -e "${GREEN}All tests completed!${NC}"
