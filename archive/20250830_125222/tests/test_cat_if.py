#!/usr/bin/env python3
"""
Unit test for CAT IF command emulation with mocked serial port
Tests the handle_ts480_command function specifically for IF response format
"""

import unittest
import sys
import os
import threading
import time
import serial
from unittest.mock import MagicMock, patch, Mock

# Add the parent directory to sys.path to import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the main module (handle dash in filename)
import importlib.util
spec = importlib.util.spec_from_file_location("trusdx", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trusdx-txrx-AI.py"))
trusdx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trusdx)

class TestCATIFCommand(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the radio state
        self.original_radio_state = trusdx.radio_state.copy()
        
        # Set up a known radio state for testing
        trusdx.radio_state.update({
            'vfo_a_freq': '00014074000',  # 14.074 MHz
            'vfo_b_freq': '00014074000',  # 14.074 MHz
            'mode': '2',                  # USB
            'rx_vfo': '0',               # VFO A
            'tx_vfo': '0',               # VFO A
            'split': '0',                # Split off
            'rit': '0',                  # RIT off
            'xit': '0',                  # XIT off
            'rit_offset': '00000',       # No offset
            'power_on': '1',             # Power on
            'ai_mode': '2'               # Auto info on
        })
        
        # Mock serial port
        self.mock_ser = MagicMock()
        
        # Mock config
        self.original_config = getattr(trusdx, 'config', {})
        trusdx.config = {'verbose': True}
        
        # Mock the log function to capture log messages
        self.log_messages = []
        self.original_log = trusdx.log
        trusdx.log = lambda msg, level='INFO': self.log_messages.append(f"[{level}] {msg}")
    
    def tearDown(self):
        """Clean up after tests"""
        # Restore original radio state
        trusdx.radio_state = self.original_radio_state
        
        # Restore original config
        trusdx.config = self.original_config
        
        # Restore original log function
        trusdx.log = self.original_log
    
    def test_if_command_response_format(self):
        """Test that IF command returns exactly 37 characters + delimiter"""
        # Test IF command
        command = b'IF;'
        response = trusdx.handle_ts480_command(command, self.mock_ser)
        
        # Verify response exists
        self.assertIsNotNone(response, "IF command should return a response")
        
        # Decode response
        response_str = response.decode('utf-8')
        print(f"IF response: '{response_str}'")
        
        # Check that it starts with 'IF'
        self.assertTrue(response_str.startswith('IF'), f"Response should start with 'IF', got: {response_str}")
        
        # Check that it ends with ';'
        self.assertTrue(response_str.endswith(';'), f"Response should end with ';', got: {response_str}")
        
        # Check total length (IF + 37 chars + ; = 40 chars)
        self.assertEqual(len(response_str), 40, 
                        f"IF response should be exactly 40 characters (IF + 37 chars + ;), got {len(response_str)}: '{response_str}'")
        
        # Extract the 37-character content (excluding 'IF' and ';')
        content = response_str[2:-1]  # Remove 'IF' and ';'
        self.assertEqual(len(content), 37, 
                        f"Content should be exactly 37 characters, got {len(content)}: '{content}'")
        
        # Test with known state - frequency should be present
        self.assertTrue('14074000' in content, f"Frequency should be in response: '{content}'")
        
        # Test that content is all digits (as per TS-480 spec)
        self.assertTrue(content.isdigit(), f"IF content should be all digits, got: '{content}'")
    
    def test_if_command_with_different_frequencies(self):
        """Test IF command with different frequencies"""
        test_frequencies = [
            '00007074000',  # 7.074 MHz (40m)
            '00014074000',  # 14.074 MHz (20m)
            '00021074000',  # 21.074 MHz (15m)
            '00028074000',  # 28.074 MHz (10m)
        ]
        
        for freq in test_frequencies:
            with self.subTest(frequency=freq):
                # Set test frequency
                trusdx.radio_state['vfo_a_freq'] = freq
                
                # Test IF command
                command = b'IF;'
                response = trusdx.handle_ts480_command(command, self.mock_ser)
                
                # Verify response
                self.assertIsNotNone(response, f"IF command should return a response for freq {freq}")
                
                response_str = response.decode('utf-8')
                self.assertEqual(len(response_str), 40, 
                                f"IF response should be 40 chars for freq {freq}, got {len(response_str)}: '{response_str}'")
                
                # Check frequency is in response (remove leading zeros for comparison)
                freq_in_response = freq.lstrip('0') or '0'
                self.assertTrue(freq_in_response in response_str, 
                               f"Frequency {freq} should be in response: '{response_str}'")
    
    def test_if_command_hamlib_compatibility(self):
        """Test IF command for Hamlib 4.6.3 compatibility"""
        # Test IF command
        command = b'IF;'
        response = trusdx.handle_ts480_command(command, self.mock_ser)
        
        # Verify response format matches Hamlib expectations
        self.assertIsNotNone(response, "IF command should return a response")
        
        response_str = response.decode('utf-8')
        
        # Hamlib expects this exact format:
        # IF<11-digit freq><5-digit RIT/XIT><RIT><XIT><Bank><RX/TX><Mode><VFO><Scan><Split><Tone><ToneFreq><CTCSS><padding>;
        
        # Extract components
        content = response_str[2:-1]  # Remove 'IF' and ';'
        
        # Check frequency (first 11 characters)
        freq_part = content[:11]
        self.assertEqual(len(freq_part), 11, f"Frequency part should be 11 chars, got {len(freq_part)}: '{freq_part}'")
        self.assertTrue(freq_part.isdigit(), f"Frequency part should be digits: '{freq_part}'")
        
        # Check RIT/XIT offset (next 5 characters)
        rit_xit_part = content[11:16]
        self.assertEqual(len(rit_xit_part), 5, f"RIT/XIT part should be 5 chars, got {len(rit_xit_part)}: '{rit_xit_part}'")
        self.assertTrue(rit_xit_part.isdigit(), f"RIT/XIT part should be digits: '{rit_xit_part}'")
        
        # Check remaining parts are present and correct length
        remaining = content[16:]
        self.assertEqual(len(remaining), 21, f"Remaining part should be 21 chars, got {len(remaining)}: '{remaining}'")
        
        print(f"IF response breakdown:")
        print(f"  Full response: '{response_str}' (length: {len(response_str)})")
        print(f"  Frequency (11): '{freq_part}'")
        print(f"  RIT/XIT (5): '{rit_xit_part}'")
        print(f"  Remaining (21): '{remaining}'")
    
    def test_v_command_response(self):
        """Test V command returns proper VFO information"""
        # Test V command (query current VFO)
        command = b'V;'
        response = trusdx.handle_ts480_command(command, self.mock_ser)
        
        # Verify response
        self.assertIsNotNone(response, "V command should return a response")
        
        response_str = response.decode('utf-8')
        print(f"V response: '{response_str}'")
        
        # Should return V0; (VFO A) or V1; (VFO B)
        self.assertTrue(response_str in ['V0;', 'V1;'], 
                       f"V response should be 'V0;' or 'V1;', got: '{response_str}'")
    
    def test_v_command_set_vfo(self):
        """Test V command can set VFO"""
        # Test setting VFO A
        command = b'V0;'
        response = trusdx.handle_ts480_command(command, self.mock_ser)
        
        # Should return None (forwarded to radio) or echo back
        # Check that radio state was updated
        self.assertEqual(trusdx.radio_state['rx_vfo'], '0', "RX VFO should be set to 0")
        self.assertEqual(trusdx.radio_state['tx_vfo'], '0', "TX VFO should be set to 0")
        
        # Test setting VFO B  
        command = b'V1;'
        response = trusdx.handle_ts480_command(command, self.mock_ser)
        
        # Check that radio state was updated
        self.assertEqual(trusdx.radio_state['rx_vfo'], '1', "RX VFO should be set to 1")
        self.assertEqual(trusdx.radio_state['tx_vfo'], '1', "TX VFO should be set to 1")
    
    def test_ai_command_response(self):
        """Test AI command returns proper auto information mode"""
        # Test AI command (query auto info mode)
        command = b'AI;'
        response = trusdx.handle_ts480_command(command, self.mock_ser)
        
        # Verify response
        self.assertIsNotNone(response, "AI command should return a response")
        
        response_str = response.decode('utf-8')
        print(f"AI response: '{response_str}'")
        
        # Should return AI<mode>; where mode is 0, 1, or 2
        self.assertTrue(response_str.startswith('AI'), f"AI response should start with 'AI', got: '{response_str}'")
        self.assertTrue(response_str.endswith(';'), f"AI response should end with ';', got: '{response_str}'")
        self.assertEqual(len(response_str), 4, f"AI response should be 4 chars, got {len(response_str)}: '{response_str}'")
        
        # Extract mode
        mode = response_str[2:-1]
        self.assertIn(mode, ['0', '1', '2'], f"AI mode should be 0, 1, or 2, got: '{mode}'")


class TestCATDriverIntegration(unittest.TestCase):
    """Integration tests that spin up the driver with mocked serial port"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock config
        self.original_config = getattr(trusdx, 'config', {})
        trusdx.config = {'verbose': False, 'unmute': False}
        
        # Mock the state
        self.original_state = trusdx.state.copy()
        trusdx.state = {
            'ser': None,
            'ser2': None,
            'in_stream': None,
            'out_stream': None,
            'reconnecting': False,
            'connection_stable': True,
            'last_data_time': time.time(),
            'reconnect_count': 0,
            'hardware_disconnected': False
        }
        
        # Mock status
        self.original_status = trusdx.status.copy()
        trusdx.status = [False, False, True, False, False, False]
        
        # Mock log function
        self.log_messages = []
        self.original_log = trusdx.log
        trusdx.log = lambda msg, level='INFO': self.log_messages.append(f"[{level}] {msg}")
        
        # Mock pyaudio
        self.pyaudio_patcher = patch('trusdx_txrx_AI.pyaudio.PyAudio')
        self.mock_pyaudio = self.pyaudio_patcher.start()
        
        # Mock serial
        self.serial_patcher = patch('trusdx_txrx_AI.serial.Serial')
        self.mock_serial = self.serial_patcher.start()
        
        # Mock os operations
        self.os_patcher = patch('trusdx_txrx_AI.os.openpty')
        self.mock_openpty = self.os_patcher.start()
        self.mock_openpty.return_value = (1, 2)  # Mock master, slave file descriptors
        
        # Mock os.fdopen
        self.fdopen_patcher = patch('trusdx_txrx_AI.os.fdopen')
        self.mock_fdopen = self.fdopen_patcher.start()
        
        # Mock os.ttyname
        self.ttyname_patcher = patch('trusdx_txrx_AI.os.ttyname')
        self.mock_ttyname = self.ttyname_patcher.start()
        self.mock_ttyname.return_value = '/dev/pts/0'
        
        # Mock os.symlink
        self.symlink_patcher = patch('trusdx_txrx_AI.os.symlink')
        self.mock_symlink = self.symlink_patcher.start()
        
        # Mock threading
        self.thread_patcher = patch('trusdx_txrx_AI.threading.Thread')
        self.mock_thread = self.thread_patcher.start()
        
        # Mock time.sleep
        self.sleep_patcher = patch('trusdx_txrx_AI.time.sleep')
        self.mock_sleep = self.sleep_patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        # Restore original values
        trusdx.config = self.original_config
        trusdx.state = self.original_state
        trusdx.status = self.original_status
        trusdx.log = self.original_log
        
        # Stop patchers
        self.pyaudio_patcher.stop()
        self.serial_patcher.stop()
        self.os_patcher.stop()
        self.fdopen_patcher.stop()
        self.ttyname_patcher.stop()
        self.symlink_patcher.stop()
        self.thread_patcher.stop()
        self.sleep_patcher.stop()


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
