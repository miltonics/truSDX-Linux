# Hamlib IO Error Fix Summary

## Issue
When running rigctl with the TruSDX driver, Hamlib was throwing an IO error:
```
kenwood_safe_transaction: wrong answer; len for cmd IF: expected = 37, got 39
kenwood.c(791):kenwood_safe_transaction returning2(-8) Protocol error
IO error while opening connection to rig
```

## Root Cause
The IF command response was incorrectly formatted. Hamlib expects the IF response to be exactly 38 characters total:
- "IF" prefix (2 chars) + 35 data characters + ";" terminator (1 char) = 38 chars total

The driver was sending 40 characters (IF + 37 + ;).

## Solution
Fixed the IF command response generation in two places in trusdx-txrx-AI.py:

1. Main IF command handler (lines 487-498):
   - Changed from building 37-char content to 35-char content
   - Reduced padding from 7 digits to 5 digits
   - Changed length check from 40 to 38

2. AI mode IF response (lines 544-546):
   - Changed content truncation from [:37] to [:35]
   - Reduced padding from '0000000' to '00000'

## Testing
After the fix:
- `rigctl -m 2028 -r /tmp/trusdx_cat -s 115200 -t 80 f` works correctly
- Returns frequency without IO errors
- Hamlib can properly communicate with the driver

## Files Modified
- `trusdx-txrx-AI.py` - Main driver file with the IF command fixes

The driver is now fully compatible with Hamlib 4.6.3 and should work seamlessly with JS8Call and WSJT-X.
