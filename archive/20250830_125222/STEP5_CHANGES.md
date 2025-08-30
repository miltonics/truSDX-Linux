# Step 5: Command Chain Modifications

## Summary
Modified shell scripts to replace `command &&` sequences with standalone commands, allowing the wrapper to capture failures properly instead of breaking out early. Critical operations using `||` for error handling were preserved.

## Files Modified

### 1. setup.sh
**Changes made:**
- Replaced inline `&&` in the `log_step()` helper function with a proper if/then/else block
- Replaced compound conditional `[[ -f "${ASRC_FILE}" ]] && grep -q "trusdx_tx" "${ASRC_FILE}" && grep -q "trusdx_rx" "${ASRC_FILE}"` with nested if statements to check each condition separately

**Preserved:**
- The `||` operators for error handling (e.g., `alsactl restore 2>/dev/null || true`)
- The subshell-based error capture pattern remains intact

### 2. trusdx-audio-connect.sh
**Changes made:**
- Replaced `[ -z "$app_output" ] && [ -z "$app_input" ]` with nested if statements in the `connect_pipewire()` function
- Replaced `[ -z "$sink_inputs" ] && [ -z "$source_outputs" ]` with nested if statements in the `connect_pulseaudio()` function

**Preserved:**
- The `||` operators for non-critical operations (e.g., `pw-link ... || true`)

### 3. test_tracking.sh
**Changes made:**
- Replaced inline `&&` in the `log_step()` helper function with a proper if/then/else block (same pattern as setup.sh)

## Rationale
The modification ensures that:
1. Individual command failures are captured by the wrapper/trap mechanism rather than causing the entire chain to exit prematurely
2. Each command's exit status can be properly logged and tracked
3. The script continues execution even when non-critical commands fail
4. Critical operations that MUST succeed still use `||` for immediate error handling

## Testing
After these changes, the scripts will:
- Continue execution even when individual commands in a sequence fail
- Properly log each step's success or failure status
- Allow the ERR trap to capture unexpected failures
- Maintain critical error handling where necessary
