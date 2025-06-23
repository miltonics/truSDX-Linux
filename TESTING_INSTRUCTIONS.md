# Testing Instructions - Enhanced Debugging Version

## 🎯 **What This Version Will Show You**

The enhanced debugging version will help us identify exactly what JS8Call is doing when it connects. You'll see detailed output like:

```bash
[DEBUG] JS8Call trying to SET frequency: 00014074000 (14.074 MHz)
[DEBUG] Full command: FA00014074000
[CAT] Blocking frequency SET command - reading actual frequency from radio
[CAT] ✅ Read actual frequency: 7.074 MHz
```

## 🧪 **Testing Steps**

### 1. **Start the Script**
```bash
cd "/home/milton/Desktop/Trusdx Linux"
python3 trusdx-txrx-AI.py --verbose
```

### 2. **Watch the Startup**
- Look for the persistent header with version info
- Note what frequency is shown initially
- Wait for "Ready for connections from WSJT-X/JS8Call..."

### 3. **Connect JS8Call**
- Start JS8Call
- Configure it to use:
  - Radio: Kenwood TS-480
  - CAT Port: `/tmp/trusdx_cat`
  - Baud: 115200
  - Audio: TRUSDX (Input/Output)

### 4. **Watch the Debug Output**
You should see detailed messages showing:
- **What commands JS8Call sends**: `[DEBUG] JS8Call trying to SET frequency: XXXXX`
- **Whether frequency reading works**: `[CAT] ✅ Read actual frequency: X.XXX MHz`
- **Any errors**: `[CAT] ❌ Invalid response from radio` or `[CAT] ⚠️ No response from radio`

## 🔍 **What to Look For**

### ✅ **Success Indicators**
- `[CAT] ✅ Read actual frequency: X.XXX MHz` (where X.XXX is NOT 14.074)
- Header updates to show the actual radio frequency
- JS8Call displays the actual radio frequency (not 14.074 MHz)

### ❌ **Failure Indicators**
- `[CAT] ❌ Invalid response from radio`
- `[CAT] ⚠️ No response from radio`
- Frequency still jumps to 14.074 MHz in JS8Call

### 🐛 **Debug Information to Collect**
Please copy and share:
1. **All debug messages** starting with `[DEBUG]`
2. **All CAT messages** starting with `[CAT]`
3. **What frequency JS8Call ends up showing**
4. **What frequency is shown in the script's header**

## 📊 **Expected vs Actual Results**

### **Expected Behavior:**
1. Script starts and shows default 14.074 MHz
2. JS8Call connects and tries to set 14.074 MHz
3. Script blocks this and reads actual frequency from radio (e.g., 7.074 MHz)
4. Script returns actual frequency to JS8Call
5. Both script header and JS8Call show actual frequency (7.074 MHz)

### **If Still Failing:**
The debug output will show us:
- Exactly what commands JS8Call is sending
- Whether the radio is responding to frequency queries
- What frequency responses we're getting back
- Where in the process it's failing

## 🔧 **Possible Issues We're Looking For**

1. **Serial Communication**: Radio not responding to `;FA;` queries
2. **Timing**: Not enough delay for radio to respond
3. **Command Format**: JS8Call using different frequency format than expected
4. **Multiple Commands**: JS8Call sending multiple frequency commands
5. **Response Parsing**: Issue with parsing the radio's frequency response

## 📋 **Information to Share**

After testing, please share:
```
1. Script startup messages (especially frequency-related)
2. All [DEBUG] messages when JS8Call connects
3. All [CAT] messages during connection
4. Final frequency shown in JS8Call
5. Final frequency shown in script header
6. Any error messages
```

This enhanced debugging will help us pinpoint exactly where the frequency jumping issue is occurring! 🎯
