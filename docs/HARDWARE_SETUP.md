# JARVIS Hardware Setup Guide

A complete, beginner-friendly guide to building the IoT hardware for JARVIS.

**No electronics experience required!** This guide assumes you've never worked with microcontrollers before.

---

## Table of Contents

1. [Shopping List](#shopping-list)
2. [Tools Needed](#tools-needed)
3. [Safety Warnings](#safety-warnings)
4. [ESP32 Setup](#esp32-setup)
5. [Light Switch Assembly](#light-switch-assembly)
6. [Door Lock Assembly](#door-lock-assembly)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Shopping List

### Required Components

| Item | Qty | Est. Price | Notes |
|------|-----|------------|-------|
| **ESP32-WROOM-32 Dev Board** | 2 | $8-12 each | Get the 30-pin version with USB-C or Micro-USB |
| **MG996R Servo Motor** | 2 | $8-12 each | High-torque metal gear, 180° rotation |
| **5V 4A DC Power Supply** | 1 | $10-15 | Must be 5V, at least 3A (4A recommended) |
| **DC Barrel Jack Splitter** | 1 | $5-8 | To power multiple servos from one supply |
| **Jumper Wires (40-pack)** | 1 | $5-8 | Get male-to-male AND male-to-female |
| **Micro USB Cable** | 2 | $5-8 | For programming ESP32 (data cable, not charge-only) |
| **3M VHB Mounting Tape** | 1 | $8-12 | Gray heavy-duty, NOT white foam tape |
| **Braided Fishing Line** | 1 | $8-10 | 50lb test, for door mechanism |

**Estimated Total: $65-95**

### Optional But Recommended

| Item | Qty | Est. Price | Notes |
|------|-----|------------|-------|
| **Reed Switch (magnetic)** | 2 | $3-5 each | To detect door open/closed state |
| **Small Breadboard** | 1 | $5-8 | For initial testing before permanent install |
| **Heat Shrink Tubing** | 1 | $5-8 | For clean wire connections |
| **Zip Ties (small)** | 1 | $3-5 | For cable management |
| **Servo Extension Cables** | 2 | $5-8 | If servo needs to be far from ESP32 |

### Where to Buy

**Amazon (Fast shipping, slightly higher prices):**
- Search: "ESP32 WROOM 32 development board"
- Search: "MG996R servo motor"
- Search: "5V 4A power supply barrel jack"

**AliExpress (Cheaper, 2-4 week shipping):**
- Same search terms, typically 30-50% cheaper

**Recommended Specific Products:**
- ESP32: HiLetgo ESP32-WROOM-32 or DORHEA ESP32
- Servo: TowerPro MG996R or Miuzei MG996R
- Power: Any UL-listed 5V 4A adapter with 5.5x2.1mm barrel jack

---

## Tools Needed

You probably have most of these at home:

- **Phillips screwdriver** (small, for servo horn screws)
- **Scissors** (for cutting tape and fishing line)
- **Ruler or measuring tape**
- **Pencil** (for marking positions)
- **Computer** (Windows, Mac, or Linux)

**Optional but helpful:**
- Wire strippers
- Multimeter (for troubleshooting)
- Small pliers

---

## Safety Warnings

⚠️ **READ BEFORE STARTING**

### Electrical Safety
- **Never exceed 5V** on the servo power line
- **Unplug power** before making any wiring changes
- **Don't touch exposed wires** when powered on
- **Use proper power supply** - phone chargers may not provide enough current

### Mechanical Safety
- **Servos can pinch** - keep fingers away from moving parts
- **Test with low angles first** - don't go full range until calibrated
- **Secure mounting** - loose servos can fall and damage things

### Fire Safety
- **Don't leave unattended** during initial testing
- **Check for hot components** - warm is OK, hot is not
- **Use appropriate wire gauge** - included jumper wires are fine for this project

### Network Security
- **Use WPA2/WPA3 WiFi** - don't use open networks
- **Strong shared secret** - use 32+ random characters
- **Keep devices on local network** - don't expose to internet

---

## ESP32 Setup

### Step 1: Install Python

If you don't have Python installed:

1. Go to https://python.org/downloads
2. Download Python 3.10 or newer
3. **Important:** Check "Add Python to PATH" during installation
4. Restart your computer after installation

### Step 2: Install Required Tools

Open Command Prompt (Windows) or Terminal (Mac/Linux):

```bash
# Install esptool for flashing firmware
pip install esptool

# Install ampy for uploading files
pip install adafruit-ampy

# Install pyserial for serial communication
pip install pyserial
```

### Step 3: Download MicroPython

1. Go to https://micropython.org/download/ESP32_GENERIC/
2. Download the latest `.bin` file (e.g., `ESP32_GENERIC-20231005-v1.21.0.bin`)
3. Save it somewhere you can find it (like Downloads folder)

### Step 4: Connect ESP32

1. Plug ESP32 into your computer via USB cable
2. Wait for drivers to install (may take a minute)
3. Find the COM port:
   - **Windows:** Open Device Manager → Ports → Look for "Silicon Labs" or "CH340"
   - **Mac:** Run `ls /dev/cu.*` in Terminal
   - **Linux:** Run `ls /dev/ttyUSB*` in Terminal

### Step 5: Flash MicroPython

Replace `COM3` with your actual port and update the `.bin` filename:

```bash
# Erase existing firmware
esptool.py --chip esp32 --port COM3 erase_flash

# Flash MicroPython (update filename to match what you downloaded)
esptool.py --chip esp32 --port COM3 --baud 460800 write_flash -z 0x1000 ESP32_GENERIC-20231005-v1.21.0.bin
```

**Expected output:**
```
Connecting....
Chip is ESP32-D0WDQ6
...
Writing at 0x00180000... (100 %)
Hash of data verified.
Leaving...
Hard resetting via RTS pin...
```

### Step 6: Upload JARVIS Firmware

1. Navigate to the JARVIS firmware directory:
   ```bash
   cd path/to/Jarvis/firmware/esp32
   ```

2. Edit `config.py` with your settings:
   ```python
   WIFI_SSID = "YourWiFiName"
   WIFI_PASSWORD = "YourWiFiPassword"
   SHARED_SECRET = "your-secret-here"  # Must match JARVIS .env
   DEVICE_ID = "light_living_room"     # Unique name for this device
   DEVICE_TYPE = "light_switch"        # or "door_lock"
   ```

3. Upload the firmware:
   ```bash
   python tools/upload.py --port COM3 --reset
   ```

### Step 7: Verify Connection

1. Open a serial terminal (or use Thonny IDE)
2. You should see:
   ```
   JARVIS IoT Device: light_living_room
   Type: light_switch
   Firmware: 2.0.0
   
   Connecting to WiFi...
   Connected! IP: 192.168.1.xxx
   Device ready!
   ```

3. Test from your browser:
   ```
   http://192.168.1.xxx/status
   ```
   
   You should see JSON with device info.

---

## Light Switch Assembly

### Overview

The light switch mechanism uses a servo to physically push a standard wall light switch. The servo arm presses the switch in one direction for ON and the other for OFF.

```
    Wall Switch
    ┌─────────┐
    │  ┌───┐  │
    │  │ ▲ │  │  ← Switch paddle
    │  │   │  │
    │  └───┘  │
    └─────────┘
         │
    ┌────┴────┐
    │  Servo  │  ← Mounted below switch
    │   Arm   │
    └─────────┘
```

### Step 1: Prepare the Servo

1. **Attach the servo horn:**
   - Use the single-arm horn (looks like a stick)
   - Press it onto the servo shaft
   - Don't screw it in yet - we'll calibrate first

2. **Test the servo:**
   - Connect servo wires to ESP32:
     - **Brown wire** → GND (ground)
     - **Red wire** → 5V (from external power supply, NOT ESP32's 3.3V!)
     - **Orange wire** → GPIO 13
   
   ⚠️ **Important:** The ESP32's 3.3V pin cannot power the servo. You MUST use an external 5V power supply.

### Step 2: Wiring Diagram

```
                    ┌──────────────┐
                    │    ESP32     │
                    │              │
    5V Power ──────►│ VIN    GND  │◄────┐
    Supply GND ────►│ GND    D13 │─────┼──► Servo Signal (Orange)
                    │              │     │
                    └──────────────┘     │
                                         │
    5V Power ────────────────────────────┼──► Servo Power (Red)
    Supply GND ──────────────────────────┴──► Servo Ground (Brown)
```

**Wire connections:**
| ESP32 Pin | Connects To |
|-----------|-------------|
| GND | Power supply GND, Servo brown wire |
| GPIO 13 | Servo orange wire (signal) |
| VIN | Power supply 5V (optional, to power ESP32) |

| Power Supply | Connects To |
|--------------|-------------|
| 5V | Servo red wire |
| GND | Servo brown wire, ESP32 GND |

### Step 3: Calibrate Servo Positions

Before mounting, find the correct angles for your switch:

1. **Power on the system**

2. **Find neutral position** (servo arm horizontal, not touching switch):
   ```bash
   curl -X POST http://192.168.1.xxx/calibrate \
     -H "Content-Type: application/json" \
     -H "X-Auth-Token: YOUR_TOKEN" \
     -H "X-Auth-Timestamp: $(date +%s)" \
     -d '{"angle": 90}'
   ```
   
   Or use the JARVIS command:
   ```
   "Calibrate light to 90 degrees"
   ```

3. **Find ON position** (angle that pushes switch up):
   - Try angles from 90 to 120
   - When you find the right angle, save it:
   ```bash
   curl -X POST http://192.168.1.xxx/calibrate \
     -d '{"position": "on", "angle": 105}'
   ```

4. **Find OFF position** (angle that pushes switch down):
   - Try angles from 90 to 60
   - Save when found:
   ```bash
   curl -X POST http://192.168.1.xxx/calibrate \
     -d '{"position": "off", "angle": 75}'
   ```

### Step 4: Mount the Servo

1. **Clean the wall** around the switch with rubbing alcohol

2. **Position the servo:**
   - Servo body should be below the switch
   - Servo arm should reach the switch paddle
   - Mark the position with pencil

3. **Apply VHB tape:**
   - Cut a piece slightly smaller than servo body
   - Apply to servo back
   - Press firmly against wall for 30 seconds

4. **Wait 24 hours** for tape to fully cure before heavy use

### Step 5: Final Adjustments

1. **Screw in the servo horn** now that position is set

2. **Test the full cycle:**
   ```
   "Turn on the light"
   "Turn off the light"
   ```

3. **Adjust if needed** - you can recalibrate anytime

---

## Door Lock Assembly

### Overview

The door lock mechanism uses a servo to pull a cable attached to the door handle's interior thumb-turn or lever. When activated, it rotates the lock to the unlocked position, then automatically releases after 3 seconds.

```
    Door Handle (interior side)
    ┌─────────────────┐
    │    ┌─────┐      │
    │    │Thumb│◄─────┼──── Fishing line
    │    │Turn │      │
    │    └─────┘      │
    │                 │
    └─────────────────┘
           │
           │ Fishing line
           │
    ┌──────┴──────┐
    │    Servo    │  ← Mounted nearby
    │     Arm     │
    └─────────────┘
```

### Step 1: Prepare the Cable Mechanism

1. **Cut fishing line:**
   - Measure from servo location to door handle
   - Add 12 inches extra for attachment and adjustment
   - Cut the braided fishing line

2. **Create a loop** at one end:
   - Tie a small loop using a bowline or figure-8 knot
   - This loop attaches to the thumb-turn

3. **Attach to servo horn:**
   - Thread line through hole in servo horn
   - Tie securely with multiple knots
   - Leave some slack for adjustment

### Step 2: Wiring

Same as light switch:

```
ESP32 GPIO 13 ──► Servo Signal (Orange)
5V Power ───────► Servo Power (Red)  
GND ────────────► Servo Ground (Brown)
```

**Optional Reed Switch** (to detect if door is open/closed):
```
ESP32 GPIO 14 ──► Reed Switch wire 1
ESP32 GND ──────► Reed Switch wire 2
```

Mount reed switch on door frame, magnet on door.

### Step 3: Mount the Servo

1. **Choose location:**
   - Must be within cable reach of thumb-turn
   - Ideally hidden (inside cabinet, behind furniture)
   - Needs power access

2. **Mount with VHB tape** or screws

3. **Route the cable:**
   - Keep line taut but not tight
   - Avoid sharp bends
   - Use small hooks or guides if needed

### Step 4: Attach to Door Handle

1. **Loop around thumb-turn:**
   - The loop should catch the thumb-turn lever
   - When servo pulls, it should rotate the lock

2. **Test manually first:**
   - Pull the line by hand
   - Verify it unlocks the door
   - Adjust loop position if needed

### Step 5: Calibrate

1. **Find locked position** (line slack):
   ```bash
   curl -X POST http://192.168.1.xxx/calibrate \
     -d '{"position": "locked", "angle": 0}'
   ```

2. **Find unlocked position** (line pulled):
   ```bash
   curl -X POST http://192.168.1.xxx/calibrate \
     -d '{"position": "unlocked", "angle": 90}'
   ```

3. **Test the cycle:**
   ```
   "Unlock the front door"
   ```
   
   Door should unlock, then auto-lock after 3 seconds.

### Safety Considerations

⚠️ **Important for door locks:**

- **Always have a backup way to unlock** (physical key)
- **Test thoroughly** before relying on it
- **Don't use on exterior doors** without physical key backup
- **Consider adding a manual override** switch

---

## Testing

### Test from Computer

1. **Check device status:**
   ```bash
   curl http://192.168.1.xxx/status
   ```

2. **Test light control:**
   ```bash
   # Generate auth token (Python)
   python -c "
   import hmac, hashlib, time, json
   secret = 'your-shared-secret'
   ts = str(int(time.time()))
   body = json.dumps({'state': 'on'})
   token = hmac.new(secret.encode(), f'{ts}:{body}'.encode(), hashlib.sha256).hexdigest()
   print(f'Token: {token}')
   print(f'Timestamp: {ts}')
   "
   
   # Use the token
   curl -X POST http://192.168.1.xxx/light \
     -H "Content-Type: application/json" \
     -H "X-Auth-Token: YOUR_TOKEN" \
     -H "X-Auth-Timestamp: YOUR_TIMESTAMP" \
     -d '{"state": "on"}'
   ```

### Test from JARVIS

1. **Start JARVIS:**
   ```bash
   python run.py
   ```

2. **Test voice commands:**
   - "Hey Jarvis, turn on the living room light"
   - "Hey Jarvis, turn off the light"
   - "Hey Jarvis, unlock the front door"

3. **Check device discovery:**
   - "Hey Jarvis, what devices are online?"

---

## Troubleshooting

### ESP32 Won't Connect to WiFi

**Symptoms:** LED blinks slowly, never goes solid

**Solutions:**
1. Double-check WiFi credentials in `config.py`
2. Ensure 2.4GHz WiFi (ESP32 doesn't support 5GHz)
3. Move closer to router
4. Check if MAC filtering is enabled on router
5. Try a different WiFi network

### Servo Doesn't Move

**Symptoms:** No movement when command sent

**Solutions:**
1. **Check power:** Servo needs 5V from external supply, not ESP32
2. **Check wiring:** Signal wire to GPIO 13, power to 5V, ground to GND
3. **Check connections:** Wiggle wires, ensure solid contact
4. **Test servo:** Try a different servo to rule out defect

### Servo Moves But Doesn't Actuate Switch

**Symptoms:** Servo moves but switch doesn't toggle

**Solutions:**
1. **Recalibrate angles:** ON/OFF positions may be wrong
2. **Adjust mounting:** Servo may be too far from switch
3. **Check servo horn:** May be loose on shaft
4. **Increase angle range:** Try more extreme angles

### Authentication Failures

**Symptoms:** 403 Forbidden errors

**Solutions:**
1. **Check shared secret:** Must match exactly in config.py and JARVIS .env
2. **Sync time:** ESP32 time must be within 5 minutes of JARVIS computer
3. **Check timestamp:** Ensure you're using current Unix timestamp
4. **Verify token generation:** Use the exact same HMAC algorithm

### Device Not Discovered

**Symptoms:** JARVIS doesn't see the device

**Solutions:**
1. **Check IP:** Access device directly by IP to verify it's running
2. **Same network:** JARVIS and device must be on same WiFi network
3. **mDNS issues:** Try accessing by IP instead of hostname
4. **Firewall:** Ensure port 80 and mDNS (5353) aren't blocked

### Servo Jitters or Buzzes

**Symptoms:** Servo vibrates or makes noise at rest

**Solutions:**
1. **Power supply:** May need more current (use 4A supply)
2. **Detach when idle:** Modify firmware to detach servo after movement
3. **Add capacitor:** 100µF capacitor across servo power can help
4. **Check for binding:** Servo may be fighting against something

---

## Getting Help

If you're stuck:

1. **Check the logs:**
   ```bash
   curl http://192.168.1.xxx/logs
   ```

2. **Serial monitor:** Connect via USB and watch output in Thonny

3. **JARVIS logs:** Check `data/logs/jarvis.log`

4. **GitHub Issues:** Open an issue with:
   - What you tried
   - Error messages
   - Photos of your setup

---

*Happy building! 🔧*
