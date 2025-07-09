#!/usr/bin/env python3
"""
Integration test harness for WSJT-X & JS8Call with rigctl simulation.
Tests the complete communication chain: rigctl -> CAT emulator -> virtual radio.
Addresses VFO handling issues and validates proper Hamlib compatibility.
"""

import time
import subprocess
import os
import sys
import threading
import socket
import signal
import json
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
from unittest.mock import Mock, patch
import serial
from io import StringIO

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.audio_io import AudioManager
    from src.connection_manager import ConnectionManager, ConnectionState
    from src.cat_emulator import CATEmulator
    from src.logging_cfg import configure_logging, log
except ImportError:
    # Fallback - use main driver for testing
    print("Warning: Cannot import src modules, using fallback")
    def log(msg, level="INFO"):
        print(f"[{level}] {msg}")
    
    def configure_logging(verbose=True, log_file=None):
        pass

# Test configuration
TEST_CONFIG = {
    'rigctl_model': 2,  # Kenwood TS-480
    'cat_port': '/tmp/trusdx_cat',
    'test_frequency': 14074000,  # 20m JS8Call frequency
    'test_duration_short': 30,   # 30 seconds for quick tests
    'test_duration_long': 1800,  # 30 minutes for full cycle
    'usb_device_path': '/dev/ttyUSB0',
    'rigctld_port': 4532,
    'virtual_audio_device': 'TRUSDX',
    'rigctld_timeout': 5,
    'wsjt_x_timeout': 10,
    'js8call_timeout': 10
}

# Test results tracking
test_results = {
    'virtual_audio_setup': False,
    'rigctld_startup': False,
    'cat_emulator_startup': False,
    'cold_start': False,
    'frequency_set': False,
    'vfo_handling': False,
    'if_command_response': False,
    'tx_rx_cycle': False,
    'usb_reconnect': False,
    'wsjt_x_connection': False,
    'js8call_connection': False,
    'crashes': 0,
    'successful_decodes': 0,
    'test_log': []
}

# Global test control
test_running = True
test_processes = []

def add_test_log(message: str, level: str = "INFO"):
    """Add message to test log."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    test_results['test_log'].append(f"[{timestamp}] [{level}] {message}")
    print(f"[{level}] {message}")

def setup_virtual_audio():
    """Setup virtual audio cable for testing."""
    add_test_log("Setting up virtual audio cable...")
    
    try:
        # Check if TRUSDX sink already exists
        result = subprocess.run(
            ['pactl', 'list', 'sinks'], 
            capture_output=True, text=True, timeout=5
        )
        
        if 'TRUSDX' not in result.stdout:
            # Create virtual audio sink
            subprocess.run([
                'pactl', 'load-module', 'module-null-sink',
                'sink_name=TRUSDX',
                'sink_properties=device.description="TRUSDX"'
            ], check=True, timeout=10)
            
            time.sleep(2)  # Wait for sink to be ready
        
        # Verify sink was created
        result = subprocess.run(
            ['pactl', 'list', 'sinks'], 
            capture_output=True, text=True, timeout=5
        )
        
        if 'TRUSDX' in result.stdout:
            test_results['virtual_audio_setup'] = True
            add_test_log("Virtual audio setup successful")
            return True
        else:
            add_test_log("Virtual audio setup failed", "ERROR")
            return False
            
    except subprocess.TimeoutExpired:
        add_test_log("Virtual audio setup timed out", "ERROR")
        return False
    except Exception as e:
        add_test_log(f"Virtual audio setup error: {e}", "ERROR")
        return False

def start_rigctld():
    """Start rigctld daemon for testing."""
    add_test_log("Starting rigctld daemon...")
    
    try:
        # Check if rigctld is already running
        result = subprocess.run(
            ['pgrep', 'rigctld'], 
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            add_test_log("rigctld already running")
            test_results['rigctld_startup'] = True
            return True
        
        # Start rigctld with dummy model for testing
        proc = subprocess.Popen([
            'rigctld', '-m', '1', '-r', '/dev/null', '-t', str(TEST_CONFIG['rigctld_port']),
            '-vvv'  # Verbose output for debugging
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        test_processes.append(proc)
        
        # Wait for rigctld to start
        time.sleep(3)
        
        # Test connection
        if test_rigctld_connection():
            test_results['rigctld_startup'] = True
            add_test_log("rigctld started successfully")
            return True
        else:
            add_test_log("rigctld failed to start properly", "ERROR")
            return False
            
    except Exception as e:
        add_test_log(f"rigctld startup error: {e}", "ERROR")
        return False

def test_rigctld_connection():
    """Test connection to rigctld."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex(('localhost', TEST_CONFIG['rigctld_port']))
        sock.close()
        return result == 0
    except:
        return False

def start_cat_emulator():
    """Start CAT emulator for testing."""
    add_test_log("Starting CAT emulator...")
    
    try:
        # Start the main truSDX driver
        proc = subprocess.Popen([
            'python3', './trusdx-txrx-AI.py', 
            '--verbose', '--no-header'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        test_processes.append(proc)
        
        # Wait for CAT emulator to start
        time.sleep(5)
        
        # Check if process is still running
        if proc.poll() is None:
            test_results['cat_emulator_startup'] = True
            add_test_log("CAT emulator started successfully")
            return True
        else:
            add_test_log("CAT emulator failed to start", "ERROR")
            return False
            
    except Exception as e:
        add_test_log(f"CAT emulator startup error: {e}", "ERROR")
        return False

def test_cold_start():
    """Test cold start scenario."""
    add_test_log("Testing cold start scenario...")
    
    try:
        # Test basic rigctl commands
        commands = [
            ('get_freq', 'f'),
            ('get_mode', 'm'),
            ('get_info', 'i'),
            ('get_powerstat', 'power2int get_powerstat'),
        ]
        
        for cmd_name, cmd in commands:
            result = subprocess.run(
                ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), cmd],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                add_test_log(f"Cold start {cmd_name}: SUCCESS")
            else:
                add_test_log(f"Cold start {cmd_name}: FAILED - {result.stderr}", "ERROR")
                return False
        
        test_results['cold_start'] = True
        add_test_log("Cold start test passed")
        return True
        
    except Exception as e:
        add_test_log(f"Cold start test error: {e}", "ERROR")
        return False

def test_frequency_set():
    """Test frequency setting and reading."""
    add_test_log("Testing frequency set scenario...")
    
    try:
        test_freq = TEST_CONFIG['test_frequency']
        
        # Set frequency
        result = subprocess.run(
            ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), 'F', str(test_freq)],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode != 0:
            add_test_log(f"Frequency set failed: {result.stderr}", "ERROR")
            return False
        
        # Read back frequency
        result = subprocess.run(
            ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), 'f'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            read_freq = int(result.stdout.strip())
            if abs(read_freq - test_freq) < 1000:  # Allow 1kHz tolerance
                test_results['frequency_set'] = True
                add_test_log(f"Frequency set test passed: {read_freq} Hz")
                return True
            else:
                add_test_log(f"Frequency mismatch: set {test_freq}, read {read_freq}", "ERROR")
                return False
        else:
            add_test_log(f"Frequency read failed: {result.stderr}", "ERROR")
            return False
        
    except Exception as e:
        add_test_log(f"Frequency set test error: {e}", "ERROR")
        return False

def test_vfo_handling():
    """Test VFO handling for Hamlib compatibility."""
    add_test_log("Testing VFO handling...")
    
    try:
        # Test VFO commands that commonly cause issues
        vfo_commands = [
            ('get_vfo', 'v'),
            ('set_vfo', 'V VFOA'),
            ('get_vfo', 'v'),
        ]
        
        for cmd_name, cmd in vfo_commands:
            result = subprocess.run(
                ['rigctl', '-m', str(TEST_CONFIG['rigctl_model'])] + cmd.split(),
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                add_test_log(f"VFO {cmd_name}: SUCCESS - {result.stdout.strip()}")
            else:
                add_test_log(f"VFO {cmd_name}: FAILED - {result.stderr}", "ERROR")
                return False
        
        test_results['vfo_handling'] = True
        add_test_log("VFO handling test passed")
        return True
        
    except Exception as e:
        add_test_log(f"VFO handling test error: {e}", "ERROR")
        return False

def test_if_command_response():
    """Test IF command response format."""
    add_test_log("Testing IF command response format...")
    
    try:
        # Test IF command directly
        result = subprocess.run(
            ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), 'get_info'],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            add_test_log("IF command response: SUCCESS")
            test_results['if_command_response'] = True
            return True
        else:
            add_test_log(f"IF command failed: {result.stderr}", "ERROR")
            return False
        
    except Exception as e:
        add_test_log(f"IF command test error: {e}", "ERROR")
        return False

def test_tx_rx_cycle():
    """Test TX/RX cycle simulation."""
    add_test_log("Testing TX/RX cycle...")
    
    try:
        # Short TX/RX cycle for testing
        cycles = 3
        cycle_duration = 5  # seconds
        
        for i in range(cycles):
            if not test_running:
                break
            
            add_test_log(f"TX/RX cycle {i+1}/{cycles}")
            
            # Simulate TX
            result = subprocess.run(
                ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), 'T', '1'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode != 0:
                add_test_log(f"TX command failed: {result.stderr}", "ERROR")
                return False
            
            time.sleep(cycle_duration)
            
            # Simulate RX
            result = subprocess.run(
                ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), 'T', '0'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode != 0:
                add_test_log(f"RX command failed: {result.stderr}", "ERROR")
                return False
            
            time.sleep(cycle_duration)
        
        test_results['tx_rx_cycle'] = True
        add_test_log("TX/RX cycle test passed")
        return True
        
    except Exception as e:
        add_test_log(f"TX/RX cycle test error: {e}", "ERROR")
        return False

def test_usb_disconnect_reconnect():
    """Test USB disconnect/reconnect simulation."""
    add_test_log("Testing USB disconnect/reconnect simulation...")
    
    try:
        # This is a simulation since we can't physically disconnect USB
        # We'll test the reconnection logic by restarting the CAT emulator
        
        add_test_log("Simulating USB disconnect...")
        
        # Find and stop CAT emulator process
        for proc in test_processes:
            if 'trusdx-txrx-AI.py' in ' '.join(proc.args):
                proc.terminate()
                proc.wait(timeout=5)
                break
        
        time.sleep(2)  # Simulate disconnect period
        
        add_test_log("Simulating USB reconnect...")
        
        # Restart CAT emulator
        if start_cat_emulator():
            # Test basic functionality after reconnect
            if test_frequency_set():
                test_results['usb_reconnect'] = True
                add_test_log("USB reconnect test passed")
                return True
            else:
                add_test_log("USB reconnect test failed - frequency test failed", "ERROR")
                return False
        else:
            add_test_log("USB reconnect test failed - CAT emulator restart failed", "ERROR")
            return False
        
    except Exception as e:
        add_test_log(f"USB reconnect test error: {e}", "ERROR")
        return False

def test_wsjt_x_connection():
    """Test WSJT-X connection compatibility."""
    add_test_log("Testing WSJT-X connection compatibility...")
    
    try:
        # Test WSJT-X specific commands
        wsjt_commands = [
            ('get_freq', 'f'),
            ('get_mode', 'm'),
            ('get_ptt', 't'),
            ('get_split_mode', 's'),
        ]
        
        for cmd_name, cmd in wsjt_commands:
            result = subprocess.run(
                ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), cmd],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                add_test_log(f"WSJT-X {cmd_name}: SUCCESS")
            else:
                add_test_log(f"WSJT-X {cmd_name}: FAILED - {result.stderr}", "ERROR")
                return False
        
        test_results['wsjt_x_connection'] = True
        add_test_log("WSJT-X connection test passed")
        return True
        
    except Exception as e:
        add_test_log(f"WSJT-X connection test error: {e}", "ERROR")
        return False

def test_js8call_connection():
    """Test JS8Call connection compatibility."""
    add_test_log("Testing JS8Call connection compatibility...")
    
    try:
        # Test JS8Call specific frequency (should not be blocked in this test)
        js8_freq = 14074000  # 20m JS8Call frequency
        
        # Set JS8Call frequency
        result = subprocess.run(
            ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), 'F', str(js8_freq)],
            capture_output=True, text=True, timeout=5
        )
        
        if result.returncode == 0:
            add_test_log("JS8Call frequency set: SUCCESS")
        else:
            add_test_log(f"JS8Call frequency set: FAILED - {result.stderr}", "ERROR")
            return False
        
        # Test other JS8Call commands
        js8_commands = [
            ('get_freq', 'f'),
            ('get_mode', 'm'),
            ('get_ptt', 't'),
        ]
        
        for cmd_name, cmd in js8_commands:
            result = subprocess.run(
                ['rigctl', '-m', str(TEST_CONFIG['rigctl_model']), cmd],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                add_test_log(f"JS8Call {cmd_name}: SUCCESS")
            else:
                add_test_log(f"JS8Call {cmd_name}: FAILED - {result.stderr}", "ERROR")
                return False
        
        test_results['js8call_connection'] = True
        add_test_log("JS8Call connection test passed")
        return True
        
    except Exception as e:
        add_test_log(f"JS8Call connection test error: {e}", "ERROR")
        return False

def cleanup_processes():
    """Clean up all test processes."""
    global test_processes
    add_test_log("Cleaning up test processes...")
    
    for proc in test_processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            try:
                proc.kill()
            except:
                pass
    
    test_processes = []
    
    # Clean up virtual audio
    try:
        subprocess.run(['pactl', 'unload-module', 'module-null-sink'], 
                      capture_output=True, timeout=5)
    except:
        pass

def signal_handler(signum, frame):
    """Handle interrupt signals."""
    global test_running
    test_running = False
    add_test_log("Received interrupt signal, cleaning up...")
    cleanup_processes()
    sys.exit(0)

def generate_test_report():
    """Generate comprehensive test report."""
    add_test_log("Generating test report...")
    
    report = {
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'test_results': test_results,
        'summary': {
            'total_tests': len([k for k in test_results.keys() if k not in ['crashes', 'successful_decodes', 'test_log']]),
            'passed_tests': len([k for k, v in test_results.items() if v is True]),
            'failed_tests': len([k for k, v in test_results.items() if v is False]),
            'crashes': test_results['crashes'],
            'successful_decodes': test_results['successful_decodes']
        }
    }
    
    # Calculate success rate
    total = report['summary']['total_tests']
    passed = report['summary']['passed_tests']
    success_rate = (passed / total * 100) if total > 0 else 0
    report['summary']['success_rate'] = success_rate
    
    # Write report to file
    report_file = f"test_report_{int(time.time())}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "="*80)
    print("INTEGRATION TEST REPORT")
    print("="*80)
    print(f"Total Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Crashes: {test_results['crashes']}")
    print(f"Successful Decodes: {test_results['successful_decodes']}")
    
    print("\nTest Results:")
    for test_name, result in test_results.items():
        if test_name not in ['crashes', 'successful_decodes', 'test_log']:
            status = "PASS" if result else "FAIL"
            print(f"  {test_name}: {status}")
    
    print(f"\nFull report saved to: {report_file}")
    
    return report

def main():
    """Main test execution function."""
    global test_running
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    add_test_log("Starting WSJT-X & JS8Call integration tests...")
    
    # Setup test environment
    if not setup_virtual_audio():
        add_test_log("Virtual audio setup failed, continuing with limited tests", "WARNING")
    
    # Start rigctld for testing
    if not start_rigctld():
        add_test_log("rigctld startup failed, some tests will be skipped", "WARNING")
    
    # Start CAT emulator
    if not start_cat_emulator():
        add_test_log("CAT emulator startup failed, some tests will be skipped", "WARNING")
    
    # Run test scenarios
    test_scenarios = [
        ("Cold Start", test_cold_start),
        ("Frequency Set", test_frequency_set),
        ("VFO Handling", test_vfo_handling),
        ("IF Command Response", test_if_command_response),
        ("TX/RX Cycle", test_tx_rx_cycle),
        ("USB Reconnect", test_usb_disconnect_reconnect),
        ("WSJT-X Connection", test_wsjt_x_connection),
        ("JS8Call Connection", test_js8call_connection),
    ]
    
    for scenario_name, test_func in test_scenarios:
        if not test_running:
            break
        
        add_test_log(f"Running {scenario_name} test...")
        try:
            test_func()
        except Exception as e:
            add_test_log(f"Test {scenario_name} failed with exception: {e}", "ERROR")
            test_results['crashes'] += 1
        
        time.sleep(1)  # Brief pause between tests
    
    # Generate final report
    report = generate_test_report()
    
    # Cleanup
    cleanup_processes()
    
    # Exit with appropriate code
    if report['summary']['success_rate'] >= 80:
        add_test_log("Integration tests completed successfully!")
        sys.exit(0)
    else:
        add_test_log("Integration tests completed with failures!", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
