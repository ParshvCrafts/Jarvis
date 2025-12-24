"""
System Controller Module for JARVIS.

Provides comprehensive system control capabilities:
- Application management
- Window control
- Volume/brightness control
- Clipboard operations
- Screenshot capture
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pygetwindow as gw
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    PYGETWINDOW_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False


@dataclass
class WindowInfo:
    """Information about a window."""
    title: str
    handle: int
    x: int
    y: int
    width: int
    height: int
    is_active: bool
    is_minimized: bool
    is_maximized: bool


@dataclass
class ProcessInfo:
    """Information about a process."""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_percent: float
    create_time: float


class ApplicationController:
    """
    Controls application launching and management.
    """
    
    # Common application mappings for Windows
    APP_MAPPINGS = {
        # Browsers
        "chrome": ["chrome", "google-chrome", "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"],
        "firefox": ["firefox", "C:\\Program Files\\Mozilla Firefox\\firefox.exe"],
        "edge": ["msedge", "microsoft-edge"],
        
        # Productivity
        "notepad": ["notepad.exe", "notepad"],
        "calculator": ["calc.exe", "calc"],
        "word": ["winword", "WINWORD.EXE"],
        "excel": ["excel", "EXCEL.EXE"],
        "powerpoint": ["powerpnt", "POWERPNT.EXE"],
        
        # Development
        "vscode": ["code", "Code.exe"],
        "terminal": ["wt", "cmd"],
        "powershell": ["powershell"],
        "cmd": ["cmd.exe"],
        
        # Media
        "spotify": ["spotify", "Spotify.exe"],
        "vlc": ["vlc", "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"],
        
        # Communication
        "discord": ["discord", "Discord.exe"],
        "slack": ["slack", "Slack.exe"],
        "teams": ["teams", "Teams.exe"],
        
        # System
        "explorer": ["explorer.exe"],
        "settings": ["ms-settings:"],
        "control": ["control"],
        "task_manager": ["taskmgr"],
    }
    
    def __init__(self, allowed_apps: Optional[List[str]] = None):
        """
        Initialize application controller.
        
        Args:
            allowed_apps: List of allowed application names. None allows all.
        """
        self.allowed_apps = allowed_apps
    
    def _is_allowed(self, app_name: str) -> bool:
        """Check if app is allowed."""
        if self.allowed_apps is None:
            return True
        return app_name.lower() in [a.lower() for a in self.allowed_apps]
    
    def _get_executable(self, app_name: str) -> Optional[str]:
        """Get executable path for an app."""
        app_lower = app_name.lower()
        
        if app_lower in self.APP_MAPPINGS:
            candidates = self.APP_MAPPINGS[app_lower]
            for candidate in candidates:
                if os.path.exists(candidate):
                    return candidate
            return candidates[0]  # Return first as fallback
        
        return app_name
    
    def open(self, app_name: str, args: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Open an application.
        
        Args:
            app_name: Name of the application.
            args: Optional command line arguments.
            
        Returns:
            Tuple of (success, message).
        """
        if not self._is_allowed(app_name):
            return False, f"Application '{app_name}' is not in the allowed list."
        
        executable = self._get_executable(app_name)
        
        try:
            if os.name == 'nt':  # Windows
                if executable.startswith("ms-"):
                    # Windows URI scheme
                    os.startfile(executable)
                else:
                    cmd = f'start "" "{executable}"'
                    if args:
                        cmd += " " + " ".join(args)
                    subprocess.Popen(cmd, shell=True)
            else:  # Linux/Mac
                cmd = [executable] + (args or [])
                subprocess.Popen(cmd, start_new_session=True)
            
            logger.info(f"Opened application: {app_name}")
            return True, f"Opened {app_name}"
        
        except Exception as e:
            logger.error(f"Failed to open {app_name}: {e}")
            return False, f"Failed to open {app_name}: {e}"
    
    def close(self, app_name: str, force: bool = False) -> Tuple[bool, str]:
        """
        Close an application.
        
        Args:
            app_name: Name of the application.
            force: Force close without saving.
            
        Returns:
            Tuple of (success, message).
        """
        if not PSUTIL_AVAILABLE:
            return False, "psutil not available"
        
        app_lower = app_name.lower()
        closed = 0
        
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if app_lower in proc.info['name'].lower():
                    if force:
                        proc.kill()
                    else:
                        proc.terminate()
                    closed += 1
            
            if closed > 0:
                logger.info(f"Closed {closed} instance(s) of {app_name}")
                return True, f"Closed {closed} instance(s) of {app_name}"
            else:
                return False, f"No running instances of {app_name} found"
        
        except Exception as e:
            logger.error(f"Failed to close {app_name}: {e}")
            return False, f"Failed to close {app_name}: {e}"
    
    def is_running(self, app_name: str) -> bool:
        """Check if an application is running."""
        if not PSUTIL_AVAILABLE:
            return False
        
        app_lower = app_name.lower()
        
        for proc in psutil.process_iter(['name']):
            if app_lower in proc.info['name'].lower():
                return True
        
        return False
    
    def list_running(self) -> List[ProcessInfo]:
        """List running processes."""
        if not PSUTIL_AVAILABLE:
            return []
        
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                info = proc.info
                processes.append(ProcessInfo(
                    pid=info['pid'],
                    name=info['name'],
                    status=info['status'],
                    cpu_percent=info['cpu_percent'] or 0,
                    memory_percent=info['memory_percent'] or 0,
                    create_time=info['create_time'] or 0,
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return processes


class WindowController:
    """
    Controls window management.
    """
    
    def __init__(self):
        self._available = PYGETWINDOW_AVAILABLE
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def get_active_window(self) -> Optional[WindowInfo]:
        """Get the currently active window."""
        if not self._available:
            return None
        
        try:
            win = gw.getActiveWindow()
            if win:
                return WindowInfo(
                    title=win.title,
                    handle=win._hWnd if hasattr(win, '_hWnd') else 0,
                    x=win.left,
                    y=win.top,
                    width=win.width,
                    height=win.height,
                    is_active=True,
                    is_minimized=win.isMinimized,
                    is_maximized=win.isMaximized,
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get active window: {e}")
            return None
    
    def get_windows(self, title_contains: Optional[str] = None) -> List[WindowInfo]:
        """Get list of windows."""
        if not self._available:
            return []
        
        windows = []
        
        try:
            all_windows = gw.getAllWindows()
            active = gw.getActiveWindow()
            active_handle = active._hWnd if active and hasattr(active, '_hWnd') else None
            
            for win in all_windows:
                if not win.title:
                    continue
                
                if title_contains and title_contains.lower() not in win.title.lower():
                    continue
                
                handle = win._hWnd if hasattr(win, '_hWnd') else 0
                
                windows.append(WindowInfo(
                    title=win.title,
                    handle=handle,
                    x=win.left,
                    y=win.top,
                    width=win.width,
                    height=win.height,
                    is_active=handle == active_handle,
                    is_minimized=win.isMinimized,
                    is_maximized=win.isMaximized,
                ))
        
        except Exception as e:
            logger.error(f"Failed to get windows: {e}")
        
        return windows
    
    def focus_window(self, title_contains: str) -> bool:
        """Focus a window by title."""
        if not self._available:
            return False
        
        try:
            windows = gw.getWindowsWithTitle(title_contains)
            if windows:
                win = windows[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to focus window: {e}")
            return False
    
    def minimize_window(self, title_contains: Optional[str] = None) -> bool:
        """Minimize a window (active if no title specified)."""
        if not self._available:
            return False
        
        try:
            if title_contains:
                windows = gw.getWindowsWithTitle(title_contains)
                if windows:
                    windows[0].minimize()
                    return True
            else:
                win = gw.getActiveWindow()
                if win:
                    win.minimize()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to minimize window: {e}")
            return False
    
    def maximize_window(self, title_contains: Optional[str] = None) -> bool:
        """Maximize a window."""
        if not self._available:
            return False
        
        try:
            if title_contains:
                windows = gw.getWindowsWithTitle(title_contains)
                if windows:
                    windows[0].maximize()
                    return True
            else:
                win = gw.getActiveWindow()
                if win:
                    win.maximize()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to maximize window: {e}")
            return False
    
    def close_window(self, title_contains: Optional[str] = None) -> bool:
        """Close a window."""
        if not self._available:
            return False
        
        try:
            if title_contains:
                windows = gw.getWindowsWithTitle(title_contains)
                if windows:
                    windows[0].close()
                    return True
            else:
                win = gw.getActiveWindow()
                if win:
                    win.close()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to close window: {e}")
            return False


class InputController:
    """
    Controls keyboard and mouse input.
    """
    
    def __init__(self):
        self._available = PYAUTOGUI_AVAILABLE
        
        if self._available:
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def type_text(self, text: str, interval: float = 0.02) -> bool:
        """Type text."""
        if not self._available:
            return False
        
        try:
            pyautogui.typewrite(text, interval=interval)
            return True
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def press_key(self, key: str) -> bool:
        """Press a single key."""
        if not self._available:
            return False
        
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            logger.error(f"Failed to press key: {e}")
            return False
    
    def hotkey(self, *keys: str) -> bool:
        """Press a key combination."""
        if not self._available:
            return False
        
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            logger.error(f"Failed to press hotkey: {e}")
            return False
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> bool:
        """Click at position."""
        if not self._available:
            return False
        
        try:
            pyautogui.click(x, y, button=button)
            return True
        except Exception as e:
            logger.error(f"Failed to click: {e}")
            return False
    
    def move_mouse(self, x: int, y: int, duration: float = 0.25) -> bool:
        """Move mouse to position."""
        if not self._available:
            return False
        
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return False
    
    def scroll(self, clicks: int) -> bool:
        """Scroll mouse wheel."""
        if not self._available:
            return False
        
        try:
            pyautogui.scroll(clicks)
            return True
        except Exception as e:
            logger.error(f"Failed to scroll: {e}")
            return False


class ScreenController:
    """
    Controls screen capture and display.
    """
    
    def __init__(self, screenshot_dir: Optional[Path] = None):
        self._available = MSS_AVAILABLE
        self.screenshot_dir = screenshot_dir or Path.home() / "Pictures" / "Screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def take_screenshot(
        self,
        filename: Optional[str] = None,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> Optional[Path]:
        """
        Take a screenshot.
        
        Args:
            filename: Optional filename (auto-generated if not provided).
            region: Optional region (x, y, width, height).
            
        Returns:
            Path to screenshot file.
        """
        if not self._available:
            return None
        
        try:
            with mss.mss() as sct:
                if filename is None:
                    filename = f"screenshot_{int(time.time())}.png"
                
                filepath = self.screenshot_dir / filename
                
                if region:
                    monitor = {
                        "left": region[0],
                        "top": region[1],
                        "width": region[2],
                        "height": region[3],
                    }
                    sct.shot(mon=monitor, output=str(filepath))
                else:
                    sct.shot(output=str(filepath))
                
                logger.info(f"Screenshot saved: {filepath}")
                return filepath
        
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    def get_screen_size(self) -> Tuple[int, int]:
        """Get screen dimensions."""
        if not self._available:
            return (0, 0)
        
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # Primary monitor
                return (monitor["width"], monitor["height"])
        except Exception:
            return (0, 0)


class ClipboardController:
    """
    Controls clipboard operations.
    """
    
    def __init__(self):
        self._available = PYPERCLIP_AVAILABLE
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def copy(self, text: str) -> bool:
        """Copy text to clipboard."""
        if not self._available:
            return False
        
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            logger.error(f"Failed to copy to clipboard: {e}")
            return False
    
    def paste(self) -> Optional[str]:
        """Get text from clipboard."""
        if not self._available:
            return None
        
        try:
            return pyperclip.paste()
        except Exception as e:
            logger.error(f"Failed to paste from clipboard: {e}")
            return None


class VolumeController:
    """
    Controls system volume (Windows).
    """
    
    def __init__(self):
        self._available = os.name == 'nt'
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    def set_volume(self, level: int) -> bool:
        """Set volume level (0-100)."""
        if not self._available:
            return False
        
        try:
            # Use nircmd if available, otherwise use PowerShell
            level = max(0, min(100, level))
            
            # PowerShell method
            script = f"""
            $obj = New-Object -ComObject WScript.Shell
            1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
            1..{level // 2} | ForEach-Object {{ $obj.SendKeys([char]175) }}
            """
            subprocess.run(["powershell", "-Command", script], capture_output=True)
            return True
        except Exception as e:
            logger.error(f"Failed to set volume: {e}")
            return False
    
    def mute(self) -> bool:
        """Mute system audio."""
        if not self._available:
            return False
        
        try:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.press('volumemute')
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to mute: {e}")
            return False
    
    def volume_up(self, steps: int = 1) -> bool:
        """Increase volume."""
        if not self._available or not PYAUTOGUI_AVAILABLE:
            return False
        
        try:
            for _ in range(steps):
                pyautogui.press('volumeup')
            return True
        except Exception as e:
            logger.error(f"Failed to increase volume: {e}")
            return False
    
    def volume_down(self, steps: int = 1) -> bool:
        """Decrease volume."""
        if not self._available or not PYAUTOGUI_AVAILABLE:
            return False
        
        try:
            for _ in range(steps):
                pyautogui.press('volumedown')
            return True
        except Exception as e:
            logger.error(f"Failed to decrease volume: {e}")
            return False


class SystemController:
    """
    Unified system controller combining all sub-controllers.
    """
    
    def __init__(
        self,
        allowed_apps: Optional[List[str]] = None,
        screenshot_dir: Optional[Path] = None,
    ):
        """
        Initialize system controller.
        
        Args:
            allowed_apps: List of allowed applications.
            screenshot_dir: Directory for screenshots.
        """
        self.apps = ApplicationController(allowed_apps)
        self.windows = WindowController()
        self.input = InputController()
        self.screen = ScreenController(screenshot_dir)
        self.clipboard = ClipboardController()
        self.volume = VolumeController()
    
    def get_status(self) -> Dict[str, bool]:
        """Get availability status of all controllers."""
        return {
            "apps": True,
            "windows": self.windows.is_available,
            "input": self.input.is_available,
            "screen": self.screen.is_available,
            "clipboard": self.clipboard.is_available,
            "volume": self.volume.is_available,
        }
