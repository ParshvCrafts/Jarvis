"""
Enhanced ESP32 Controller for JARVIS.

Improvements over original:
- mDNS device discovery
- HMAC-SHA256 authentication with replay protection
- Command acknowledgment system
- Position feedback
- Heartbeat monitoring
- OTA update support
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    # Stub classes when zeroconf not available
    class ServiceListener:
        pass
    class Zeroconf:
        pass
    class ServiceBrowser:
        pass


class DeviceType(Enum):
    """Types of IoT devices."""
    LIGHT_SWITCH = "light_switch"
    DOOR_LOCK = "door_lock"
    SENSOR = "sensor"
    GENERIC = "generic"


class DeviceState(Enum):
    """Device states."""
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """Information about an IoT device."""
    device_id: str
    device_type: DeviceType
    name: str
    ip_address: str
    port: int = 80
    state: DeviceState = DeviceState.UNKNOWN
    last_seen: float = 0.0
    firmware_version: str = ""
    capabilities: List[str] = field(default_factory=list)
    current_position: Optional[int] = None
    
    @property
    def url(self) -> str:
        return f"http://{self.ip_address}:{self.port}"
    
    @property
    def is_online(self) -> bool:
        return self.state == DeviceState.ONLINE and (time.time() - self.last_seen) < 60


@dataclass
class CommandResult:
    """Result of a device command."""
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    response_time: float = 0.0


class DeviceDiscovery(ServiceListener):
    """
    mDNS-based device discovery.
    
    Discovers JARVIS IoT devices on the local network.
    """
    
    SERVICE_TYPE = "_jarvis-iot._tcp.local."
    
    def __init__(self, on_device_found: Optional[Callable[[DeviceInfo], None]] = None):
        self.devices: Dict[str, DeviceInfo] = {}
        self.on_device_found = on_device_found
        self._zeroconf: Optional[Zeroconf] = None
        self._browser: Optional[ServiceBrowser] = None
    
    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is discovered."""
        info = zc.get_service_info(type_, name)
        if info:
            try:
                ip = ".".join(str(b) for b in info.addresses[0])
                port = info.port
                
                # Parse properties
                props = {k.decode(): v.decode() if isinstance(v, bytes) else v 
                        for k, v in info.properties.items()}
                
                device_id = props.get("id", name.split(".")[0])
                device_type_str = props.get("type", "generic")
                
                try:
                    device_type = DeviceType(device_type_str)
                except ValueError:
                    device_type = DeviceType.GENERIC
                
                device = DeviceInfo(
                    device_id=device_id,
                    device_type=device_type,
                    name=props.get("name", device_id),
                    ip_address=ip,
                    port=port,
                    state=DeviceState.ONLINE,
                    last_seen=time.time(),
                    firmware_version=props.get("version", ""),
                    capabilities=props.get("caps", "").split(",") if props.get("caps") else [],
                )
                
                self.devices[device_id] = device
                logger.info(f"Discovered device: {device.name} ({device.ip_address})")
                
                if self.on_device_found:
                    self.on_device_found(device)
            
            except Exception as e:
                logger.error(f"Error parsing device info: {e}")
    
    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is removed."""
        device_id = name.split(".")[0]
        if device_id in self.devices:
            self.devices[device_id].state = DeviceState.OFFLINE
            logger.info(f"Device offline: {device_id}")
    
    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Called when a service is updated."""
        self.add_service(zc, type_, name)
    
    def start(self) -> bool:
        """Start device discovery."""
        if not ZEROCONF_AVAILABLE:
            logger.warning("Zeroconf not available for device discovery")
            return False
        
        try:
            self._zeroconf = Zeroconf()
            self._browser = ServiceBrowser(self._zeroconf, self.SERVICE_TYPE, self)
            logger.info("Device discovery started")
            return True
        except Exception as e:
            logger.error(f"Failed to start discovery: {e}")
            return False
    
    def stop(self) -> None:
        """Stop device discovery."""
        if self._browser:
            self._browser.cancel()
        if self._zeroconf:
            self._zeroconf.close()
        logger.info("Device discovery stopped")


class SecureDeviceClient:
    """
    Secure HTTP client for IoT devices.
    
    Features:
    - HMAC-SHA256 authentication
    - Timestamp-based replay protection
    - Request signing
    """
    
    def __init__(
        self,
        shared_secret: str,
        timeout: float = 10.0,
        max_timestamp_drift: int = 300,
    ):
        """
        Initialize secure client.
        
        Args:
            shared_secret: Shared secret for HMAC.
            timeout: Request timeout in seconds.
            max_timestamp_drift: Maximum allowed timestamp drift in seconds.
        """
        self.shared_secret = shared_secret
        self.timeout = timeout
        self.max_timestamp_drift = max_timestamp_drift
    
    def _generate_token(self, timestamp: int, payload: str = "") -> str:
        """Generate HMAC token."""
        message = f"{timestamp}:{payload}"
        return hmac.new(
            self.shared_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _get_headers(self, payload: str = "") -> Dict[str, str]:
        """Get authentication headers."""
        timestamp = int(time.time())
        token = self._generate_token(timestamp, payload)
        
        return {
            "Content-Type": "application/json",
            "X-Auth-Token": token,
            "X-Auth-Timestamp": str(timestamp),
        }
    
    async def send_command(
        self,
        device: DeviceInfo,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> CommandResult:
        """
        Send a command to a device.
        
        Args:
            device: Target device.
            endpoint: API endpoint.
            data: Request data.
            method: HTTP method.
            
        Returns:
            CommandResult with response.
        """
        if not HTTPX_AVAILABLE:
            return CommandResult(success=False, message="httpx not available")
        
        url = f"{device.url}/{endpoint.lstrip('/')}"
        payload = json.dumps(data) if data else ""
        headers = self._get_headers(payload)
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, headers=headers, content=payload)
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    try:
                        response_data = response.json()
                    except json.JSONDecodeError:
                        response_data = {"raw": response.text}
                    
                    return CommandResult(
                        success=True,
                        message="Command executed",
                        data=response_data,
                        response_time=response_time,
                    )
                else:
                    return CommandResult(
                        success=False,
                        message=f"HTTP {response.status_code}: {response.text}",
                        response_time=response_time,
                    )
        
        except httpx.TimeoutException:
            return CommandResult(success=False, message="Request timed out")
        except httpx.ConnectError:
            return CommandResult(success=False, message="Connection failed")
        except Exception as e:
            return CommandResult(success=False, message=str(e))
    
    def send_command_sync(
        self,
        device: DeviceInfo,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> CommandResult:
        """Synchronous version of send_command."""
        return asyncio.run(self.send_command(device, endpoint, data, method))


class EnhancedESP32Controller:
    """
    Enhanced ESP32 IoT controller.
    
    Features:
    - Automatic device discovery
    - Secure communication
    - Command acknowledgment
    - Heartbeat monitoring
    - Position feedback
    """
    
    def __init__(
        self,
        shared_secret: str,
        auto_discover: bool = True,
        heartbeat_interval: int = 30,
    ):
        """
        Initialize controller.
        
        Args:
            shared_secret: Shared secret for authentication.
            auto_discover: Enable automatic device discovery.
            heartbeat_interval: Heartbeat check interval in seconds.
        """
        self.client = SecureDeviceClient(shared_secret)
        self.discovery = DeviceDiscovery(on_device_found=self._on_device_found)
        self.devices: Dict[str, DeviceInfo] = {}
        self.heartbeat_interval = heartbeat_interval
        
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        if auto_discover:
            self.discovery.start()
    
    def _on_device_found(self, device: DeviceInfo) -> None:
        """Handle discovered device."""
        self.devices[device.device_id] = device
    
    def add_device(
        self,
        device_id: str,
        ip_address: str,
        device_type: DeviceType,
        name: Optional[str] = None,
        port: int = 80,
    ) -> DeviceInfo:
        """Manually add a device."""
        device = DeviceInfo(
            device_id=device_id,
            device_type=device_type,
            name=name or device_id,
            ip_address=ip_address,
            port=port,
            state=DeviceState.UNKNOWN,
        )
        self.devices[device_id] = device
        return device
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get a device by ID."""
        return self.devices.get(device_id)
    
    async def check_device_status(self, device: DeviceInfo) -> bool:
        """Check if device is online."""
        result = await self.client.send_command(device, "/status", method="GET")
        
        if result.success:
            device.state = DeviceState.ONLINE
            device.last_seen = time.time()
            
            # Update device info from response
            if "version" in result.data:
                device.firmware_version = result.data["version"]
            if "position" in result.data:
                device.current_position = result.data["position"]
            
            return True
        else:
            device.state = DeviceState.OFFLINE
            return False
    
    async def _heartbeat_loop(self) -> None:
        """Heartbeat monitoring loop."""
        while self._running:
            for device in list(self.devices.values()):
                await self.check_device_status(device)
            
            await asyncio.sleep(self.heartbeat_interval)
    
    def start_heartbeat(self) -> None:
        """Start heartbeat monitoring."""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    def stop_heartbeat(self) -> None:
        """Stop heartbeat monitoring."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
    
    # Light Switch Commands
    async def light_on(self, device_id: str) -> CommandResult:
        """Turn light on."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(success=False, message=f"Device not found: {device_id}")
        
        return await self.client.send_command(device, "/light", {"state": "on"})
    
    async def light_off(self, device_id: str) -> CommandResult:
        """Turn light off."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(success=False, message=f"Device not found: {device_id}")
        
        return await self.client.send_command(device, "/light", {"state": "off"})
    
    async def light_toggle(self, device_id: str) -> CommandResult:
        """Toggle light state."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(success=False, message=f"Device not found: {device_id}")
        
        return await self.client.send_command(device, "/light", {"state": "toggle"})
    
    # Door Lock Commands
    async def door_unlock(self, device_id: str, duration: int = 3) -> CommandResult:
        """Unlock door."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(success=False, message=f"Device not found: {device_id}")
        
        return await self.client.send_command(device, "/door", {
            "action": "unlock",
            "duration": duration,
        })
    
    async def door_lock(self, device_id: str) -> CommandResult:
        """Lock door."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(success=False, message=f"Device not found: {device_id}")
        
        return await self.client.send_command(device, "/door", {"action": "lock"})
    
    async def door_status(self, device_id: str) -> CommandResult:
        """Get door status."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(success=False, message=f"Device not found: {device_id}")
        
        return await self.client.send_command(device, "/door/status", method="GET")
    
    # Calibration Commands
    async def calibrate(self, device_id: str, position: str = "on") -> CommandResult:
        """Calibrate device position."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(success=False, message=f"Device not found: {device_id}")
        
        return await self.client.send_command(device, "/calibrate", {"position": position})
    
    # OTA Update
    async def check_update(self, device_id: str) -> CommandResult:
        """Check for firmware update."""
        device = self.get_device(device_id)
        if not device:
            return CommandResult(success=False, message=f"Device not found: {device_id}")
        
        return await self.client.send_command(device, "/ota/check", method="GET")
    
    def get_all_devices(self) -> List[DeviceInfo]:
        """Get all registered devices."""
        return list(self.devices.values())
    
    def get_online_devices(self) -> List[DeviceInfo]:
        """Get all online devices."""
        return [d for d in self.devices.values() if d.is_online]


# =============================================================================
# Enhanced ESP32 Firmware Templates
# =============================================================================

ESP32_ENHANCED_LIGHT_FIRMWARE = '''
/*
 * JARVIS Enhanced Light Switch Firmware
 * 
 * Features:
 * - HMAC-SHA256 authentication with replay protection
 * - mDNS for automatic discovery
 * - Position feedback
 * - Calibration mode
 * - Watchdog timer
 * - OTA updates
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>
#include <Preferences.h>
#include <Update.h>
#include <esp_task_wdt.h>

// ============= CONFIGURATION =============
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SHARED_SECRET = "YOUR_SHARED_SECRET";
const char* DEVICE_ID = "light_living_room";
const char* DEVICE_NAME = "Living Room Light";

const int SERVO_PIN = 13;
const int LED_PIN = 2;

// Servo positions (calibrate these!)
int SERVO_OFF_POS = 80;
int SERVO_ON_POS = 100;
int SERVO_NEUTRAL = 90;

// Security settings
const int MAX_TIMESTAMP_DRIFT = 300;  // 5 minutes
// =========================================

WebServer server(80);
Servo servo;
Preferences prefs;

bool lightState = false;
unsigned long lastRequestTime = 0;
String firmwareVersion = "2.0.0";

// HMAC-SHA256 verification
bool verifyHMAC(String token, String timestamp, String payload) {
    long ts = timestamp.toInt();
    long now = time(nullptr);
    
    // Check timestamp drift
    if (abs(now - ts) > MAX_TIMESTAMP_DRIFT) {
        Serial.println("Timestamp too old");
        return false;
    }
    
    // Prevent replay attacks
    if (ts <= lastRequestTime) {
        Serial.println("Replay attack detected");
        return false;
    }
    
    // Calculate expected HMAC
    String message = timestamp + ":" + payload;
    
    byte hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    mbedtls_md_hmac_starts(&ctx, (const unsigned char*)SHARED_SECRET, strlen(SHARED_SECRET));
    mbedtls_md_hmac_update(&ctx, (const unsigned char*)message.c_str(), message.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);
    
    // Convert to hex
    String expected = "";
    for (int i = 0; i < 32; i++) {
        char hex[3];
        sprintf(hex, "%02x", hmacResult[i]);
        expected += hex;
    }
    
    if (token == expected) {
        lastRequestTime = ts;
        return true;
    }
    
    Serial.println("HMAC mismatch");
    return false;
}

bool authenticate() {
    if (!server.hasHeader("X-Auth-Token") || !server.hasHeader("X-Auth-Timestamp")) {
        server.send(401, "application/json", "{\\"error\\":\\"Missing auth headers\\"}");
        return false;
    }
    
    String token = server.header("X-Auth-Token");
    String timestamp = server.header("X-Auth-Timestamp");
    String payload = server.arg("plain");
    
    if (!verifyHMAC(token, timestamp, payload)) {
        server.send(403, "application/json", "{\\"error\\":\\"Authentication failed\\"}");
        return false;
    }
    
    return true;
}

void moveServo(int position, bool gradual = true) {
    if (gradual) {
        int current = servo.read();
        int step = (position > current) ? 1 : -1;
        
        while (current != position) {
            current += step;
            servo.write(current);
            delay(15);  // Smooth movement
        }
    } else {
        servo.write(position);
    }
}

void setLight(bool on) {
    int targetPos = on ? SERVO_ON_POS : SERVO_OFF_POS;
    
    // Only move if not already in position
    int currentPos = servo.read();
    if (abs(currentPos - targetPos) > 5) {
        moveServo(targetPos);
        delay(300);
        moveServo(SERVO_NEUTRAL);
    }
    
    lightState = on;
    digitalWrite(LED_PIN, on ? HIGH : LOW);
    
    // Save state
    prefs.putBool("lightState", lightState);
}

void handleStatus() {
    StaticJsonDocument<256> doc;
    doc["device_id"] = DEVICE_ID;
    doc["name"] = DEVICE_NAME;
    doc["type"] = "light_switch";
    doc["version"] = firmwareVersion;
    doc["state"] = lightState ? "on" : "off";
    doc["position"] = servo.read();
    doc["uptime"] = millis() / 1000;
    doc["rssi"] = WiFi.RSSI();
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void handleLight() {
    if (!authenticate()) return;
    
    StaticJsonDocument<128> doc;
    DeserializationError error = deserializeJson(doc, server.arg("plain"));
    
    if (error) {
        server.send(400, "application/json", "{\\"error\\":\\"Invalid JSON\\"}");
        return;
    }
    
    String state = doc["state"] | "";
    
    if (state == "on") {
        setLight(true);
    } else if (state == "off") {
        setLight(false);
    } else if (state == "toggle") {
        setLight(!lightState);
    } else {
        server.send(400, "application/json", "{\\"error\\":\\"Invalid state\\"}");
        return;
    }
    
    StaticJsonDocument<128> response;
    response["success"] = true;
    response["state"] = lightState ? "on" : "off";
    response["position"] = servo.read();
    
    String responseStr;
    serializeJson(response, responseStr);
    server.send(200, "application/json", responseStr);
}

void handleCalibrate() {
    if (!authenticate()) return;
    
    StaticJsonDocument<128> doc;
    deserializeJson(doc, server.arg("plain"));
    
    String position = doc["position"] | "neutral";
    int angle = doc["angle"] | -1;
    
    if (angle >= 0 && angle <= 180) {
        servo.write(angle);
        
        if (position == "on") {
            SERVO_ON_POS = angle;
            prefs.putInt("servoOn", angle);
        } else if (position == "off") {
            SERVO_OFF_POS = angle;
            prefs.putInt("servoOff", angle);
        }
    }
    
    server.send(200, "application/json", "{\\"success\\":true}");
}

void setup() {
    Serial.begin(115200);
    
    // Initialize watchdog
    esp_task_wdt_init(30, true);
    esp_task_wdt_add(NULL);
    
    // Initialize preferences
    prefs.begin("jarvis", false);
    SERVO_ON_POS = prefs.getInt("servoOn", SERVO_ON_POS);
    SERVO_OFF_POS = prefs.getInt("servoOff", SERVO_OFF_POS);
    lightState = prefs.getBool("lightState", false);
    
    // Initialize pins
    pinMode(LED_PIN, OUTPUT);
    servo.attach(SERVO_PIN);
    servo.write(SERVO_NEUTRAL);
    
    // Connect to WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        esp_task_wdt_reset();
    }
    Serial.println("\\nConnected: " + WiFi.localIP().toString());
    
    // Configure time
    configTime(0, 0, "pool.ntp.org");
    
    // Start mDNS
    if (MDNS.begin(DEVICE_ID)) {
        MDNS.addService("_jarvis-iot", "_tcp", 80);
        MDNS.addServiceTxt("_jarvis-iot", "_tcp", "id", DEVICE_ID);
        MDNS.addServiceTxt("_jarvis-iot", "_tcp", "type", "light_switch");
        MDNS.addServiceTxt("_jarvis-iot", "_tcp", "name", DEVICE_NAME);
        MDNS.addServiceTxt("_jarvis-iot", "_tcp", "version", firmwareVersion);
    }
    
    // Setup routes
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/light", HTTP_POST, handleLight);
    server.on("/calibrate", HTTP_POST, handleCalibrate);
    
    server.begin();
    Serial.println("Server started");
    
    // Restore light state
    digitalWrite(LED_PIN, lightState ? HIGH : LOW);
}

void loop() {
    server.handleClient();
    esp_task_wdt_reset();
    delay(10);
}
'''

ESP32_ENHANCED_DOOR_FIRMWARE = '''
/*
 * JARVIS Enhanced Door Lock Firmware
 * 
 * Features:
 * - HMAC-SHA256 authentication
 * - Auto-release after unlock
 * - Reed switch for door state
 * - Position feedback
 * - Safety features
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>
#include <Preferences.h>
#include <esp_task_wdt.h>

// ============= CONFIGURATION =============
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SHARED_SECRET = "YOUR_SHARED_SECRET";
const char* DEVICE_ID = "door_front";
const char* DEVICE_NAME = "Front Door";

const int SERVO_PIN = 13;
const int REED_SWITCH_PIN = 14;
const int LED_PIN = 2;

// Servo positions
int SERVO_LOCKED = 0;
int SERVO_UNLOCKED = 90;

// Timing
const int AUTO_RELEASE_MS = 3000;  // Auto-release after 3 seconds
const int MAX_TIMESTAMP_DRIFT = 300;
// =========================================

WebServer server(80);
Servo servo;
Preferences prefs;

bool isUnlocked = false;
bool doorClosed = true;
unsigned long unlockTime = 0;
unsigned long lastRequestTime = 0;
String firmwareVersion = "2.0.0";

bool verifyHMAC(String token, String timestamp, String payload) {
    long ts = timestamp.toInt();
    long now = time(nullptr);
    
    if (abs(now - ts) > MAX_TIMESTAMP_DRIFT) return false;
    if (ts <= lastRequestTime) return false;
    
    String message = timestamp + ":" + payload;
    
    byte hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    mbedtls_md_hmac_starts(&ctx, (const unsigned char*)SHARED_SECRET, strlen(SHARED_SECRET));
    mbedtls_md_hmac_update(&ctx, (const unsigned char*)message.c_str(), message.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);
    
    String expected = "";
    for (int i = 0; i < 32; i++) {
        char hex[3];
        sprintf(hex, "%02x", hmacResult[i]);
        expected += hex;
    }
    
    if (token == expected) {
        lastRequestTime = ts;
        return true;
    }
    return false;
}

bool authenticate() {
    if (!server.hasHeader("X-Auth-Token") || !server.hasHeader("X-Auth-Timestamp")) {
        server.send(401, "application/json", "{\\"error\\":\\"Missing auth\\"}");
        return false;
    }
    
    if (!verifyHMAC(server.header("X-Auth-Token"), 
                    server.header("X-Auth-Timestamp"), 
                    server.arg("plain"))) {
        server.send(403, "application/json", "{\\"error\\":\\"Auth failed\\"}");
        return false;
    }
    return true;
}

void updateDoorState() {
    doorClosed = digitalRead(REED_SWITCH_PIN) == LOW;
}

void unlock(int duration = AUTO_RELEASE_MS) {
    servo.write(SERVO_UNLOCKED);
    isUnlocked = true;
    unlockTime = millis();
    digitalWrite(LED_PIN, HIGH);
    Serial.println("Door unlocked");
}

void lock() {
    servo.write(SERVO_LOCKED);
    isUnlocked = false;
    unlockTime = 0;
    digitalWrite(LED_PIN, LOW);
    Serial.println("Door locked");
}

void handleStatus() {
    updateDoorState();
    
    StaticJsonDocument<256> doc;
    doc["device_id"] = DEVICE_ID;
    doc["name"] = DEVICE_NAME;
    doc["type"] = "door_lock";
    doc["version"] = firmwareVersion;
    doc["locked"] = !isUnlocked;
    doc["door_closed"] = doorClosed;
    doc["position"] = servo.read();
    doc["uptime"] = millis() / 1000;
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void handleDoor() {
    if (!authenticate()) return;
    
    StaticJsonDocument<128> doc;
    deserializeJson(doc, server.arg("plain"));
    
    String action = doc["action"] | "";
    int duration = doc["duration"] | AUTO_RELEASE_MS;
    
    if (action == "unlock") {
        unlock(duration);
    } else if (action == "lock") {
        lock();
    } else {
        server.send(400, "application/json", "{\\"error\\":\\"Invalid action\\"}");
        return;
    }
    
    updateDoorState();
    
    StaticJsonDocument<128> response;
    response["success"] = true;
    response["locked"] = !isUnlocked;
    response["door_closed"] = doorClosed;
    
    String responseStr;
    serializeJson(response, responseStr);
    server.send(200, "application/json", responseStr);
}

void setup() {
    Serial.begin(115200);
    esp_task_wdt_init(30, true);
    esp_task_wdt_add(NULL);
    
    prefs.begin("jarvis", false);
    SERVO_LOCKED = prefs.getInt("servoLocked", SERVO_LOCKED);
    SERVO_UNLOCKED = prefs.getInt("servoUnlocked", SERVO_UNLOCKED);
    
    pinMode(LED_PIN, OUTPUT);
    pinMode(REED_SWITCH_PIN, INPUT_PULLUP);
    servo.attach(SERVO_PIN);
    servo.write(SERVO_LOCKED);
    
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        esp_task_wdt_reset();
    }
    Serial.println("Connected: " + WiFi.localIP().toString());
    
    configTime(0, 0, "pool.ntp.org");
    
    if (MDNS.begin(DEVICE_ID)) {
        MDNS.addService("_jarvis-iot", "_tcp", 80);
        MDNS.addServiceTxt("_jarvis-iot", "_tcp", "id", DEVICE_ID);
        MDNS.addServiceTxt("_jarvis-iot", "_tcp", "type", "door_lock");
        MDNS.addServiceTxt("_jarvis-iot", "_tcp", "name", DEVICE_NAME);
    }
    
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/door", HTTP_POST, handleDoor);
    server.on("/door/status", HTTP_GET, handleStatus);
    
    server.begin();
}

void loop() {
    server.handleClient();
    
    // Auto-release after unlock
    if (isUnlocked && (millis() - unlockTime > AUTO_RELEASE_MS)) {
        lock();
    }
    
    esp_task_wdt_reset();
    delay(10);
}
'''
