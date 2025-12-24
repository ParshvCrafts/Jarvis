#!/usr/bin/env python3
"""
JARVIS Installation Script

Cross-platform installer that:
1. Detects operating system
2. Checks Python version
3. Creates virtual environment (optional)
4. Installs appropriate requirements tier
5. Tests basic imports
6. Reports available features
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# Minimum Python version
MIN_PYTHON = (3, 10)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Colors for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"  {text}")

def check_python_version():
    """Check if Python version meets requirements."""
    print_header("Checking Python Version")
    
    version = sys.version_info[:2]
    version_str = f"{version[0]}.{version[1]}"
    
    if version >= MIN_PYTHON:
        print_success(f"Python {version_str} detected (minimum: {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
        return True
    else:
        print_error(f"Python {version_str} detected, but {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required")
        return False

def detect_os():
    """Detect operating system."""
    print_header("Detecting Operating System")
    
    system = platform.system()
    
    if system == "Windows":
        print_success("Windows detected")
        print_info("Will avoid packages requiring C++ compilation")
        return "windows"
    elif system == "Darwin":
        print_success("macOS detected")
        return "macos"
    elif system == "Linux":
        print_success("Linux detected")
        return "linux"
    else:
        print_warning(f"Unknown OS: {system}")
        return "unknown"

def check_pip():
    """Check if pip is available."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                      capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def install_requirements(tier: str):
    """Install requirements for the specified tier."""
    print_header(f"Installing {tier.upper()} Dependencies")
    
    req_file = PROJECT_ROOT / f"requirements-{tier}.txt"
    
    if not req_file.exists():
        print_error(f"Requirements file not found: {req_file}")
        return False
    
    print_info(f"Installing from {req_file.name}...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print_success(f"Successfully installed {tier} dependencies")
            return True
        else:
            print_error(f"Failed to install some packages")
            print_info("Error output:")
            for line in result.stderr.split('\n')[:10]:
                if line.strip():
                    print_info(f"  {line}")
            return False
            
    except Exception as e:
        print_error(f"Installation failed: {e}")
        return False

def test_imports():
    """Test if core imports work."""
    print_header("Testing Core Imports")
    
    results = {}
    
    # Core imports (must work)
    core_tests = [
        ("pydantic", "Configuration"),
        ("yaml", "YAML parsing"),
        ("dotenv", "Environment variables"),
        ("loguru", "Logging"),
        ("httpx", "HTTP client"),
        ("requests", "HTTP requests"),
    ]
    
    for module, description in core_tests:
        try:
            __import__(module)
            print_success(f"{description} ({module})")
            results[module] = True
        except ImportError:
            print_error(f"{description} ({module}) - NOT INSTALLED")
            results[module] = False
    
    # Optional imports
    print("\n  Optional dependencies:")
    optional_tests = [
        ("fastapi", "API Server"),
        ("numpy", "Voice Processing"),
        ("sounddevice", "Audio I/O"),
        ("cv2", "Computer Vision"),
        ("langchain", "LLM Framework"),
        ("chromadb", "Vector Store"),
    ]
    
    for module, description in optional_tests:
        try:
            __import__(module)
            print_success(f"{description} ({module})")
            results[module] = True
        except ImportError:
            print_warning(f"{description} ({module}) - not installed")
            results[module] = False
    
    return results

def test_jarvis_import():
    """Test if JARVIS modules can be imported."""
    print_header("Testing JARVIS Modules")
    
    # Add project to path
    sys.path.insert(0, str(PROJECT_ROOT))
    
    try:
        from src.core.config import config
        print_success("Core configuration loaded")
        return True
    except ImportError as e:
        print_error(f"Failed to import core config: {e}")
        return False
    except Exception as e:
        print_warning(f"Config loaded with warnings: {e}")
        return True

def show_available_features(import_results):
    """Show which features are available based on installed packages."""
    print_header("Available Features")
    
    features = {
        "Text Mode": all([import_results.get(m, False) for m in ["pydantic", "yaml", "loguru"]]),
        "API Server": import_results.get("fastapi", False),
        "Voice Input": all([import_results.get(m, False) for m in ["numpy", "sounddevice"]]),
        "Face Auth": import_results.get("cv2", False),
        "LLM Agents": import_results.get("langchain", False),
        "Vector Memory": import_results.get("chromadb", False),
    }
    
    for feature, available in features.items():
        if available:
            print_success(feature)
        else:
            print_warning(f"{feature} - install additional dependencies")
    
    return features

def show_next_steps(os_type, features):
    """Show next steps for the user."""
    print_header("Next Steps")
    
    if features.get("Text Mode"):
        print_success("JARVIS is ready to run in text mode!")
        print_info("")
        print_info("  Run JARVIS:")
        print_info("    python run.py --text")
        print_info("")
    else:
        print_error("Core dependencies missing. Please run:")
        print_info("    pip install -r requirements-core.txt")
        print_info("")
        return
    
    if not features.get("API Server"):
        print_info("  To enable Mobile API:")
        print_info("    pip install -r requirements-api.txt")
        print_info("")
    
    if not features.get("Voice Input"):
        print_info("  To enable Voice features:")
        print_info("    pip install -r requirements-voice.txt")
        print_info("")
    
    print_info("  For all features:")
    if os_type == "windows":
        print_info("    pip install -r requirements-windows.txt")
    else:
        print_info("    pip install -r requirements-full.txt")
    
    print_info("")
    print_info("  Configuration:")
    print_info("    1. Copy .env.example to .env")
    print_info("    2. Add your API keys (at least GROQ_API_KEY)")
    print_info("    3. Run: python run.py --check-config")

def main():
    """Main installation flow."""
    print(f"\n{Colors.BOLD}JARVIS Installation Script{Colors.END}")
    print(f"Project: {PROJECT_ROOT}\n")
    
    # Check Python version
    if not check_python_version():
        print_error("\nPlease install Python 3.10 or later")
        sys.exit(1)
    
    # Detect OS
    os_type = detect_os()
    
    # Check pip
    if not check_pip():
        print_error("pip not available. Please install pip first.")
        sys.exit(1)
    
    # Ask user which tier to install
    print_header("Installation Options")
    print("  1. Core only (text mode, minimal)")
    print("  2. Core + API (mobile app support)")
    print("  3. Core + Voice (voice interaction)")
    print("  4. Full (all features)")
    print("  5. Skip installation (just test)")
    print("")
    
    choice = input("Select option [1-5] (default: 1): ").strip() or "1"
    
    install_success = True
    
    if choice == "1":
        install_success = install_requirements("core")
    elif choice == "2":
        install_success = install_requirements("api")
    elif choice == "3":
        install_success = install_requirements("voice")
    elif choice == "4":
        if os_type == "windows":
            install_success = install_requirements("windows")
        else:
            install_success = install_requirements("full")
    elif choice == "5":
        print_info("Skipping installation...")
    else:
        print_warning(f"Invalid choice: {choice}, defaulting to core")
        install_success = install_requirements("core")
    
    # Test imports
    import_results = test_imports()
    
    # Test JARVIS import
    jarvis_ok = test_jarvis_import()
    
    # Show available features
    features = show_available_features(import_results)
    
    # Show next steps
    show_next_steps(os_type, features)
    
    # Final status
    print_header("Installation Complete")
    
    core_ok = all([import_results.get(m, False) for m in ["pydantic", "yaml", "loguru"]])
    
    if core_ok and jarvis_ok:
        print_success("JARVIS is ready to use!")
        sys.exit(0)
    else:
        print_warning("Some dependencies are missing. See above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
