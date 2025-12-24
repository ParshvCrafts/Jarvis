"""
JARVIS ESP32 Main Application

This is the main entry point for the JARVIS IoT device firmware.
It initializes all components and runs the main loop.
"""

import gc
import time
import machine
import ntptime

# Import configuration
import config

# Import library modules
from lib.wifi_manager import WiFiManager
from lib.auth import Authenticator, extract_auth_headers
from lib.http_server import HTTPServer, json_response, error_response
from lib.servo_control import LightSwitchServo, DoorLockServo
from lib.led_status import StatusLED
from lib.mdns_service import MDNSService
from lib.storage import Storage
from lib.logger import CommandLogger


# =============================================================================
# Global Objects
# =============================================================================

wifi = None
server = None
auth = None
servo = None
led = None
mdns = None
storage = None
logger = None

# Device state
device_state = {
    "light_on": False,
    "door_locked": True,
}

uptime_start = 0


# =============================================================================
# Initialization
# =============================================================================

def init_hardware():
    """Initialize hardware components."""
    global led, servo, storage, logger
    
    print("Initializing hardware...")
    
    # Status LED
    led = StatusLED(config.LED_PIN)
    led.indicate_connecting()
    
    # Persistent storage
    storage = Storage("jarvis_data.json")
    
    # Command logger
    if config.ENABLE_LOGGING:
        logger = CommandLogger(max_entries=config.MAX_LOG_ENTRIES)
    
    # Servo based on device type
    if config.DEVICE_TYPE == "light_switch":
        servo = LightSwitchServo(
            pin=config.SERVO_PIN,
            off_pos=storage.get_int("servo_off", config.SERVO_LIGHT_OFF),
            on_pos=storage.get_int("servo_on", config.SERVO_LIGHT_ON),
            neutral_pos=storage.get_int("servo_neutral", config.SERVO_LIGHT_NEUTRAL),
            speed=config.SERVO_SPEED,
        )
        device_state["light_on"] = storage.get_bool("light_state", False)
        
    elif config.DEVICE_TYPE == "door_lock":
        servo = DoorLockServo(
            pin=config.SERVO_PIN,
            locked_pos=storage.get_int("servo_locked", config.SERVO_DOOR_LOCKED),
            unlocked_pos=storage.get_int("servo_unlocked", config.SERVO_DOOR_UNLOCKED),
            speed=config.SERVO_SPEED,
            auto_release_ms=config.DOOR_AUTO_RELEASE_MS,
        )
        device_state["door_locked"] = True
    
    print("Hardware initialized")


def init_wifi():
    """Initialize WiFi connection."""
    global wifi
    
    print("Connecting to WiFi...")
    
    wifi = WiFiManager(
        ssid=config.WIFI_SSID,
        password=config.WIFI_PASSWORD,
        ssid_backup=config.WIFI_SSID_BACKUP,
        password_backup=config.WIFI_PASSWORD_BACKUP,
    )
    
    if not wifi.connect(timeout=30):
        led.indicate_error()
        print("WiFi connection failed!")
        # Retry after delay
        time.sleep(10)
        machine.reset()
    
    led.indicate_connected()
    print(f"Connected: {wifi.ip_address}")
    
    # Sync time via NTP
    try:
        ntptime.host = config.NTP_SERVER
        ntptime.settime()
        print(f"Time synced: {time.localtime()}")
    except Exception as e:
        print(f"NTP sync failed: {e}")


def init_mdns():
    """Initialize mDNS service."""
    global mdns
    
    mdns = MDNSService(
        device_id=config.DEVICE_ID,
        device_name=config.DEVICE_NAME,
        device_type=config.DEVICE_TYPE,
        port=config.HTTP_PORT,
        version=config.FIRMWARE_VERSION,
    )
    mdns.register()


def init_auth():
    """Initialize authentication."""
    global auth
    
    auth = Authenticator(
        shared_secret=config.SHARED_SECRET,
        max_drift=config.MAX_TIMESTAMP_DRIFT,
        rate_limit=config.MAX_REQUESTS_PER_SECOND,
    )


def init_server():
    """Initialize HTTP server and routes."""
    global server
    
    server = HTTPServer(port=config.HTTP_PORT)
    
    # Register routes
    server.add_route("/status", handle_status, methods=["GET"])
    server.add_route("/health", handle_health, methods=["GET"])
    server.add_route("/reboot", handle_reboot, methods=["POST"])
    server.add_route("/calibrate", handle_calibrate, methods=["POST"])
    server.add_route("/logs", handle_logs, methods=["GET"])
    
    if config.DEVICE_TYPE == "light_switch":
        server.add_route("/light", handle_light, methods=["POST"])
    elif config.DEVICE_TYPE == "door_lock":
        server.add_route("/door", handle_door, methods=["POST"])
        server.add_route("/door/status", handle_door_status, methods=["GET"])
    
    server.start()


# =============================================================================
# Request Handlers
# =============================================================================

def authenticate_request(request):
    """Authenticate a request. Returns (success, error_response)."""
    token, timestamp = extract_auth_headers(request["headers"])
    
    if not token or not timestamp:
        return False, error_response("Missing authentication headers", 401)
    
    success, error = auth.verify(token, timestamp, request.get("body", ""))
    
    if not success:
        return False, error_response(error, 403)
    
    return True, None


def handle_status(request):
    """Handle GET /status - Device status (no auth required)."""
    status = {
        "device_id": config.DEVICE_ID,
        "name": config.DEVICE_NAME,
        "type": config.DEVICE_TYPE,
        "version": config.FIRMWARE_VERSION,
        "uptime": time.time() - uptime_start,
        "wifi": wifi.get_status() if wifi else {},
        "free_memory": gc.mem_free(),
    }
    
    if config.DEVICE_TYPE == "light_switch":
        status["state"] = "on" if device_state["light_on"] else "off"
        status["position"] = servo.read() if servo else 0
        status["calibration"] = servo.get_calibration() if servo else {}
        
    elif config.DEVICE_TYPE == "door_lock":
        status["locked"] = device_state["door_locked"]
        status["position"] = servo.read() if servo else 0
        status["calibration"] = servo.get_calibration() if servo else {}
    
    return json_response(status)


def handle_health(request):
    """Handle GET /health - Simple health check."""
    return json_response({"status": "ok", "uptime": time.time() - uptime_start})


def handle_reboot(request):
    """Handle POST /reboot - Reboot device."""
    ok, err = authenticate_request(request)
    if not ok:
        return err
    
    if logger:
        logger.log("reboot", success=True)
    
    # Schedule reboot
    def do_reboot(timer):
        machine.reset()
    
    timer = machine.Timer(1)
    timer.init(period=1000, mode=machine.Timer.ONE_SHOT, callback=do_reboot)
    
    return json_response({"success": True, "message": "Rebooting in 1 second"})


def handle_calibrate(request):
    """Handle POST /calibrate - Calibrate servo positions."""
    ok, err = authenticate_request(request)
    if not ok:
        return err
    
    data = request.get("json", {})
    position = data.get("position", "")
    angle = data.get("angle", -1)
    
    if angle < 0 or angle > 180:
        return error_response("Invalid angle (must be 0-180)")
    
    if not position:
        # Just move to angle for testing
        servo.write_smooth(angle)
        return json_response({"success": True, "angle": angle})
    
    # Calibrate specific position
    servo.calibrate(position, angle)
    
    # Save calibration
    if config.DEVICE_TYPE == "light_switch":
        if position == "on":
            storage.set("servo_on", angle)
        elif position == "off":
            storage.set("servo_off", angle)
        elif position == "neutral":
            storage.set("servo_neutral", angle)
    elif config.DEVICE_TYPE == "door_lock":
        if position == "locked":
            storage.set("servo_locked", angle)
        elif position == "unlocked":
            storage.set("servo_unlocked", angle)
    
    if logger:
        logger.log("calibrate", success=True, details={"position": position, "angle": angle})
    
    return json_response({
        "success": True,
        "position": position,
        "angle": angle,
        "calibration": servo.get_calibration(),
    })


def handle_logs(request):
    """Handle GET /logs - Get command logs."""
    if not logger:
        return json_response({"logs": [], "stats": {}})
    
    return json_response({
        "logs": logger.get_recent(20),
        "stats": logger.get_stats(),
    })


def handle_light(request):
    """Handle POST /light - Control light switch."""
    ok, err = authenticate_request(request)
    if not ok:
        return err
    
    led.indicate_command()
    
    data = request.get("json", {})
    state = data.get("state", "")
    
    if state == "on":
        servo.turn_on()
        device_state["light_on"] = True
        storage.set("light_state", True)
        
    elif state == "off":
        servo.turn_off()
        device_state["light_on"] = False
        storage.set("light_state", False)
        
    elif state == "toggle":
        if device_state["light_on"]:
            servo.turn_off()
            device_state["light_on"] = False
        else:
            servo.turn_on()
            device_state["light_on"] = True
        storage.set("light_state", device_state["light_on"])
        
    else:
        return error_response("Invalid state (use: on, off, toggle)")
    
    if logger:
        logger.log("light", success=True, details={"state": state, "result": device_state["light_on"]})
    
    led.indicate_success()
    
    return json_response({
        "success": True,
        "state": "on" if device_state["light_on"] else "off",
        "position": servo.read(),
    })


def handle_door(request):
    """Handle POST /door - Control door lock."""
    ok, err = authenticate_request(request)
    if not ok:
        return err
    
    led.indicate_command()
    
    data = request.get("json", {})
    action = data.get("action", "")
    
    if action == "unlock":
        servo.unlock()
        device_state["door_locked"] = False
        
    elif action == "lock":
        servo.lock()
        device_state["door_locked"] = True
        
    else:
        return error_response("Invalid action (use: lock, unlock)")
    
    if logger:
        logger.log("door", success=True, details={"action": action})
    
    led.indicate_success()
    
    return json_response({
        "success": True,
        "locked": device_state["door_locked"],
        "position": servo.read(),
    })


def handle_door_status(request):
    """Handle GET /door/status - Get door status."""
    # Check reed switch if available
    door_closed = True
    try:
        from machine import Pin
        reed = Pin(config.REED_SWITCH_PIN, Pin.IN, Pin.PULL_UP)
        door_closed = reed.value() == 0
    except:
        pass
    
    return json_response({
        "locked": device_state["door_locked"],
        "door_closed": door_closed,
        "position": servo.read() if servo else 0,
    })


# =============================================================================
# Main Loop
# =============================================================================

def main():
    """Main application entry point."""
    global uptime_start
    
    print("\n" + "=" * 40)
    print(f"JARVIS IoT Device: {config.DEVICE_ID}")
    print(f"Type: {config.DEVICE_TYPE}")
    print(f"Firmware: {config.FIRMWARE_VERSION}")
    print("=" * 40 + "\n")
    
    uptime_start = time.time()
    
    # Initialize watchdog
    try:
        wdt = machine.WDT(timeout=config.WATCHDOG_TIMEOUT * 1000)
    except:
        wdt = None
        print("Watchdog not available")
    
    # Initialize components
    init_hardware()
    init_wifi()
    init_mdns()
    init_auth()
    init_server()
    
    print("\nDevice ready!")
    print(f"Access at: http://{wifi.ip_address}")
    if mdns:
        print(f"Or: http://{mdns.hostname}")
    print()
    
    # Main loop
    last_wifi_check = 0
    wifi_check_interval = 10  # seconds
    
    while True:
        try:
            # Feed watchdog
            if wdt:
                wdt.feed()
            
            # Handle HTTP requests
            server.handle_request()
            
            # Check WiFi connection periodically
            now = time.time()
            if now - last_wifi_check > wifi_check_interval:
                if not wifi.check_connection():
                    led.indicate_error()
                else:
                    led.indicate_connected()
                last_wifi_check = now
            
            # Door auto-release check
            if config.DEVICE_TYPE == "door_lock" and servo:
                if servo.check_auto_release():
                    device_state["door_locked"] = True
                    if logger:
                        logger.log("door_auto_lock", success=True)
            
            # Small delay to prevent tight loop
            time.sleep_ms(10)
            
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Main loop error: {e}")
            led.indicate_error()
            time.sleep(1)
    
    # Cleanup
    if server:
        server.stop()
    if mdns:
        mdns.unregister()
    led.off()


# Run main application
if __name__ == "__main__":
    main()
