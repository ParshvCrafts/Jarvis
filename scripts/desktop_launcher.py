"""
JARVIS Desktop App Launcher

Launches JARVIS in a dedicated desktop window (browser app mode).
This provides a native app-like experience without browser chrome.

Usage:
    python scripts/desktop_launcher.py [--text] [--port PORT]

Options:
    --text      Start in text mode (no voice)
    --port      API port (default: 8000)
    --no-sound  Disable startup sound
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
import socket
from pathlib import Path


# Browser paths by platform
BROWSER_PATHS = {
    "Windows": [
        # Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        # Edge
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        # Brave
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    ],
    "Darwin": [  # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ],
    "Linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/microsoft-edge",
        "/usr/bin/brave-browser",
    ],
}


def find_browser() -> str | None:
    """Find an installed Chromium-based browser."""
    system = platform.system()
    paths = BROWSER_PATHS.get(system, [])
    
    for path in paths:
        expanded = os.path.expandvars(path)
        if os.path.exists(expanded):
            return expanded
    
    # Try to find in PATH
    for browser in ["chrome", "google-chrome", "chromium", "msedge", "brave"]:
        found = shutil.which(browser)
        if found:
            return found
    
    return None


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def wait_for_server(port: int, timeout: int = 30) -> bool:
    """Wait for server to be ready."""
    print(f"Waiting for JARVIS server on port {port}...")
    start = time.time()
    
    while time.time() - start < timeout:
        if is_port_in_use(port):
            print("Server is ready!")
            return True
        time.sleep(0.5)
        print(".", end="", flush=True)
    
    print("\nTimeout waiting for server")
    return False


def launch_browser_app(url: str, title: str = "JARVIS") -> subprocess.Popen | None:
    """Launch browser in app mode."""
    browser = find_browser()
    
    if not browser:
        print("ERROR: No Chromium-based browser found.")
        print("Please install Chrome, Edge, or Brave.")
        return None
    
    print(f"Using browser: {browser}")
    
    # App mode arguments
    args = [
        browser,
        f"--app={url}",
        f"--app-name={title}",
        "--new-window",
        "--disable-extensions",
        "--disable-plugins",
        "--start-maximized",
    ]
    
    # Platform-specific adjustments
    if platform.system() == "Windows":
        # Hide console window on Windows
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return subprocess.Popen(args, startupinfo=startupinfo)
    else:
        return subprocess.Popen(args)


def start_jarvis_backend(text_mode: bool = False, port: int = 8000) -> subprocess.Popen:
    """Start the JARVIS backend server."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Build command
    cmd = [sys.executable, "run.py"]
    if text_mode:
        cmd.append("--text")
    
    # Set environment for API port
    env = os.environ.copy()
    env["JARVIS_API_PORT"] = str(port)
    
    print(f"Starting JARVIS backend...")
    print(f"Command: {' '.join(cmd)}")
    print(f"Working directory: {project_root}")
    
    # Start backend process
    if platform.system() == "Windows":
        # Create new console window for backend
        return subprocess.Popen(
            cmd,
            cwd=project_root,
            env=env,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    else:
        return subprocess.Popen(
            cmd,
            cwd=project_root,
            env=env,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Launch JARVIS in desktop app mode"
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Start in text mode (no voice)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API port (default: 8000)",
    )
    parser.add_argument(
        "--pwa-port",
        type=int,
        default=3000,
        help="PWA development server port (default: 3000)",
    )
    parser.add_argument(
        "--no-backend",
        action="store_true",
        help="Don't start backend (assume already running)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser (just start backend)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("JARVIS Desktop Launcher")
    print("=" * 60)
    print()
    
    backend_process = None
    browser_process = None
    
    try:
        # Start backend if needed
        if not args.no_backend:
            if is_port_in_use(args.port):
                print(f"Port {args.port} already in use - assuming JARVIS is running")
            else:
                backend_process = start_jarvis_backend(
                    text_mode=args.text,
                    port=args.port,
                )
                
                # Wait for server to be ready
                if not wait_for_server(args.port, timeout=30):
                    print("Failed to start JARVIS backend")
                    if backend_process:
                        backend_process.terminate()
                    return 1
        
        # Launch browser in app mode
        if not args.no_browser:
            # Check if PWA dev server is running
            if is_port_in_use(args.pwa_port):
                url = f"http://localhost:{args.pwa_port}"
                print(f"PWA dev server detected at {url}")
            else:
                # Use API server directly (basic UI)
                url = f"http://localhost:{args.port}"
                print(f"Using API server at {url}")
                print("TIP: Run 'cd mobile && npm run dev' for full PWA experience")
            
            print()
            print(f"Opening JARVIS in app mode: {url}")
            browser_process = launch_browser_app(url, "JARVIS")
            
            if not browser_process:
                print("Failed to launch browser")
                print(f"Please open {url} manually in your browser")
        
        print()
        print("JARVIS is running!")
        print("Press Ctrl+C to stop")
        print()
        
        # Keep running until interrupted
        if backend_process:
            backend_process.wait()
        elif browser_process:
            browser_process.wait()
        else:
            # Just wait for interrupt
            while True:
                time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    
    finally:
        # Cleanup
        if browser_process:
            try:
                browser_process.terminate()
            except:
                pass
        
        if backend_process:
            try:
                backend_process.terminate()
                backend_process.wait(timeout=5)
            except:
                backend_process.kill()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
