#!/usr/bin/env python3
"""
JARVIS Import Verification Script

Systematically tests all module imports to identify:
- Missing dependencies
- Circular imports
- Typos in import statements
- Optional dependency handling issues

Run with: python scripts/verify_imports.py
"""

import sys
import os
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Results tracking
results: Dict[str, List] = {
    "success": [],
    "failed": [],
    "optional_missing": [],
}


def test_import(module_name: str, optional: bool = False) -> Tuple[bool, str]:
    """Test importing a module and return success status and message."""
    try:
        importlib.import_module(module_name)
        return True, "OK"
    except ImportError as e:
        if optional:
            return True, f"Optional (not installed): {e}"
        return False, f"ImportError: {e}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def verify_core_dependencies():
    """Verify core Python dependencies are installed."""
    print("\n" + "=" * 60)
    print("CORE DEPENDENCIES (Required)")
    print("=" * 60)
    
    # These are REQUIRED - app won't start without them
    core_deps = [
        ("yaml", "PyYAML"),
        ("dotenv", "python-dotenv"),
        ("loguru", "loguru"),
        ("pydantic", "pydantic"),
        ("pydantic_settings", "pydantic-settings"),
        ("httpx", "httpx"),
        ("aiofiles", "aiofiles"),
        ("requests", "requests"),
        ("aiohttp", "aiohttp"),
    ]
    
    all_ok = True
    for import_name, package_name in core_deps:
        success, msg = test_import(import_name)
        status = "✓" if success else "✗"
        print(f"  {status} {import_name} ({package_name}): {msg}")
        if not success:
            results["failed"].append((import_name, f"REQUIRED: {msg}"))
            print(f"    → Install with: pip install {package_name}")
            all_ok = False
        else:
            results["success"].append(import_name)
    
    return all_ok


def verify_optional_dependencies():
    """Verify optional dependencies with graceful handling."""
    print("\n" + "=" * 60)
    print("OPTIONAL DEPENDENCIES")
    print("=" * 60)
    
    optional_deps = [
        # LLM
        ("langchain", "langchain"),
        ("langchain_groq", "langchain-groq"),
        ("groq", "groq"),
        ("google.generativeai", "google-generativeai"),
        ("mistralai", "mistralai"),
        # API
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("jose", "python-jose"),
        ("passlib", "passlib"),
        ("bcrypt", "bcrypt"),
        # Voice
        ("numpy", "numpy"),
        ("sounddevice", "sounddevice"),
        ("faster_whisper", "faster-whisper"),
        ("edge_tts", "edge-tts"),
        ("torch", "torch"),
        # Vision
        ("cv2", "opencv-python"),
        ("face_recognition", "face-recognition"),
        # Memory
        ("chromadb", "chromadb"),
        # Other
        ("telegram", "python-telegram-bot"),
        ("zeroconf", "zeroconf"),
    ]
    
    for import_name, package_name in optional_deps:
        success, msg = test_import(import_name, optional=True)
        status = "✓" if success and "Optional" not in msg else "○"
        print(f"  {status} {import_name}: {msg}")
        if "Optional" in msg:
            results["optional_missing"].append((import_name, package_name))
        else:
            results["success"].append(import_name)


def verify_jarvis_modules():
    """Verify all JARVIS source modules import correctly."""
    print("\n" + "=" * 60)
    print("JARVIS MODULES")
    print("=" * 60)
    
    # List of all JARVIS modules to test (based on actual files)
    modules = [
        # Core
        "src",
        "src.core",
        "src.core.config",
        "src.core.llm",
        "src.core.llm_router",
        "src.core.llm_providers",
        "src.core.cache",
        "src.core.streaming",
        "src.core.performance",
        "src.core.performance_integration",
        "src.core.dashboard",
        "src.core.health_monitor",
        "src.core.help_system",
        "src.core.internal_api",
        "src.core.logger",
        
        # Auth
        "src.auth",
        "src.auth.auth_manager",
        "src.auth.face_auth",
        "src.auth.voice_auth",
        "src.auth.liveness",
        "src.auth.session",
        
        # Voice
        "src.voice",
        "src.voice.wake_word",
        "src.voice.stt",
        "src.voice.tts",
        "src.voice.pipeline",
        
        # Agents
        "src.agents",
        "src.agents.base",
        "src.agents.specialized",
        "src.agents.tools",
        "src.agents.tools_enhanced",
        "src.agents.supervisor",
        "src.agents.supervisor_enhanced",
        
        # Memory
        "src.memory",
        "src.memory.conversation",
        "src.memory.vector_store",
        "src.memory.episodic",
        
        # System
        "src.system",
        "src.system.browser",
        
        # IoT
        "src.iot",
        "src.iot.esp32_controller",
        "src.iot.esp32_enhanced",
        "src.iot.controller_enhanced",
        
        # Telegram
        "src.telegram",
        "src.telegram.bot",
        "src.telegram.bot_enhanced",
        
        # Proactive
        "src.proactive",
        
        # Utils
        "src.utils",
        
        # API
        "src.api",
        "src.api.app",
        "src.api.auth",
        "src.api.routes",
        "src.api.websocket",
        "src.api.voice",
        "src.api.notifications",
        "src.api.models",
        
        # Main
        "src.jarvis",
        "src.jarvis_unified",
    ]
    
    for module in modules:
        success, msg = test_import(module)
        status = "✓" if success else "✗"
        print(f"  {status} {module}: {msg}")
        if success:
            results["success"].append(module)
        else:
            results["failed"].append((module, msg))


def verify_circular_imports():
    """Check for potential circular import issues."""
    print("\n" + "=" * 60)
    print("CIRCULAR IMPORT CHECK")
    print("=" * 60)
    
    # Test importing in different orders to detect circular imports
    test_orders = [
        ["src.api", "src.core", "src.jarvis_unified"],
        ["src.jarvis_unified", "src.api", "src.core"],
        ["src.agents", "src.memory", "src.core"],
    ]
    
    for order in test_orders:
        # Clear cached imports
        for mod in list(sys.modules.keys()):
            if mod.startswith("src."):
                del sys.modules[mod]
        
        try:
            for module in order:
                importlib.import_module(module)
            print(f"  ✓ Order {' → '.join(order)}: OK")
        except Exception as e:
            print(f"  ✗ Order {' → '.join(order)}: {e}")
            results["failed"].append((f"circular:{order}", str(e)))


def print_summary():
    """Print summary of verification results."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print(f"\n  ✓ Successful imports: {len(results['success'])}")
    print(f"  ○ Optional (not installed): {len(results['optional_missing'])}")
    print(f"  ✗ Failed (required): {len(results['failed'])}")
    
    if results["failed"]:
        print("\n  FAILED IMPORTS (must fix):")
        for module, error in results["failed"]:
            print(f"    - {module}: {error}")
        print("\n  To fix, run:")
        print("    pip install -r requirements-core.txt")
    
    if results["optional_missing"]:
        print("\n  OPTIONAL DEPENDENCIES NOT INSTALLED:")
        for module, package in results["optional_missing"][:10]:  # Show first 10
            print(f"    - {module} (pip install {package})")
        if len(results["optional_missing"]) > 10:
            print(f"    ... and {len(results['optional_missing']) - 10} more")
    
    print("\n" + "=" * 60)
    
    if results["failed"]:
        print("STATUS: FAILED - Fix the above required imports")
        print("\nQuick fix:")
        print("  pip install -r requirements-core.txt")
        return 1
    else:
        print("STATUS: PASSED - All required imports successful")
        if results["optional_missing"]:
            print("\nTo enable more features:")
            print("  pip install -r requirements-api.txt    # Mobile API")
            print("  pip install -r requirements-voice.txt  # Voice features")
            print("  pip install -r requirements-windows.txt  # All features (Windows)")
        return 0


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("JARVIS Import Verification")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Project: {PROJECT_ROOT}")
    
    verify_core_dependencies()
    verify_optional_dependencies()
    verify_jarvis_modules()
    verify_circular_imports()
    
    return print_summary()


if __name__ == "__main__":
    sys.exit(main())
