Issue Baseline Dataset - README
================================

Created: 2025-07-10
Archive: issue_baseline.tgz

This archive contains debugging information collected during a test session with:
- truSDX-AI Python driver v1.2.2 running with verbose logging
- rigctl (Hamlib 4.6.3) test command: FA (get frequency)
- JS8Call 30-second session
- PulseAudio state capture before and after

Contents:
---------

1. PulseAudio State Files:
   - sources_before.txt: Audio sources before the test
   - sources_after.txt: Audio sources after the test
   - sinks_before.txt: Audio sinks before the test
   - sinks_after.txt: Audio sinks after the test

2. Python Driver Logs:
   - driver_verbose.log: Console output with verbose (-v) flag enabled
   - debug_driver.log: Detailed debug log file with CAT command processing

3. Hamlib Traces:
   - hamlib.trace.*: strace output files capturing system calls from rigctl
     Shows all file operations, reads, writes, and ioctl calls

4. JS8Call Session:
   - js8call_session.log: Output from 30-second JS8Call test session

Test Sequence:
--------------
1. Captured initial PulseAudio state
2. Started truSDX-AI driver with: python3 trusdx-txrx-AI.py -v --logfile debug_driver.log
3. Ran rigctl test: strace -o hamlib.trace -ff rigctl -m 2028 -r /tmp/trusdx_cat -vvvv FA
4. Started JS8Call for 30 seconds
5. Captured final PulseAudio state
6. Stopped all processes and archived logs

Key Observations:
-----------------
- The Python driver successfully established CAT port at /tmp/trusdx_cat
- rigctl connected and communicated with the driver
- CAT commands were processed (PS, IF, AI, ID, KS, FA)
- The driver emulated TS-480 responses successfully
- No PulseAudio source/sink changes detected during the session

This baseline can be used for:
- Regression testing after code changes
- Debugging CAT communication issues
- Analyzing system call patterns
- Verifying audio device stability
