# JARVIS Hardware Setup Guide

This guide provides detailed instructions for setting up the ESP32-based IoT hardware for JARVIS, designed for users with no prior electronics experience.

## 📦 Shopping List

### Required Components

| Component | Quantity | Purpose | Where to Buy | Est. Price |
|-----------|----------|---------|--------------|------------|
| ESP32-WROOM-32 DevKit | 2 | Microcontrollers | Amazon, AliExpress | $8-15 each |
| MG996R Servo Motor | 2 | Actuate switches/locks | Amazon, AliExpress | $8-12 each |
| 5V 4A Power Supply | 1 | Power servos | Amazon | $10-15 |
| DC Barrel Jack Adapter | 1 | Connect power supply | Amazon | $5-8 |
| Jumper Wires (M-M, M-F) | 1 pack | Connections | Amazon | $5-8 |
| Micro USB Cable | 2 | Program ESP32 | Amazon | $5-8 |
| 3M VHB Heavy Duty Tape | 1 roll | Mounting (no damage) | Amazon, Hardware store | $10-15 |

### Optional Components

| Component | Quantity | Purpose | Est. Price |
|-----------|----------|---------|------------|
| Reed Switch | 2 | Door state detection | $3-5 each |
| Small Breadboard | 2 | Prototyping | $3-5 each |
| Steel Fishing Line (50lb braided) | 1 spool | Door cable pull | $8-12 |
| Heat Shrink Tubing | 1 pack | Wire protection | $5-8 |
| Project Enclosure Box | 2 | Protect electronics | $5-10 each |

**Total Estimated Cost: $70-120**

## 🔧 Light Switch Setup

### Overview

The light switch mechanism uses a servo motor to physically press your existing light switch. This is completely non-destructive and can be removed without any damage.

### Wiring Diagram

```
                    ┌─────────────────────────────────────┐
                    │           ESP32 DevKit              │
                    │                                     │
                    │  3V3  [●]                    [●] VIN│
                    │  GND  [●]────────┐          [●] GND│
                    │  D15  [●]        │          [●] D13│──── Servo Signal
                    │  D2   [●]        │          [●] D12│
                    │  D4   [●]        │          [●] D14│
                    │  ...             │          ...    │
                    └──────────────────│──────────────────┘
                                       │
                                       │ (Black/Brown)
    ┌──────────────────────────────────┴──────────────────┐
    │                                                      │
    │  ┌─────────────────┐      ┌─────────────────────┐   │
    │  │  5V 4A Power    │      │    MG996R Servo     │   │
    │  │    Supply       │      │                     │   │
    │  │                 │      │  ┌───┐              │   │
    │  │  [+5V]──────────│──────│──│Red│ VCC (5V)    │   │
    │  │                 │      │  └───┘              │   │
    │  │  [GND]──────────│──┬───│──│Brn│ GND         │   │
    │  │                 │  │   │  └───┘              │   │
    │  └─────────────────┘  │   │  ┌───┐              │   │
    │                       │   │──│Org│ Signal ─────────── To GPIO13
    │                       │   │  └───┘              │   │
    │                       │   └─────────────────────┘   │
    │                       │                              │
    │                       └──────────────────────────────┘
    │                         Common Ground
    └──────────────────────────────────────────────────────┘
```

### Step-by-Step Assembly

#### Step 1: Prepare the ESP32

1. Connect the ESP32 to your computer via USB
2. Install Arduino IDE from https://www.arduino.cc/en/software
3. Add ESP32 board support:
   - Go to File → Preferences
   - Add to "Additional Board Manager URLs":
     ```
     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
     ```
   - Go to Tools → Board → Boards Manager
   - Search "esp32" and install "ESP32 by Espressif Systems"

#### Step 2: Install Required Libraries

In Arduino IDE, go to Sketch → Include Library → Manage Libraries:
- Install "ESP32Servo"
- Install "ArduinoJson"

#### Step 3: Flash the Firmware

1. Open a new sketch in Arduino IDE
2. Copy the light switch code from `src/iot/esp32_controller.py` (the `ESP32_LIGHT_SWITCH_CODE` variable)
3. Update these values in the code:
   ```cpp
   const char* WIFI_SSID = "YOUR_WIFI_NAME";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   const char* SHARED_SECRET = "YOUR_SECRET_KEY";  // Same as in .env file
   ```
4. Select board: Tools → Board → ESP32 Dev Module
5. Select port: Tools → Port → (your ESP32's COM port)
6. Click Upload

#### Step 4: Wire the Servo

**IMPORTANT: Disconnect USB before wiring!**

1. **Servo Signal Wire (Orange/Yellow)**
   - Connect to ESP32 GPIO 13

2. **Servo Ground Wire (Brown/Black)**
   - Connect to ESP32 GND
   - Also connect to Power Supply GND (common ground!)

3. **Servo Power Wire (Red)**
   - Connect to 5V Power Supply positive terminal
   - **DO NOT connect to ESP32 5V** - the servo draws too much current

#### Step 5: Mount the Servo

1. **Test First**: Power on and verify the servo moves correctly
2. **Position**: Hold the servo against your light switch to find the optimal position
3. **Attach Arm**: Use the servo horn that best reaches the switch
4. **Mount**: Use 3M VHB tape to secure the servo body to the wall plate
5. **Calibrate**: Adjust `SERVO_ON_POS` and `SERVO_OFF_POS` in the code if needed

### Mounting Tips

```
    Wall Plate                    Servo Mounted
    ┌─────────────┐              ┌─────────────┐
    │             │              │    ┌───┐    │
    │   ┌─────┐   │              │    │ S │    │
    │   │     │   │     →        │    │ E │────┼── Servo arm
    │   │ ON  │   │              │    │ R │    │   presses switch
    │   │     │   │              │    │ V │    │
    │   │ OFF │   │              │    │ O │    │
    │   │     │   │              │    └───┘    │
    │   └─────┘   │              │             │
    └─────────────┘              └─────────────┘
```

## 🚪 Door Lock Setup

### Overview

The door lock mechanism uses a servo with a cable-pull system to actuate your door handle. This is more complex but still non-destructive.

### Safety Features

- **Auto-release**: The servo automatically releases after 3 seconds
- **Status detection**: Optional reed switch confirms door state
- **High authorization**: Requires face + liveness verification

### Wiring Diagram

```
                    ┌─────────────────────────────────────┐
                    │           ESP32 DevKit              │
                    │                                     │
                    │  3V3  [●]                    [●] VIN│
                    │  GND  [●]────────┐          [●] GND│
                    │  D15  [●]        │          [●] D13│──── Servo Signal
                    │  D2   [●]        │          [●] D12│
                    │  D4   [●]        │          [●] D14│──── Reed Switch
                    │  ...             │          ...    │
                    └──────────────────│──────────────────┘
                                       │
    ┌──────────────────────────────────┴──────────────────┐
    │                                                      │
    │  ┌─────────────────┐      ┌─────────────────────┐   │
    │  │  5V 4A Power    │      │   MG996R/25kg Servo │   │
    │  │    Supply       │      │                     │   │
    │  │  [+5V]──────────│──────│── VCC (Red)        │   │
    │  │  [GND]──────────│──┬───│── GND (Brown)      │   │
    │  └─────────────────┘  │   │── Signal (Orange) ─────── GPIO13
    │                       │   └─────────────────────┘   │
    │                       │                              │
    │  ┌─────────────────┐  │                              │
    │  │   Reed Switch   │  │                              │
    │  │   [Terminal 1]──│──┴── GND                       │
    │  │   [Terminal 2]──│───── GPIO14 (with internal     │
    │  └─────────────────┘       pull-up enabled)         │
    └──────────────────────────────────────────────────────┘
```

### Cable-Pull Mechanism

```
    Door Handle (Side View)
    
    ┌─────────────────────────────────┐
    │                                 │
    │    ┌─────┐                      │
    │    │     │ ← Handle             │
    │    │     │                      │
    │    │  ○──│─── Fishing line      │
    │    │     │    attachment point  │
    │    └─────┘                      │
    │         │                       │
    │         │ Fishing line          │
    │         │ (50lb braided)        │
    │         │                       │
    │    ┌────┴────┐                  │
    │    │  Servo  │ ← Mounted nearby │
    │    │   ○─────│── Line wraps     │
    │    │         │   around horn    │
    │    └─────────┘                  │
    │                                 │
    └─────────────────────────────────┘
```

### Assembly Steps

1. **Mount servo** near the door handle using VHB tape
2. **Attach fishing line** to the servo horn
3. **Route line** to the door handle
4. **Secure line** to the handle (use a small loop or hook)
5. **Calibrate positions** in the firmware
6. **Test thoroughly** before relying on it

### Reed Switch Installation (Optional)

The reed switch detects if the door is closed:

1. Mount the reed switch on the door frame
2. Mount the magnet on the door, aligned with the switch
3. When door closes, magnet triggers switch
4. ESP32 reads this to confirm door state

## 🔌 Power Considerations

### Why External Power?

The MG996R servo can draw up to 2.5A under load. The ESP32's 5V pin can only provide ~500mA. Using external power prevents:
- ESP32 brownouts/resets
- Weak servo movement
- Potential damage

### Power Supply Specs

- **Voltage**: 5V DC (regulated)
- **Current**: 4A minimum (for 2 servos)
- **Connector**: 2.1mm barrel jack (standard)

### Wiring Safety

1. **Always disconnect power before wiring**
2. **Double-check polarity** (+ and -)
3. **Use common ground** between ESP32 and power supply
4. **Secure all connections** with heat shrink or electrical tape

## 🌐 Network Configuration

### Finding Your ESP32

After flashing and powering on:

1. **Serial Monitor**: Open Arduino IDE Serial Monitor (115200 baud) to see the IP address
2. **mDNS**: Access via `http://jarvis-light.local` or `http://jarvis-door.local`
3. **Router**: Check your router's connected devices list

### Firewall Settings

Ensure your computer can reach the ESP32:
- Both devices must be on the same network
- Port 80 must be accessible
- mDNS (port 5353) for device discovery

## 🧪 Testing

### Test Light Switch

```bash
# Using curl (replace IP with your ESP32's IP)
curl -X POST http://192.168.1.100/light \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: YOUR_TOKEN" \
  -H "X-Auth-Timestamp: $(date +%s)" \
  -d '{"state": "on"}'
```

### Test Door Lock

```bash
curl -X POST http://192.168.1.101/door \
  -H "Content-Type: application/json" \
  -H "X-Auth-Token: YOUR_TOKEN" \
  -H "X-Auth-Timestamp: $(date +%s)" \
  -d '{"action": "unlock"}'
```

### Check Status

```bash
curl http://192.168.1.100/status
```

## ⚠️ Troubleshooting

### ESP32 Won't Connect to WiFi

- Verify SSID and password (case-sensitive)
- Ensure 2.4GHz network (ESP32 doesn't support 5GHz)
- Check router isn't blocking new devices
- Try moving closer to router

### Servo Not Moving

- Check power supply is on
- Verify wiring (especially common ground)
- Test with simple Arduino servo example first
- Check GPIO pin number in code

### Authentication Failing

- Ensure shared secret matches exactly
- Check system time is correct (for timestamp)
- Verify token generation in JARVIS logs

### Servo Jittering

- Add capacitor (100-470µF) across servo power
- Check for loose connections
- Ensure adequate power supply current

## 📚 Additional Resources

- [ESP32 Pinout Reference](https://randomnerdtutorials.com/esp32-pinout-reference-gpios/)
- [MG996R Servo Datasheet](https://www.electronicoscaldas.com/datasheet/MG996R_Tower-Pro.pdf)
- [Arduino ESP32 Documentation](https://docs.espressif.com/projects/arduino-esp32/)

---

**Remember**: Take your time, double-check connections, and test incrementally. It's better to go slow and get it right than to rush and damage components!
