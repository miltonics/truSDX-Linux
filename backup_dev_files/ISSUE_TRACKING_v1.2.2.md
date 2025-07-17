# Issue Tracking List - TruSDX-AI v1.2.2-refactor

**Project**: TruSDX-AI Driver  
**Version**: 1.2.2-refactor  
**Date**: 2025-07-09  

## Issue Categories

### 🚀 HIGH PRIORITY ISSUES

#### ISSUE-001: VU Meter Real-time Implementation
**Status**: 🔴 Not Started  
**Priority**: High  
**Category**: Feature Enhancement  
**Estimated Effort**: 4-6 hours  

**Description**: Implement real-time VU meter display for audio level monitoring during transmission.

**Current State**: 
- Basic audio handling exists in `play_receive_audio()` function
- No visual feedback for audio levels
- Framework exists but needs implementation

**Required Changes**:
1. **File**: `trusdx-txrx-AI.py`
2. **Functions to Modify**:
   - `transmit_audio_via_serial()` (lines 923-961) - Add level calculation
   - `refresh_header_only()` (lines 176-213) - Add VU meter display
   - `handle_vox()` (lines 784-796) - Add level detection
3. **New Functions Needed**:
   - `calculate_audio_level(samples)` - Calculate RMS/peak levels
   - `draw_vu_meter(level)` - ASCII art VU meter
   - `update_vu_display(level)` - Update display in real-time

**Acceptance Criteria**:
- [ ] Real-time audio level display during TX
- [ ] ASCII art VU meter in header
- [ ] Peak hold functionality
- [ ] Configurable update rate
- [ ] No performance impact on audio processing

**Code Locations**:
- Line 930: Insert level calculation in TX audio loop
- Line 200: Add VU meter to header display
- Line 790: Enhance VOX with level detection

---

#### ISSUE-002: Enhanced CAT Command Support
**Status**: 🔴 Not Started  
**Priority**: High  
**Category**: Compatibility  
**Estimated Effort**: 6-8 hours  

**Description**: Expand CAT command support for better Hamlib compatibility and additional radio software.

**Current State**:
- Basic TS-480 emulation implemented
- 25+ commands supported
- Some commands missing or incomplete

**Required Changes**:
1. **File**: `trusdx-txrx-AI.py`
2. **Functions to Modify**:
   - `handle_ts480_command()` (lines 374-634) - Add missing commands
   - `TS480_COMMANDS` dictionary (lines 95-126) - Expand command list
3. **New Commands to Add**:
   - `BC` - Beat Cancel
   - `CN` - CTCSS Tone
   - `CT` - CTCSS Tone Frequency
   - `FW` - Filter Width
   - `GT` - AGC Time Constant
   - `KS` - Keying Speed
   - `LK` - Lock Status
   - `MF` - Menu Function
   - `MR` - Memory Read
   - `PF` - Speech Processor
   - `PR` - Speech Processor Level
   - `QR` - Quick Memory

**Acceptance Criteria**:
- [ ] All missing TS-480 commands implemented
- [ ] Proper command validation and error responses
- [ ] Full Hamlib rigctl compatibility
- [ ] Support for additional radio models (FT-991A, IC-7300)
- [ ] Comprehensive command testing

**Code Locations**:
- Lines 95-126: Expand TS480_COMMANDS dictionary
- Lines 374-634: Add command handlers
- Lines 624-634: Improve error handling

---

#### ISSUE-003: Improved Error Handling and Recovery
**Status**: 🔴 Not Started  
**Priority**: High  
**Category**: Reliability  
**Estimated Effort**: 4-5 hours  

**Description**: Implement comprehensive error handling with user-friendly messages and recovery suggestions.

**Current State**:
- Basic error logging with `log()` function
- Some try-catch blocks but inconsistent
- Limited user guidance on errors

**Required Changes**:
1. **File**: `trusdx-txrx-AI.py`
2. **Functions to Modify**:
   - `log()` (lines 135-155) - Add error categories and colors
   - `run()` (lines 1378-1716) - Improve exception handling
   - `safe_reconnect()` (lines 1118-1308) - Better error recovery
3. **New Functions Needed**:
   - `handle_error(error_type, message, suggestions)` - Centralized error handling
   - `suggest_recovery(error_code)` - User-friendly recovery suggestions
   - `validate_system_state()` - System health checks

**Acceptance Criteria**:
- [ ] Categorized error messages with color coding
- [ ] User-friendly error descriptions
- [ ] Automatic recovery suggestions
- [ ] Error code system for troubleshooting
- [ ] Comprehensive error logging

**Code Locations**:
- Lines 135-155: Enhance log() function
- Lines 1687-1689: Improve main exception handling
- Lines 1757-1804: Add recovery suggestions

---

### 🔶 MEDIUM PRIORITY ISSUES

#### ISSUE-004: Header Display Enhancements
**Status**: 🔴 Not Started  
**Priority**: Medium  
**Category**: User Interface  
**Estimated Effort**: 3-4 hours  

**Description**: Enhance header display with real-time frequency, mode, and status information.

**Current State**:
- Basic header with static information
- No real-time updates except power status
- Limited connection information

**Required Changes**:
1. **File**: `trusdx-txrx-AI.py`
2. **Functions to Modify**:
   - `show_persistent_header()` (lines 160-175) - Add dynamic fields
   - `refresh_header_only()` (lines 176-213) - Real-time updates
3. **New Information to Display**:
   - Current frequency (from `radio_state['vfo_a_freq']`)
   - Operating mode (from `radio_state['mode']`)
   - TX/RX status with colored indicators
   - Connection quality/stability
   - Data rate and buffer status

**Acceptance Criteria**:
- [ ] Real-time frequency display
- [ ] Mode indication (USB, LSB, CW, etc.)
- [ ] TX/RX status with colors
- [ ] Connection quality indicator
- [ ] Minimal performance impact

**Code Locations**:
- Lines 166-171: Add frequency and mode display
- Lines 194-201: Add status indicators
- Lines 888-900: Trigger updates on frequency changes

---

#### ISSUE-005: Power Monitor Optimizations
**Status**: 🔴 Not Started  
**Priority**: Medium  
**Category**: Performance  
**Estimated Effort**: 2-3 hours  

**Description**: Optimize power monitoring for better responsiveness and accuracy.

**Current State**:
- 5-second polling interval
- Basic 0W detection
- No power history or trending

**Required Changes**:
1. **File**: `trusdx-txrx-AI.py`
2. **Functions to Modify**:
   - `poll_power()` (lines 962-1061) - Reduce interval and add trending
3. **Constants to Modify**:
   - `POWER_POLL_INTERVAL` (line 90) - Reduce from 5.0 to 2.0 seconds
4. **New Features**:
   - Power trend analysis
   - Average power calculation
   - Power history buffer

**Acceptance Criteria**:
- [ ] Faster power polling (2-second interval)
- [ ] Power trend analysis
- [ ] Improved 0W detection accuracy
- [ ] Power history tracking
- [ ] Better reconnection logic

**Code Locations**:
- Line 90: Reduce POWER_POLL_INTERVAL
- Lines 983-1051: Add trend analysis
- Lines 1014-1032: Improve 0W detection

---

#### ISSUE-006: Configuration Management System
**Status**: 🔴 Not Started  
**Priority**: Medium  
**Category**: Usability  
**Estimated Effort**: 4-5 hours  

**Description**: Implement comprehensive configuration management with validation and migration.

**Current State**:
- Basic JSON configuration file
- Limited options
- No validation or migration

**Required Changes**:
1. **File**: `trusdx-txrx-AI.py`
2. **Functions to Modify**:
   - `load_config()` (lines 245-253) - Add validation
   - `save_config()` (lines 255-262) - Add backup/migration
3. **New Functions Needed**:
   - `validate_config(config)` - Configuration validation
   - `migrate_config(old_config)` - Version migration
   - `reset_config()` - Factory reset

**Acceptance Criteria**:
- [ ] Configuration validation
- [ ] Automatic migration between versions
- [ ] Default configuration reset
- [ ] Configuration backup
- [ ] Runtime configuration changes

**Code Locations**:
- Lines 245-253: Add validation to load_config()
- Lines 255-262: Add backup to save_config()
- Lines 129-133: Expand PERSISTENT_PORTS

---

### 🔵 LOW PRIORITY ISSUES

#### ISSUE-007: Code Refactoring and Modularization
**Status**: 🔴 Not Started  
**Priority**: Low  
**Category**: Maintainability  
**Estimated Effort**: 8-10 hours  

**Description**: Refactor monolithic code into modular components for better maintainability.

**Current State**:
- Single 1824-line file
- Mixed responsibilities
- Difficult to test individual components

**Required Changes**:
1. **Create New Files**:
   - `src/cat_handler.py` - CAT command processing
   - `src/audio_processor.py` - Audio handling
   - `src/connection_manager.py` - Connection monitoring
   - `src/power_monitor.py` - Power monitoring
   - `src/ui_manager.py` - Display and UI
2. **Modify**: `trusdx-txrx-AI.py` - Keep only main loop and initialization

**Acceptance Criteria**:
- [ ] Separate modules for each major function
- [ ] Clear interfaces between modules
- [ ] Improved testability
- [ ] Backward compatibility maintained
- [ ] No functionality loss

---

#### ISSUE-008: Comprehensive Test Suite
**Status**: 🔴 Not Started  
**Priority**: Low  
**Category**: Quality Assurance  
**Estimated Effort**: 6-8 hours  

**Description**: Implement comprehensive test suite for all major functions.

**Current State**:
- Basic smoke tests in setup.sh
- No unit tests
- No integration tests

**Required Changes**:
1. **Create Test Files**:
   - `tests/test_cat_commands.py` - CAT command testing
   - `tests/test_audio_processing.py` - Audio function testing
   - `tests/test_power_monitoring.py` - Power monitoring tests
   - `tests/test_connection_manager.py` - Connection testing
   - `tests/test_integration.py` - End-to-end testing

**Acceptance Criteria**:
- [ ] Unit tests for all major functions
- [ ] Integration tests for workflows
- [ ] Mock hardware for testing
- [ ] Automated test running
- [ ] Coverage reporting

---

## Implementation Schedule

### Week 1: Core Functionality
- **Day 1-2**: ISSUE-001 (VU Meter Implementation)
- **Day 3-4**: ISSUE-002 (Enhanced CAT Commands)
- **Day 5**: ISSUE-003 (Error Handling)

### Week 2: User Experience
- **Day 1-2**: ISSUE-004 (Header Enhancements)
- **Day 3**: ISSUE-005 (Power Monitor Optimizations)
- **Day 4-5**: ISSUE-006 (Configuration Management)

### Week 3: Quality & Maintenance
- **Day 1-3**: ISSUE-007 (Code Refactoring)
- **Day 4-5**: ISSUE-008 (Test Suite)

## Development Guidelines

### Code Standards
- Follow existing code style and conventions
- Add comprehensive comments for new functions
- Maintain backward compatibility
- Test all changes before committing

### Testing Requirements
- All new features must have unit tests
- Manual testing with actual hardware
- Verify compatibility with WSJT-X and JS8Call
- Check performance impact

### Documentation Requirements
- Update function docstrings
- Add usage examples
- Update README.md with new features
- Create troubleshooting guides

## Progress Tracking

Use the following format for progress updates:

```
ISSUE-XXX: [Status] - [Date] - [Progress Description]
- [x] Completed subtask
- [ ] Pending subtask
- [!] Blocked subtask
```

## Risk Mitigation

### High Risk Areas
1. **Audio Processing Changes** - Test thoroughly with different audio devices
2. **CAT Command Changes** - Verify compatibility with multiple clients
3. **Connection Management** - Ensure stable reconnection logic

### Mitigation Strategies
1. **Incremental Development** - Small, testable changes
2. **Backup Strategy** - Keep working versions
3. **Hardware Testing** - Test with actual TruSDX hardware
4. **User Feedback** - Get feedback from beta testers

---

*This issue tracking list serves as the development roadmap for v1.2.2-refactor.*
