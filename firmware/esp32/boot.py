"""
JARVIS ESP32 Boot Script

This runs first when the ESP32 starts.
Sets up basic system configuration before main.py runs.
"""

import gc
import machine

# Disable debug output on REPL to save memory
import esp
esp.osdebug(None)

# Run garbage collection to free memory
gc.collect()

# Set CPU frequency to 240MHz for best performance
machine.freq(240000000)

print("JARVIS ESP32 Firmware booting...")
print(f"Free memory: {gc.mem_free()} bytes")
