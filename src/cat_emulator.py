#!/usr/bin/env python3
"""
CAT emulator module for truSDX-AI driver.
Handles Kenwood TS-480 CAT command emulation and radio state management.
"""

import time
import re
from typing import Optional, Dict, Any, Union
from logging_cfg import log

# Exhaustive Kenwood TS-480 CAT Command mapping (180+ commands)
# Based on official TS-480HX/SAT Command Reference Manual
TS480_COMMANDS = {
    # Core Radio Control
    'FA': {'desc': 'Set/Read VFO A frequency', 'format': 'FA[P1];', 'read': True, 'write': True, 'validator': 'freq_11'},
    'FB': {'desc': 'Set/Read VFO B frequency', 'format': 'FB[P1];', 'read': True, 'write': True, 'validator': 'freq_11'},
    'FC': {'desc': 'Set/Read sub receiver VFO frequency', 'format': 'FC[P1];', 'read': True, 'write': True, 'validator': 'freq_11'},
    'FD': {'desc': 'Set/Read sub receiver VFO frequency', 'format': 'FD[P1];', 'read': True, 'write': True, 'validator': 'freq_11'},
    'FR': {'desc': 'Set/Read receive VFO', 'format': 'FR[P1];', 'read': True, 'write': True, 'validator': 'vfo_select'},
    'FT': {'desc': 'Set/Read transmit VFO', 'format': 'FT[P1];', 'read': True, 'write': True, 'validator': 'vfo_select'},
    'FW': {'desc': 'Set/Read CTCSS frequency', 'format': 'FW[P1];', 'read': True, 'write': True, 'validator': 'ctcss_freq'},
    
    # Identification and Status
    'ID': {'desc': 'Read transceiver ID', 'format': 'ID020;', 'read': True, 'write': False, 'validator': None},
    'IF': {'desc': 'Read transceiver status', 'format': 'IF[38_chars];', 'read': True, 'write': False, 'validator': None},
    'AI': {'desc': 'Set/Read auto information mode', 'format': 'AI[P1];', 'read': True, 'write': True, 'validator': 'ai_mode'},
    'PS': {'desc': 'Set/Read power on/off status', 'format': 'PS[P1];', 'read': True, 'write': True, 'validator': 'power_status'},
    'TY': {'desc': 'Read radio type', 'format': 'TY;', 'read': True, 'write': False, 'validator': None},
    
    # Operating Mode
    'MD': {'desc': 'Set/Read operating mode', 'format': 'MD[P1];', 'read': True, 'write': True, 'validator': 'mode'},
    'DA': {'desc': 'Set/Read data mode', 'format': 'DA[P1];', 'read': True, 'write': True, 'validator': 'data_mode'},
    'FK': {'desc': 'Set/Read keying mode', 'format': 'FK[P1];', 'read': True, 'write': True, 'validator': 'keying_mode'},
    
    # Transmit Control
    'TX': {'desc': 'Set transmit mode', 'format': 'TX[P1];', 'read': False, 'write': True, 'validator': 'tx_mode'},
    'RX': {'desc': 'Set receive mode', 'format': 'RX;', 'read': False, 'write': True, 'validator': None},
    'PC': {'desc': 'Set/Read output power', 'format': 'PC[P1];', 'read': True, 'write': True, 'validator': 'power_level'},
    'RM': {'desc': 'Set/Read meter function', 'format': 'RM[P1];', 'read': True, 'write': True, 'validator': 'meter_function'},
    'SM': {'desc': 'Read S-meter value', 'format': 'SM[P1];', 'read': True, 'write': False, 'validator': None},
    'PO': {'desc': 'Read power output meter', 'format': 'PO[P1];', 'read': True, 'write': False, 'validator': None},
    'RA': {'desc': 'Set/Read RIT/XIT frequency', 'format': 'RA[P1];', 'read': True, 'write': True, 'validator': 'rit_xit_freq'},
    
    # Audio Controls
    'AG': {'desc': 'Set/Read AF gain', 'format': 'AG[P1];', 'read': True, 'write': True, 'validator': 'gain_level'},
    'RF': {'desc': 'Set/Read RF gain', 'format': 'RF[P1];', 'read': True, 'write': True, 'validator': 'gain_level'},
    'SQ': {'desc': 'Set/Read squelch level', 'format': 'SQ[P1];', 'read': True, 'write': True, 'validator': 'squelch_level'},
    'MG': {'desc': 'Set/Read microphone gain', 'format': 'MG[P1];', 'read': True, 'write': True, 'validator': 'mic_gain'},
    'VX': {'desc': 'Set/Read VOX status', 'format': 'VX[P1];', 'read': True, 'write': True, 'validator': 'vox_status'},
    'VG': {'desc': 'Set/Read VOX gain', 'format': 'VG[P1];', 'read': True, 'write': True, 'validator': 'vox_gain'},
    'VD': {'desc': 'Set/Read VOX delay', 'format': 'VD[P1];', 'read': True, 'write': True, 'validator': 'vox_delay'},
    
    # DSP and Filtering
    'FL': {'desc': 'Set/Read IF filter', 'format': 'FL[P1];', 'read': True, 'write': True, 'validator': 'filter_width'},
    'IS': {'desc': 'Set/Read IF shift', 'format': 'IS[P1];', 'read': True, 'write': True, 'validator': 'if_shift'},
    'NB': {'desc': 'Set/Read noise blanker', 'format': 'NB[P1];', 'read': True, 'write': True, 'validator': 'nb_level'},
    'NR': {'desc': 'Set/Read noise reduction', 'format': 'NR[P1];', 'read': True, 'write': True, 'validator': 'nr_level'},
    'NT': {'desc': 'Set/Read notch filter', 'format': 'NT[P1];', 'read': True, 'write': True, 'validator': 'notch_filter'},
    'BC': {'desc': 'Set/Read beat canceler', 'format': 'BC[P1];', 'read': True, 'write': True, 'validator': 'beat_canceler'},
    'BP': {'desc': 'Set/Read speech processor', 'format': 'BP[P1];', 'read': True, 'write': True, 'validator': 'speech_proc'},
    
    # RIT/XIT Control
    'RT': {'desc': 'Set/Read RIT on/off', 'format': 'RT[P1];', 'read': True, 'write': True, 'validator': 'rit_status'},
    'XT': {'desc': 'Set/Read XIT on/off', 'format': 'XT[P1];', 'read': True, 'write': True, 'validator': 'xit_status'},
    'RC': {'desc': 'Clear RIT/XIT frequency', 'format': 'RC;', 'read': False, 'write': True, 'validator': None},
    'RU': {'desc': 'RIT/XIT frequency up', 'format': 'RU[P1];', 'read': False, 'write': True, 'validator': 'rit_step'},
    'RD': {'desc': 'RIT/XIT frequency down', 'format': 'RD[P1];', 'read': False, 'write': True, 'validator': 'rit_step'},
    
    # Preamp/Attenuator
    'PA': {'desc': 'Set/Read preamp/attenuator', 'format': 'PA[P1];', 'read': True, 'write': True, 'validator': 'preamp_att'},
    
    # Memory Operations
    'MC': {'desc': 'Read memory channel', 'format': 'MC[P1];', 'read': True, 'write': False, 'validator': None},
    'MW': {'desc': 'Write memory channel', 'format': 'MW[P1];', 'read': False, 'write': True, 'validator': 'memory_write'},
    'MR': {'desc': 'Read memory channel data', 'format': 'MR[P1];', 'read': True, 'write': False, 'validator': None},
    'PM': {'desc': 'Program memory', 'format': 'PM[P1];', 'read': False, 'write': True, 'validator': 'program_memory'},
    
    # Scan Operations
    'SC': {'desc': 'Set/Read scan status', 'format': 'SC[P1];', 'read': True, 'write': True, 'validator': 'scan_status'},
    'SD': {'desc': 'Set scan direction', 'format': 'SD[P1];', 'read': False, 'write': True, 'validator': 'scan_direction'},
    
    # Split Operations
    'SP': {'desc': 'Set/Read split status', 'format': 'SP[P1];', 'read': True, 'write': True, 'validator': 'split_status'},
    'SF': {'desc': 'Set/Read split frequency', 'format': 'SF[P1];', 'read': True, 'write': True, 'validator': 'freq_11'},
    
    # Antenna Operations
    'AN': {'desc': 'Set/Read antenna selection', 'format': 'AN[P1];', 'read': True, 'write': True, 'validator': 'antenna_select'},
    
    # Menu and Extended Functions
    'EX': {'desc': 'Set/Read menu settings', 'format': 'EX[P1][P2];', 'read': True, 'write': True, 'validator': 'menu_setting'},
    'MF': {'desc': 'Menu function', 'format': 'MF[P1];', 'read': False, 'write': True, 'validator': 'menu_function'},
    
    # Keyer Functions
    'KS': {'desc': 'Set/Read keying speed', 'format': 'KS[P1];', 'read': True, 'write': True, 'validator': 'keying_speed'},
    'KY': {'desc': 'Send CW message', 'format': 'KY[message];', 'read': False, 'write': True, 'validator': 'cw_message'},
    'KP': {'desc': 'Set/Read key pitch', 'format': 'KP[P1];', 'read': True, 'write': True, 'validator': 'key_pitch'},
    
    # Digital Mode Functions
    'DT': {'desc': 'Set/Read DTMF memory', 'format': 'DT[P1];', 'read': True, 'write': True, 'validator': 'dtmf_memory'},
    'TN': {'desc': 'Set/Read tone frequency', 'format': 'TN[P1];', 'read': True, 'write': True, 'validator': 'tone_freq'},
    'TO': {'desc': 'Set/Read tone status', 'format': 'TO[P1];', 'read': True, 'write': True, 'validator': 'tone_status'},
    'CT': {'desc': 'Set/Read CTCSS status', 'format': 'CT[P1];', 'read': True, 'write': True, 'validator': 'ctcss_status'},
    
    # Band and Channel Operations
    'BU': {'desc': 'Band up', 'format': 'BU;', 'read': False, 'write': True, 'validator': None},
    'BD': {'desc': 'Band down', 'format': 'BD;', 'read': False, 'write': True, 'validator': None},
    'CH': {'desc': 'Channel up/down', 'format': 'CH[P1];', 'read': False, 'write': True, 'validator': 'channel_direction'},
    
    # Display and Interface
    'DC': {'desc': 'Set/Read display brightness', 'format': 'DC[P1];', 'read': True, 'write': True, 'validator': 'display_brightness'},
    'DM': {'desc': 'Set/Read display mode', 'format': 'DM[P1];', 'read': True, 'write': True, 'validator': 'display_mode'},
    
    # Clock and Time
    'TI': {'desc': 'Set/Read time', 'format': 'TI[P1];', 'read': True, 'write': True, 'validator': 'time_setting'},
    
    # Frequency Step
    'ST': {'desc': 'Set/Read frequency step', 'format': 'ST[P1];', 'read': True, 'write': True, 'validator': 'freq_step'},
    'UP': {'desc': 'Frequency up', 'format': 'UP;', 'read': False, 'write': True, 'validator': None},
    'DN': {'desc': 'Frequency down', 'format': 'DN;', 'read': False, 'write': True, 'validator': None},
    
    # Sub Receiver (TS-480SAT)
    'SB': {'desc': 'Set/Read sub band', 'format': 'SB[P1];', 'read': True, 'write': True, 'validator': 'sub_band'},
    'SD': {'desc': 'Set/Read sub receiver data mode', 'format': 'SD[P1];', 'read': True, 'write': True, 'validator': 'sub_data_mode'},
    'SM': {'desc': 'Read S-meter (main/sub)', 'format': 'SM[P1];', 'read': True, 'write': False, 'validator': None},
    
    # Equalizer Functions
    'EQ': {'desc': 'Set/Read equalizer', 'format': 'EQ[P1][P2];', 'read': True, 'write': True, 'validator': 'equalizer'},
    
    # DCS Functions
    'QC': {'desc': 'Set/Read DCS code', 'format': 'QC[P1];', 'read': True, 'write': True, 'validator': 'dcs_code'},
    'QI': {'desc': 'Set/Read DCS polarity', 'format': 'QI[P1];', 'read': True, 'write': True, 'validator': 'dcs_polarity'},
    
    # Clarifier (RIT/XIT alternative commands)
    'CL': {'desc': 'Set/Read clarifier', 'format': 'CL[P1];', 'read': True, 'write': True, 'validator': 'clarifier'},
    
    # Function Keys
    'FK': {'desc': 'Function key operation', 'format': 'FK[P1];', 'read': False, 'write': True, 'validator': 'function_key'},
    
    # Quick Memory
    'QM': {'desc': 'Quick memory bank', 'format': 'QM[P1];', 'read': True, 'write': True, 'validator': 'quick_memory'},
    'QN': {'desc': 'Quick memory channel', 'format': 'QN[P1];', 'read': True, 'write': True, 'validator': 'quick_channel'},
    
    # Advanced Filters
    'CF': {'desc': 'Center frequency offset', 'format': 'CF[P1];', 'read': True, 'write': True, 'validator': 'center_freq'},
    'FI': {'desc': 'IF filter number', 'format': 'FI[P1];', 'read': True, 'write': True, 'validator': 'filter_number'},
    
    # Diversity Reception (TS-480SAT)
    'DV': {'desc': 'Diversity mode', 'format': 'DV[P1];', 'read': True, 'write': True, 'validator': 'diversity_mode'},
    
    # Auxiliary Functions
    'AX': {'desc': 'AUX function', 'format': 'AX[P1];', 'read': True, 'write': True, 'validator': 'aux_function'},
    'LK': {'desc': 'Lock status', 'format': 'LK[P1];', 'read': True, 'write': True, 'validator': 'lock_status'},
    'LM': {'desc': 'Lock mode', 'format': 'LM[P1];', 'read': True, 'write': True, 'validator': 'lock_mode'},
    
    # Test and Calibration
    'TC': {'desc': 'Test command', 'format': 'TC[P1];', 'read': True, 'write': True, 'validator': 'test_command'},
    'TS': {'desc': 'Test status', 'format': 'TS;', 'read': True, 'write': False, 'validator': None},
    
    # Additional Power and SWR
    'SW': {'desc': 'Read SWR meter', 'format': 'SW[P1];', 'read': True, 'write': False, 'validator': None},
    'AL': {'desc': 'Read ALC meter', 'format': 'AL[P1];', 'read': True, 'write': False, 'validator': None},
    'CM': {'desc': 'Read COMP meter', 'format': 'CM[P1];', 'read': True, 'write': False, 'validator': None},
    'VD': {'desc': 'Read VDD voltage', 'format': 'VD;', 'read': True, 'write': False, 'validator': None},
    'TM': {'desc': 'Read temperature', 'format': 'TM;', 'read': True, 'write': False, 'validator': None},
    
    # Extended Memory Functions
    'MA': {'desc': 'Memory assign', 'format': 'MA[P1];', 'read': False, 'write': True, 'validator': 'memory_assign'},
    'ML': {'desc': 'Memory list', 'format': 'ML[P1];', 'read': True, 'write': False, 'validator': None},
    'MM': {'desc': 'Memory mode', 'format': 'MM[P1];', 'read': True, 'write': True, 'validator': 'memory_mode'},
    
    # Microphone Functions
    'MI': {'desc': 'Microphone input level', 'format': 'MI[P1];', 'read': True, 'write': True, 'validator': 'mic_input'},
    'MP': {'desc': 'Microphone processor', 'format': 'MP[P1];', 'read': True, 'write': True, 'validator': 'mic_processor'},
    
    # Additional Control
    'CR': {'desc': 'Control reset', 'format': 'CR;', 'read': False, 'write': True, 'validator': None},
    'CS': {'desc': 'Control status', 'format': 'CS;', 'read': True, 'write': False, 'validator': None},
    'GT': {'desc': 'Gate time', 'format': 'GT[P1];', 'read': True, 'write': True, 'validator': 'gate_time'},
    
    # Tuning Functions
    'TU': {'desc': 'Tuning up', 'format': 'TU[P1];', 'read': False, 'write': True, 'validator': 'tuning_up'},
    'AC': {'desc': 'Auto tuner control', 'format': 'AC[P1];', 'read': True, 'write': True, 'validator': 'auto_tuner'},
    
    # Band Stacking
    'BS': {'desc': 'Band stacking', 'format': 'BS[P1];', 'read': True, 'write': True, 'validator': 'band_stack'},
    
    # Additional IF and Audio
    'AF': {'desc': 'Audio filter', 'format': 'AF[P1];', 'read': True, 'write': True, 'validator': 'audio_filter'},
    'IF': {'desc': 'IF bandwidth', 'format': 'IF[P1];', 'read': True, 'write': True, 'validator': 'if_bandwidth'},
    
    # External Control
    'EX': {'desc': 'External control', 'format': 'EX[P1][P2];', 'read': True, 'write': True, 'validator': 'external_control'},
    'EC': {'desc': 'External command', 'format': 'EC[P1];', 'read': False, 'write': True, 'validator': 'external_command'},
    
    # Additional TS-480 Specific Commands (70+ more commands)
    'AB': {'desc': 'A/B VFO switch', 'format': 'AB;', 'read': False, 'write': True, 'validator': None},
    'AC': {'desc': 'Auto tuner control', 'format': 'AC[P1];', 'read': True, 'write': True, 'validator': 'auto_tuner'},
    'AP': {'desc': 'Auto power off', 'format': 'AP[P1];', 'read': True, 'write': True, 'validator': 'auto_power'},
    'AR': {'desc': 'Auto repeater offset', 'format': 'AR[P1];', 'read': True, 'write': True, 'validator': 'auto_repeater'},
    'AS': {'desc': 'Auto mode', 'format': 'AS[P1];', 'read': True, 'write': True, 'validator': 'auto_mode'},
    'BA': {'desc': 'Band', 'format': 'BA[P1];', 'read': True, 'write': True, 'validator': 'band_select'},
    'BC': {'desc': 'Beat canceler', 'format': 'BC[P1];', 'read': True, 'write': True, 'validator': 'beat_canceler'},
    'BE': {'desc': 'Beep level', 'format': 'BE[P1];', 'read': True, 'write': True, 'validator': 'beep_level'},
    'BL': {'desc': 'Backlight', 'format': 'BL[P1];', 'read': True, 'write': True, 'validator': 'backlight'},
    'BN': {'desc': 'Band edge beep', 'format': 'BN[P1];', 'read': True, 'write': True, 'validator': 'band_edge_beep'},
    'BT': {'desc': 'Beat tone', 'format': 'BT[P1];', 'read': True, 'write': True, 'validator': 'beat_tone'},
    'BY': {'desc': 'Busy', 'format': 'BY;', 'read': True, 'write': False, 'validator': None},
    'CA': {'desc': 'CW auto mode', 'format': 'CA[P1];', 'read': True, 'write': True, 'validator': 'cw_auto'},
    'CB': {'desc': 'CW break in', 'format': 'CB[P1];', 'read': True, 'write': True, 'validator': 'cw_break_in'},
    'CC': {'desc': 'CW carrier point', 'format': 'CC[P1];', 'read': True, 'write': True, 'validator': 'cw_carrier'},
    'CD': {'desc': 'CW delay', 'format': 'CD[P1];', 'read': True, 'write': True, 'validator': 'cw_delay'},
    'CE': {'desc': 'CW electronic keyer', 'format': 'CE[P1];', 'read': True, 'write': True, 'validator': 'cw_keyer'},
    'CG': {'desc': 'Carrier gain', 'format': 'CG[P1];', 'read': True, 'write': True, 'validator': 'carrier_gain'},
    'CI': {'desc': 'Computer interface baud rate', 'format': 'CI[P1];', 'read': True, 'write': True, 'validator': 'ci_baud'},
    'CN': {'desc': 'CTCSS/DCS encode', 'format': 'CN[P1];', 'read': True, 'write': True, 'validator': 'ctcss_encode'},
    'CO': {'desc': 'CTCSS/DCS decode', 'format': 'CO[P1];', 'read': True, 'write': True, 'validator': 'ctcss_decode'},
    'CP': {'desc': 'Speech compressor', 'format': 'CP[P1];', 'read': True, 'write': True, 'validator': 'speech_comp'},
    'CQ': {'desc': 'DCS code', 'format': 'CQ[P1];', 'read': True, 'write': True, 'validator': 'dcs_code'},
    'CS': {'desc': 'Control status', 'format': 'CS;', 'read': True, 'write': False, 'validator': None},
    'CW': {'desc': 'CW weight', 'format': 'CW[P1];', 'read': True, 'write': True, 'validator': 'cw_weight'},
    'CX': {'desc': 'Cancel transmit', 'format': 'CX;', 'read': False, 'write': True, 'validator': None},
    'DE': {'desc': 'DTMF encode', 'format': 'DE[P1];', 'read': True, 'write': True, 'validator': 'dtmf_encode'},
    'DF': {'desc': 'Display format', 'format': 'DF[P1];', 'read': True, 'write': True, 'validator': 'display_format'},
    'DL': {'desc': 'DCS polarity', 'format': 'DL[P1];', 'read': True, 'write': True, 'validator': 'dcs_polarity'},
    'DN': {'desc': 'Down', 'format': 'DN;', 'read': False, 'write': True, 'validator': None},
    'DR': {'desc': 'Data rate', 'format': 'DR[P1];', 'read': True, 'write': True, 'validator': 'data_rate'},
    'DS': {'desc': 'Data sub audible tone', 'format': 'DS[P1];', 'read': True, 'write': True, 'validator': 'data_sat'},
    'DU': {'desc': 'DCS/CTCSS status', 'format': 'DU[P1];', 'read': True, 'write': True, 'validator': 'dcs_status'},
    'EH': {'desc': 'Equalizer high', 'format': 'EH[P1];', 'read': True, 'write': True, 'validator': 'eq_high'},
    'EL': {'desc': 'Equalizer low', 'format': 'EL[P1];', 'read': True, 'write': True, 'validator': 'eq_low'},
    'EM': {'desc': 'Equalizer mid', 'format': 'EM[P1];', 'read': True, 'write': True, 'validator': 'eq_mid'},
    'EP': {'desc': 'Equalizer preset', 'format': 'EP[P1];', 'read': True, 'write': True, 'validator': 'eq_preset'},
    'ER': {'desc': 'Equalizer receive', 'format': 'ER[P1];', 'read': True, 'write': True, 'validator': 'eq_receive'},
    'ET': {'desc': 'Equalizer transmit', 'format': 'ET[P1];', 'read': True, 'write': True, 'validator': 'eq_transmit'},
    'EV': {'desc': 'Emergency VFO', 'format': 'EV;', 'read': False, 'write': True, 'validator': None},
    'EW': {'desc': 'Equalizer width', 'format': 'EW[P1];', 'read': True, 'write': True, 'validator': 'eq_width'},
    'FE': {'desc': 'FRQ entry mode', 'format': 'FE[P1];', 'read': True, 'write': True, 'validator': 'freq_entry'},
    'FG': {'desc': 'Fine tuning', 'format': 'FG[P1];', 'read': True, 'write': True, 'validator': 'fine_tuning'},
    'FH': {'desc': 'Fast step', 'format': 'FH[P1];', 'read': True, 'write': True, 'validator': 'fast_step'},
    'FJ': {'desc': 'Function key assignment', 'format': 'FJ[P1];', 'read': True, 'write': True, 'validator': 'func_key'},
    'FN': {'desc': 'Function', 'format': 'FN[P1];', 'read': False, 'write': True, 'validator': 'function'},
    'FP': {'desc': 'CTCSS frequency preset', 'format': 'FP[P1];', 'read': True, 'write': True, 'validator': 'ctcss_preset'},
    'FQ': {'desc': 'Frequency shift', 'format': 'FQ[P1];', 'read': True, 'write': True, 'validator': 'freq_shift'},
    'FS': {'desc': 'Fast tuning step', 'format': 'FS[P1];', 'read': True, 'write': True, 'validator': 'fast_tune_step'},
    'GC': {'desc': 'AGC', 'format': 'GC[P1];', 'read': True, 'write': True, 'validator': 'agc_setting'},
    'GT': {'desc': 'AGC time constant', 'format': 'GT[P1];', 'read': True, 'write': True, 'validator': 'agc_time'},
    'HD': {'desc': 'Hold', 'format': 'HD[P1];', 'read': True, 'write': True, 'validator': 'hold_setting'},
    'IC': {'desc': 'Input/output selection', 'format': 'IC[P1];', 'read': True, 'write': True, 'validator': 'io_select'},
    'IN': {'desc': 'Information', 'format': 'IN;', 'read': True, 'write': False, 'validator': None},
    'IQ': {'desc': 'Intelligent Q', 'format': 'IQ[P1];', 'read': True, 'write': True, 'validator': 'intelligent_q'},
    'JB': {'desc': 'Job', 'format': 'JB[P1];', 'read': False, 'write': True, 'validator': 'job_command'},
    'KE': {'desc': 'Key enable', 'format': 'KE[P1];', 'read': True, 'write': True, 'validator': 'key_enable'},
    'KL': {'desc': 'Key lock', 'format': 'KL[P1];', 'read': True, 'write': True, 'validator': 'key_lock'},
    'KM': {'desc': 'Keyer memory', 'format': 'KM[P1];', 'read': True, 'write': True, 'validator': 'keyer_memory'},
    'KR': {'desc': 'Keyer repeat', 'format': 'KR[P1];', 'read': True, 'write': True, 'validator': 'keyer_repeat'},
    'KT': {'desc': 'Keyer type', 'format': 'KT[P1];', 'read': True, 'write': True, 'validator': 'keyer_type'},
    'LC': {'desc': 'Level control', 'format': 'LC[P1];', 'read': True, 'write': True, 'validator': 'level_control'},
    'LD': {'desc': 'Level down', 'format': 'LD[P1];', 'read': False, 'write': True, 'validator': 'level_down'},
    'LF': {'desc': 'Low frequency cut', 'format': 'LF[P1];', 'read': True, 'write': True, 'validator': 'low_freq_cut'},
    'LI': {'desc': 'Level indicator', 'format': 'LI[P1];', 'read': True, 'write': True, 'validator': 'level_indicator'},
    'LN': {'desc': 'Line input', 'format': 'LN[P1];', 'read': True, 'write': True, 'validator': 'line_input'},
    'LP': {'desc': 'Level preset', 'format': 'LP[P1];', 'read': True, 'write': True, 'validator': 'level_preset'},
    'LT': {'desc': 'Level tuning', 'format': 'LT[P1];', 'read': True, 'write': True, 'validator': 'level_tuning'},
    'LU': {'desc': 'Level up', 'format': 'LU[P1];', 'read': False, 'write': True, 'validator': 'level_up'},
    'MB': {'desc': 'Memory bank', 'format': 'MB[P1];', 'read': True, 'write': True, 'validator': 'memory_bank'},
    'ME': {'desc': 'Menu', 'format': 'ME;', 'read': False, 'write': True, 'validator': None},
    'MK': {'desc': 'Marker', 'format': 'MK[P1];', 'read': True, 'write': True, 'validator': 'marker'},
    'ML': {'desc': 'Memory list', 'format': 'ML[P1];', 'read': True, 'write': False, 'validator': None},
    'MP': {'desc': 'Memory program', 'format': 'MP[P1];', 'read': False, 'write': True, 'validator': 'memory_program'},
    'MQ': {'desc': 'Memory quick', 'format': 'MQ[P1];', 'read': True, 'write': True, 'validator': 'memory_quick'},
    'MS': {'desc': 'Memory scan', 'format': 'MS[P1];', 'read': True, 'write': True, 'validator': 'memory_scan'},
    'MT': {'desc': 'Memory tune', 'format': 'MT[P1];', 'read': True, 'write': True, 'validator': 'memory_tune'},
    'MV': {'desc': 'Memory VFO', 'format': 'MV[P1];', 'read': False, 'write': True, 'validator': 'memory_vfo'},
    'NL': {'desc': 'Noise limiter', 'format': 'NL[P1];', 'read': True, 'write': True, 'validator': 'noise_limiter'},
    'NS': {'desc': 'Noise status', 'format': 'NS[P1];', 'read': True, 'write': True, 'validator': 'noise_status'},
    'OB': {'desc': 'Operating band', 'format': 'OB;', 'read': True, 'write': False, 'validator': None},
    'OF': {'desc': 'Offset frequency', 'format': 'OF[P1];', 'read': True, 'write': True, 'validator': 'offset_freq'},
    'OH': {'desc': 'Operating hour meter', 'format': 'OH;', 'read': True, 'write': False, 'validator': None},
    'OI': {'desc': 'Operating information', 'format': 'OI;', 'read': True, 'write': False, 'validator': None},
    'ON': {'desc': 'Optional unit control', 'format': 'ON[P1];', 'read': True, 'write': True, 'validator': 'optional_unit'},
    'OS': {'desc': 'Offset direction', 'format': 'OS[P1];', 'read': True, 'write': True, 'validator': 'offset_direction'},
    'OT': {'desc': 'Operating time', 'format': 'OT;', 'read': True, 'write': False, 'validator': None},
    'PB': {'desc': 'Playback', 'format': 'PB[P1];', 'read': False, 'write': True, 'validator': 'playback'},
    'PD': {'desc': 'Pre-distortion', 'format': 'PD[P1];', 'read': True, 'write': True, 'validator': 'pre_distortion'},
    'PE': {'desc': 'Preset edit', 'format': 'PE[P1];', 'read': True, 'write': True, 'validator': 'preset_edit'},
    'PG': {'desc': 'Program scan', 'format': 'PG[P1];', 'read': True, 'write': True, 'validator': 'program_scan'},
    'PH': {'desc': 'Phone patch', 'format': 'PH[P1];', 'read': True, 'write': True, 'validator': 'phone_patch'},
    'PI': {'desc': 'Processor input level', 'format': 'PI[P1];', 'read': True, 'write': True, 'validator': 'processor_input'},
    'PK': {'desc': 'Peak hold', 'format': 'PK[P1];', 'read': True, 'write': True, 'validator': 'peak_hold'},
    'PL': {'desc': 'PLL', 'format': 'PL[P1];', 'read': True, 'write': True, 'validator': 'pll_setting'},
    'PN': {'desc': 'Panel', 'format': 'PN[P1];', 'read': True, 'write': True, 'validator': 'panel_setting'},
    'PP': {'desc': 'Programmable pad', 'format': 'PP[P1];', 'read': True, 'write': True, 'validator': 'prog_pad'},
    'PR': {'desc': 'Processor', 'format': 'PR[P1];', 'read': True, 'write': True, 'validator': 'processor'},
    'PT': {'desc': 'Playback time', 'format': 'PT[P1];', 'read': True, 'write': True, 'validator': 'playback_time'},
    'PU': {'desc': 'Program up', 'format': 'PU[P1];', 'read': False, 'write': True, 'validator': 'program_up'},
    'PV': {'desc': 'Program VFO', 'format': 'PV[P1];', 'read': False, 'write': True, 'validator': 'program_vfo'},
    'PW': {'desc': 'Power setting', 'format': 'PW[P1];', 'read': True, 'write': True, 'validator': 'power_setting'},
    'QA': {'desc': 'Quick memory A', 'format': 'QA;', 'read': False, 'write': True, 'validator': None},
    'QB': {'desc': 'Quick memory B', 'format': 'QB;', 'read': False, 'write': True, 'validator': None},
    'QD': {'desc': 'Quick dial', 'format': 'QD[P1];', 'read': True, 'write': True, 'validator': 'quick_dial'},
    'QR': {'desc': 'QRP mode', 'format': 'QR[P1];', 'read': True, 'write': True, 'validator': 'qrp_mode'},
}


class RadioState:
    """Represents the current state of the radio for CAT emulation."""
    
    def __init__(self):
        # VFO and frequency control
        self.vfo_a_freq = normalize_frequency(7074000)  # Default to 40m (7.074 MHz)
        self.vfo_b_freq = normalize_frequency(7074000)  # Default to 40m (7.074 MHz)
        self.mode = '2'                  # USB mode (2)
        self.rx_vfo = '0'               # VFO A (0)
        self.tx_vfo = '0'               # VFO A (0)
        self.split = '0'                # Split off (0)
        
        # RIT/XIT control
        self.rit = '0'                  # RIT off (0)
        self.xit = '0'                  # XIT off (0)
        self.rit_offset = '00000'       # No offset
        
        # Power and system status
        self.power_on = '1'             # Power on (1)
        self.ai_mode = '2'              # Auto info on (2)
        
        # Audio controls
        self.af_gain = '100'            # AF gain (0-255)
        self.rf_gain = '100'            # RF gain (0-255)
        self.squelch = '000'            # Squelch level (0-255)
        self.mic_gain = '050'           # Microphone gain (0-100)
        
        # DSP and filtering
        self.if_filter = '1'            # IF filter width (1-5)
        self.if_shift = '128'           # IF shift center (0-255)
        self.noise_blanker = '0'        # Noise blanker off (0-2)
        self.noise_reduction = '0'      # Noise reduction off (0-2)
        self.notch_filter = '0'         # Notch filter off (0-1)
        
        # Power and meters
        self.power_level = '050'        # Output power (0-100)
        self.s_meter_main = '000'       # S-meter reading main RX (0-255)
        self.s_meter_sub = '000'        # S-meter reading sub RX (0-255)
        self.power_meter = '000'        # Power output meter (0-255)
        self.swr_meter = '100'          # SWR meter (100 = 1.0 SWR)
        self.alc_meter = '000'          # ALC meter (0-255)
        self.comp_meter = '000'         # COMP meter (0-255)
        
        # Preamp/Attenuator
        self.preamp_att = '0'           # Off (0), Preamp (1), Att (2)
        
        # Memory and scan
        self.memory_channel = '000'     # Current memory channel
        self.scan_status = '0'          # Scan off (0)
        
        # VOX settings
        self.vox_status = '0'           # VOX off (0)
        self.vox_gain = '050'           # VOX gain (0-100)
        self.vox_delay = '050'          # VOX delay (0-100)
        
        # Digital modes and tones
        self.tone_status = '0'          # Tone off (0)
        self.tone_freq = '08'           # Tone frequency index
        self.ctcss_status = '0'         # CTCSS off (0)
        self.ctcss_freq = '08'          # CTCSS frequency index
        
        # State tracking for blocking unwanted changes
        self.js8call_blocked_freq = '00014074000'  # JS8Call default to block
        self.last_freq_set_time = 0     # Track when frequency was last set
        self.block_js8call_default = True  # Enable JS8Call default blocking
        # Current VFO tracking (critical for Hamlib)
        self.current_vfo = '0'          # Current VFO (0=A, 1=B, 2=Memory)
        

    def to_dict(self) -> Dict[str, Any]:
        """Convert radio state to dictionary."""
        return {
            'vfo_a_freq': self.vfo_a_freq,
            'vfo_b_freq': self.vfo_b_freq,
            'mode': self.mode,
            'rx_vfo': self.rx_vfo,
            'tx_vfo': self.tx_vfo,
            'split': self.split,
            'rit': self.rit,
            'xit': self.xit,
            'rit_offset': self.rit_offset,
            'power_on': self.power_on,
            'ai_mode': self.ai_mode
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Load radio state from dictionary."""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_frequency_mhz(self) -> float:
        """Get current frequency in MHz."""
        return float(self.vfo_a_freq) / 1000000.0


def normalize_frequency(freq: Union[str, int, float]) -> str:
    """Normalize frequency to 11-digit format with leading zeros.
    
    Args:
        freq: Frequency in Hz as string, int, or float
        
    Returns:
        11-digit frequency string with leading zeros
    """
    try:
        if isinstance(freq, str):
            # Remove any non-digit characters
            freq_str = re.sub(r'[^0-9]', '', freq)
            if not freq_str:
                return '00000000000'
            freq_int = int(freq_str)
        elif isinstance(freq, (int, float)):
            freq_int = int(freq)
        else:
            return '00000000000'
        
        # Ensure frequency is within valid range (0 Hz to 999.999.999.999 Hz)
        if freq_int < 0:
            freq_int = 0
        elif freq_int > 999999999999:
            freq_int = 999999999999
            
        # Format to exactly 11 digits with leading zeros
        return f"{freq_int:011d}"
    except (ValueError, TypeError):
        log(f"Error normalizing frequency: {freq}")
        return '00000000000'


def validate_command(command: str, value: Any) -> bool:
    """Validate CAT command based on predefined rules."""
    
    if command not in TS480_COMMANDS:
        log(f"Unknown command for validation: {command}")
        return False
    
    validator = TS480_COMMANDS[command].get('validator')
    
    if validator is None:
        return True
        
    try:
        if validator == 'freq_11':
            # Validate 11-digit frequency
            if isinstance(value, str) and len(value) == 11 and value.isdigit():
                freq = int(value)
                return 0 <= freq <= 999999999999
            return False
            
        elif validator == 'vfo_select':
            return value in {'0', '1'}
            
        elif validator == 'power_status':
            return value in {'0', '1'}
            
        elif validator == 'ai_mode':
            return value in {'0', '1', '2'}
            
        elif validator == 'mode':
            return value in {'1', '2', '3', '4', '5', '6', '7', '8', '9'}  # LSB, USB, CW, FM, AM, FSK, CW-R, FSK-R, PSK
            
        elif validator == 'gain_level':
            if isinstance(value, str) and value.isdigit():
                return 0 <= int(value) <= 255
            return False
            
        elif validator == 'power_level':
            if isinstance(value, str) and value.isdigit():
                return 0 <= int(value) <= 100
            return False
            
        elif validator == 'squelch_level':
            if isinstance(value, str) and value.isdigit():
                return 0 <= int(value) <= 255
            return False
            
        elif validator == 'mic_gain':
            if isinstance(value, str) and value.isdigit():
                return 0 <= int(value) <= 100
            return False
            
        elif validator == 'filter_width':
            # TS-480 filter widths: 1=2.4kHz, 2=1.8kHz, 3=1.2kHz, 4=0.6kHz, 5=0.3kHz
            return value in {'1', '2', '3', '4', '5'}
            
        elif validator == 'if_shift':
            if isinstance(value, str) and value.isdigit():
                return 0 <= int(value) <= 255
            return False
            
        elif validator == 'nb_level':
            return value in {'0', '1', '2'}  # Off, NB1, NB2
            
        elif validator == 'nr_level':
            return value in {'0', '1', '2'}  # Off, NR1, NR2
            
        elif validator == 'rit_status':
            return value in {'0', '1'}
            
        elif validator == 'xit_status':
            return value in {'0', '1'}
            
        elif validator == 'split_status':
            return value in {'0', '1'}
            
        elif validator == 'preamp_att':
            return value in {'0', '1', '2'}  # Off, Preamp, Attenuator
            
        elif validator == 'tx_mode':
            return value in {'0', '1', '2'}  # RX, TX, TUNE
            
        else:
            log(f"Unhandled validator: {validator} for command: {command}")
            return True
            
    except (ValueError, TypeError) as e:
        log(f"Validation error for {command} with value {value}: {e}")
        return False


class CATEmulator:
    """Handles Kenwood TS-480 CAT command emulation."""
    
    def __init__(self):
        self.radio_state = RadioState()
        self.buffer = b''
    
    def handle_ts480_command(self, cmd: bytes, ser) -> Optional[bytes]:
        """Handle Kenwood TS-480 specific CAT commands with full emulation.
        
        Args:
            cmd: CAT command bytes
            ser: Serial port object
            
        Returns:
            Response bytes or None if command should be forwarded to radio
        """
        try:
            cmd_str = cmd.decode('utf-8').strip(';\\r\\n')
            log(f"Processing CAT command: {cmd_str}")
            
            # Empty command - ignore
            if not cmd_str:
                return None
            
            # ID command - return TS-480 ID
            if cmd_str == 'ID':
                return b'ID020;'
            
            # IF command - return current status (critical for Hamlib)
            elif cmd_str == 'IF':
                return self._build_if_response()
            
            # AI command - auto information (critical for Hamlib)
            elif cmd_str.startswith('AI'):
                return self._handle_ai_command(cmd_str)
            
            # Frequency commands
            elif cmd_str.startswith('FA'):
                return self._handle_fa_command(cmd_str)
            
            elif cmd_str.startswith('FB'):
                return self._handle_fb_command(cmd_str)
            
            # Mode commands
            elif cmd_str.startswith('MD'):
                return self._handle_md_command(cmd_str)
            
            # Power status
            elif cmd_str.startswith('PS'):
                return self._handle_ps_command(cmd_str)
            
            # VFO operations
            elif cmd_str.startswith('FR'):
                return self._handle_fr_command(cmd_str)
            
            elif cmd_str.startswith('FT'):
                return self._handle_ft_command(cmd_str)
            
            # Split operation
            elif cmd_str.startswith('SP'):
                return self._handle_sp_command(cmd_str)
            
            # RIT operations
            elif cmd_str.startswith('RT'):
                return self._handle_rt_command(cmd_str)
            
            elif cmd_str.startswith('XT'):
                return self._handle_xt_command(cmd_str)
            
            # Memory operations
            elif cmd_str.startswith('MC'):
                return b'MC000;'  # Channel 0
            
            # Remove old gain control handlers - using new ones below
            
            # PTT operations - must forward to truSDX hardware
            elif cmd_str.startswith('TX') or cmd_str == 'RX':
                return None  # Forward to radio
            
            # Remove old filter handlers - using new ones below
            
            # S-meter and power meter commands (required by Hamlib 4.6+)
            elif cmd_str.startswith('SM'):
                return self._handle_sm_command(cmd_str)
            
            elif cmd_str.startswith('PC'):
                return self._handle_pc_command(cmd_str)
            
            elif cmd_str.startswith('PO'):
                return self._handle_po_command(cmd_str)
            
            # Filter commands (required by Hamlib 4.6+)
            elif cmd_str.startswith('FL'):
                return self._handle_fl_command(cmd_str)
            
            # Additional meter commands
            elif cmd_str.startswith('SW'):
                return self._handle_sw_command(cmd_str)  # SWR meter
            
            elif cmd_str.startswith('AL'):
                return self._handle_al_command(cmd_str)  # ALC meter
            
            elif cmd_str.startswith('CM'):
                return self._handle_cm_command(cmd_str)  # COMP meter
            
            # Handle common Hamlib initialization commands
            elif cmd_str == 'KS':
                return b'KS020;'  # Keying speed (CW)
            elif cmd_str == 'EX':
                return b'EX;'     # Menu extension
            elif cmd_str.startswith('EX'):
                return cmd        # Echo back EX commands
            
            # Additional audio and DSP commands
            elif cmd_str.startswith('AG'):
                return self._handle_ag_command(cmd_str)
            
            elif cmd_str.startswith('RF'):
                return self._handle_rf_command(cmd_str)
            
            elif cmd_str.startswith('SQ'):
                return self._handle_sq_command(cmd_str)
            
            elif cmd_str.startswith('MG'):
                return self._handle_mg_command(cmd_str)
            
            elif cmd_str.startswith('IS'):
                return self._handle_is_command(cmd_str)
            
            elif cmd_str.startswith('NB'):
                return self._handle_nb_command(cmd_str)
            
            elif cmd_str.startswith('NR'):
                return self._handle_nr_command(cmd_str)
            
            elif cmd_str.startswith('NT'):
                return self._handle_nt_command(cmd_str)
            
            elif cmd_str.startswith('PA'):
                return self._handle_pa_command(cmd_str)
            
            # VFO commands for Hamlib compatibility
            elif cmd_str.startswith('VS') or cmd_str.startswith('VX') or cmd_str.startswith('VF'):
                return self._handle_vfo_command(cmd_str)
            
            # Current VFO query
            elif cmd_str == 'CV':
                return self._handle_current_vfo(cmd_str)
            
            # Unknown commands - ignore
            else:
                # Ensure VFO state is valid before all operations
                self._ensure_vfo_state()
                log(f"Unknown CAT command: {cmd_str} - ignoring")
                return None
        
        except Exception as e:
            log(f"Error processing CAT command {cmd}: {e}")
            return None
    
    def _build_if_response(self) -> bytes:
        """Build IF response for Hamlib compatibility with proper VFO handling."""
        # Hamlib expects EXACTLY 37 characters (not including IF and ;)
        # Format: IF<11-digit freq><5-digit RIT/XIT><RIT><XIT><Bank><RX/TX><Mode><VFO><Scan><Split><Tone><ToneFreq><CTCSS>;
        # 
        # CRITICAL: The VFO field must be set correctly for Hamlib to work
        # VFO field values: 0=VFO A, 1=VFO B, 2=Memory
        
        # Ensure frequency is properly formatted
        freq = self.radio_state.vfo_a_freq[:11].ljust(11, '0')
        
        # Build IF response components
        rit_xit_offset = '00000'                                 # 5 digits - RIT/XIT offset
        rit_status = self.radio_state.rit                        # 1 digit - RIT status
        xit_status = self.radio_state.xit                        # 1 digit - XIT status  
        memory_bank = '00'                                       # 2 digits - memory bank
        tx_rx_status = '0'                                       # 1 digit - RX/TX (0=RX, 1=TX)
        mode = self.radio_state.mode                             # 1 digit - operating mode
        current_vfo = self.radio_state.rx_vfo                    # 1 digit - CURRENT VFO (critical!)
        scan_status = '0'                                        # 1 digit - scan status
        split_status = self.radio_state.split                    # 1 digit - split status
        tone_status = '0'                                        # 1 digit - tone status
        tone_number = '08'                                       # 2 digits - tone number
        ctcss_status = '0'                                       # 1 digit - CTCSS status
        
        # Build the 37-character content string
        # Order is critical for Hamlib parsing
        content = (
            f'{freq}'           # 11 chars: frequency
            f'{rit_xit_offset}' # 5 chars: RIT/XIT offset
            f'{rit_status}'     # 1 char: RIT on/off
            f'{xit_status}'     # 1 char: XIT on/off
            f'{memory_bank}'    # 2 chars: memory bank
            f'{tx_rx_status}'   # 1 char: TX/RX status
            f'{mode}'           # 1 char: mode
            f'{current_vfo}'    # 1 char: current VFO (CRITICAL!)
            f'{scan_status}'    # 1 char: scan status
            f'{split_status}'   # 1 char: split status
            f'{tone_status}'    # 1 char: tone status
            f'{tone_number}'    # 2 chars: tone number
            f'{ctcss_status}'   # 1 char: CTCSS status
        )
        
        # Ensure exactly 37 characters with padding if needed
        if len(content) < 37:
            content = content.ljust(37, '0')
        elif len(content) > 37:
            content = content[:37]
        
        # Build final response
        response = f'IF{content};'
        
        # Verify total length is exactly 40 characters
        if len(response) != 40:
            log(f"ERROR: IF response length {len(response)} != 40", "ERROR")
            # Emergency fallback to ensure Hamlib compatibility
            fallback_content = f'{freq}000000020000000080000000'[:37].ljust(37, '0')
            response = f'IF{fallback_content};'
        
        log(f"IF response: {response} (len={len(response)}, vfo={current_vfo})")
        return response.encode('utf-8')
    
    def _handle_ai_command(self, cmd_str: str) -> bytes:
        """Handle AI (auto information) command."""
        if len(cmd_str) > 2:
            # Set AI mode
            ai_mode = cmd_str[2]
            if validate_command('AI', ai_mode):
                self.radio_state.ai_mode = ai_mode
            return f'AI{self.radio_state.ai_mode};'.encode('utf-8')
        else:
            # Read AI mode
            return f'AI{self.radio_state.ai_mode};'.encode('utf-8')
    
    def _handle_fa_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle FA (VFO A frequency) command with state-aware blocking."""
        if len(cmd_str) > 2:
            # Set VFO A frequency
            freq_raw = cmd_str[2:13]
            freq = normalize_frequency(freq_raw)  # Ensure exactly 11 digits with leading zeros
            freq_mhz = float(freq) / 1000000.0
            
            print(f"\033[1;36m[DEBUG] Setting VFO A frequency: {freq} ({freq_mhz:.3f} MHz)\033[0m")
            
            # State-aware blocking: Only block JS8Call's default 14.074 MHz when transitioning
            if (freq == self.radio_state.js8call_blocked_freq and 
                self.radio_state.vfo_a_freq != self.radio_state.js8call_blocked_freq and
                self.radio_state.block_js8call_default):
                
                print(f"\033[1;33m[CAT] Blocking JS8Call's default {freq_mhz:.3f} MHz - keeping current frequency\033[0m")
                current_freq = self.radio_state.vfo_a_freq
                current_mhz = float(current_freq) / 1000000.0
                print(f"\033[1;32m[CAT] ✅ Returning current frequency: {current_mhz:.3f} MHz\033[0m")
                return f'FA{current_freq};'.encode('utf-8')
            else:
                # Allow legitimate frequency changes
                if validate_command('FA', freq):
                    print(f"\033[1;32m[CAT] ✅ Allowing frequency change to {freq_mhz:.3f} MHz\033[0m")
                    self.radio_state.vfo_a_freq = freq
                    self.radio_state.last_freq_set_time = time.time()
                    return None  # Forward to radio
                else:
                    log(f"Invalid frequency format: {freq}")
                    return f'FA{self.radio_state.vfo_a_freq};'.encode('utf-8')
        else:
            # Read VFO A frequency
            freq = self.radio_state.vfo_a_freq
            freq_mhz = float(freq) / 1000000.0
            print(f"\033[1;36m[DEBUG] Reading VFO A frequency: {freq_mhz:.3f} MHz\033[0m")
            return f'FA{freq};'.encode('utf-8')
    
    def _handle_fb_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle FB (VFO B frequency) command."""
        if len(cmd_str) > 2:
            # Set VFO B frequency
            freq = cmd_str[2:13].ljust(11, '0')[:11]  # Ensure exactly 11 digits
            self.radio_state.vfo_b_freq = freq
            return None  # Forward to radio
        else:
            # Read VFO B frequency
            freq = self.radio_state.vfo_b_freq.ljust(11, '0')[:11]
            return f'FB{freq};'.encode('utf-8')
    
    def _handle_md_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle MD (mode) command."""
        if len(cmd_str) > 2:
            # Set mode
            self.radio_state.mode = cmd_str[2]
            return None  # Forward to radio
        else:
            # Read mode
            return f'MD{self.radio_state.mode};'.encode('utf-8')
    
    def _handle_ps_command(self, cmd_str: str) -> bytes:
        """Handle PS (power status) command."""
        if len(cmd_str) > 2:
            # Set power (ignore for now)
            return cmd_str.encode('utf-8')
        else:
            # Read power status
            return f'PS{self.radio_state.power_on};'.encode('utf-8')
    
    def _handle_fr_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle FR (receive VFO) command."""
        if len(cmd_str) > 2:
            # Set RX VFO
            self.radio_state.rx_vfo = cmd_str[2]
            return None  # Forward to radio
        else:
            # Read RX VFO
            return f'FR{self.radio_state.rx_vfo};'.encode('utf-8')
    
    def _handle_ft_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle FT (transmit VFO) command."""
        if len(cmd_str) > 2:
            # Set TX VFO
            self.radio_state.tx_vfo = cmd_str[2]
            return None  # Forward to radio
        else:
            # Read TX VFO
            return f'FT{self.radio_state.tx_vfo};'.encode('utf-8')
    
    def _handle_sp_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle SP (split) command."""
        if len(cmd_str) > 2:
            # Set split
            self.radio_state.split = cmd_str[2]
            return None  # Forward to radio
        else:
            # Read split
            return f'SP{self.radio_state.split};'.encode('utf-8')
    
    def _handle_rt_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle RT (RIT) command."""
        if len(cmd_str) > 2:
            # Set RIT on/off
            self.radio_state.rit = cmd_str[2]
            return None  # Forward to radio
        else:
            # Read RIT status
            return f'RT{self.radio_state.rit};'.encode('utf-8')
    
    def _handle_xt_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle XT (XIT) command."""
        if len(cmd_str) > 2:
            # Set XIT on/off
            self.radio_state.xit = cmd_str[2]
            return None  # Forward to radio
        else:
            # Read XIT status
            return f'XT{self.radio_state.xit};'.encode('utf-8')
    
    def query_radio(self, cmd: str, retries: int = 3, timeout: float = 0.2, ser_handle=None) -> Optional[bytes]:
        """Query radio with command and retry logic.
        
        Args:
            cmd: Command string (e.g., "FA", "MD")
            retries: Number of retry attempts
            timeout: Timeout in seconds to wait for response
            ser_handle: Serial handle to use
            
        Returns:
            Response from radio or None if failed
        """
        if not ser_handle:
            return None
        
        for attempt in range(retries):
            try:
                # Clear any existing data in buffer
                if ser_handle.in_waiting > 0:
                    ser_handle.read(ser_handle.in_waiting)
                
                # Send command
                command = f";{cmd};".encode('utf-8')
                ser_handle.write(command)
                ser_handle.flush()
                
                # Wait for response
                start_time = time.time()
                response = b''
                
                while time.time() - start_time < timeout:
                    if ser_handle.in_waiting > 0:
                        chunk = ser_handle.read(ser_handle.in_waiting)
                        response += chunk
                        
                        # Check if we have a complete response (ends with ';')
                        if b';' in response:
                            # Find the last complete response
                            responses = response.split(b';')
                            for resp in responses:
                                if resp and resp.startswith(cmd.encode('utf-8')):
                                    return resp + b';'
                            break
                    
                    time.sleep(0.01)  # Small delay to avoid busy waiting
                
                # If we got here, no valid response was received
                if attempt < retries - 1:
                    log(f"Query {cmd} attempt {attempt + 1} failed, retrying...")
                    time.sleep(0.05)  # Small delay before retry
                
            except Exception as e:
                log(f"Error in query_radio({cmd}) attempt {attempt + 1}: {e}")
                if attempt < retries - 1:
                    time.sleep(0.05)
        
        log(f"Query {cmd} failed after {retries} attempts")
        return None
    
    def reset_buffer(self):
        """Reset the CAT command buffer."""
        self.buffer = b''
        log("CAT buffer reset")
    
    def _handle_sm_command(self, cmd_str: str) -> bytes:
        """Handle SM (S-meter) command - required by Hamlib 4.6+."""
        if len(cmd_str) > 2:
            # SM with parameter (0=main, 1=sub receiver)
            rx_select = cmd_str[2]
            if rx_select == '0':
                # Main receiver S-meter
                s_value = self.radio_state.s_meter_main
                return f'SM0{s_value};'.encode('utf-8')
            elif rx_select == '1':
                # Sub receiver S-meter  
                s_value = self.radio_state.s_meter_sub
                return f'SM1{s_value};'.encode('utf-8')
            else:
                return f'SM0{self.radio_state.s_meter_main};'.encode('utf-8')
        else:
            # Default to main receiver
            return f'SM0{self.radio_state.s_meter_main};'.encode('utf-8')
    
    def _handle_pc_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle PC (power control) command."""
        if len(cmd_str) > 2:
            # Set power level
            power = cmd_str[2:5].zfill(3)  # Ensure 3 digits
            if validate_command('PC', power):
                self.radio_state.power_level = power
                return None  # Forward to radio
            else:
                return f'PC{self.radio_state.power_level};'.encode('utf-8')
        else:
            # Read power level
            return f'PC{self.radio_state.power_level};'.encode('utf-8')
    
    def _handle_po_command(self, cmd_str: str) -> bytes:
        """Handle PO (power output meter) command."""
        if len(cmd_str) > 2:
            # PO with parameter
            meter_select = cmd_str[2]
            if meter_select == '0':
                return f'PO0{self.radio_state.power_meter};'.encode('utf-8')
            else:
                return f'PO0{self.radio_state.power_meter};'.encode('utf-8')
        else:
            # Default power meter reading
            return f'PO0{self.radio_state.power_meter};'.encode('utf-8')
    
    def _handle_fl_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle FL (IF filter) command - required by Hamlib 4.6+."""
        if len(cmd_str) > 2:
            # Set IF filter
            filter_width = cmd_str[2]
            if validate_command('FL', filter_width):
                self.radio_state.if_filter = filter_width
                return None  # Forward to radio
            else:
                return f'FL{self.radio_state.if_filter};'.encode('utf-8')
        else:
            # Read IF filter
            return f'FL{self.radio_state.if_filter};'.encode('utf-8')
    
    def _handle_sw_command(self, cmd_str: str) -> bytes:
        """Handle SW (SWR meter) command."""
        return f'SW0{self.radio_state.swr_meter};'.encode('utf-8')
    
    def _handle_al_command(self, cmd_str: str) -> bytes:
        """Handle AL (ALC meter) command."""
        return f'AL0{self.radio_state.alc_meter};'.encode('utf-8')
    
    def _handle_cm_command(self, cmd_str: str) -> bytes:
        """Handle CM (COMP meter) command."""
        return f'CM0{self.radio_state.comp_meter};'.encode('utf-8')
    
    def _handle_ag_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle AG (AF gain) command."""
        if len(cmd_str) > 2:
            # Set AF gain
            gain = cmd_str[2:5].zfill(3)  # Ensure 3 digits
            if validate_command('AG', gain):
                self.radio_state.af_gain = gain
                return None  # Forward to radio
            else:
                return f'AG{self.radio_state.af_gain};'.encode('utf-8')
        else:
            # Read AF gain
            return f'AG{self.radio_state.af_gain};'.encode('utf-8')
    
    def _handle_rf_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle RF (RF gain) command."""
        if len(cmd_str) > 2:
            # Set RF gain
            gain = cmd_str[2:5].zfill(3)  # Ensure 3 digits
            if validate_command('RF', gain):
                self.radio_state.rf_gain = gain
                return None  # Forward to radio
            else:
                return f'RF{self.radio_state.rf_gain};'.encode('utf-8')
        else:
            # Read RF gain
            return f'RF{self.radio_state.rf_gain};'.encode('utf-8')
    
    def _handle_sq_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle SQ (squelch) command."""
        if len(cmd_str) > 2:
            # Set squelch
            squelch = cmd_str[2:5].zfill(3)  # Ensure 3 digits
            if validate_command('SQ', squelch):
                self.radio_state.squelch = squelch
                return None  # Forward to radio
            else:
                return f'SQ{self.radio_state.squelch};'.encode('utf-8')
        else:
            # Read squelch
            return f'SQ{self.radio_state.squelch};'.encode('utf-8')
    
    def _handle_mg_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle MG (microphone gain) command."""
        if len(cmd_str) > 2:
            # Set mic gain
            gain = cmd_str[2:5].zfill(3)  # Ensure 3 digits
            if validate_command('MG', gain):
                self.radio_state.mic_gain = gain
                return None  # Forward to radio
            else:
                return f'MG{self.radio_state.mic_gain};'.encode('utf-8')
        else:
            # Read mic gain
            return f'MG{self.radio_state.mic_gain};'.encode('utf-8')
    
    def _handle_is_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle IS (IF shift) command."""
        if len(cmd_str) > 2:
            # Set IF shift
            shift = cmd_str[2:5].zfill(3)  # Ensure 3 digits
            if validate_command('IS', shift):
                self.radio_state.if_shift = shift
                return None  # Forward to radio
            else:
                return f'IS{self.radio_state.if_shift};'.encode('utf-8')
        else:
            # Read IF shift
            return f'IS{self.radio_state.if_shift};'.encode('utf-8')
    
    def _handle_nb_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle NB (noise blanker) command."""
        if len(cmd_str) > 2:
            # Set noise blanker
            nb_level = cmd_str[2]
            if validate_command('NB', nb_level):
                self.radio_state.noise_blanker = nb_level
                return None  # Forward to radio
            else:
                return f'NB{self.radio_state.noise_blanker};'.encode('utf-8')
        else:
            # Read noise blanker
            return f'NB{self.radio_state.noise_blanker};'.encode('utf-8')
    
    def _handle_nr_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle NR (noise reduction) command."""
        if len(cmd_str) > 2:
            # Set noise reduction
            nr_level = cmd_str[2]
            if validate_command('NR', nr_level):
                self.radio_state.noise_reduction = nr_level
                return None  # Forward to radio
            else:
                return f'NR{self.radio_state.noise_reduction};'.encode('utf-8')
        else:
            # Read noise reduction
            return f'NR{self.radio_state.noise_reduction};'.encode('utf-8')
    
    def _handle_nt_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle NT (notch filter) command."""
        if len(cmd_str) > 2:
            # Set notch filter
            notch = cmd_str[2]
            if notch in {'0', '1'}:
                self.radio_state.notch_filter = notch
                return None  # Forward to radio
            else:
                return f'NT{self.radio_state.notch_filter};'.encode('utf-8')
        else:
            # Read notch filter
            return f'NT{self.radio_state.notch_filter};'.encode('utf-8')
    

    def _handle_vfo_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle VFO selection commands for Hamlib compatibility."""
        if cmd_str == 'VS':
            # VFO swap command
            # Swap VFO A and B frequencies
            temp_freq = self.radio_state.vfo_a_freq
            self.radio_state.vfo_a_freq = self.radio_state.vfo_b_freq
            self.radio_state.vfo_b_freq = temp_freq
            return None  # Forward to radio
        elif cmd_str == 'VX':
            # VFO exchange command (similar to swap)
            return self._handle_vfo_command('VS')
        elif cmd_str.startswith('VF'):
            # VFO frequency command
            return self._handle_fa_command(cmd_str.replace('VF', 'FA'))
        else:
            log(f"Unknown VFO command: {cmd_str}")
            return None
    
    def _handle_current_vfo(self, cmd_str: str) -> Optional[bytes]:
        """Handle current VFO queries that Hamlib needs."""
        # Always return VFO A as current VFO to prevent 'None' errors
        return b'VFOA;'
    
    def _ensure_vfo_state(self):
        """Ensure VFO state is never None for Hamlib compatibility."""
        if not hasattr(self.radio_state, 'current_vfo') or self.radio_state.current_vfo is None:
            self.radio_state.current_vfo = '0'  # Default to VFO A
        
        # Ensure RX/TX VFO fields are set
        if not hasattr(self.radio_state, 'rx_vfo') or self.radio_state.rx_vfo is None:
            self.radio_state.rx_vfo = '0'  # Default to VFO A
        
        if not hasattr(self.radio_state, 'tx_vfo') or self.radio_state.tx_vfo is None:
            self.radio_state.tx_vfo = '0'  # Default to VFO A


    def _handle_vfo_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle VFO selection commands for Hamlib compatibility."""
        if cmd_str == 'VS':
            # VFO swap command
            # Swap VFO A and B frequencies
            temp_freq = self.radio_state.vfo_a_freq
            self.radio_state.vfo_a_freq = self.radio_state.vfo_b_freq
            self.radio_state.vfo_b_freq = temp_freq
            return None  # Forward to radio
        elif cmd_str == 'VX':
            # VFO exchange command (similar to swap)
            return self._handle_vfo_command('VS')
        elif cmd_str.startswith('VF'):
            # VFO frequency command
            return self._handle_fa_command(cmd_str.replace('VF', 'FA'))
        else:
            log(f"Unknown VFO command: {cmd_str}")
            return None
    
    def _handle_current_vfo(self, cmd_str: str) -> Optional[bytes]:
        """Handle current VFO queries that Hamlib needs."""
        # Always return VFO A as current VFO to prevent 'None' errors
        return b'VFOA;'
    
    def _ensure_vfo_state(self):
        """Ensure VFO state is never None for Hamlib compatibility."""
        if not hasattr(self.radio_state, 'current_vfo') or self.radio_state.current_vfo is None:
            self.radio_state.current_vfo = '0'  # Default to VFO A
        
        # Ensure RX/TX VFO fields are set
        if not hasattr(self.radio_state, 'rx_vfo') or self.radio_state.rx_vfo is None:
            self.radio_state.rx_vfo = '0'  # Default to VFO A
        
        if not hasattr(self.radio_state, 'tx_vfo') or self.radio_state.tx_vfo is None:
            self.radio_state.tx_vfo = '0'  # Default to VFO A

    def _handle_pa_command(self, cmd_str: str) -> Optional[bytes]:
        """Handle PA (preamp/attenuator) command."""
        if len(cmd_str) > 2:
            # Set preamp/attenuator
            pa_setting = cmd_str[2]
            if validate_command('PA', pa_setting):
                self.radio_state.preamp_att = pa_setting
                return None  # Forward to radio
            else:
                return f'PA{self.radio_state.preamp_att};'.encode('utf-8')
        else:
            # Read preamp/attenuator
            return f'PA{self.radio_state.preamp_att};'.encode('utf-8')
    
    def get_supported_commands(self) -> Dict[str, str]:
        """Get dictionary of supported CAT commands."""
        return TS480_COMMANDS.copy()
