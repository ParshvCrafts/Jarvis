"""
JARVIS ESP32 Device Configuration

Edit this file with your specific settings before uploading to ESP32.
"""

# =============================================================================
# WiFi Configuration
# =============================================================================
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

# Backup WiFi (optional) - will try if primary fails
WIFI_SSID_BACKUP = ""
WIFI_PASSWORD_BACKUP = ""

# =============================================================================
# Device Identity
# =============================================================================
# Unique device ID - used for mDNS and identification
# Examples: "light_living_room", "light_bedroom", "door_front", "door_garage"
DEVICE_ID = "light_living_room"

# Human-readable name shown in JARVIS
DEVICE_NAME = "Living Room Light"

# Device type: "light_switch" or "door_lock"
DEVICE_TYPE = "light_switch"

# =============================================================================
# Security
# =============================================================================
# Shared secret for HMAC authentication
# MUST match IOT_SHARED_SECRET in JARVIS .env file
# Use a strong random string (32+ characters recommended)
SHARED_SECRET = "your-shared-secret-here-change-me"

# Maximum timestamp drift allowed (seconds)
# Requests older than this are rejected
MAX_TIMESTAMP_DRIFT = 300  # 5 minutes

# Rate limiting
MAX_REQUESTS_PER_SECOND = 10

# =============================================================================
# Hardware Pins
# =============================================================================
# Servo control pin (PWM capable)
SERVO_PIN = 13

# Status LED pin (built-in LED on most ESP32 boards)
LED_PIN = 2

# Reed switch pin for door state detection (door_lock only)
REED_SWITCH_PIN = 14

# =============================================================================
# Servo Configuration
# =============================================================================
# Light Switch Servo Positions (degrees 0-180)
# These need calibration for your specific setup
SERVO_LIGHT_OFF = 80      # Position to push switch OFF
SERVO_LIGHT_ON = 100      # Position to push switch ON
SERVO_LIGHT_NEUTRAL = 90  # Rest position (not touching switch)

# Door Lock Servo Positions
SERVO_DOOR_LOCKED = 0     # Locked position
SERVO_DOOR_UNLOCKED = 90  # Unlocked position

# Servo movement speed (ms delay between degrees)
SERVO_SPEED = 15  # Lower = faster

# =============================================================================
# Door Lock Specific
# =============================================================================
# Auto-release time after unlock (milliseconds)
DOOR_AUTO_RELEASE_MS = 3000  # 3 seconds

# =============================================================================
# Network
# =============================================================================
# HTTP server port
HTTP_PORT = 80

# mDNS service type (don't change unless you know what you're doing)
MDNS_SERVICE_TYPE = "_jarvis-iot._tcp"

# NTP server for time synchronization
NTP_SERVER = "pool.ntp.org"

# =============================================================================
# Watchdog
# =============================================================================
# Watchdog timeout (seconds) - device reboots if not fed
WATCHDOG_TIMEOUT = 30

# =============================================================================
# Logging
# =============================================================================
# Enable command logging to flash (uses storage space)
ENABLE_LOGGING = True

# Maximum log entries to keep
MAX_LOG_ENTRIES = 100

# =============================================================================
# Firmware Info
# =============================================================================
FIRMWARE_VERSION = "2.0.0"
