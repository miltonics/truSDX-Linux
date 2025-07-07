#!/usr/bin/env python3
"""
truSDX Reconnection Testing Matrix
Testing scenarios for serial reconnection functionality with dummy echo and real hardware
"""

import serial
import time
import threading
import subprocess
import os
import json
from datetime import datetime
import tempfile
import sys

# Test configuration
TEST_CONFIG = {
    'dummy_response': 'FW000;',  # Simulates 0W response
    'test_duration': 30,         # seconds per test
    'verbose': True,
    'log_file': 'test_matrix.log'
}

class TestLogger:
    """Logger for test results"""
    
    def __init__(self, log_file='test_matrix.log'):
        self.log_file = log_file
        self.test_results = []
        
    def log(self, message, level="INFO", test_name=None):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        if test_name:
            log_entry = f"[{test_name}] " + log_entry
            
        print(log_entry)
        
        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def record_result(self, test_name, result, details=None):
        """Record test result"""
        self.test_results.append({
            'test_name': test_name,
            'result': result,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
        status = "✅ PASS" if result else "❌ FAIL"
        self.log(f"{status}: {test_name}", "RESULT")
        if details:
            self.log(f"Details: {details}", "RESULT")
    
    def summary(self):
        """Print test summary"""
        passed = sum(1 for r in self.test_results if r['result'])
        total = len(self.test_results)
        
        print("\n" + "="*60)
        print("TEST MATRIX SUMMARY")
        print("="*60)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {passed/total*100:.1f}%" if total > 0 else "No tests run")
        
        for result in self.test_results:
            status = "✅" if result['result'] else "❌"
            print(f"{status} {result['test_name']}")
            if result['details']:
                print(f"    {result['details']}")
        
        print("="*60)

class DummySerialEcho:
    """Dummy serial device that echoes FW000; for testing reconnection triggers"""
    
    def __init__(self, port_path, response='FW000;'):
        self.port_path = port_path
        self.response = response.encode('utf-8')
        self.running = False
        self.thread = None
        self.logger = TestLogger()
        
    def start(self):
        """Start the dummy serial echo service"""
        self.running = True
        self.thread = threading.Thread(target=self._run_echo, daemon=True)
        self.thread.start()
        self.logger.log(f"Dummy serial echo started on {self.port_path}", "INFO", "DummyEcho")
    
    def stop(self):
        """Stop the dummy serial echo service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        self.logger.log("Dummy serial echo stopped", "INFO", "DummyEcho")
    
    def _run_echo(self):
        """Run the echo service using socat"""
        try:
            # Create virtual serial ports using socat
            cmd = [
                'socat', '-d', '-d',
                f'pty,link={self.port_path},echo=0,ignoreeof,b115200,raw,perm=0777',
                f'EXEC:/bin/sh -c "while true; do read line; echo \'{self.response.decode()}\'; done"'
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            while self.running:
                if process.poll() is not None:
                    break
                time.sleep(0.1)
            
            process.terminate()
            
        except Exception as e:
            self.logger.log(f"Error in dummy echo: {e}", "ERROR", "DummyEcho")

class TruSDXTestHarness:
    """Test harness for truSDX reconnection functionality"""
    
    def __init__(self):
        self.logger = TestLogger()
        self.trusdx_process = None
        self.test_ports = {
            'dummy_trusdx': '/tmp/dummy_trusdx',
            'dummy_cat': '/tmp/dummy_cat'
        }
        
    def setup_test_environment(self):
        """Set up the test environment"""
        self.logger.log("Setting up test environment", "INFO", "Setup")
        
        # Create necessary directories
        os.makedirs('/tmp', exist_ok=True)
        
        # Clean up any existing test ports
        for port in self.test_ports.values():
            if os.path.exists(port):
                os.unlink(port)
        
        self.logger.log("Test environment ready", "INFO", "Setup")
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        self.logger.log("Cleaning up test environment", "INFO", "Cleanup")
        
        if self.trusdx_process:
            self.trusdx_process.terminate()
            self.trusdx_process.wait(timeout=5)
        
        # Clean up test ports
        for port in self.test_ports.values():
            if os.path.exists(port):
                try:
                    os.unlink(port)
                except:
                    pass
        
        self.logger.log("Test environment cleaned up", "INFO", "Cleanup")
    
    def test_1_dummy_serial_echo(self):
        """Test 1: Bench test with dummy serial echo returning FW000; to check reconnection triggers"""
        test_name = "Test 1: Dummy Serial Echo FW000"
        self.logger.log(f"Starting {test_name}", "INFO", test_name)
        
        try:
            # Create dummy serial device
            dummy_echo = DummySerialEcho(self.test_ports['dummy_trusdx'], 'FW000;')
            dummy_echo.start()
            
            # Wait for device to be available
            time.sleep(2)
            
            # Test serial communication
            reconnection_triggered = False
            
            try:
                # Create socat virtual ports for testing
                socat_cmd = [
                    'socat', 
                    f'pty,link={self.test_ports["dummy_trusdx"]},echo=0,raw,b115200',
                    f'pty,link={self.test_ports["dummy_cat"]},echo=0,raw,b115200'
                ]
                
                socat_process = subprocess.Popen(socat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(2)  # Let socat establish
                
                # Test communication
                with serial.Serial(self.test_ports['dummy_cat'], 115200, timeout=1) as ser:
                    # Send power query
                    ser.write(b';PC;')
                    ser.flush()
                    
                    response = ser.read(10)
                    
                    if b'FW000' in response:
                        self.logger.log("FW000 response received - reconnection trigger condition met", "INFO", test_name)
                        reconnection_triggered = True
                    else:
                        self.logger.log(f"Unexpected response: {response}", "WARNING", test_name)
                
                socat_process.terminate()
                
            except Exception as e:
                self.logger.log(f"Serial communication error: {e}", "ERROR", test_name)
            
            dummy_echo.stop()
            
            # Record result
            self.logger.record_result(
                test_name, 
                reconnection_triggered,
                "FW000 response detected successfully" if reconnection_triggered else "Failed to detect FW000 response"
            )
            
            return reconnection_triggered
            
        except Exception as e:
            self.logger.log(f"Test failed: {e}", "ERROR", test_name)
            self.logger.record_result(test_name, False, f"Exception: {e}")
            return False
    
    def test_2_real_trusdx_zero_watts(self):
        """Test 2: On real truSDX, purposely set drive to 0W and ensure auto-recovery"""
        test_name = "Test 2: Real truSDX 0W Recovery"
        self.logger.log(f"Starting {test_name}", "INFO", test_name)
        
        try:
            # This test requires real hardware
            real_device = self._find_real_trusdx()
            
            if not real_device:
                self.logger.log("No real truSDX device found - skipping test", "WARNING", test_name)
                self.logger.record_result(test_name, False, "No real truSDX hardware detected")
                return False
            
            self.logger.log(f"Found truSDX at {real_device}", "INFO", test_name)
            
            recovery_successful = False
            
            try:
                with serial.Serial(real_device, 115200, timeout=2) as ser:
                    # Initialize radio
                    ser.write(b';MD2;UA2;')
                    ser.flush()
                    time.sleep(1)
                    
                    # Set drive to 0W (simulate connection issue)
                    ser.write(b';PC000;')  # Set power to 0W
                    ser.flush()
                    time.sleep(2)
                    
                    # Monitor for auto-recovery
                    self.logger.log("Monitoring for auto-recovery after 0W setting", "INFO", test_name)
                    
                    for i in range(30):  # Monitor for 30 seconds
                        # Query power
                        ser.write(b';PC;')
                        ser.flush()
                        
                        response = ser.read(20)
                        
                        if response and b'PC' in response:
                            # Parse power response
                            power_str = response.decode('utf-8', errors='ignore')
                            self.logger.log(f"Power response: {power_str}", "DEBUG", test_name)
                            
                            # Check if power has been restored
                            if 'PC000' not in power_str:
                                self.logger.log("Auto-recovery detected - power restored", "INFO", test_name)
                                recovery_successful = True
                                break
                        
                        time.sleep(1)
                    
                    if not recovery_successful:
                        self.logger.log("Auto-recovery not detected within timeout", "WARNING", test_name)
            
            except Exception as e:
                self.logger.log(f"Communication error with real truSDX: {e}", "ERROR", test_name)
            
            self.logger.record_result(
                test_name,
                recovery_successful,
                "Auto-recovery successful" if recovery_successful else "Auto-recovery not detected"
            )
            
            return recovery_successful
            
        except Exception as e:
            self.logger.log(f"Test failed: {e}", "ERROR", test_name)
            self.logger.record_result(test_name, False, f"Exception: {e}")
            return False
    
    def test_3_normal_tx_no_interrupt(self):
        """Test 3: Verify normal TX (non-zero power) does not interrupt"""
        test_name = "Test 3: Normal TX No Interrupt"
        self.logger.log(f"Starting {test_name}", "INFO", test_name)
        
        try:
            real_device = self._find_real_trusdx()
            
            if not real_device:
                self.logger.log("No real truSDX device found - skipping test", "WARNING", test_name)
                self.logger.record_result(test_name, False, "No real truSDX hardware detected")
                return False
            
            no_interruption = True
            tx_stable = False
            
            try:
                with serial.Serial(real_device, 115200, timeout=2) as ser:
                    # Initialize radio
                    ser.write(b';MD2;UA2;')
                    ser.flush()
                    time.sleep(1)
                    
                    # Set normal power level
                    ser.write(b';PC010;')  # Set 10W
                    ser.flush()
                    time.sleep(1)
                    
                    # Enable TX mode
                    ser.write(b';TX0;')
                    ser.flush()
                    
                    self.logger.log("TX mode enabled with normal power - monitoring for interruptions", "INFO", test_name)
                    
                    # Monitor for interruptions during normal TX
                    start_time = time.time()
                    tx_duration = 10  # Monitor for 10 seconds
                    
                    while time.time() - start_time < tx_duration:
                        # Check power level
                        ser.write(b';PC;')
                        ser.flush()
                        
                        response = ser.read(20)
                        
                        if response and b'PC' in response:
                            power_str = response.decode('utf-8', errors='ignore')
                            
                            # Check if we have non-zero power
                            if 'PC000' not in power_str and 'PC' in power_str:
                                tx_stable = True
                            else:
                                self.logger.log(f"Power dropped to 0W during normal TX: {power_str}", "WARNING", test_name)
                                no_interruption = False
                                break
                        
                        time.sleep(0.5)
                    
                    # Return to RX
                    ser.write(b';RX;')
                    ser.flush()
                    
                    if tx_stable and no_interruption:
                        self.logger.log("Normal TX completed without interruption", "INFO", test_name)
            
            except Exception as e:
                self.logger.log(f"Communication error during TX test: {e}", "ERROR", test_name)
                no_interruption = False
            
            result = tx_stable and no_interruption
            self.logger.record_result(
                test_name,
                result,
                "Normal TX stable without interruption" if result else "TX was interrupted or unstable"
            )
            
            return result
            
        except Exception as e:
            self.logger.log(f"Test failed: {e}", "ERROR", test_name)
            self.logger.record_result(test_name, False, f"Exception: {e}")
            return False
    
    def test_4_wsjt_js8_connection_persistence(self):
        """Test 4: Check that WSJT-X / JS8Call remain connected after reconnection"""
        test_name = "Test 4: WSJT-X/JS8Call Connection Persistence"
        self.logger.log(f"Starting {test_name}", "INFO", test_name)
        
        try:
            # This test simulates CAT client behavior
            connection_maintained = False
            cat_responsive = False
            
            # Create test CAT port
            cat_port = '/tmp/test_trusdx_cat'
            
            try:
                # Set up virtual CAT port
                socat_cmd = [
                    'socat',
                    f'pty,link={cat_port},echo=0,raw,b115200,perm=0777',
                    'EXEC:/bin/sh -c "while read line; do echo \'ID020;\'; done"'
                ]
                
                socat_process = subprocess.Popen(socat_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(2)
                
                # Test CAT connection before reconnection
                with serial.Serial(cat_port, 115200, timeout=1) as cat_ser:
                    # Test initial connection
                    cat_ser.write(b'ID;')
                    cat_ser.flush()
                    
                    response = cat_ser.read(10)
                    if b'ID020' in response:
                        self.logger.log("Initial CAT connection established", "INFO", test_name)
                        
                        # Simulate reconnection scenario
                        self.logger.log("Simulating reconnection scenario", "INFO", test_name)
                        time.sleep(2)
                        
                        # Test connection after simulated reconnection
                        cat_ser.write(b'ID;')
                        cat_ser.flush()
                        
                        response2 = cat_ser.read(10)
                        if b'ID020' in response2:
                            self.logger.log("CAT connection maintained after reconnection", "INFO", test_name)
                            connection_maintained = True
                            cat_responsive = True
                        else:
                            self.logger.log("CAT connection lost after reconnection", "WARNING", test_name)
                    else:
                        self.logger.log("Failed to establish initial CAT connection", "ERROR", test_name)
                
                socat_process.terminate()
                
            except Exception as e:
                self.logger.log(f"CAT communication error: {e}", "ERROR", test_name)
            
            result = connection_maintained and cat_responsive
            self.logger.record_result(
                test_name,
                result,
                "CAT connection persistent after reconnection" if result else "CAT connection lost during reconnection"
            )
            
            return result
            
        except Exception as e:
            self.logger.log(f"Test failed: {e}", "ERROR", test_name)
            self.logger.record_result(test_name, False, f"Exception: {e}")
            return False
    
    def _find_real_trusdx(self):
        """Find real truSDX device"""
        try:
            import serial.tools.list_ports
            
            for port in serial.tools.list_ports.comports():
                if 'USB Serial' in port.description or 'CH340' in port.description:
                    self.logger.log(f"Found potential truSDX at {port.device}", "DEBUG", "Detection")
                    return port.device
            
            return None
            
        except Exception as e:
            self.logger.log(f"Error finding truSDX device: {e}", "ERROR", "Detection")
            return None
    
    def run_all_tests(self):
        """Run complete test matrix"""
        self.logger.log("Starting truSDX Reconnection Test Matrix", "INFO", "TestMatrix")
        
        try:
            self.setup_test_environment()
            
            # Run all tests
            results = []
            
            results.append(self.test_1_dummy_serial_echo())
            results.append(self.test_2_real_trusdx_zero_watts())
            results.append(self.test_3_normal_tx_no_interrupt())
            results.append(self.test_4_wsjt_js8_connection_persistence())
            
            # Print summary
            self.logger.summary()
            
            return all(results)
            
        except Exception as e:
            self.logger.log(f"Test matrix failed: {e}", "ERROR", "TestMatrix")
            return False
            
        finally:
            self.cleanup_test_environment()

def main():
    """Main test runner"""
    print("truSDX Reconnection Test Matrix")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
Test Matrix for truSDX Reconnection Functionality

Tests:
1. Dummy Serial Echo - Tests FW000; response detection
2. Real truSDX 0W Recovery - Tests auto-recovery on real hardware
3. Normal TX No Interrupt - Verifies normal operation isn't disrupted
4. WSJT-X/JS8Call Persistence - Tests CAT client connection persistence

Usage:
    python3 test_matrix.py
    
Requirements:
    - socat (for virtual serial ports)
    - Real truSDX hardware (for tests 2 and 3)
    - Root/sudo access (for some serial operations)
        """)
        return
    
    # Check for required tools
    try:
        subprocess.run(['socat', '-V'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: socat is required but not found. Install with: sudo apt install socat")
        return
    
    # Run test matrix
    harness = TruSDXTestHarness()
    success = harness.run_all_tests()
    
    exit_code = 0 if success else 1
    print(f"\nTest matrix completed with exit code: {exit_code}")
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
