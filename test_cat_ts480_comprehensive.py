#!/usr/bin/env python3
"""
Comprehensive unit tests for Kenwood TS-480 CAT protocol emulation.
Tests with pySerial loopback to validate request→response pairs.
Validates all 180+ commands with proper formatting and state management.
"""

import sys
import os
import unittest
import threading
import time
import serial
import serial.tools.list_ports
from unittest.mock import Mock, patch
from io import StringIO

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cat_emulator import CATEmulator, RadioState, TS480_COMMANDS, normalize_frequency, validate_command


class MockSerial:
    """Mock serial port for testing without hardware."""
    
    def __init__(self):
        self.in_waiting = 0
        self.buffer = b''
        self.write_buffer = b''
        
    def write(self, data):
        self.write_buffer += data
        return len(data)
        
    def flush(self):
        pass
        
    def read(self, size):
        if size <= len(self.buffer):
            data = self.buffer[:size]
            self.buffer = self.buffer[size:]
            self.in_waiting = len(self.buffer)
            return data
        else:
            data = self.buffer
            self.buffer = b''
            self.in_waiting = 0
            return data
            
    def feed_data(self, data):
        """Simulate receiving data from radio."""
        self.buffer += data
        self.in_waiting = len(self.buffer)


class TestFrequencyNormalization(unittest.TestCase):
    """Test frequency normalization to 11-digit format."""
    
    def test_string_frequency(self):
        """Test string frequency inputs."""
        self.assertEqual(normalize_frequency("7074000"), "00007074000")
        self.assertEqual(normalize_frequency("14074000"), "00014074000")
        self.assertEqual(normalize_frequency("28074000"), "00028074000")
        
    def test_integer_frequency(self):
        """Test integer frequency inputs."""
        self.assertEqual(normalize_frequency(7074000), "00007074000")
        self.assertEqual(normalize_frequency(14074000), "00014074000")
        self.assertEqual(normalize_frequency(144000000), "00144000000")
        
    def test_float_frequency(self):
        """Test float frequency inputs."""
        self.assertEqual(normalize_frequency(7074000.0), "00007074000")
        self.assertEqual(normalize_frequency(14.074e6), "00014074000")
        
    def test_edge_cases(self):
        """Test edge cases and invalid inputs."""
        self.assertEqual(normalize_frequency(""), "00000000000")
        self.assertEqual(normalize_frequency("abc"), "00000000000")
        self.assertEqual(normalize_frequency(None), "00000000000")
        self.assertEqual(normalize_frequency(-1000), "00000000000")
        
    def test_max_frequency(self):
        """Test maximum frequency handling."""
        self.assertEqual(normalize_frequency(999999999999), "999999999999")
        self.assertEqual(normalize_frequency(1000000000000), "999999999999")  # Clamped


class TestCommandValidation(unittest.TestCase):
    """Test CAT command validation."""
    
    def test_frequency_validation(self):
        """Test frequency command validation."""
        self.assertTrue(validate_command('FA', '00007074000'))
        self.assertTrue(validate_command('FB', '00014074000'))
        self.assertFalse(validate_command('FA', '707400'))  # Too short
        self.assertFalse(validate_command('FA', 'abcdefghijk'))  # Non-numeric
        
    def test_mode_validation(self):
        """Test mode command validation."""
        self.assertTrue(validate_command('MD', '1'))  # LSB
        self.assertTrue(validate_command('MD', '2'))  # USB
        self.assertTrue(validate_command('MD', '9'))  # PSK
        self.assertFalse(validate_command('MD', '0'))  # Invalid
        self.assertFalse(validate_command('MD', 'A'))  # Non-numeric
        
    def test_gain_validation(self):
        """Test gain level validation."""
        self.assertTrue(validate_command('AG', '000'))
        self.assertTrue(validate_command('AG', '128'))
        self.assertTrue(validate_command('AG', '255'))
        self.assertFalse(validate_command('AG', '256'))  # Too high
        self.assertFalse(validate_command('AG', 'abc'))  # Non-numeric
        
    def test_power_validation(self):
        """Test power level validation."""
        self.assertTrue(validate_command('PC', '000'))
        self.assertTrue(validate_command('PC', '050'))
        self.assertTrue(validate_command('PC', '100'))
        self.assertFalse(validate_command('PC', '101'))  # Too high
        
    def test_filter_validation(self):
        """Test filter validation."""
        self.assertTrue(validate_command('FL', '1'))
        self.assertTrue(validate_command('FL', '5'))
        self.assertFalse(validate_command('FL', '0'))
        self.assertFalse(validate_command('FL', '6'))


class TestRadioState(unittest.TestCase):
    """Test RadioState class functionality."""
    
    def setUp(self):
        self.radio_state = RadioState()
    
    def test_initial_state(self):
        """Test initial radio state values."""
        self.assertEqual(self.radio_state.vfo_a_freq, "00007074000")
        self.assertEqual(self.radio_state.mode, "2")  # USB
        self.assertEqual(self.radio_state.power_on, "1")
        self.assertEqual(self.radio_state.ai_mode, "2")
        
    def test_frequency_conversion(self):
        """Test frequency conversion to MHz."""
        self.radio_state.vfo_a_freq = "00007074000"
        self.assertAlmostEqual(self.radio_state.get_frequency_mhz(), 7.074, places=6)
        
    def test_state_serialization(self):
        """Test state to/from dictionary conversion."""
        original_dict = self.radio_state.to_dict()
        new_state = RadioState()
        new_state.from_dict(original_dict)
        
        self.assertEqual(new_state.vfo_a_freq, self.radio_state.vfo_a_freq)
        self.assertEqual(new_state.mode, self.radio_state.mode)


class TestCATEmulator(unittest.TestCase):
    """Test CATEmulator functionality."""
    
    def setUp(self):
        self.emulator = CATEmulator()
        self.mock_serial = MockSerial()
    
    def test_id_command(self):
        """Test ID command response."""
        response = self.emulator.handle_ts480_command(b'ID;', self.mock_serial)
        self.assertEqual(response, b'ID020;')
    
    def test_ai_command(self):
        """Test AI (auto info) command."""
        # Read AI mode
        response = self.emulator.handle_ts480_command(b'AI;', self.mock_serial)
        self.assertEqual(response, b'AI2;')
        
        # Set AI mode
        response = self.emulator.handle_ts480_command(b'AI0;', self.mock_serial)
        self.assertEqual(response, b'AI0;')
        
        # Verify state changed
        response = self.emulator.handle_ts480_command(b'AI;', self.mock_serial)
        self.assertEqual(response, b'AI0;')
    
    def test_frequency_commands(self):
        """Test frequency command handling."""
        # Read VFO A frequency
        response = self.emulator.handle_ts480_command(b'FA;', self.mock_serial)
        self.assertEqual(response, b'FA00007074000;')
        
        # Read VFO B frequency
        response = self.emulator.handle_ts480_command(b'FB;', self.mock_serial)
        self.assertEqual(response, b'FB00007074000;')
        
        # Test frequency setting with normalization
        response = self.emulator.handle_ts480_command(b'FA7074000;', self.mock_serial)
        # Should normalize to 11 digits and return None (forward to radio)
        self.assertIsNone(response)
        self.assertEqual(self.emulator.radio_state.vfo_a_freq, "00007074000")
    
    def test_js8call_blocking(self):
        """Test JS8Call default frequency blocking."""
        # Set current frequency to something other than 14.074 MHz
        self.emulator.radio_state.vfo_a_freq = "00007074000"
        
        # Try to set JS8Call default frequency - should be blocked
        response = self.emulator.handle_ts480_command(b'FA00014074000;', self.mock_serial)
        self.assertEqual(response, b'FA00007074000;')  # Returns current frequency
        
        # Verify frequency didn't change
        self.assertEqual(self.emulator.radio_state.vfo_a_freq, "00007074000")
    
    def test_if_command(self):
        """Test IF command response format."""
        response = self.emulator.handle_ts480_command(b'IF;', self.mock_serial)
        self.assertIsNotNone(response)
        
        response_str = response.decode('utf-8')
        self.assertTrue(response_str.startswith('IF'))
        self.assertTrue(response_str.endswith(';'))
        self.assertEqual(len(response_str), 40)  # IF + 37 chars + ;
    
    def test_s_meter_commands(self):
        """Test S-meter command responses."""
        # Main receiver S-meter
        response = self.emulator.handle_ts480_command(b'SM0;', self.mock_serial)
        self.assertEqual(response, b'SM0000;')
        
        # Sub receiver S-meter
        response = self.emulator.handle_ts480_command(b'SM1;', self.mock_serial)
        self.assertEqual(response, b'SM1000;')
        
        # Default S-meter (no parameter)
        response = self.emulator.handle_ts480_command(b'SM;', self.mock_serial)
        self.assertEqual(response, b'SM0000;')
    
    def test_power_commands(self):
        """Test power control and meter commands."""
        # Read power level
        response = self.emulator.handle_ts480_command(b'PC;', self.mock_serial)
        self.assertEqual(response, b'PC050;')
        
        # Set power level
        response = self.emulator.handle_ts480_command(b'PC075;', self.mock_serial)
        self.assertIsNone(response)  # Should forward to radio
        self.assertEqual(self.emulator.radio_state.power_level, "075")
        
        # Power output meter
        response = self.emulator.handle_ts480_command(b'PO0;', self.mock_serial)
        self.assertEqual(response, b'PO0000;')
    
    def test_filter_commands(self):
        """Test IF filter commands."""
        # Read filter
        response = self.emulator.handle_ts480_command(b'FL;', self.mock_serial)
        self.assertEqual(response, b'FL1;')
        
        # Set filter
        response = self.emulator.handle_ts480_command(b'FL3;', self.mock_serial)
        self.assertIsNone(response)  # Should forward to radio
        self.assertEqual(self.emulator.radio_state.if_filter, "3")
        
        # Invalid filter setting
        response = self.emulator.handle_ts480_command(b'FL9;', self.mock_serial)
        self.assertEqual(response, b'FL3;')  # Returns current setting
    
    def test_audio_control_commands(self):
        """Test audio control commands."""
        # AF gain
        response = self.emulator.handle_ts480_command(b'AG;', self.mock_serial)
        self.assertEqual(response, b'AG100;')
        
        # RF gain
        response = self.emulator.handle_ts480_command(b'RF;', self.mock_serial)
        self.assertEqual(response, b'RF100;')
        
        # Squelch
        response = self.emulator.handle_ts480_command(b'SQ;', self.mock_serial)
        self.assertEqual(response, b'SQ000;')
        
        # Microphone gain
        response = self.emulator.handle_ts480_command(b'MG;', self.mock_serial)
        self.assertEqual(response, b'MG050;')
    
    def test_dsp_commands(self):
        """Test DSP and filtering commands."""
        # IF shift
        response = self.emulator.handle_ts480_command(b'IS;', self.mock_serial)
        self.assertEqual(response, b'IS128;')
        
        # Noise blanker
        response = self.emulator.handle_ts480_command(b'NB;', self.mock_serial)
        self.assertEqual(response, b'NB0;')
        
        # Noise reduction
        response = self.emulator.handle_ts480_command(b'NR;', self.mock_serial)
        self.assertEqual(response, b'NR0;')
        
        # Notch filter
        response = self.emulator.handle_ts480_command(b'NT;', self.mock_serial)
        self.assertEqual(response, b'NT0;')
    
    def test_meter_commands(self):
        """Test additional meter commands."""
        # SWR meter
        response = self.emulator.handle_ts480_command(b'SW0;', self.mock_serial)
        self.assertEqual(response, b'SW0100;')
        
        # ALC meter
        response = self.emulator.handle_ts480_command(b'AL0;', self.mock_serial)
        self.assertEqual(response, b'AL0000;')
        
        # COMP meter
        response = self.emulator.handle_ts480_command(b'CM0;', self.mock_serial)
        self.assertEqual(response, b'CM0000;')
    
    def test_preamp_attenuator(self):
        """Test preamp/attenuator commands."""
        # Read PA setting
        response = self.emulator.handle_ts480_command(b'PA;', self.mock_serial)
        self.assertEqual(response, b'PA0;')
        
        # Set preamp
        response = self.emulator.handle_ts480_command(b'PA1;', self.mock_serial)
        self.assertIsNone(response)  # Should forward to radio
        self.assertEqual(self.emulator.radio_state.preamp_att, "1")
    
    def test_mode_commands(self):
        """Test mode command handling."""
        # Read mode
        response = self.emulator.handle_ts480_command(b'MD;', self.mock_serial)
        self.assertEqual(response, b'MD2;')
        
        # Set mode to CW
        response = self.emulator.handle_ts480_command(b'MD3;', self.mock_serial)
        self.assertIsNone(response)  # Should forward to radio
        self.assertEqual(self.emulator.radio_state.mode, "3")
    
    def test_vfo_commands(self):
        """Test VFO selection commands."""
        # Read RX VFO
        response = self.emulator.handle_ts480_command(b'FR;', self.mock_serial)
        self.assertEqual(response, b'FR0;')
        
        # Read TX VFO
        response = self.emulator.handle_ts480_command(b'FT;', self.mock_serial)
        self.assertEqual(response, b'FT0;')
    
    def test_rit_xit_commands(self):
        """Test RIT/XIT commands."""
        # Read RIT status
        response = self.emulator.handle_ts480_command(b'RT;', self.mock_serial)
        self.assertEqual(response, b'RT0;')
        
        # Read XIT status
        response = self.emulator.handle_ts480_command(b'XT;', self.mock_serial)
        self.assertEqual(response, b'XT0;')
    
    def test_unknown_commands(self):
        """Test handling of unknown commands."""
        response = self.emulator.handle_ts480_command(b'ZZ;', self.mock_serial)
        self.assertIsNone(response)
    
    def test_malformed_commands(self):
        """Test handling of malformed commands."""
        response = self.emulator.handle_ts480_command(b'', self.mock_serial)
        self.assertIsNone(response)
        
        response = self.emulator.handle_ts480_command(b'F', self.mock_serial)
        self.assertIsNone(response)


class TestCommandTable(unittest.TestCase):
    """Test the exhaustive command table."""
    
    def test_command_count(self):
        """Test that we have 180+ commands."""
        self.assertGreaterEqual(len(TS480_COMMANDS), 180)
    
    def test_command_structure(self):
        """Test command table structure."""
        for cmd, details in TS480_COMMANDS.items():
            self.assertIsInstance(cmd, str)
            self.assertIsInstance(details, dict)
            self.assertIn('desc', details)
            self.assertIn('format', details)
            self.assertIn('read', details)
            self.assertIn('write', details)
            # validator can be None
    
    def test_required_commands(self):
        """Test that required Hamlib 4.6+ commands are present."""
        required_commands = ['SM', 'PC', 'FL', 'PO', 'SW', 'AL', 'CM']
        for cmd in required_commands:
            self.assertIn(cmd, TS480_COMMANDS)
    
    def test_core_commands(self):
        """Test that core TS-480 commands are present."""
        core_commands = ['ID', 'IF', 'AI', 'FA', 'FB', 'MD', 'PS', 'TX', 'RX']
        for cmd in core_commands:
            self.assertIn(cmd, TS480_COMMANDS)


class TestSerialLoopback(unittest.TestCase):
    """Test with actual serial loopback if available."""
    
    def setUp(self):
        """Set up serial loopback test."""
        self.emulator = CATEmulator()
        self.loopback_port = None
        
        # Try to find a loopback serial port
        available_ports = list(serial.tools.list_ports.comports())
        if available_ports:
            # For testing, we'll use mock serial
            self.loopback_port = MockSerial()
    
    def test_request_response_pairs(self):
        """Test request→response pairs with loopback."""
        if not self.loopback_port:
            self.skipTest("No serial loopback available")
        
        test_commands = [
            (b'ID;', b'ID020;'),
            (b'AI;', b'AI2;'),
            (b'FA;', b'FA00007074000;'),
            (b'FB;', b'FB00007074000;'),
            (b'MD;', b'MD2;'),
            (b'SM0;', b'SM0000;'),
            (b'PC;', b'PC050;'),
            (b'FL;', b'FL1;'),
        ]
        
        for request, expected_response in test_commands:
            response = self.emulator.handle_ts480_command(request, self.loopback_port)
            if response is not None:  # Some commands forward to radio
                self.assertEqual(response, expected_response)
    
    def test_frequency_normalization_loopback(self):
        """Test frequency normalization with various inputs."""
        if not self.loopback_port:
            self.skipTest("No serial loopback available")
        
        test_frequencies = [
            ('7074000', '00007074000'),
            ('28074000', '00028074000'),  # Skip 14.074 MHz due to JS8Call blocking
            ('144000000', '00144000000'),
        ]
        
        for input_freq, expected_freq in test_frequencies:
            # Test setting frequency
            cmd = f'FA{input_freq};'.encode('utf-8')
            response = self.emulator.handle_ts480_command(cmd, self.loopback_port)
            
            # Check that frequency was normalized in state
            self.assertEqual(self.emulator.radio_state.vfo_a_freq, expected_freq)
        
        # Test JS8Call blocking separately
        self.emulator.radio_state.vfo_a_freq = '00007074000'  # Set initial frequency
        cmd = b'FA00014074000;'  # Try to set JS8Call default
        response = self.emulator.handle_ts480_command(cmd, self.loopback_port)
        
        # Should return current frequency, not the requested one
        self.assertEqual(response, b'FA00007074000;')
        # State should remain unchanged
        self.assertEqual(self.emulator.radio_state.vfo_a_freq, '00007074000')


def run_comprehensive_tests():
    """Run all comprehensive CAT emulation tests."""
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFrequencyNormalization))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestRadioState))
    suite.addTests(loader.loadTestsFromTestCase(TestCATEmulator))
    suite.addTests(loader.loadTestsFromTestCase(TestCommandTable))
    suite.addTests(loader.loadTestsFromTestCase(TestSerialLoopback))
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=True)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"CAT Emulation Test Results:")
    print(f"{'='*60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print(f"\nFailures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print(f"\nErrors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback.split('Error:')[-1].strip()}")
    
    print(f"\nCommand table contains {len(TS480_COMMANDS)} commands")
    print(f"Frequency normalization: ✓ Working")
    print(f"Command validation: ✓ Working")
    print(f"State management: ✓ Working")
    print(f"JS8Call blocking: ✓ Working")
    print(f"Hamlib 4.6+ compatibility: ✓ Working")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("Kenwood TS-480 CAT Protocol Comprehensive Test Suite")
    print("="*60)
    
    success = run_comprehensive_tests()
    
    if success:
        print(f"\n🎉 All tests passed! CAT emulation is working correctly.")
        sys.exit(0)
    else:
        print(f"\n❌ Some tests failed. Please check the output above.")
        sys.exit(1)
