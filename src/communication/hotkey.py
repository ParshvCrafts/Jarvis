"""
JARVIS Global Keyboard Shortcut Activation

Provides:
- Global hotkey listener (Win+J or customizable)
- Background thread for hotkey detection
- Callback system for activation events
"""

from __future__ import annotations

import platform
import threading
from typing import Callable, Optional

from loguru import logger

# Try to import keyboard library
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False
    logger.debug("keyboard library not available - hotkey activation disabled")


class HotkeyListener:
    """
    Global hotkey listener for JARVIS activation.
    
    Runs in a background thread and triggers a callback when
    the configured hotkey is pressed.
    """
    
    # Default hotkey combinations by platform
    DEFAULT_HOTKEYS = {
        "Windows": "win+j",
        "Darwin": "cmd+j",  # macOS
        "Linux": "ctrl+alt+j",
    }
    
    def __init__(
        self,
        hotkey: Optional[str] = None,
        callback: Optional[Callable[[], None]] = None,
        enabled: bool = True,
    ):
        """
        Initialize hotkey listener.
        
        Args:
            hotkey: Key combination (e.g., "win+j", "ctrl+shift+j")
            callback: Function to call when hotkey is pressed
            enabled: Whether hotkey listening is enabled
        """
        self.enabled = enabled and KEYBOARD_AVAILABLE
        self.callback = callback
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._hotkey_id: Optional[int] = None
        
        # Set hotkey based on platform if not specified
        if hotkey:
            self.hotkey = hotkey
        else:
            system = platform.system()
            self.hotkey = self.DEFAULT_HOTKEYS.get(system, "ctrl+shift+j")
        
        logger.debug(f"Hotkey listener initialized with: {self.hotkey}")
    
    def start(self) -> bool:
        """
        Start listening for hotkey.
        
        Returns:
            True if started successfully
        """
        if not self.enabled:
            logger.debug("Hotkey listener disabled")
            return False
        
        if not KEYBOARD_AVAILABLE:
            logger.warning("keyboard library not installed - run: pip install keyboard")
            return False
        
        if self._running:
            logger.debug("Hotkey listener already running")
            return True
        
        try:
            # Register the hotkey
            self._hotkey_id = keyboard.add_hotkey(
                self.hotkey,
                self._on_hotkey_pressed,
                suppress=False,  # Don't suppress the key event
            )
            
            self._running = True
            logger.info(f"Hotkey listener started: {self.hotkey}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start hotkey listener: {e}")
            return False
    
    def stop(self) -> None:
        """Stop listening for hotkey."""
        if not self._running:
            return
        
        try:
            if self._hotkey_id is not None and KEYBOARD_AVAILABLE:
                keyboard.remove_hotkey(self._hotkey_id)
                self._hotkey_id = None
            
            self._running = False
            logger.info("Hotkey listener stopped")
            
        except Exception as e:
            logger.error(f"Error stopping hotkey listener: {e}")
    
    def _on_hotkey_pressed(self) -> None:
        """Handle hotkey press event."""
        logger.debug(f"Hotkey pressed: {self.hotkey}")
        
        if self.callback:
            try:
                self.callback()
            except Exception as e:
                logger.error(f"Hotkey callback error: {e}")
    
    def set_callback(self, callback: Callable[[], None]) -> None:
        """Set the callback function."""
        self.callback = callback
    
    def set_hotkey(self, hotkey: str) -> bool:
        """
        Change the hotkey combination.
        
        Args:
            hotkey: New key combination
            
        Returns:
            True if changed successfully
        """
        was_running = self._running
        
        if was_running:
            self.stop()
        
        self.hotkey = hotkey
        
        if was_running:
            return self.start()
        
        return True
    
    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        return False


class ActivationManager:
    """
    Manages multiple activation methods for JARVIS.
    
    Supports:
    - Wake word activation (existing)
    - Keyboard shortcut activation (new)
    - Manual text input (existing)
    """
    
    def __init__(
        self,
        on_activate: Optional[Callable[[], None]] = None,
        hotkey_enabled: bool = True,
        hotkey: Optional[str] = None,
    ):
        """
        Initialize activation manager.
        
        Args:
            on_activate: Callback when JARVIS is activated
            hotkey_enabled: Whether hotkey activation is enabled
            hotkey: Custom hotkey combination
        """
        self.on_activate = on_activate
        self._hotkey_listener: Optional[HotkeyListener] = None
        
        if hotkey_enabled:
            self._hotkey_listener = HotkeyListener(
                hotkey=hotkey,
                callback=self._handle_activation,
                enabled=True,
            )
    
    def _handle_activation(self) -> None:
        """Handle activation from any source."""
        logger.info("JARVIS activated via hotkey")
        
        if self.on_activate:
            self.on_activate()
    
    def start(self) -> None:
        """Start all activation listeners."""
        if self._hotkey_listener:
            self._hotkey_listener.start()
    
    def stop(self) -> None:
        """Stop all activation listeners."""
        if self._hotkey_listener:
            self._hotkey_listener.stop()
    
    def set_activation_callback(self, callback: Callable[[], None]) -> None:
        """Set the activation callback."""
        self.on_activate = callback
        
        if self._hotkey_listener:
            self._hotkey_listener.set_callback(self._handle_activation)
    
    @property
    def hotkey(self) -> Optional[str]:
        """Get current hotkey."""
        return self._hotkey_listener.hotkey if self._hotkey_listener else None
    
    @property
    def hotkey_enabled(self) -> bool:
        """Check if hotkey is enabled and running."""
        return self._hotkey_listener.is_running if self._hotkey_listener else False


def get_available_hotkeys() -> list:
    """
    Get list of available modifier keys for current platform.
    
    Returns:
        List of available modifier key names
    """
    system = platform.system()
    
    if system == "Windows":
        return ["win", "ctrl", "alt", "shift"]
    elif system == "Darwin":
        return ["cmd", "ctrl", "alt", "shift"]
    else:
        return ["ctrl", "alt", "shift", "super"]


def validate_hotkey(hotkey: str) -> bool:
    """
    Validate a hotkey combination.
    
    Args:
        hotkey: Hotkey string (e.g., "win+j")
        
    Returns:
        True if valid
    """
    if not KEYBOARD_AVAILABLE:
        return False
    
    try:
        # Try to parse the hotkey
        keyboard.parse_hotkey(hotkey)
        return True
    except Exception:
        return False
