# JARVIS ESP32 Firmware

Production-ready MicroPython firmware for ESP32 IoT devices.

## Supported Devices

1. **Light Switch Controller** - Servo-based light switch actuator
2. **Door Lock Controller** - Servo-based door handle actuator with auto-release

## Features

- ✅ WiFi with automatic reconnection
- ✅ mDNS registration for automatic discovery
- ✅ HMAC-SHA256 authentication with replay protection
- ✅ HTTP API server
- ✅ Servo control with smooth motion
- ✅ Position calibration via API
- ✅ Status LED indicator
- ✅ Watchdog timer for crash recovery
- ✅ Persistent configuration storage
- ✅ Rate limiting (10 requests/second)
- ✅ Command logging

## Directory Structure

```
firmware/esp32/
├── README.md           # This file
├── config.py           # Configuration template
├── boot.py             # Boot script (runs first)
├── main.py             # Main application entry
├── lib/
│   ├── wifi_manager.py # WiFi connection management
│   ├── mdns_service.py # mDNS registration
│   ├── auth.py         # HMAC authentication
│   ├── http_server.py  # HTTP server implementation
│   ├── servo_control.py# Servo control with smooth motion
│   └── led_status.py   # Status LED patterns
├── devices/
│   ├── light_switch.py # Light switch device logic
│   └── door_lock.py    # Door lock device logic
└── tools/
    ├── upload.py       # Upload firmware to ESP32
    └── calibrate.py    # Servo calibration tool
```

## Quick Start

### 1. Install MicroPython on ESP32

```bash
# Download MicroPython firmware from micropython.org
# ESP32 generic: https://micropython.org/download/ESP32_GENERIC/

# Install esptool
pip install esptool

# Erase flash
esptool.py --chip esp32 --port COM3 erase_flash

# Flash MicroPython
esptool.py --chip esp32 --port COM3 write_flash -z 0x1000 ESP32_GENERIC-20231005-v1.21.0.bin
```

### 2. Configure Device

Edit `config.py` with your settings:
```python
WIFI_SSID = "YourWiFiName"
WIFI_PASSWORD = "YourWiFiPassword"
SHARED_SECRET = "YourSharedSecret"  # Must match JARVIS config
DEVICE_ID = "light_living_room"
DEVICE_TYPE = "light_switch"  # or "door_lock"
```

### 3. Upload Firmware

Using Thonny IDE:
1. Connect ESP32 via USB
2. Open Thonny, select MicroPython (ESP32) interpreter
3. Upload all files maintaining directory structure

Or using ampy:
```bash
pip install adafruit-ampy
ampy --port COM3 put boot.py
ampy --port COM3 put main.py
ampy --port COM3 put config.py
ampy --port COM3 mkdir lib
ampy --port COM3 put lib/wifi_manager.py lib/wifi_manager.py
# ... repeat for all files
```

### 4. Test Connection

```bash
# From JARVIS directory
python -c "from src.iot import EnhancedESP32Controller; c = EnhancedESP32Controller('your_secret'); print(c.get_all_devices())"
```

## API Endpoints

### All Devices

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Device status (no auth required) |
| `/health` | GET | Health check |
| `/calibrate` | POST | Calibrate servo positions |
| `/reboot` | POST | Reboot device |

### Light Switch

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/light` | POST | `{"state": "on"}` | Turn light on |
| `/light` | POST | `{"state": "off"}` | Turn light off |
| `/light` | POST | `{"state": "toggle"}` | Toggle light |

### Door Lock

| Endpoint | Method | Body | Description |
|----------|--------|------|-------------|
| `/door` | POST | `{"action": "unlock"}` | Unlock door |
| `/door` | POST | `{"action": "lock"}` | Lock door |
| `/door/status` | GET | - | Get door state |

## Authentication

All POST requests require HMAC-SHA256 authentication:

**Headers:**
- `X-Auth-Token`: HMAC-SHA256 of `{timestamp}:{body}`
- `X-Auth-Timestamp`: Unix timestamp

**Python Example:**
```python
import hmac
import hashlib
import time

timestamp = str(int(time.time()))
body = '{"state": "on"}'
message = f"{timestamp}:{body}"
token = hmac.new(
    SHARED_SECRET.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

headers = {
    "X-Auth-Token": token,
    "X-Auth-Timestamp": timestamp,
    "Content-Type": "application/json"
}
```

## LED Status Codes

| Pattern | Meaning |
|---------|---------|
| Solid ON | Connected, idle |
| Slow blink (1Hz) | Connecting to WiFi |
| Fast blink (5Hz) | Error state |
| Double blink | Command received |
| Off | Deep sleep / powered off |

## Troubleshooting

### Device not discovered
1. Check WiFi connection (LED should be solid)
2. Verify mDNS is working: `ping light_living_room.local`
3. Check firewall allows mDNS (port 5353 UDP)

### Authentication failures
1. Verify `SHARED_SECRET` matches JARVIS config
2. Check system time is synchronized (NTP)
3. Ensure timestamp is within 5 minutes

### Servo not moving
1. Check power supply (5V, 2A minimum per servo)
2. Verify servo pin configuration
3. Run calibration: `POST /calibrate {"angle": 90}`

## Safety Notes

⚠️ **Electrical Safety:**
- Never exceed 5V on servo power
- Use appropriate wire gauge for current
- Keep connections dry

⚠️ **Mechanical Safety:**
- Servos can pinch - keep fingers clear
- Test with low torque settings first
- Ensure mounting is secure

⚠️ **Security:**
- Keep devices on secure WiFi network
- Use strong shared secret (32+ characters)
- Regularly update firmware
