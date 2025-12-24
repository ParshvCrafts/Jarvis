#!/usr/bin/env python3
"""
JARVIS ESP32 Firmware Upload Tool

Uploads firmware files to ESP32 via serial connection.
Requires: pip install adafruit-ampy esptool
"""

import argparse
import os
import sys
import time
from pathlib import Path

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

FIRMWARE_DIR = Path(__file__).parent.parent


def find_esp32_port():
    """Find ESP32 serial port automatically."""
    if not SERIAL_AVAILABLE:
        return None
    
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        # Common ESP32 USB-to-serial chips
        if any(chip in port.description.lower() for chip in ["cp210", "ch340", "ftdi", "silicon labs"]):
            return port.device
        if "esp32" in port.description.lower():
            return port.device
    
    # Return first available port as fallback
    if ports:
        return ports[0].device
    
    return None


def upload_file(port, local_path, remote_path, baud=115200):
    """Upload a single file to ESP32."""
    import subprocess
    
    cmd = [
        sys.executable, "-m", "ampy",
        "--port", port,
        "--baud", str(baud),
        "put", str(local_path), remote_path
    ]
    
    print(f"  Uploading: {local_path.name} -> {remote_path}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"    ERROR: {result.stderr}")
        return False
    
    return True


def create_directory(port, path, baud=115200):
    """Create a directory on ESP32."""
    import subprocess
    
    cmd = [
        sys.executable, "-m", "ampy",
        "--port", port,
        "--baud", str(baud),
        "mkdir", path
    ]
    
    # Ignore errors (directory may already exist)
    subprocess.run(cmd, capture_output=True)


def upload_firmware(port, baud=115200, skip_lib=False):
    """Upload all firmware files to ESP32."""
    print(f"\nUploading JARVIS firmware to {port}...")
    print("=" * 50)
    
    # Files to upload (in order)
    files = [
        ("boot.py", "/boot.py"),
        ("config.py", "/config.py"),
        ("main.py", "/main.py"),
    ]
    
    # Library files
    lib_files = [
        ("lib/wifi_manager.py", "/lib/wifi_manager.py"),
        ("lib/auth.py", "/lib/auth.py"),
        ("lib/http_server.py", "/lib/http_server.py"),
        ("lib/servo_control.py", "/lib/servo_control.py"),
        ("lib/led_status.py", "/lib/led_status.py"),
        ("lib/mdns_service.py", "/lib/mdns_service.py"),
        ("lib/storage.py", "/lib/storage.py"),
        ("lib/logger.py", "/lib/logger.py"),
    ]
    
    # Create lib directory
    if not skip_lib:
        print("\nCreating /lib directory...")
        create_directory(port, "/lib", baud)
    
    # Upload main files
    print("\nUploading main files...")
    for local, remote in files:
        local_path = FIRMWARE_DIR / local
        if local_path.exists():
            if not upload_file(port, local_path, remote, baud):
                return False
        else:
            print(f"  WARNING: {local} not found, skipping")
    
    # Upload library files
    if not skip_lib:
        print("\nUploading library files...")
        for local, remote in lib_files:
            local_path = FIRMWARE_DIR / local
            if local_path.exists():
                if not upload_file(port, local_path, remote, baud):
                    return False
            else:
                print(f"  WARNING: {local} not found, skipping")
    
    print("\n" + "=" * 50)
    print("Upload complete!")
    print("\nNext steps:")
    print("1. Edit config.py on the device with your WiFi credentials")
    print("2. Reset the ESP32 to start the firmware")
    print("3. Check serial output for IP address")
    
    return True


def reset_device(port, baud=115200):
    """Reset the ESP32."""
    import subprocess
    
    print(f"Resetting device on {port}...")
    
    cmd = [
        sys.executable, "-m", "ampy",
        "--port", port,
        "--baud", str(baud),
        "reset"
    ]
    
    subprocess.run(cmd, capture_output=True)
    print("Device reset")


def list_files(port, path="/", baud=115200):
    """List files on ESP32."""
    import subprocess
    
    cmd = [
        sys.executable, "-m", "ampy",
        "--port", port,
        "--baud", str(baud),
        "ls", path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"Files in {path}:")
        print(result.stdout)
    else:
        print(f"Error: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="JARVIS ESP32 Firmware Upload Tool")
    
    parser.add_argument(
        "--port", "-p",
        help="Serial port (auto-detected if not specified)"
    )
    parser.add_argument(
        "--baud", "-b",
        type=int,
        default=115200,
        help="Baud rate (default: 115200)"
    )
    parser.add_argument(
        "--skip-lib",
        action="store_true",
        help="Skip uploading library files"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset device after upload"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List files on device instead of uploading"
    )
    parser.add_argument(
        "--find-port",
        action="store_true",
        help="Find and display ESP32 port"
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    try:
        import ampy
    except ImportError:
        print("ERROR: adafruit-ampy not installed")
        print("Install with: pip install adafruit-ampy")
        sys.exit(1)
    
    # Find port
    port = args.port or find_esp32_port()
    
    if args.find_port:
        if port:
            print(f"Found ESP32 on: {port}")
        else:
            print("No ESP32 found")
            if SERIAL_AVAILABLE:
                print("\nAvailable ports:")
                for p in serial.tools.list_ports.comports():
                    print(f"  {p.device}: {p.description}")
        return
    
    if not port:
        print("ERROR: No serial port found")
        print("Specify port with --port or connect ESP32")
        sys.exit(1)
    
    print(f"Using port: {port}")
    
    if args.list:
        list_files(port, baud=args.baud)
        return
    
    # Upload firmware
    success = upload_firmware(port, args.baud, args.skip_lib)
    
    if success and args.reset:
        time.sleep(1)
        reset_device(port, args.baud)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
