#!/usr/bin/env python3
"""
JARVIS Setup Verification Script

Checks that all dependencies are installed and configured correctly.
Run this after installation to verify your setup.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def check_python_version():
    """Check Python version."""
    print("Checking Python version...", end=" ")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor} (need 3.11+)")
        return False


def check_core_dependencies():
    """Check core dependencies."""
    print("\n--- Core Dependencies ---")
    
    dependencies = [
        ("pydantic", "Configuration"),
        ("yaml", "YAML parsing"),
        ("loguru", "Logging"),
        ("dotenv", "Environment variables"),
    ]
    
    all_ok = True
    for module, purpose in dependencies:
        try:
            __import__(module)
            print(f"✓ {module} - {purpose}")
        except ImportError:
            print(f"✗ {module} - {purpose} (not installed)")
            all_ok = False
    
    return all_ok


def check_llm_dependencies():
    """Check LLM dependencies."""
    print("\n--- LLM Dependencies ---")
    
    dependencies = [
        ("groq", "Groq API"),
        ("anthropic", "Anthropic API"),
        ("ollama", "Ollama local LLM"),
        ("langchain_core", "LangChain Core"),
        ("langgraph", "LangGraph"),
    ]
    
    all_ok = True
    for module, purpose in dependencies:
        try:
            __import__(module)
            print(f"✓ {module} - {purpose}")
        except ImportError:
            print(f"✗ {module} - {purpose} (not installed)")
            all_ok = False
    
    return all_ok


def check_voice_dependencies():
    """Check voice pipeline dependencies."""
    print("\n--- Voice Dependencies ---")
    
    dependencies = [
        ("openwakeword", "Wake word detection"),
        ("faster_whisper", "Speech-to-text"),
        ("edge_tts", "Text-to-speech"),
        ("sounddevice", "Audio I/O"),
        ("soundfile", "Audio file handling"),
        ("torch", "PyTorch (for VAD)"),
    ]
    
    all_ok = True
    for module, purpose in dependencies:
        try:
            __import__(module)
            print(f"✓ {module} - {purpose}")
        except ImportError:
            print(f"✗ {module} - {purpose} (not installed)")
            all_ok = False
    
    return all_ok


def check_auth_dependencies():
    """Check authentication dependencies."""
    print("\n--- Authentication Dependencies ---")
    
    dependencies = [
        ("face_recognition", "Face recognition"),
        ("cv2", "OpenCV"),
        ("mediapipe", "MediaPipe (liveness)"),
        ("resemblyzer", "Voice verification"),
    ]
    
    all_ok = True
    for module, purpose in dependencies:
        try:
            __import__(module)
            print(f"✓ {module} - {purpose}")
        except ImportError:
            print(f"✗ {module} - {purpose} (not installed)")
            all_ok = False
    
    return all_ok


def check_system_dependencies():
    """Check system control dependencies."""
    print("\n--- System Control Dependencies ---")
    
    dependencies = [
        ("pyautogui", "Keyboard/mouse control"),
        ("pygetwindow", "Window management"),
        ("psutil", "Process management"),
        ("mss", "Screenshot capture"),
        ("pyperclip", "Clipboard"),
    ]
    
    all_ok = True
    for module, purpose in dependencies:
        try:
            __import__(module)
            print(f"✓ {module} - {purpose}")
        except ImportError:
            print(f"✗ {module} - {purpose} (not installed)")
            all_ok = False
    
    return all_ok


def check_memory_dependencies():
    """Check memory system dependencies."""
    print("\n--- Memory Dependencies ---")
    
    dependencies = [
        ("chromadb", "Vector store"),
        ("sentence_transformers", "Embeddings"),
        ("sqlite3", "SQLite (built-in)"),
    ]
    
    all_ok = True
    for module, purpose in dependencies:
        try:
            __import__(module)
            print(f"✓ {module} - {purpose}")
        except ImportError:
            print(f"✗ {module} - {purpose} (not installed)")
            all_ok = False
    
    return all_ok


def check_config():
    """Check configuration files."""
    print("\n--- Configuration ---")
    
    config_file = PROJECT_ROOT / "config" / "settings.yaml"
    env_file = PROJECT_ROOT / ".env"
    env_example = PROJECT_ROOT / ".env.example"
    
    all_ok = True
    
    if config_file.exists():
        print(f"✓ settings.yaml exists")
    else:
        print(f"✗ settings.yaml missing")
        all_ok = False
    
    if env_file.exists():
        print(f"✓ .env exists")
        
        # Check for API keys
        from dotenv import load_dotenv
        import os
        load_dotenv(env_file)
        
        if os.getenv("GROQ_API_KEY"):
            print(f"  ✓ GROQ_API_KEY configured")
        else:
            print(f"  ⚠ GROQ_API_KEY not set (primary LLM)")
    else:
        print(f"⚠ .env missing (copy from .env.example)")
        if env_example.exists():
            print(f"  Run: copy .env.example .env")
    
    return all_ok


def check_ollama():
    """Check if Ollama is running."""
    print("\n--- Ollama Status ---")
    
    try:
        import httpx
        response = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            print(f"✓ Ollama running")
            if models:
                print(f"  Available models: {', '.join(models[:5])}")
            else:
                print(f"  ⚠ No models installed. Run: ollama pull llama3.2")
            return True
    except Exception:
        pass
    
    print(f"⚠ Ollama not running (optional, for offline LLM)")
    print(f"  Install from: https://ollama.ai")
    return False


def check_audio_devices():
    """Check audio devices."""
    print("\n--- Audio Devices ---")
    
    try:
        import sounddevice as sd
        
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        output_devices = [d for d in devices if d['max_output_channels'] > 0]
        
        print(f"✓ Found {len(input_devices)} input device(s)")
        if input_devices:
            default_input = sd.query_devices(kind='input')
            print(f"  Default: {default_input['name']}")
        
        print(f"✓ Found {len(output_devices)} output device(s)")
        if output_devices:
            default_output = sd.query_devices(kind='output')
            print(f"  Default: {default_output['name']}")
        
        return len(input_devices) > 0 and len(output_devices) > 0
    except Exception as e:
        print(f"✗ Audio check failed: {e}")
        return False


def check_camera():
    """Check camera availability."""
    print("\n--- Camera ---")
    
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print(f"✓ Camera available ({frame.shape[1]}x{frame.shape[0]})")
                return True
        print(f"⚠ Camera not available")
        return False
    except Exception as e:
        print(f"✗ Camera check failed: {e}")
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("JARVIS Setup Verification")
    print("=" * 60)
    
    results = {}
    
    results["python"] = check_python_version()
    results["core"] = check_core_dependencies()
    results["llm"] = check_llm_dependencies()
    results["voice"] = check_voice_dependencies()
    results["auth"] = check_auth_dependencies()
    results["system"] = check_system_dependencies()
    results["memory"] = check_memory_dependencies()
    results["config"] = check_config()
    results["ollama"] = check_ollama()
    results["audio"] = check_audio_devices()
    results["camera"] = check_camera()
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    critical = ["python", "core", "config"]
    important = ["llm", "voice", "memory"]
    optional = ["auth", "system", "ollama", "audio", "camera"]
    
    critical_ok = all(results.get(k, False) for k in critical)
    important_ok = all(results.get(k, False) for k in important)
    
    if critical_ok and important_ok:
        print("\n✓ All critical and important checks passed!")
        print("\nYou can run JARVIS with:")
        print("  python run.py --text    # Text mode (no audio)")
        print("  python run.py           # Full mode with voice")
    elif critical_ok:
        print("\n⚠ Critical checks passed, but some features may be limited.")
        print("\nYou can try text mode:")
        print("  python run.py --text")
    else:
        print("\n✗ Critical checks failed. Please install missing dependencies:")
        print("  pip install -r requirements.txt")
    
    # Show what's missing
    missing = [k for k, v in results.items() if not v]
    if missing:
        print(f"\nMissing/unavailable: {', '.join(missing)}")


if __name__ == "__main__":
    main()
