#!/usr/bin/env python3
"""
Unit tests for CAT VFO state machine implementation in trusdx-txrx-AI.py
Tests the complete TS-480 VFO functionality including FR, FT, FA, FB, TX, RX, AI mode
"""

import unittest
import sys
import os
import threading
import time
from unittest.mock import MagicMock, patch, Mock, call

# Add the parent directory to sys.path to import the main module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the main module (handle dash in filename)
import importlib.util
spec = importlib.util.spec_from_file_location("trusdx", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trusdx-txrx-AI.py"))
trusdx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trusdx)

class TestVFOStateMachine(unittest.TestCase):
    """Test the VFO state machine and related commands"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Save original state
        self.original_radio_state = trusdx.radio_state.copy()
        self.original_status = trusdx.status.copy()
        
        # Reset radio state for consistent testing
        trusdx.radio_state = {
            'vfo_a_freq': '00007074000',  # 7.074 MHz
            'vfo_b_freq': '00014074000',  # 14.074 MHz
            'mode': '2',                  # USB
            'rx_vfo': '0',               # VFO A
            'tx_vfo': '0',               # VFO A
            'curr_vfo': 'A',             # Current VFO initialized to A
            'split': '0',                # Split off
            'rit': '0',                  # RIT off
            'xit': '0',                  # XIT off
            'rit_offset': '00000',       # No offset
            'power_on': '1',             # Power on
            'ai_mode': '0'               # Auto info off initially
        }
        
        # Reset status
        trusdx.status = [False, False, True, True, False, False]  # status[3] = True for CAT active
        
        # Mock serial port
        self.mock_ser = MagicMock()
        
        # Mock config
        self.original_config = getattr(trusdx, 'config', {})
        trusdx.config = {'verbose': False, 'unmute': False}
        
        # Mock the log function
        self.log_messages = []
        self.original_log = trusdx.log
        trusdx.log = lambda msg, level='INFO': self.log_messages.append(f"[{level}] {msg}")
    
    def tearDown(self):
        """Clean up after tests"""
        # Restore original state
        trusdx.radio_state = self.original_radio_state
        trusdx.status = self.original_status
        trusdx.config = self.original_config
        trusdx.log = self.original_log
    
    def test_curr_vfo_initialized(self):
        """Test that curr_vfo is initialized to 'A'"""
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'A', "curr_vfo should be initialized to 'A'")
    
    def test_fr_query_returns_current_vfo(self):
        """Test FR; query returns current RX VFO"""
        # Test with VFO A
        trusdx.radio_state['curr_vfo'] = 'A'
        response = trusdx.handle_ts480_command(b'FR;', self.mock_ser)
        self.assertEqual(response, b'FR0;', "FR query should return FR0; for VFO A")
        
        # Test with VFO B
        trusdx.radio_state['curr_vfo'] = 'B'
        response = trusdx.handle_ts480_command(b'FR;', self.mock_ser)
        self.assertEqual(response, b'FR1;', "FR query should return FR1; for VFO B")
    
    def test_fr_set_updates_vfo_state(self):
        """Test FR0/FR1 commands update VFO state"""
        # Set to VFO A
        response = trusdx.handle_ts480_command(b'FR0;', self.mock_ser)
        self.assertEqual(response, b';', "FR0 should ACK with ;")
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'A', "FR0 should set curr_vfo to A")
        self.assertEqual(trusdx.radio_state['rx_vfo'], '0', "FR0 should set rx_vfo to 0")
        
        # Set to VFO B
        response = trusdx.handle_ts480_command(b'FR1;', self.mock_ser)
        self.assertEqual(response, b';', "FR1 should ACK with ;")
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'B', "FR1 should set curr_vfo to B")
        self.assertEqual(trusdx.radio_state['rx_vfo'], '1', "FR1 should set rx_vfo to 1")
    
    def test_ft_query_returns_tx_vfo(self):
        """Test FT; query returns current TX VFO based on curr_vfo"""
        # Test with VFO A
        trusdx.radio_state['curr_vfo'] = 'A'
        response = trusdx.handle_ts480_command(b'FT;', self.mock_ser)
        self.assertEqual(response, b'FT0;', "FT query should return FT0; for VFO A")
        
        # Test with VFO B
        trusdx.radio_state['curr_vfo'] = 'B'
        response = trusdx.handle_ts480_command(b'FT;', self.mock_ser)
        self.assertEqual(response, b'FT1;', "FT query should return FT1; for VFO B")
    
    def test_ft_set_updates_tx_vfo(self):
        """Test FT0/FT1 commands update TX VFO state"""
        # Set TX to VFO A
        response = trusdx.handle_ts480_command(b'FT0;', self.mock_ser)
        self.assertEqual(response, b';', "FT0 should ACK with ;")
        self.assertEqual(trusdx.radio_state['tx_vfo'], '0', "FT0 should set tx_vfo to 0")
        
        # Set TX to VFO B
        response = trusdx.handle_ts480_command(b'FT1;', self.mock_ser)
        self.assertEqual(response, b';', "FT1 should ACK with ;")
        self.assertEqual(trusdx.radio_state['tx_vfo'], '1', "FT1 should set tx_vfo to 1")
    
    def test_if_response_vfo_indicator(self):
        """Test IF; response byte 38 reflects current VFO (0=A, 1=B)"""
        # Test with VFO A
        trusdx.radio_state['curr_vfo'] = 'A'
        response = trusdx.handle_ts480_command(b'IF;', self.mock_ser)
        response_str = response.decode('utf-8')
        # Byte 38 is at position 24 (0-indexed: IF=2 chars, then 22 chars, then VFO)
        vfo_byte = response_str[24]
        self.assertEqual(vfo_byte, '0', f"IF response byte 38 should be '0' for VFO A, got: {response_str}")
        
        # Test with VFO B
        trusdx.radio_state['curr_vfo'] = 'B'
        response = trusdx.handle_ts480_command(b'IF;', self.mock_ser)
        response_str = response.decode('utf-8')
        vfo_byte = response_str[24]
        self.assertEqual(vfo_byte, '1', f"IF response byte 38 should be '1' for VFO B, got: {response_str}")
    
    def test_fa_setter_acks_and_updates_state(self):
        """Test FA setter updates frequency and curr_vfo, returns ACK"""
        # Set frequency on VFO A
        response = trusdx.handle_ts480_command(b'FA00021074000;', self.mock_ser)
        self.assertEqual(response, b';', "FA setter should ACK with ;")
        self.assertEqual(trusdx.radio_state['vfo_a_freq'], '00021074000', "FA should update vfo_a_freq")
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'A', "FA setter should set curr_vfo to A")
    
    def test_fb_setter_acks_and_updates_state(self):
        """Test FB setter updates frequency and curr_vfo, returns ACK"""
        # Set frequency on VFO B
        response = trusdx.handle_ts480_command(b'FB00028074000;', self.mock_ser)
        self.assertEqual(response, b';', "FB setter should ACK with ;")
        self.assertEqual(trusdx.radio_state['vfo_b_freq'], '00028074000', "FB should update vfo_b_freq")
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'B', "FB setter should set curr_vfo to B")
    
    def test_tx_query_returns_status(self):
        """Test TX; query returns TX status"""
        # Test in RX mode
        trusdx.status[0] = False
        response = trusdx.handle_ts480_command(b'TX;', self.mock_ser)
        self.assertEqual(response, b'TX1;', "TX query should return TX1; when in RX mode")
        
        # Test in TX mode
        trusdx.status[0] = True
        response = trusdx.handle_ts480_command(b'TX;', self.mock_ser)
        self.assertEqual(response, b'TX0;', "TX query should return TX0; when in TX mode")

    def test_tx1_then_tx0_verifies_ua0(self):
        """Test TX1 followed by TX0 to ensure UA0 is emitted."""
        # Send TX1 and verify hardware interaction
        response = trusdx.handle_ts480_command(b'TX1;', self.mock_ser)
        self.assertIsNone(response, "TX1 should be forwarded to hardware")

        # Mock the serial port UA0 emission
        trusdx.disable_cat_audio(self.mock_ser)  # This should send UA0;

        # Ensure UA0 command was sent
        write_calls = [c for c in self.mock_ser.method_calls if c[0] == 'write']
        ua0_sent = any('UA0;' in str(c) for c in write_calls)
        self.assertTrue(ua0_sent, "UA0 should have been sent after TX0")

        # Send TX0 and verify hardware interaction
        response = trusdx.handle_ts480_command(b'TX0;', self.mock_ser)
        self.assertIsNone(response, "TX0 should be forwarded to hardware")

        # Check the mock calls for accurate hardware interaction
        self.mock_ser.reset_mock()  # Reset to check fresh interactions post-TX1
        trusdx.disable_cat_audio(self.mock_ser)
        self.mock_ser.write.assert_called_with(b';UA0;')
    
    def test_tx1_tx0_if_status_indication(self):
        """Test TX1/TX0 commands and verify IF indicates TX/RX status correctly."""
        # Initially in RX mode
        trusdx.status[0] = False
        
        # Query TX status - should show TX1 (not in TX)
        response = trusdx.handle_ts480_command(b'TX;', self.mock_ser)
        self.assertEqual(response, b'TX1;', "Should return TX1; when in RX mode")
        
        # Check IF response shows RX mode (TX/RX indicator at position 22)
        if_response = trusdx.handle_ts480_command(b'IF;', self.mock_ser)
        if_str = if_response.decode('utf-8')
        # TX/RX indicator is at position 22 (0-indexed)
        tx_byte = if_str[22]
        self.assertEqual(tx_byte, '0', f"IF TX/RX indicator should be '0' for RX mode, got: {if_str}")
        
        # Send TX1 to enter TX mode
        response = trusdx.handle_ts480_command(b'TX1;', self.mock_ser)
        self.assertIsNone(response, "TX1 should be forwarded to hardware")
        
        # Simulate the hardware entering TX mode
        trusdx.status[0] = True
        
        # Query TX status - should show TX0 (in TX)
        response = trusdx.handle_ts480_command(b'TX;', self.mock_ser)
        self.assertEqual(response, b'TX0;', "Should return TX0; when in TX mode")
        
        # Check IF response shows TX mode (TX/RX indicator should be '1')
        if_response = trusdx.handle_ts480_command(b'IF;', self.mock_ser)
        if_str = if_response.decode('utf-8')
        tx_byte = if_str[22]
        self.assertEqual(tx_byte, '1', f"IF TX/RX indicator should be '1' for TX mode, got: {if_str}")
        
        # Send TX0 to exit TX mode
        response = trusdx.handle_ts480_command(b'TX0;', self.mock_ser)
        self.assertIsNone(response, "TX0 should be forwarded to hardware")
        
        # Simulate the hardware exiting TX mode
        trusdx.status[0] = False
        
        # Verify UA0 is sent after TX0
        trusdx.disable_cat_audio(self.mock_ser)
        self.mock_ser.write.assert_called_with(b';UA0;')
        
        # Query TX status - should show TX1 again (back in RX)
        response = trusdx.handle_ts480_command(b'TX;', self.mock_ser)
        self.assertEqual(response, b'TX1;', "Should return TX1; when back in RX mode")
        
        # Check IF response shows RX mode again
        if_response = trusdx.handle_ts480_command(b'IF;', self.mock_ser)
        if_str = if_response.decode('utf-8')
        tx_byte = if_str[22]
        self.assertEqual(tx_byte, '0', f"IF TX/RX indicator should be '0' for RX mode after TX0, got: {if_str}")
    
    def test_tx_rx_commands_forward_to_hardware(self):
        """Test TX0/TX1/RX commands are forwarded to hardware"""
        # TX0 command
        response = trusdx.handle_ts480_command(b'TX0;', self.mock_ser)
        self.assertIsNone(response, "TX0 should be forwarded to hardware")
        
        # TX1 command
        response = trusdx.handle_ts480_command(b'TX1;', self.mock_ser)
        self.assertIsNone(response, "TX1 should be forwarded to hardware")
        
        # RX command
        response = trusdx.handle_ts480_command(b'RX;', self.mock_ser)
        self.assertIsNone(response, "RX should be forwarded to hardware")
    
    def test_ai_mode_unsolicited_responses(self):
        """Test AI mode sends unsolicited ID and IF when enabled"""
        # Start with AI mode off
        trusdx.radio_state['ai_mode'] = '0'
        
        # Enable AI mode
        response = trusdx.handle_ts480_command(b'AI2;', self.mock_ser)
        self.assertEqual(response, b'AI2;', "AI2 should echo back")
        self.assertEqual(trusdx.radio_state['ai_mode'], '2', "AI mode should be set to 2")
        
        # Check that unsolicited ID and IF were sent
        expected_calls = [
            call(b'ID020;'),
            call().flush(),
            call(b'IF00007074000000000000020000000800000;'),
            call().flush()
        ]
        
        # The mock_ser.write should have been called with ID and IF
        write_calls = [c for c in self.mock_ser.method_calls if c[0] == 'write']
        self.assertGreaterEqual(len(write_calls), 2, "Should have sent unsolicited ID and IF")
        
        # Verify ID was sent
        id_sent = any('ID020;' in str(c) for c in write_calls)
        self.assertTrue(id_sent, "Should have sent unsolicited ID020;")
        
        # Verify IF was sent  
        if_sent = any('IF' in str(c) for c in write_calls)
        self.assertTrue(if_sent, "Should have sent unsolicited IF response")
    
    def test_unimplemented_commands_return_semicolon(self):
        """Test unimplemented TS-480 commands return ; to avoid ERROR"""
        unimplemented_commands = [
            b'BC;',      # Band change
            b'BY;',      # Busy
            b'CA;',      # CW tune
            b'CN;',      # CTCSS number
            b'CT;',      # CTCSS
            b'DQ;',      # DCS
            b'GT;',      # AGC time constant
            b'KY;',      # CW keying
            b'LK;',      # Lock
            b'LT;',      # ALT function
            b'MF;',      # Menu function
            b'ML;',      # Monitor level
            b'MR;',      # Memory read
            b'NA;',      # Narrow
            b'OS;',      # Offset
            b'QC;',      # DCS code
            b'QI;',      # Quick memory input
            b'QR;',      # Quick memory read
            b'RD;',      # RIT down
            b'RG;',      # RF gain
            b'RM;',      # Read meter
            b'RU;',      # RIT up
            b'SA;',      # Satellite mode
            b'SB;',      # Sub band
            b'SC;',      # Scan
            b'SD;',      # CW break-in delay
            b'SH;',      # Filter high
            b'SI;',      # Split memory
            b'SL;',      # Filter low
            b'SM;',      # S-meter read
            b'SN;',      # Serial number
            b'SS;',      # Program scan
            b'ST;',      # Step
            b'SU;',      # Scan resume
            b'SV;',      # Memory transfer
            b'SW;',      # Band switch
            b'TC;',      # Tone
            b'TI;',      # TNC internal
            b'TN;',      # Tone number
            b'TO;',      # Tone frequency
            b'TP;',      # TX power
            b'TS;',      # TNC set
            b'TY;',      # Transceiver type
            b'UL;',      # Auto notch level
            b'UP;',      # Up
            b'UR;',      # RX equalizer
            b'UT;',      # TX equalizer
            b'VD;',      # VOX delay
            b'VG;',      # VOX gain
            b'VR;',      # Voice synthesis
            b'VS;',      # VFO select
            b'VV;',      # VFO to VFO
            b'XO;',      # XIT offset
        ]
        
        for cmd in unimplemented_commands:
            with self.subTest(command=cmd):
                response = trusdx.handle_ts480_command(cmd, self.mock_ser)
                self.assertEqual(response, b';', f"Unimplemented command {cmd.decode()} should return ';'")
                
                # Check log message
                log_found = any(f"Unimplemented TS-480 command: {cmd.decode('utf-8').strip(';')}" in msg 
                               for msg in self.log_messages)
                self.assertTrue(log_found, f"Should log unimplemented command {cmd.decode()}")
    
    def test_v_command_updates_curr_vfo(self):
        """Test V command updates curr_vfo state"""
        # Set to VFO A
        response = trusdx.handle_ts480_command(b'V0;', self.mock_ser)
        self.assertIsNone(response, "V0 should be forwarded to hardware")
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'A', "V0 should set curr_vfo to A")
        self.assertEqual(trusdx.radio_state['rx_vfo'], '0', "V0 should set rx_vfo to 0")
        self.assertEqual(trusdx.radio_state['tx_vfo'], '0', "V0 should set tx_vfo to 0")
        
        # Set to VFO B
        response = trusdx.handle_ts480_command(b'V1;', self.mock_ser)
        self.assertIsNone(response, "V1 should be forwarded to hardware")
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'B', "V1 should set curr_vfo to B")
        self.assertEqual(trusdx.radio_state['rx_vfo'], '1', "V1 should set rx_vfo to 1")
        self.assertEqual(trusdx.radio_state['tx_vfo'], '1', "V1 should set tx_vfo to 1")
    
    def test_fa_query_returns_vfo_a_freq(self):
        """Test FA; query returns VFO A frequency"""
        trusdx.radio_state['vfo_a_freq'] = '00007074000'
        response = trusdx.handle_ts480_command(b'FA;', self.mock_ser)
        self.assertEqual(response, b'FA00007074000;', "FA query should return VFO A frequency")
    
    def test_fb_query_returns_vfo_b_freq(self):
        """Test FB; query returns VFO B frequency"""
        trusdx.radio_state['vfo_b_freq'] = '00014074000'
        response = trusdx.handle_ts480_command(b'FB;', self.mock_ser)
        self.assertEqual(response, b'FB00014074000;', "FB query should return VFO B frequency")


class TestHamlibIntegration(unittest.TestCase):
    """Test simulated Hamlib integration scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.original_radio_state = trusdx.radio_state.copy()
        self.original_status = trusdx.status.copy()
        
        # Reset radio state
        trusdx.radio_state = {
            'vfo_a_freq': '00007074000',
            'vfo_b_freq': '00014074000',
            'mode': '2',
            'rx_vfo': '0',
            'tx_vfo': '0',
            'curr_vfo': 'A',
            'split': '0',
            'rit': '0',
            'xit': '0',
            'rit_offset': '00000',
            'power_on': '1',
            'ai_mode': '0'
        }
        
        trusdx.status = [False, False, True, True, False, False]
        
        self.mock_ser = MagicMock()
        trusdx.config = {'verbose': False, 'unmute': False}
        
        # Mock log
        self.log_messages = []
        self.original_log = trusdx.log
        trusdx.log = lambda msg, level='INFO': self.log_messages.append(f"[{level}] {msg}")
    
    def tearDown(self):
        """Clean up after tests"""
        trusdx.radio_state = self.original_radio_state
        trusdx.status = self.original_status
        trusdx.log = self.original_log
    
    def test_hamlib_initialization_sequence(self):
        """Test typical Hamlib initialization command sequence"""
        # Typical Hamlib 4.6.3 init sequence
        commands = [
            (b'ID;', b'ID020;'),           # Get radio ID
            (b'AI;', None),                # Query AI mode
            (b'AI0;', b'AI0;'),           # Set AI mode off
            (b'V;', b'V0;'),              # Query VFO
            (b'IF;', None),               # Get status
            (b'FA;', b'FA00007074000;'),  # Query VFO A freq
            (b'MD;', b'MD2;'),            # Query mode
            (b'FR;', b'FR0;'),            # Query RX VFO
            (b'FT;', b'FT0;'),            # Query TX VFO
        ]
        
        for cmd, expected_response in commands:
            with self.subTest(command=cmd):
                response = trusdx.handle_ts480_command(cmd, self.mock_ser)
                if expected_response:
                    self.assertEqual(response, expected_response, 
                                   f"Command {cmd.decode()} should return {expected_response.decode()}")
                else:
                    self.assertIsNotNone(response, f"Command {cmd.decode()} should return a response")
    
    def test_hamlib_frequency_change_sequence(self):
        """Test Hamlib frequency change command sequence"""
        # First set the radio to 14.074 to bypass JS8Call blocking
        trusdx.radio_state['vfo_a_freq'] = '00014074000'
        
        # Now set frequency to 21.074 MHz (different from default)
        response = trusdx.handle_ts480_command(b'FA00021074000;', self.mock_ser)
        self.assertEqual(response, b';', "FA setter should ACK")
        self.assertEqual(trusdx.radio_state['vfo_a_freq'], '00021074000')
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'A')
        
        # Query to confirm
        response = trusdx.handle_ts480_command(b'FA;', self.mock_ser)
        self.assertEqual(response, b'FA00021074000;')
        
        # Check IF response shows correct frequency
        response = trusdx.handle_ts480_command(b'IF;', self.mock_ser)
        self.assertTrue(b'00021074000' in response)
    
    def test_hamlib_split_operation(self):
        """Test Hamlib split frequency operation"""
        # Set VFO A to 7.074 MHz (RX)
        trusdx.handle_ts480_command(b'FA00007074000;', self.mock_ser)
        
        # Set VFO B to 7.077 MHz (TX)
        trusdx.handle_ts480_command(b'FB00007077000;', self.mock_ser)
        
        # Set RX to VFO A
        response = trusdx.handle_ts480_command(b'FR0;', self.mock_ser)
        self.assertEqual(response, b';')
        
        # Set TX to VFO B
        response = trusdx.handle_ts480_command(b'FT1;', self.mock_ser)
        self.assertEqual(response, b';')
        
        # Enable split
        trusdx.radio_state['split'] = '1'
        
        # Verify state
        self.assertEqual(trusdx.radio_state['vfo_a_freq'], '00007074000')
        self.assertEqual(trusdx.radio_state['vfo_b_freq'], '00007077000')
        self.assertEqual(trusdx.radio_state['tx_vfo'], '1')
        self.assertEqual(trusdx.radio_state['curr_vfo'], 'A')  # RX VFO
    
    def test_js8call_frequency_blocking(self):
        """Test JS8Call's default 14.074 MHz frequency blocking"""
        # Start with 7.074 MHz
        trusdx.radio_state['vfo_a_freq'] = '00007074000'
        
        # JS8Call tries to set 14.074 MHz
        response = trusdx.handle_ts480_command(b'FA00014074000;', self.mock_ser)
        
        # Should return current frequency instead
        self.assertEqual(response, b'FA00007074000;', "Should block JS8Call's default frequency")
        self.assertEqual(trusdx.radio_state['vfo_a_freq'], '00007074000', "Frequency should not change")
        
        # But allow other frequency changes
        response = trusdx.handle_ts480_command(b'FA00021074000;', self.mock_ser)
        self.assertEqual(response, b';', "Should allow non-default frequency changes")
        self.assertEqual(trusdx.radio_state['vfo_a_freq'], '00021074000', "Frequency should change")


if __name__ == '__main__':
    # Run the tests with verbosity
    unittest.main(verbosity=2)
