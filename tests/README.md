# truSDX-AI CAT Emulation Tests

This directory contains comprehensive unit tests for the enhanced Kenwood TS-480 CAT emulation in truSDX-AI.

## Test Coverage

The test suite validates the following enhanced command coverage for 115200 baud firmware 2.00x:

### VFO Operations
- `FA` - VFO A frequency set/read
- `FB` - VFO B frequency set/read  
- `FR` - RX VFO selection
- `FT` - TX VFO selection
- `SV` - VFO A/B swap

### CW Operations
- `KS` - CW speed set/read
- `CW` - CW memory send (forwarded to radio)

### Filter Controls
- `FW` - Filter width set/read
- `SH` - High cut filter set/read
- `SL` - Low cut filter set/read

### S-meter Reading
- `SM` - S-meter signal strength reading

### RIT/XIT Operations
- `RT` - RIT on/off
- `XT` - XIT on/off
- `RD` - RIT frequency offset
- `XO` - XIT frequency offset
- `RC` - Clear RIT/XIT frequency

### Preamp/Attenuator
- `PA` - Preamp/attenuator control

### Core Commands
- `ID` - Radio identification
- `IF` - Status information (Hamlib critical)
- `AI` - Auto information mode
- `MD` - Operating mode
- `PS` - Power status
- `MC` - Memory channel
- `AG`/`RF`/`SQ` - Gain controls
- `EX` - Menu commands

## Running the Tests

### Prerequisites

```bash
# Install required dependencies
pip install pyserial

# For integration tests (optional)
sudo apt install hamlib-utils  # For rigctld
```

### Basic Test Run

```bash
# Run all tests
cd tests
python3 test_cat_emulation.py

# Run specific test class
python3 -m unittest test_cat_emulation.TestTS480CATEmulation

# Run specific test method
python3 -m unittest test_cat_emulation.TestTS480CATEmulation.test_vfo_frequency_operations
```

### Verbose Test Run

```bash
# Run with verbose output
python3 -m unittest -v test_cat_emulation
```

## Test Structure

### `TestTS480CATEmulation`
Main test class that validates individual CAT commands using pyserial loopback:

- **Serial Loopback**: Uses pseudo-terminals (pty) to create a bidirectional serial connection
- **State Validation**: Verifies that radio state is properly updated for set commands
- **Response Validation**: Confirms that read commands return properly formatted responses
- **Hamlib Compatibility**: Tests typical initialization sequences used by Hamlib

### `TestHamlibCompatibility`
Validates response formats against Hamlib rigctld expectations:

- **Format Validation**: Uses regex patterns to verify response structure
- **Length Validation**: Ensures critical commands like `IF` return exactly 40 characters
- **Protocol Compliance**: Validates against TS-480 CAT protocol specifications

### Integration Test
Optional integration test that uses actual Hamlib rigctld:

- **Real-world Validation**: Tests with actual rigctld process
- **End-to-end Testing**: Validates complete communication chain
- **Compatibility Verification**: Confirms rigctld recognizes the emulation

## Expected Output

```
=== truSDX-AI TS-480 CAT Emulation Test Suite ===
Testing enhanced command coverage for 115200 baud firmware 2.00x

test_ai_mode_operation (__main__.TestTS480CATEmulation) ... ok
test_basic_identification (__main__.TestTS480CATEmulation) ... ok
test_cw_operations (__main__.TestTS480CATEmulation) ... ok
test_filter_operations (__main__.TestTS480CATEmulation) ... ok
test_if_status_command (__main__.TestTS480CATEmulation) ... ok
...

=== Test Summary ===
Tests run: XX
Failures: 0
Errors: 0

=== Integration Test ===
Running integration test with rigctld...
✓ Integration test: rigctld recognized TS-480 emulation

✓ All tests passed!
```

## Troubleshooting

### Import Errors
If you get import errors for the main module:
```bash
# Ensure you're in the right directory
cd /path/to/trusdx-audio/Trusdx\ Linux/tests
export PYTHONPATH=..
python3 test_cat_emulation.py
```

### Serial Port Issues
If you get permission errors on Linux:
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Integration Test Failures
If integration tests fail:
```bash
# Install hamlib
sudo apt install hamlib-utils

# Verify rigctld is available
which rigctld

# Test manually
rigctld -m 2014 -r /dev/pts/X -s 115200 -t 4532
```

## Contributing

When adding new CAT commands:

1. Add the command handler to `handle_ts480_command()` in the main file
2. Add corresponding radio state variables if needed
3. Create test methods in `TestTS480CATEmulation`
4. Add format validation in `TestHamlibCompatibility`
5. Update this README with the new command coverage

## References

- [Kenwood TS-480 CAT Reference Manual](https://www.kenwood.com/i/products/info/amateur/ts_480/pdf/ts_480_pc.pdf)
- [Hamlib Documentation](https://hamlib.sourceforge.io/)
- [truSDX Hardware Documentation](https://github.com/threeme3/trusdx)
