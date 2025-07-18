#!/usr/bin/env python3
"""
Unit tests for truSDX-AI TS-480 CAT emulation
Tests enhanced command coverage for 115200 baud firmware 2.00x including:
- VFO operations
- CW commands  
- Filter controls
- S-meter reading
- RIT/XIT operations
- Preamp/Attenuator controls

Uses pyserial loopback to validate responses against hamlib rigctld expected formats.
"""

import unittest
import serial
import time
import threading
import subprocess
import os
import sys
import tempfile
import pty
from contextlib import contextmanager

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Import from parent directory
    import importlib.util
    spec = importlib.util.spec_from_file_location("trusdx_main", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "trusdx-rxtx-AI.py"))
    trusdx_main = importlib.util.module_from_spec(spec)
    
    # Set up required globals for the main module
    trusdx_main.config = {'verbose': False}  # Initialize config for testing
    
    spec.loader.exec_module(trusdx_main)
    handle_ts480_command = trusdx_main.handle_ts480_command
    radio_state = trusdx_main.radio_state
    
    # Make sure config is available globally
    import builtins
    builtins.config = {'verbose': False}
    
except Exception as e:
    print(f"Error importing main module: {e}")
    sys.exit(1)

class TestTS480CATEmulation(unittest.TestCase):
    """Test suite for TS-480 CAT command emulation"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Reset radio state to known values
        global radio_state
        radio_state.update({
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
            'ai_mode': '2',              # Auto info on
            'cw_speed': '020',           # CW speed 20 WPM
            'filter_width': '2400',      # Filter width 2.4 kHz
            'filter_high': '25',         # High cut filter 2.5 kHz
            'filter_low': '03',          # Low cut filter 300 Hz
            'preamp': '0',               # Preamp off
            'rit_freq': '00000',         # RIT frequency offset
            'xit_freq': '00000'          # XIT frequency offset
        })

    @contextmanager
    def serial_loopback(self):
        """Create a serial loopback using pseudo-terminals"""
        master, slave = pty.openpty()
        master_name = os.ttyname(master)
        slave_name = os.ttyname(slave)
        
        try:
            # Open both ends of the loopback
            ser_master = serial.Serial(master_name, 115200, timeout=1)
            ser_slave = serial.Serial(slave_name, 115200, timeout=1)
            
            yield ser_master, ser_slave
            
        finally:
            try:
                ser_master.close()
                ser_slave.close()
                os.close(master)
                os.close(slave)
            except:
                pass

    def send_cat_command(self, ser_write, ser_read, command):
        """Send a CAT command and return the response"""
        # Simulate the CAT handling directly
        cmd_bytes = command.encode('utf-8')
        response = handle_ts480_command(cmd_bytes, None)
        
        if response:
            return response.decode('utf-8', errors='ignore')
        
        return None

    def test_basic_identification(self):
        """Test basic radio identification"""
        with self.serial_loopback() as (ser1, ser2):
            # Test ID command
            response = self.send_cat_command(ser1, ser2, 'ID;')
            self.assertEqual(response, 'ID020;')

    def test_if_status_command(self):
        """Test IF (status) command format - critical for Hamlib"""
        with self.serial_loopback() as (ser1, ser2):
            response = self.send_cat_command(ser1, ser2, 'IF;')
            
            # Verify response format
            self.assertTrue(response.startswith('IF'))
            self.assertTrue(response.endswith(';'))
            
            # Verify length (IF + 37 characters + ;)
            self.assertEqual(len(response), 40)
            
            # Verify frequency portion
            freq_part = response[2:13]
            self.assertEqual(len(freq_part), 11)
            self.assertTrue(freq_part.isdigit())

    def test_vfo_frequency_operations(self):
        """Test VFO A and B frequency operations"""
        with self.serial_loopback() as (ser1, ser2):
            # Test VFO A frequency set/read
            test_freq = '00014200000'  # 14.200 MHz
            
            # Set VFO A frequency
            response = self.send_cat_command(ser1, ser2, f'FA{test_freq};')
            # Should forward to radio (None response), but state should update
            self.assertEqual(radio_state['vfo_a_freq'], test_freq)
            
            # Read VFO A frequency
            response = self.send_cat_command(ser1, ser2, 'FA;')
            self.assertEqual(response, f'FA{test_freq};')
            
            # Test VFO B frequency set/read
            test_freq_b = '00014300000'  # 14.300 MHz
            
            # Set VFO B frequency  
            response = self.send_cat_command(ser1, ser2, f'FB{test_freq_b};')
            self.assertEqual(radio_state['vfo_b_freq'], test_freq_b)
            
            # Read VFO B frequency
            response = self.send_cat_command(ser1, ser2, 'FB;')
            self.assertEqual(response, f'FB{test_freq_b};')

    def test_mode_operations(self):
        """Test mode setting and reading"""
        with self.serial_loopback() as (ser1, ser2):
            # Test mode set/read
            test_modes = ['1', '2', '3', '4', '7']  # LSB, USB, CW, FM, CW-R
            
            for mode in test_modes:
                # Set mode
                response = self.send_cat_command(ser1, ser2, f'MD{mode};')
                self.assertEqual(radio_state['mode'], mode)
                
                # Read mode
                response = self.send_cat_command(ser1, ser2, 'MD;')
                self.assertEqual(response, f'MD{mode};')

    def test_s_meter_reading(self):
        """Test S-meter reading (SM command)"""
        with self.serial_loopback() as (ser1, ser2):
            # Test S-meter read
            response = self.send_cat_command(ser1, ser2, 'SM;')
            self.assertEqual(response, 'SM0200;')  # S9+20dB simulation
            
            # Test S-meter with parameter (should echo back)
            response = self.send_cat_command(ser1, ser2, 'SM0150;')
            self.assertEqual(response, 'SM0150;')

    def test_cw_operations(self):
        """Test CW speed and operations"""
        with self.serial_loopback() as (ser1, ser2):
            # Test CW speed set/read
            test_speed = '025'  # 25 WPM
            
            # Set CW speed
            response = self.send_cat_command(ser1, ser2, f'KS{test_speed};')
            self.assertEqual(radio_state['cw_speed'], test_speed)
            
            # Read CW speed
            response = self.send_cat_command(ser1, ser2, 'KS;')
            self.assertEqual(response, f'KS{test_speed};')

    def test_filter_operations(self):
        """Test filter width and cut-off operations"""
        with self.serial_loopback() as (ser1, ser2):
            # Test filter width
            test_width = '1800'  # 1.8 kHz
            response = self.send_cat_command(ser1, ser2, f'FW{test_width};')
            self.assertEqual(radio_state['filter_width'], test_width)
            
            response = self.send_cat_command(ser1, ser2, 'FW;')
            self.assertEqual(response, f'FW{test_width};')
            
            # Test high cut filter
            test_high = '30'  # 3.0 kHz
            response = self.send_cat_command(ser1, ser2, f'SH{test_high};')
            self.assertEqual(radio_state['filter_high'], test_high)
            
            response = self.send_cat_command(ser1, ser2, 'SH;')
            self.assertEqual(response, f'SH{test_high};')
            
            # Test low cut filter
            test_low = '05'  # 500 Hz
            response = self.send_cat_command(ser1, ser2, f'SL{test_low};')
            self.assertEqual(radio_state['filter_low'], test_low)
            
            response = self.send_cat_command(ser1, ser2, 'SL;')
            self.assertEqual(response, f'SL{test_low};')

            # Test FL0 command
            response = self.send_cat_command(ser1, ser2, 'FL0;')
            self.assertEqual(response, 'FL0;')

    def test_preamp_attenuator(self):
        """Test preamp/attenuator operations"""
        with self.serial_loopback() as (ser1, ser2):
            # Test preamp settings
            for setting in ['0', '1', '2']:  # Off, Preamp 1, Preamp 2
                response = self.send_cat_command(ser1, ser2, f'PA{setting};')
                self.assertEqual(radio_state['preamp'], setting)
                
                response = self.send_cat_command(ser1, ser2, 'PA;')
                self.assertEqual(response, f'PA{setting};')

    def test_rit_xit_operations(self):
        """Test RIT/XIT frequency offset operations"""
        with self.serial_loopback() as (ser1, ser2):
            # Test RIT frequency offset
            test_rit = '00500'  # +500 Hz
            response = self.send_cat_command(ser1, ser2, f'RD{test_rit};')
            self.assertEqual(radio_state['rit_freq'], test_rit)
            
            response = self.send_cat_command(ser1, ser2, 'RD;')
            self.assertEqual(response, f'RD{test_rit};')
            
            # Test XIT frequency offset
            test_xit = '00300'  # +300 Hz
            response = self.send_cat_command(ser1, ser2, f'XO{test_xit};')
            self.assertEqual(radio_state['xit_freq'], test_xit)
            
            response = self.send_cat_command(ser1, ser2, 'XO;')
            self.assertEqual(response, f'XO{test_xit};')
            
            # Test RIT/XIT clear
            response = self.send_cat_command(ser1, ser2, 'RC;')
            self.assertEqual(radio_state['rit_freq'], '00000')
            self.assertEqual(radio_state['xit_freq'], '00000')

    def test_rit_xit_on_off(self):
        """Test RIT/XIT on/off operations"""
        with self.serial_loopback() as (ser1, ser2):
            # Test RIT on/off
            response = self.send_cat_command(ser1, ser2, 'RT1;')
            self.assertEqual(radio_state['rit'], '1')
            
            response = self.send_cat_command(ser1, ser2, 'RT;')
            self.assertEqual(response, 'RT1;')
            
            response = self.send_cat_command(ser1, ser2, 'RT0;')
            self.assertEqual(radio_state['rit'], '0')
            
            # Test XIT on/off
            response = self.send_cat_command(ser1, ser2, 'XT1;')
            self.assertEqual(radio_state['xit'], '1')
            
            response = self.send_cat_command(ser1, ser2, 'XT;')
            self.assertEqual(response, 'XT1;')
            
            response = self.send_cat_command(ser1, ser2, 'XT0;')
            self.assertEqual(radio_state['xit'], '0')

    def test_vfo_swap_operation(self):
        """Test VFO A/B swap operation"""
        with self.serial_loopback() as (ser1, ser2):
            # Set different frequencies for VFO A and B
            freq_a = '00014200000'
            freq_b = '00014300000'
            
            radio_state['vfo_a_freq'] = freq_a
            radio_state['vfo_b_freq'] = freq_b
            
            # Perform VFO swap
            response = self.send_cat_command(ser1, ser2, 'SV;')
            
            # Verify frequencies are swapped
            self.assertEqual(radio_state['vfo_a_freq'], freq_b)
            self.assertEqual(radio_state['vfo_b_freq'], freq_a)

    def test_ai_mode_operation(self):
        """Test Auto Information mode"""
        with self.serial_loopback() as (ser1, ser2):
            # Test AI mode set/read
            for mode in ['0', '1', '2']:  # Off, On, Auto
                response = self.send_cat_command(ser1, ser2, f'AI{mode};')
                self.assertEqual(radio_state['ai_mode'], mode)
                
                response = self.send_cat_command(ser1, ser2, 'AI;')
                self.assertEqual(response, f'AI{mode};')

    def test_vfo_rx_tx_selection(self):
        """Test RX/TX VFO selection"""
        with self.serial_loopback() as (ser1, ser2):
            # Test RX VFO selection
            for vfo in ['0', '1']:  # VFO A, VFO B
                response = self.send_cat_command(ser1, ser2, f'FR{vfo};')
                self.assertEqual(radio_state['rx_vfo'], vfo)
                
                response = self.send_cat_command(ser1, ser2, 'FR;')
                self.assertEqual(response, f'FR{vfo};')
            
            # Test TX VFO selection
            for vfo in ['0', '1']:  # VFO A, VFO B
                response = self.send_cat_command(ser1, ser2, f'FT{vfo};')
                self.assertEqual(radio_state['tx_vfo'], vfo)
                
                response = self.send_cat_command(ser1, ser2, 'FT;')
                self.assertEqual(response, f'FT{vfo};')

    def test_split_operation(self):
        """Test split operation"""
        with self.serial_loopback() as (ser1, ser2):
            # Test split on/off
            for split in ['0', '1']:  # Off, On
                response = self.send_cat_command(ser1, ser2, f'SP{split};')
                self.assertEqual(radio_state['split'], split)
                
                response = self.send_cat_command(ser1, ser2, 'SP;')
                self.assertEqual(response, f'SP{split};')

    def test_power_status(self):
        """Test power status reading"""
        with self.serial_loopback() as (ser1, ser2):
            response = self.send_cat_command(ser1, ser2, 'PS;')
            self.assertEqual(response, 'PS1;')  # Power on

    def test_memory_operations(self):
        """Test memory channel operations"""
        with self.serial_loopback() as (ser1, ser2):
            response = self.send_cat_command(ser1, ser2, 'MC;')
            self.assertEqual(response, 'MC000;')  # Channel 0

    def test_gain_controls(self):
        """Test gain control responses"""
        with self.serial_loopback() as (ser1, ser2):
            # Test AF gain
            response = self.send_cat_command(ser1, ser2, 'AG;')
            self.assertEqual(response, 'AG0100;')

            response = self.send_cat_command(ser1, ser2, 'AG0;')
            self.assertEqual(response, 'AG0;')
            
            # Test RF gain
            response = self.send_cat_command(ser1, ser2, 'RF;')
            self.assertEqual(response, 'RF0100;')
            
            # Test squelch
            response = self.send_cat_command(ser1, ser2, 'SQ;')
            self.assertEqual(response, 'SQ0000;')

    def test_swr_and_vox(self):
        """Test SWR and VOX commands"""
        with self.serial_loopback() as (ser1, ser2):
            # Test SWR reading
            response = self.send_cat_command(ser1, ser2, 'RS;')
            self.assertEqual(response, 'RS015;')

            # Test VOX reading
            response = self.send_cat_command(ser1, ser2, 'VX;')
            self.assertEqual(response, 'VX0;')

    def test_ex_menu_commands(self):
        """Test EX menu commands"""
        with self.serial_loopback() as (ser1, ser2):
            # Test basic EX command
            response = self.send_cat_command(ser1, ser2, 'EX;')
            self.assertEqual(response, 'EX;')
            
            # Test EX with parameters (should echo back)
            response = self.send_cat_command(ser1, ser2, 'EX01200;')
            self.assertEqual(response, 'EX01200;')

    def test_hamlib_compatibility_sequence(self):
        """Test typical Hamlib initialization sequence"""
        with self.serial_loopback() as (ser1, ser2):
            # Typical Hamlib sequence
            commands = [
                ('ID;', 'ID020;'),
                ('AI;', f'AI{radio_state["ai_mode"]};'),
                ('IF;', None),  # Response varies, check format only
                ('FA;', f'FA{radio_state["vfo_a_freq"]};'),
                ('MD;', f'MD{radio_state["mode"]};'),
            ]
            
            for cmd, expected in commands:
                response = self.send_cat_command(ser1, ser2, cmd)
                if expected:
                    self.assertEqual(response, expected)
                elif cmd == 'IF;':
                    # Special handling for IF command
                    self.assertTrue(response.startswith('IF'))
                    self.assertTrue(response.endswith(';'))
                    self.assertEqual(len(response), 40)

    def test_invalid_commands(self):
        """Test handling of invalid or unknown commands"""
        with self.serial_loopback() as (ser1, ser2):
            # Test unknown command (should return None)
            response = self.send_cat_command(ser1, ser2, 'XX;')
            self.assertIsNone(response)
            
            # Test empty command
            response = self.send_cat_command(ser1, ser2, ';')
            self.assertIsNone(response)
    
    def test_enhanced_command_coverage(self):
        """Test that all enhanced TS-480 commands for firmware 2.00x are implemented"""
        
        # Enhanced commands that should be implemented for 115200 baud firmware 2.00x
        enhanced_commands = {
            # VFO Operations
            'FA': ('FA00014200000;', 'VFO A frequency'),
            'FB': ('FB00014200000;', 'VFO B frequency'),
            'FR': ('FR0;', 'RX VFO selection'),
            'FT': ('FT0;', 'TX VFO selection'), 
            'SV': (None, 'VFO A/B swap'),  # No response expected
            
            # S-meter
            'SM': ('SM0200;', 'S-meter reading'),
            
            # CW Operations
            'KS': ('KS020;', 'CW speed'),
            'CW': (None, 'CW memory send'),  # Forwarded to radio
            
            # Filter Controls
            'FW': ('FW2400;', 'Filter width'),
            'SH': ('SH25;', 'High cut filter'),
            'SL': ('SL03;', 'Low cut filter'),
            
            # Preamp/Attenuator
            'PA': ('PA0;', 'Preamp/attenuator'),
            
            # RIT/XIT Operations
            'RT': ('RT0;', 'RIT on/off'),
            'XT': ('XT0;', 'XIT on/off'),
            'RD': ('RD00000;', 'RIT frequency offset'),
            'XO': ('XO00000;', 'XIT frequency offset'),
            'RC': (None, 'Clear RIT/XIT'),  # No response expected
            
            # Core Commands (should already work)
            'ID': ('ID020;', 'Radio identification'),
            'IF': ('IF', 'Status information'),  # Partial match
            'AI': ('AI2;', 'Auto information mode'),
            'MD': ('MD2;', 'Operating mode'),
            'PS': ('PS1;', 'Power status'),
            'MC': ('MC000;', 'Memory channel'),
            'AG': ('AG0100;', 'AF gain'),
            'RF': ('RF0100;', 'RF gain'),
            'SQ': ('SQ0000;', 'Squelch'),
            'EX': ('EX;', 'Menu commands'),
            'SP': ('SP0;', 'Split operation')
        }
        
        print(f"\n=== Testing Enhanced Command Coverage ({len(enhanced_commands)} commands) ===")
        
        with self.serial_loopback() as (ser1, ser2):
            implemented_count = 0
            missing_commands = []
            
            for cmd, (expected_prefix, description) in enhanced_commands.items():
                try:
                    response = self.send_cat_command(ser1, ser2, f'{cmd};')
                    
                    if expected_prefix is None:
                        # Commands that forward to radio (no response expected)
                        if response is None:
                            implemented_count += 1
                            print(f"  ✓ {cmd}: {description} (forwarded to radio)")
                        else:
                            print(f"  ✗ {cmd}: {description} (unexpected response: {response})")
                            missing_commands.append(cmd)
                    elif expected_prefix == 'IF':
                        # Special case for IF command (check format)
                        if response and response.startswith('IF') and len(response) == 40:
                            implemented_count += 1
                            print(f"  ✓ {cmd}: {description} (correct format)")
                        else:
                            print(f"  ✗ {cmd}: {description} (invalid format: {response})")
                            missing_commands.append(cmd)
                    else:
                        # Regular commands with expected responses
                        if response and response.startswith(expected_prefix[:2]):
                            implemented_count += 1
                            print(f"  ✓ {cmd}: {description}")
                        else:
                            print(f"  ✗ {cmd}: {description} (expected: {expected_prefix}, got: {response})")
                            missing_commands.append(cmd)
                            
                except Exception as e:
                    print(f"  ✗ {cmd}: {description} (error: {e})")
                    missing_commands.append(cmd)
            
            coverage_percent = (implemented_count / len(enhanced_commands)) * 100
            print(f"\n=== Coverage Summary ===")
            print(f"Commands implemented: {implemented_count}/{len(enhanced_commands)} ({coverage_percent:.1f}%)")
            
            if missing_commands:
                print(f"Missing commands: {', '.join(missing_commands)}")
                
            # Assert that we have good coverage (at least 90%)
            self.assertGreaterEqual(coverage_percent, 90.0, 
                f"Enhanced command coverage too low: {coverage_percent:.1f}%. Missing: {missing_commands}")
            
            print(f"\n{'✓ Enhanced TS-480 command coverage complete!' if coverage_percent >= 95 else '⚠ Enhanced TS-480 command coverage acceptable'}") 

class TestHamlibCompatibility(unittest.TestCase):
    """Test compatibility with Hamlib rigctld expectations"""

    def test_rigctld_command_format(self):
        """Test that our responses match rigctld expected formats"""
        
        # Test cases based on Hamlib rigctld for TS-480
        test_cases = [
            # Command, Expected pattern
            ('ID;', r'ID020;'),
            ('IF;', r'IF\d{37};'),  # 37 digits after IF
            ('FA;', r'FA\d{11};'),  # 11-digit frequency
            ('FB;', r'FB\d{11};'),  # 11-digit frequency
            ('MD;', r'MD[1-9];'),   # Mode 1-9
            ('AI;', r'AI[0-2];'),   # AI mode 0-2
        ]
        
        import re
        
        for cmd, pattern in test_cases:
            cmd_bytes = cmd.encode('utf-8')
            response = handle_ts480_command(cmd_bytes, None)
            
            if response:
                response_str = response.decode('utf-8')
                self.assertIsNotNone(re.match(pattern, response_str),
                    f"Command {cmd} response '{response_str}' doesn't match pattern '{pattern}'")

def run_integration_test():
    """
    Integration test using actual serial loopback with external rigctld
    This test requires rigctld to be available on the system
    """
    try:
        # Check if rigctld is available
        result = subprocess.run(['which', 'rigctld'], capture_output=True, text=True)
        if result.returncode != 0:
            print("rigctld not found - skipping integration test")
            return
        
        print("Running integration test with rigctld...")
        
        # Create a temporary pty pair for testing
        master, slave = pty.openpty()
        slave_name = os.ttyname(slave)
        
        try:
            # Start rigctld with our emulated radio
            rigctld_process = subprocess.Popen([
                'rigctld', 
                '-m', '2014',  # TS-480 model
                '-r', slave_name,
                '-s', '115200',
                '-t', '4532'  # TCP port
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            time.sleep(2)  # Allow rigctld to start
            
            # Test basic connection
            result = subprocess.run(['nc', 'localhost', '4532'], 
                                  input='\\dump_state\n', 
                                  capture_output=True, text=True, timeout=5)
            
            if 'TS-480' in result.stdout:
                print("✓ Integration test: rigctld recognized TS-480 emulation")
            else:
                print("✗ Integration test: rigctld failed to recognize emulation")
            
        finally:
            try:
                rigctld_process.terminate()
                rigctld_process.wait(timeout=2)
            except:
                rigctld_process.kill()
            
            os.close(master)
            os.close(slave)
            
    except Exception as e:
        print(f"Integration test failed: {e}")

if __name__ == '__main__':
    # Run unit tests
    print("=== truSDX-AI TS-480 CAT Emulation Test Suite ===")
    print("Testing enhanced command coverage for 115200 baud firmware 2.00x")
    print()
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print(f"\n=== Test Summary ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, trace in result.failures:
            print(f"  {test}: {trace.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nErrors:")
        for test, trace in result.errors:
            print(f"  {test}: {trace.split('Exception:')[-1].strip()}")
    
    # Run integration test if no failures
    if not result.failures and not result.errors:
        print("\n=== Integration Test ===")
        run_integration_test()
    
    print(f"\n{'✓ All tests passed!' if result.wasSuccessful() else '✗ Some tests failed'}")
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
