"""
ESP32 IoT Controller Module for JARVIS.

Provides secure communication with ESP32 devices for:
- Light switch control
- Door lock control
- Device discovery via mDNS
- Status monitoring
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

try:
    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    from zeroconf.asyncio import AsyncZeroconf, AsyncServiceBrowser
    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False


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
    UNKNOWN = "unknown"
    ERROR = "error"


@dataclass
class IoTDevice:
    """Represents an IoT device."""
    device_id: str
    device_type: DeviceType
    hostname: str
    port: int = 80
    name: str = ""
    state: DeviceState = DeviceState.UNKNOWN
    last_seen: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def url(self) -> str:
        return f"http://{self.hostname}:{self.port}"
    
    @property
    def is_online(self) -> bool:
        return self.state == DeviceState.ONLINE


class SecureTokenAuth:
    """
    Token-based authentication for ESP32 communication.
    
    Uses HMAC-SHA256 for request signing.
    """
    
    def __init__(self, shared_secret: str):
        """
        Initialize token auth.
        
        Args:
            shared_secret: Shared secret for HMAC signing.
        """
        self.shared_secret = shared_secret.encode()
    
    def generate_token(self, timestamp: Optional[int] = None) -> Tuple[str, int]:
        """
        Generate an authentication token.
        
        Args:
            timestamp: Optional timestamp (uses current time if not provided).
            
        Returns:
            Tuple of (token, timestamp).
        """
        if timestamp is None:
            timestamp = int(time.time())
        
        message = str(timestamp).encode()
        token = hmac.new(self.shared_secret, message, hashlib.sha256).hexdigest()
        
        return token, timestamp
    
    def verify_token(self, token: str, timestamp: int, max_age: int = 300) -> bool:
        """
        Verify an authentication token.
        
        Args:
            token: Token to verify.
            timestamp: Timestamp the token was generated with.
            max_age: Maximum age of token in seconds.
            
        Returns:
            True if token is valid.
        """
        # Check timestamp age
        current_time = int(time.time())
        if abs(current_time - timestamp) > max_age:
            return False
        
        # Verify HMAC
        expected_token, _ = self.generate_token(timestamp)
        return hmac.compare_digest(token, expected_token)
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for requests."""
        token, timestamp = self.generate_token()
        return {
            "X-Auth-Token": token,
            "X-Auth-Timestamp": str(timestamp),
        }


class DeviceDiscovery:
    """
    mDNS-based device discovery.
    """
    
    def __init__(self, service_type: str = "_jarvis._tcp.local."):
        """
        Initialize device discovery.
        
        Args:
            service_type: mDNS service type to discover.
        """
        self.service_type = service_type
        self._devices: Dict[str, IoTDevice] = {}
        self._zeroconf: Optional[Zeroconf] = None
        self._browser: Optional[ServiceBrowser] = None
    
    @property
    def is_available(self) -> bool:
        return ZEROCONF_AVAILABLE
    
    def _on_service_state_change(self, zeroconf, service_type, name, state_change):
        """Handle service state changes."""
        if state_change.name == "Added":
            info = zeroconf.get_service_info(service_type, name)
            if info:
                device = IoTDevice(
                    device_id=name,
                    device_type=DeviceType.GENERIC,
                    hostname=info.server,
                    port=info.port,
                    name=info.name,
                    state=DeviceState.ONLINE,
                    last_seen=time.time(),
                    properties={
                        k.decode(): v.decode() if isinstance(v, bytes) else v
                        for k, v in info.properties.items()
                    },
                )
                
                # Determine device type from properties
                device_type_str = device.properties.get("type", "generic")
                if device_type_str == "light":
                    device.device_type = DeviceType.LIGHT_SWITCH
                elif device_type_str == "door":
                    device.device_type = DeviceType.DOOR_LOCK
                
                self._devices[name] = device
                logger.info(f"Discovered device: {name} at {info.server}:{info.port}")
        
        elif state_change.name == "Removed":
            if name in self._devices:
                self._devices[name].state = DeviceState.OFFLINE
                logger.info(f"Device offline: {name}")
    
    def start_discovery(self) -> bool:
        """Start device discovery."""
        if not ZEROCONF_AVAILABLE:
            logger.warning("Zeroconf not available for device discovery")
            return False
        
        try:
            self._zeroconf = Zeroconf()
            
            class Listener(ServiceListener):
                def __init__(self, callback):
                    self.callback = callback
                
                def add_service(self, zc, type_, name):
                    self.callback(zc, type_, name, type("", (), {"name": "Added"})())
                
                def remove_service(self, zc, type_, name):
                    self.callback(zc, type_, name, type("", (), {"name": "Removed"})())
                
                def update_service(self, zc, type_, name):
                    pass
            
            listener = Listener(self._on_service_state_change)
            self._browser = ServiceBrowser(self._zeroconf, self.service_type, listener)
            
            logger.info(f"Started mDNS discovery for {self.service_type}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start discovery: {e}")
            return False
    
    def stop_discovery(self) -> None:
        """Stop device discovery."""
        if self._zeroconf:
            self._zeroconf.close()
            self._zeroconf = None
            self._browser = None
    
    def get_devices(self) -> List[IoTDevice]:
        """Get discovered devices."""
        return list(self._devices.values())
    
    def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """Get a specific device."""
        return self._devices.get(device_id)
    
    def add_manual_device(
        self,
        device_id: str,
        hostname: str,
        device_type: DeviceType,
        port: int = 80,
        name: str = "",
    ) -> IoTDevice:
        """
        Manually add a device (for when mDNS is not available).
        
        Args:
            device_id: Unique device identifier.
            hostname: Device hostname or IP.
            device_type: Type of device.
            port: HTTP port.
            name: Friendly name.
            
        Returns:
            Created device.
        """
        device = IoTDevice(
            device_id=device_id,
            device_type=device_type,
            hostname=hostname,
            port=port,
            name=name or device_id,
            state=DeviceState.UNKNOWN,
        )
        self._devices[device_id] = device
        return device


class ESP32Controller:
    """
    Controller for ESP32 IoT devices.
    
    Provides secure communication with ESP32 devices
    for light and door control.
    """
    
    def __init__(
        self,
        shared_secret: str,
        discovery_enabled: bool = True,
        service_type: str = "_jarvis._tcp.local.",
        command_timeout: int = 10,
    ):
        """
        Initialize ESP32 controller.
        
        Args:
            shared_secret: Shared secret for authentication.
            discovery_enabled: Enable mDNS discovery.
            service_type: mDNS service type.
            command_timeout: Command timeout in seconds.
        """
        self.auth = SecureTokenAuth(shared_secret)
        self.command_timeout = command_timeout
        
        self.discovery = DeviceDiscovery(service_type)
        self._discovery_enabled = discovery_enabled
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def start(self) -> None:
        """Start the controller."""
        if AIOHTTP_AVAILABLE:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.command_timeout)
            )
        
        if self._discovery_enabled:
            self.discovery.start_discovery()
        
        logger.info("ESP32 controller started")
    
    async def stop(self) -> None:
        """Stop the controller."""
        if self._session:
            await self._session.close()
            self._session = None
        
        self.discovery.stop_discovery()
        logger.info("ESP32 controller stopped")
    
    async def _send_command(
        self,
        device: IoTDevice,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        method: str = "POST",
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Send a command to a device.
        
        Args:
            device: Target device.
            endpoint: API endpoint.
            data: Request data.
            method: HTTP method.
            
        Returns:
            Tuple of (success, response_data).
        """
        if not AIOHTTP_AVAILABLE or self._session is None:
            return False, {"error": "HTTP client not available"}
        
        url = f"{device.url}{endpoint}"
        headers = self.auth.get_auth_headers()
        headers["Content-Type"] = "application/json"
        
        try:
            async with self._session.request(
                method,
                url,
                json=data,
                headers=headers,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    device.state = DeviceState.ONLINE
                    device.last_seen = time.time()
                    return True, result
                else:
                    error_text = await response.text()
                    return False, {"error": f"HTTP {response.status}: {error_text}"}
        
        except asyncio.TimeoutError:
            device.state = DeviceState.OFFLINE
            return False, {"error": "Request timed out"}
        
        except Exception as e:
            device.state = DeviceState.ERROR
            return False, {"error": str(e)}
    
    async def check_device_status(self, device: IoTDevice) -> Tuple[bool, Dict[str, Any]]:
        """
        Check device status.
        
        Args:
            device: Device to check.
            
        Returns:
            Tuple of (online, status_data).
        """
        success, data = await self._send_command(device, "/status", method="GET")
        return success, data
    
    async def control_light(
        self,
        device: IoTDevice,
        state: bool,
    ) -> Tuple[bool, str]:
        """
        Control a light switch.
        
        Args:
            device: Light switch device.
            state: True for on, False for off.
            
        Returns:
            Tuple of (success, message).
        """
        if device.device_type != DeviceType.LIGHT_SWITCH:
            return False, "Device is not a light switch"
        
        success, data = await self._send_command(
            device,
            "/light",
            {"state": "on" if state else "off"},
        )
        
        if success:
            return True, f"Light turned {'on' if state else 'off'}"
        else:
            return False, data.get("error", "Unknown error")
    
    async def control_door(
        self,
        device: IoTDevice,
        unlock: bool,
    ) -> Tuple[bool, str]:
        """
        Control a door lock.
        
        Args:
            device: Door lock device.
            unlock: True to unlock, False to lock.
            
        Returns:
            Tuple of (success, message).
        """
        if device.device_type != DeviceType.DOOR_LOCK:
            return False, "Device is not a door lock"
        
        success, data = await self._send_command(
            device,
            "/door",
            {"action": "unlock" if unlock else "lock"},
        )
        
        if success:
            return True, f"Door {'unlocked' if unlock else 'locked'}"
        else:
            return False, data.get("error", "Unknown error")
    
    async def get_device_info(self, device: IoTDevice) -> Dict[str, Any]:
        """Get detailed device information."""
        success, data = await self._send_command(device, "/info", method="GET")
        
        if success:
            return data
        return {"error": data.get("error", "Failed to get device info")}
    
    def get_light_devices(self) -> List[IoTDevice]:
        """Get all light switch devices."""
        return [
            d for d in self.discovery.get_devices()
            if d.device_type == DeviceType.LIGHT_SWITCH
        ]
    
    def get_door_devices(self) -> List[IoTDevice]:
        """Get all door lock devices."""
        return [
            d for d in self.discovery.get_devices()
            if d.device_type == DeviceType.DOOR_LOCK
        ]
    
    def add_device(
        self,
        device_id: str,
        hostname: str,
        device_type: str,
        port: int = 80,
    ) -> IoTDevice:
        """
        Manually add a device.
        
        Args:
            device_id: Device identifier.
            hostname: Device hostname/IP.
            device_type: "light" or "door".
            port: HTTP port.
            
        Returns:
            Created device.
        """
        dtype = DeviceType.LIGHT_SWITCH if device_type == "light" else DeviceType.DOOR_LOCK
        return self.discovery.add_manual_device(device_id, hostname, dtype, port)


# =============================================================================
# ESP32 Firmware Code Template
# =============================================================================

ESP32_LIGHT_SWITCH_CODE = '''
/*
 * JARVIS Light Switch Controller
 * ESP32 Firmware for servo-based light switch control
 * 
 * Hardware:
 * - ESP32-WROOM-32 DevKit
 * - MG996R Servo
 * - 5V Power Supply
 * 
 * Wiring:
 * - Servo Signal (Orange) -> GPIO 13
 * - Servo VCC (Red) -> 5V External
 * - Servo GND (Brown) -> GND (shared with ESP32)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>

// Configuration
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* DEVICE_NAME = "jarvis-light";
const char* SHARED_SECRET = "YOUR_SHARED_SECRET";

// Servo configuration
const int SERVO_PIN = 13;
const int SERVO_ON_POS = 90;   // Adjust based on your switch
const int SERVO_OFF_POS = 0;
const int SERVO_NEUTRAL = 45;

Servo lightServo;
WebServer server(80);
bool lightState = false;

// HMAC verification
bool verifyToken(String token, String timestamp) {
    int ts = timestamp.toInt();
    int currentTime = time(nullptr);
    
    // Check timestamp (5 minute window)
    if (abs(currentTime - ts) > 300) {
        return false;
    }
    
    // Calculate expected HMAC
    byte hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    mbedtls_md_hmac_starts(&ctx, (const unsigned char*)SHARED_SECRET, strlen(SHARED_SECRET));
    mbedtls_md_hmac_update(&ctx, (const unsigned char*)timestamp.c_str(), timestamp.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);
    
    // Convert to hex string
    String expected = "";
    for (int i = 0; i < 32; i++) {
        if (hmacResult[i] < 16) expected += "0";
        expected += String(hmacResult[i], HEX);
    }
    
    return token.equalsIgnoreCase(expected);
}

bool checkAuth() {
    if (!server.hasHeader("X-Auth-Token") || !server.hasHeader("X-Auth-Timestamp")) {
        server.send(401, "application/json", "{\\"error\\":\\"Missing auth headers\\"}");
        return false;
    }
    
    String token = server.header("X-Auth-Token");
    String timestamp = server.header("X-Auth-Timestamp");
    
    if (!verifyToken(token, timestamp)) {
        server.send(403, "application/json", "{\\"error\\":\\"Invalid token\\"}");
        return false;
    }
    
    return true;
}

void handleStatus() {
    StaticJsonDocument<200> doc;
    doc["device"] = DEVICE_NAME;
    doc["type"] = "light";
    doc["state"] = lightState ? "on" : "off";
    doc["uptime"] = millis() / 1000;
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void handleLight() {
    if (!checkAuth()) return;
    
    if (server.method() == HTTP_POST) {
        StaticJsonDocument<100> doc;
        deserializeJson(doc, server.arg("plain"));
        
        String state = doc["state"];
        
        if (state == "on") {
            lightServo.write(SERVO_ON_POS);
            delay(500);
            lightServo.write(SERVO_NEUTRAL);
            lightState = true;
        } else if (state == "off") {
            lightServo.write(SERVO_OFF_POS);
            delay(500);
            lightServo.write(SERVO_NEUTRAL);
            lightState = false;
        }
        
        StaticJsonDocument<100> response;
        response["success"] = true;
        response["state"] = lightState ? "on" : "off";
        
        String responseStr;
        serializeJson(response, responseStr);
        server.send(200, "application/json", responseStr);
    }
}

void handleInfo() {
    StaticJsonDocument<300> doc;
    doc["device_id"] = DEVICE_NAME;
    doc["type"] = "light_switch";
    doc["firmware"] = "1.0.0";
    doc["ip"] = WiFi.localIP().toString();
    doc["rssi"] = WiFi.RSSI();
    doc["free_heap"] = ESP.getFreeHeap();
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void setup() {
    Serial.begin(115200);
    
    // Initialize servo
    lightServo.attach(SERVO_PIN);
    lightServo.write(SERVO_NEUTRAL);
    
    // Connect to WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\\nConnected to WiFi");
    Serial.println(WiFi.localIP());
    
    // Configure time for token verification
    configTime(0, 0, "pool.ntp.org");
    
    // Start mDNS
    if (MDNS.begin(DEVICE_NAME)) {
        MDNS.addService("_jarvis", "_tcp", 80);
        MDNS.addServiceTxt("_jarvis", "_tcp", "type", "light");
        Serial.println("mDNS started");
    }
    
    // Setup routes
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/light", HTTP_POST, handleLight);
    server.on("/info", HTTP_GET, handleInfo);
    
    server.collectHeaders("X-Auth-Token", "X-Auth-Timestamp");
    server.begin();
    Serial.println("Server started");
}

void loop() {
    server.handleClient();
}
'''

ESP32_DOOR_LOCK_CODE = '''
/*
 * JARVIS Door Lock Controller
 * ESP32 Firmware for servo-based door lock control
 * 
 * Hardware:
 * - ESP32-WROOM-32 DevKit
 * - MG996R or 25kg Servo
 * - Reed switch for door state detection
 * - 5V 4A Power Supply
 * 
 * Wiring:
 * - Servo Signal (Orange) -> GPIO 13
 * - Servo VCC (Red) -> 5V External
 * - Servo GND (Brown) -> GND
 * - Reed Switch -> GPIO 14 (with pull-up)
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <ESP32Servo.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>

// Configuration
const char* WIFI_SSID = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* DEVICE_NAME = "jarvis-door";
const char* SHARED_SECRET = "YOUR_SHARED_SECRET";

// Servo configuration
const int SERVO_PIN = 13;
const int REED_PIN = 14;
const int SERVO_UNLOCK_POS = 90;
const int SERVO_LOCK_POS = 0;
const int AUTO_RELEASE_MS = 3000;  // Auto-release after 3 seconds

Servo doorServo;
WebServer server(80);
bool isUnlocked = false;
unsigned long unlockTime = 0;

// HMAC verification (same as light switch)
bool verifyToken(String token, String timestamp) {
    int ts = timestamp.toInt();
    int currentTime = time(nullptr);
    
    if (abs(currentTime - ts) > 300) {
        return false;
    }
    
    byte hmacResult[32];
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    mbedtls_md_hmac_starts(&ctx, (const unsigned char*)SHARED_SECRET, strlen(SHARED_SECRET));
    mbedtls_md_hmac_update(&ctx, (const unsigned char*)timestamp.c_str(), timestamp.length());
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);
    
    String expected = "";
    for (int i = 0; i < 32; i++) {
        if (hmacResult[i] < 16) expected += "0";
        expected += String(hmacResult[i], HEX);
    }
    
    return token.equalsIgnoreCase(expected);
}

bool checkAuth() {
    if (!server.hasHeader("X-Auth-Token") || !server.hasHeader("X-Auth-Timestamp")) {
        server.send(401, "application/json", "{\\"error\\":\\"Missing auth headers\\"}");
        return false;
    }
    
    if (!verifyToken(server.header("X-Auth-Token"), server.header("X-Auth-Timestamp"))) {
        server.send(403, "application/json", "{\\"error\\":\\"Invalid token\\"}");
        return false;
    }
    
    return true;
}

bool isDoorClosed() {
    return digitalRead(REED_PIN) == LOW;  // Reed switch closed when door closed
}

void handleStatus() {
    StaticJsonDocument<200> doc;
    doc["device"] = DEVICE_NAME;
    doc["type"] = "door";
    doc["lock_state"] = isUnlocked ? "unlocked" : "locked";
    doc["door_state"] = isDoorClosed() ? "closed" : "open";
    doc["uptime"] = millis() / 1000;
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void handleDoor() {
    if (!checkAuth()) return;
    
    if (server.method() == HTTP_POST) {
        StaticJsonDocument<100> doc;
        deserializeJson(doc, server.arg("plain"));
        
        String action = doc["action"];
        
        if (action == "unlock") {
            doorServo.write(SERVO_UNLOCK_POS);
            isUnlocked = true;
            unlockTime = millis();
        } else if (action == "lock") {
            doorServo.write(SERVO_LOCK_POS);
            isUnlocked = false;
        }
        
        StaticJsonDocument<100> response;
        response["success"] = true;
        response["lock_state"] = isUnlocked ? "unlocked" : "locked";
        response["door_state"] = isDoorClosed() ? "closed" : "open";
        
        String responseStr;
        serializeJson(response, responseStr);
        server.send(200, "application/json", responseStr);
    }
}

void handleInfo() {
    StaticJsonDocument<300> doc;
    doc["device_id"] = DEVICE_NAME;
    doc["type"] = "door_lock";
    doc["firmware"] = "1.0.0";
    doc["ip"] = WiFi.localIP().toString();
    doc["rssi"] = WiFi.RSSI();
    doc["free_heap"] = ESP.getFreeHeap();
    doc["auto_release_ms"] = AUTO_RELEASE_MS;
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
}

void setup() {
    Serial.begin(115200);
    
    // Initialize pins
    doorServo.attach(SERVO_PIN);
    doorServo.write(SERVO_LOCK_POS);
    pinMode(REED_PIN, INPUT_PULLUP);
    
    // Connect to WiFi
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\\nConnected to WiFi");
    Serial.println(WiFi.localIP());
    
    configTime(0, 0, "pool.ntp.org");
    
    if (MDNS.begin(DEVICE_NAME)) {
        MDNS.addService("_jarvis", "_tcp", 80);
        MDNS.addServiceTxt("_jarvis", "_tcp", "type", "door");
        Serial.println("mDNS started");
    }
    
    server.on("/status", HTTP_GET, handleStatus);
    server.on("/door", HTTP_POST, handleDoor);
    server.on("/info", HTTP_GET, handleInfo);
    
    server.collectHeaders("X-Auth-Token", "X-Auth-Timestamp");
    server.begin();
    Serial.println("Server started");
}

void loop() {
    server.handleClient();
    
    // Auto-release after timeout (safety feature)
    if (isUnlocked && (millis() - unlockTime > AUTO_RELEASE_MS)) {
        doorServo.write(SERVO_LOCK_POS);
        isUnlocked = false;
        Serial.println("Auto-released door lock");
    }
}
'''


def get_esp32_code(device_type: str) -> str:
    """
    Get ESP32 firmware code template.
    
    Args:
        device_type: "light" or "door".
        
    Returns:
        Arduino code as string.
    """
    if device_type == "light":
        return ESP32_LIGHT_SWITCH_CODE
    elif device_type == "door":
        return ESP32_DOOR_LOCK_CODE
    else:
        raise ValueError(f"Unknown device type: {device_type}")
