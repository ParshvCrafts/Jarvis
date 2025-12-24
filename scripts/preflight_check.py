#!/usr/bin/env python3
"""
JARVIS Pre-Flight Check Script

Comprehensive validation of system requirements, configuration,
modules, and hardware before running JARVIS.

Usage:
    python scripts/preflight_check.py [--verbose] [--fix] [--json]

Options:
    --verbose   Show detailed output for each check
    --fix       Attempt to fix issues automatically where possible
    --json      Output results as JSON (for automation)
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


class CheckStatus(Enum):
    """Status of a pre-flight check."""
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class CheckResult:
    """Result of a single check."""
    name: str
    status: CheckStatus
    message: str
    details: str = ""
    fix_instruction: str = ""
    fix_command: str = ""
    duration_ms: float = 0.0


@dataclass
class CheckCategory:
    """Category of checks with results."""
    name: str
    results: List[CheckResult] = field(default_factory=list)
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.PASS)
    
    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.WARN)
    
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.FAIL)
    
    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == CheckStatus.SKIP)


class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    
    @classmethod
    def disable(cls):
        """Disable colors (for non-TTY output)."""
        cls.RESET = ""
        cls.BOLD = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.CYAN = ""


class PreflightChecker:
    """
    Comprehensive pre-flight checker for JARVIS.
    
    Validates:
    - System requirements (Python, OS, hardware)
    - Configuration files and API keys
    - Module imports and dependencies
    - Hardware detection (audio, camera, IoT)
    """
    
    # Minimum requirements
    MIN_PYTHON_VERSION = (3, 9)
    MIN_DISK_GB = 1.0
    MIN_RAM_GB = 2.0
    
    # Required packages with minimum versions
    REQUIRED_PACKAGES = {
        "loguru": None,
        "pydantic": "2.0.0",
        "pyyaml": None,
        "python-dotenv": None,
        "aiohttp": None,
        "httpx": None,
    }
    
    # Optional packages for specific features
    OPTIONAL_PACKAGES = {
        "sounddevice": "Audio input/output",
        "numpy": "Audio processing",
        "torch": "Wake word detection, VAD",
        "faster_whisper": "Local speech-to-text",
        "openai-whisper": "Alternative STT",
        "pyttsx3": "Text-to-speech",
        "edge_tts": "Cloud TTS",
        "opencv-python": "Face recognition",
        "face_recognition": "Face recognition",
        "chromadb": "Vector memory",
        "langchain": "Agent framework",
        "langgraph": "Agent orchestration",
        "playwright": "Browser automation",
        "pyautogui": "System control",
        "python-telegram-bot": "Telegram integration",
        "zeroconf": "IoT device discovery",
        "psutil": "System monitoring",
    }
    
    # Core modules to check
    CORE_MODULES = [
        "src.core",
        "src.core.config",
        "src.core.llm",
        "src.voice",
        "src.agents",
        "src.memory",
        "src.system",
    ]
    
    # Enhanced modules (preferred)
    ENHANCED_MODULES = [
        ("src.voice.pipeline_enhanced", "EnhancedVoicePipeline"),
        ("src.voice.stt_enhanced", "EnhancedSpeechToText"),
        ("src.voice.wake_word_enhanced", "EnhancedWakeWordDetector"),
        ("src.agents.supervisor_enhanced", "EnhancedSupervisor"),
        ("src.iot.esp32_enhanced", "EnhancedESP32Controller"),
    ]
    
    def __init__(self, project_root: Optional[Path] = None, verbose: bool = False):
        self.project_root = project_root or Path(__file__).parent.parent
        self.verbose = verbose
        self.categories: List[CheckCategory] = []
        self.start_time = time.time()
        
        # Add project root to path
        sys.path.insert(0, str(self.project_root))
    
    def run_check(
        self,
        name: str,
        check_func: Callable[[], Tuple[CheckStatus, str, str]],
    ) -> CheckResult:
        """Run a single check and capture result."""
        start = time.time()
        
        try:
            status, message, details = check_func()
            fix_instruction = ""
            fix_command = ""
            
            # Extract fix info if provided in details
            if "FIX:" in details:
                parts = details.split("FIX:", 1)
                details = parts[0].strip()
                fix_instruction = parts[1].strip()
            if "CMD:" in details:
                parts = details.split("CMD:", 1)
                details = parts[0].strip()
                fix_command = parts[1].strip()
                
        except Exception as e:
            status = CheckStatus.FAIL
            message = f"Check failed with exception"
            details = str(e)
            fix_instruction = ""
            fix_command = ""
        
        duration = (time.time() - start) * 1000
        
        return CheckResult(
            name=name,
            status=status,
            message=message,
            details=details,
            fix_instruction=fix_instruction,
            fix_command=fix_command,
            duration_ms=duration,
        )
    
    # =========================================================================
    # System Requirements Checks
    # =========================================================================
    
    def check_python_version(self) -> Tuple[CheckStatus, str, str]:
        """Check Python version meets requirements."""
        version = sys.version_info
        required = self.MIN_PYTHON_VERSION
        
        if version >= required:
            return (
                CheckStatus.PASS,
                f"Python {version.major}.{version.minor}.{version.micro}",
                "",
            )
        else:
            return (
                CheckStatus.FAIL,
                f"Python {version.major}.{version.minor} (need {required[0]}.{required[1]}+)",
                f"FIX: Install Python {required[0]}.{required[1]} or newer from python.org",
            )
    
    def check_os_platform(self) -> Tuple[CheckStatus, str, str]:
        """Check operating system."""
        system = platform.system()
        release = platform.release()
        
        supported = ["Windows", "Linux", "Darwin"]
        
        if system in supported:
            return (
                CheckStatus.PASS,
                f"{system} {release}",
                "",
            )
        else:
            return (
                CheckStatus.WARN,
                f"{system} {release} (untested)",
                "JARVIS is tested on Windows, Linux, and macOS",
            )
    
    def check_disk_space(self) -> Tuple[CheckStatus, str, str]:
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.project_root)
            free_gb = free / (1024**3)
            
            if free_gb >= self.MIN_DISK_GB:
                return (
                    CheckStatus.PASS,
                    f"{free_gb:.1f} GB free",
                    "",
                )
            else:
                return (
                    CheckStatus.FAIL,
                    f"{free_gb:.1f} GB free (need {self.MIN_DISK_GB} GB)",
                    "FIX: Free up disk space by removing unused files",
                )
        except Exception as e:
            return (CheckStatus.WARN, "Could not check", str(e))
    
    def check_memory(self) -> Tuple[CheckStatus, str, str]:
        """Check available RAM."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            total_gb = mem.total / (1024**3)
            available_gb = mem.available / (1024**3)
            
            if available_gb >= self.MIN_RAM_GB:
                return (
                    CheckStatus.PASS,
                    f"{available_gb:.1f} GB available ({total_gb:.1f} GB total)",
                    "",
                )
            elif total_gb >= self.MIN_RAM_GB:
                return (
                    CheckStatus.WARN,
                    f"{available_gb:.1f} GB available (low)",
                    "Close other applications to free memory",
                )
            else:
                return (
                    CheckStatus.FAIL,
                    f"{total_gb:.1f} GB total (need {self.MIN_RAM_GB} GB)",
                    "FIX: Add more RAM or use a machine with more memory",
                )
        except ImportError:
            return (
                CheckStatus.SKIP,
                "psutil not installed",
                "CMD: pip install psutil",
            )
    
    def check_network(self) -> Tuple[CheckStatus, str, str]:
        """Check network connectivity."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return (CheckStatus.PASS, "Internet connected", "")
        except OSError:
            return (
                CheckStatus.WARN,
                "No internet connection",
                "Some features require internet (LLM APIs, web search)",
            )
    
    # =========================================================================
    # Package Checks
    # =========================================================================
    
    def check_required_package(self, package: str, min_version: Optional[str]) -> Tuple[CheckStatus, str, str]:
        """Check if a required package is installed."""
        try:
            mod = importlib.import_module(package.replace("-", "_"))
            version = getattr(mod, "__version__", "unknown")
            
            if min_version and version != "unknown":
                from packaging import version as pkg_version
                if pkg_version.parse(version) < pkg_version.parse(min_version):
                    return (
                        CheckStatus.WARN,
                        f"v{version} (need {min_version}+)",
                        f"CMD: pip install --upgrade {package}",
                    )
            
            return (CheckStatus.PASS, f"v{version}", "")
            
        except ImportError:
            return (
                CheckStatus.FAIL,
                "Not installed",
                f"CMD: pip install {package}",
            )
    
    def check_optional_package(self, package: str, feature: str) -> Tuple[CheckStatus, str, str]:
        """Check if an optional package is installed."""
        try:
            mod = importlib.import_module(package.replace("-", "_").replace("opencv-python", "cv2"))
            version = getattr(mod, "__version__", "installed")
            return (CheckStatus.PASS, f"v{version}", "")
        except ImportError:
            return (
                CheckStatus.SKIP,
                f"Not installed ({feature})",
                f"CMD: pip install {package}",
            )
    
    # =========================================================================
    # Configuration Checks
    # =========================================================================
    
    def check_env_file(self) -> Tuple[CheckStatus, str, str]:
        """Check .env file exists."""
        env_path = self.project_root / ".env"
        
        if env_path.exists():
            return (CheckStatus.PASS, "Found", "")
        else:
            example_path = self.project_root / ".env.example"
            if example_path.exists():
                return (
                    CheckStatus.FAIL,
                    "Missing",
                    "FIX: Copy .env.example to .env and fill in your API keys",
                )
            return (
                CheckStatus.FAIL,
                "Missing",
                "FIX: Create .env file with required API keys",
            )
    
    def check_settings_yaml(self) -> Tuple[CheckStatus, str, str]:
        """Check settings.yaml exists and is valid."""
        settings_path = self.project_root / "config" / "settings.yaml"
        
        if not settings_path.exists():
            return (
                CheckStatus.FAIL,
                "Missing",
                "FIX: Create config/settings.yaml from template",
            )
        
        try:
            import yaml
            with open(settings_path) as f:
                config = yaml.safe_load(f)
            
            if not config:
                return (CheckStatus.FAIL, "Empty file", "FIX: Add configuration to settings.yaml")
            
            return (CheckStatus.PASS, "Valid YAML", "")
            
        except yaml.YAMLError as e:
            return (
                CheckStatus.FAIL,
                "Invalid YAML syntax",
                f"FIX: Fix syntax error: {e}",
            )
    
    def check_api_key(self, key_name: str, env_var: str, pattern: Optional[str] = None) -> Tuple[CheckStatus, str, str]:
        """Check if an API key is configured."""
        from dotenv import load_dotenv
        load_dotenv(self.project_root / ".env")
        
        value = os.getenv(env_var, "")
        
        if not value:
            return (
                CheckStatus.WARN,
                "Not configured",
                f"FIX: Add {env_var}=your_key to .env file",
            )
        
        if value.startswith("your_") or value == "xxx":
            return (
                CheckStatus.WARN,
                "Placeholder value",
                f"FIX: Replace placeholder with actual {key_name} key",
            )
        
        if pattern and not re.match(pattern, value):
            return (
                CheckStatus.WARN,
                "Invalid format",
                f"FIX: Check {key_name} key format",
            )
        
        # Mask the key for display
        masked = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
        return (CheckStatus.PASS, f"Configured ({masked})", "")
    
    async def check_api_connectivity(self, provider: str, test_func: Callable) -> Tuple[CheckStatus, str, str]:
        """Test API connectivity for a provider."""
        try:
            result = await asyncio.wait_for(test_func(), timeout=10)
            if result:
                return (CheckStatus.PASS, "Connected", "")
            else:
                return (CheckStatus.WARN, "Connection failed", "Check API key and network")
        except asyncio.TimeoutError:
            return (CheckStatus.WARN, "Timeout", "API may be slow or unreachable")
        except Exception as e:
            return (CheckStatus.WARN, f"Error: {str(e)[:50]}", "")
    
    # =========================================================================
    # Module Checks
    # =========================================================================
    
    def check_module_import(self, module_path: str) -> Tuple[CheckStatus, str, str]:
        """Check if a module can be imported."""
        try:
            importlib.import_module(module_path)
            return (CheckStatus.PASS, "OK", "")
        except ImportError as e:
            return (
                CheckStatus.FAIL,
                "Import failed",
                f"Error: {e}",
            )
        except Exception as e:
            return (
                CheckStatus.FAIL,
                "Error during import",
                f"Error: {e}",
            )
    
    def check_enhanced_module(self, module_path: str, class_name: str) -> Tuple[CheckStatus, str, str]:
        """Check if an enhanced module is available."""
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name, None)
            
            if cls:
                return (CheckStatus.PASS, f"{class_name} available", "")
            else:
                return (
                    CheckStatus.WARN,
                    f"{class_name} not found",
                    "Enhanced features may not be available",
                )
        except ImportError:
            return (
                CheckStatus.WARN,
                "Module not available",
                "Will fall back to legacy module",
            )
    
    # =========================================================================
    # Hardware Checks
    # =========================================================================
    
    def check_audio_input(self) -> Tuple[CheckStatus, str, str]:
        """Check for audio input devices."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            inputs = [d for d in devices if d["max_input_channels"] > 0]
            
            if inputs:
                default = sd.query_devices(kind="input")
                return (
                    CheckStatus.PASS,
                    f"{len(inputs)} device(s), default: {default['name'][:30]}",
                    "",
                )
            else:
                return (
                    CheckStatus.FAIL,
                    "No input devices found",
                    "FIX: Connect a microphone",
                )
        except ImportError:
            return (
                CheckStatus.SKIP,
                "sounddevice not installed",
                "CMD: pip install sounddevice",
            )
        except Exception as e:
            return (CheckStatus.FAIL, "Error detecting", str(e))
    
    def check_audio_output(self) -> Tuple[CheckStatus, str, str]:
        """Check for audio output devices."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            outputs = [d for d in devices if d["max_output_channels"] > 0]
            
            if outputs:
                default = sd.query_devices(kind="output")
                return (
                    CheckStatus.PASS,
                    f"{len(outputs)} device(s), default: {default['name'][:30]}",
                    "",
                )
            else:
                return (
                    CheckStatus.FAIL,
                    "No output devices found",
                    "FIX: Connect speakers or headphones",
                )
        except ImportError:
            return (
                CheckStatus.SKIP,
                "sounddevice not installed",
                "CMD: pip install sounddevice",
            )
        except Exception as e:
            return (CheckStatus.FAIL, "Error detecting", str(e))
    
    def check_camera(self) -> Tuple[CheckStatus, str, str]:
        """Check for camera availability."""
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            
            if cap.isOpened():
                ret, _ = cap.read()
                cap.release()
                
                if ret:
                    return (CheckStatus.PASS, "Camera available", "")
                else:
                    return (CheckStatus.WARN, "Camera found but can't read", "Check camera permissions")
            else:
                return (
                    CheckStatus.WARN,
                    "No camera detected",
                    "Face recognition will be disabled",
                )
        except ImportError:
            return (
                CheckStatus.SKIP,
                "opencv not installed",
                "CMD: pip install opencv-python",
            )
        except Exception as e:
            return (CheckStatus.WARN, "Error detecting", str(e))
    
    def check_iot_devices(self) -> Tuple[CheckStatus, str, str]:
        """Scan for IoT devices via mDNS."""
        try:
            from zeroconf import ServiceBrowser, Zeroconf
            
            devices = []
            
            class Listener:
                def add_service(self, zc, type_, name):
                    if "jarvis" in name.lower() or "esp32" in name.lower():
                        devices.append(name)
                def remove_service(self, *args): pass
                def update_service(self, *args): pass
            
            zc = Zeroconf()
            browser = ServiceBrowser(zc, "_http._tcp.local.", Listener())
            
            # Wait briefly for discovery
            time.sleep(2)
            zc.close()
            
            if devices:
                return (
                    CheckStatus.PASS,
                    f"Found {len(devices)} device(s)",
                    ", ".join(devices[:3]),
                )
            else:
                return (
                    CheckStatus.SKIP,
                    "No IoT devices found",
                    "IoT features will be unavailable until devices are configured",
                )
        except ImportError:
            return (
                CheckStatus.SKIP,
                "zeroconf not installed",
                "CMD: pip install zeroconf",
            )
        except Exception as e:
            return (CheckStatus.SKIP, "Scan failed", str(e))
    
    # =========================================================================
    # Run All Checks
    # =========================================================================
    
    def run_all_checks(self) -> List[CheckCategory]:
        """Run all pre-flight checks."""
        self.categories = []
        
        # System Requirements
        system_cat = CheckCategory("System Requirements")
        system_cat.results.append(self.run_check("Python Version", self.check_python_version))
        system_cat.results.append(self.run_check("Operating System", self.check_os_platform))
        system_cat.results.append(self.run_check("Disk Space", self.check_disk_space))
        system_cat.results.append(self.run_check("Memory (RAM)", self.check_memory))
        system_cat.results.append(self.run_check("Network", self.check_network))
        self.categories.append(system_cat)
        
        # Required Packages
        pkg_cat = CheckCategory("Required Packages")
        for package, min_ver in self.REQUIRED_PACKAGES.items():
            pkg_cat.results.append(self.run_check(
                package,
                lambda p=package, v=min_ver: self.check_required_package(p, v)
            ))
        self.categories.append(pkg_cat)
        
        # Optional Packages
        opt_cat = CheckCategory("Optional Packages")
        for package, feature in self.OPTIONAL_PACKAGES.items():
            opt_cat.results.append(self.run_check(
                package,
                lambda p=package, f=feature: self.check_optional_package(p, f)
            ))
        self.categories.append(opt_cat)
        
        # Configuration
        config_cat = CheckCategory("Configuration")
        config_cat.results.append(self.run_check(".env File", self.check_env_file))
        config_cat.results.append(self.run_check("settings.yaml", self.check_settings_yaml))
        
        # API Keys
        api_keys = [
            ("Groq", "GROQ_API_KEY", r"gsk_.*"),
            ("Gemini", "GEMINI_API_KEY", None),
            ("Mistral", "MISTRAL_API_KEY", None),
            ("OpenAI", "OPENAI_API_KEY", r"sk-.*"),
            ("Anthropic", "ANTHROPIC_API_KEY", r"sk-ant-.*"),
            ("Telegram Bot", "TELEGRAM_BOT_TOKEN", r"\d+:.*"),
        ]
        for name, env_var, pattern in api_keys:
            config_cat.results.append(self.run_check(
                f"{name} API Key",
                lambda n=name, e=env_var, p=pattern: self.check_api_key(n, e, p)
            ))
        self.categories.append(config_cat)
        
        # Core Modules
        module_cat = CheckCategory("Core Modules")
        for module in self.CORE_MODULES:
            module_cat.results.append(self.run_check(
                module,
                lambda m=module: self.check_module_import(m)
            ))
        self.categories.append(module_cat)
        
        # Enhanced Modules
        enhanced_cat = CheckCategory("Enhanced Modules")
        for module, class_name in self.ENHANCED_MODULES:
            enhanced_cat.results.append(self.run_check(
                class_name,
                lambda m=module, c=class_name: self.check_enhanced_module(m, c)
            ))
        self.categories.append(enhanced_cat)
        
        # Hardware
        hw_cat = CheckCategory("Hardware Detection")
        hw_cat.results.append(self.run_check("Audio Input (Microphone)", self.check_audio_input))
        hw_cat.results.append(self.run_check("Audio Output (Speakers)", self.check_audio_output))
        hw_cat.results.append(self.run_check("Camera", self.check_camera))
        hw_cat.results.append(self.run_check("IoT Devices (mDNS)", self.check_iot_devices))
        self.categories.append(hw_cat)
        
        return self.categories
    
    # =========================================================================
    # Output Methods
    # =========================================================================
    
    def print_results(self) -> None:
        """Print results to terminal with colors."""
        total_pass = 0
        total_warn = 0
        total_fail = 0
        total_skip = 0
        
        print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}  JARVIS PRE-FLIGHT CHECK{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")
        
        for category in self.categories:
            print(f"{Colors.CYAN}{Colors.BOLD}[{category.name}]{Colors.RESET}")
            
            for result in category.results:
                # Status indicator
                if result.status == CheckStatus.PASS:
                    icon = f"{Colors.GREEN}✓{Colors.RESET}"
                    total_pass += 1
                elif result.status == CheckStatus.WARN:
                    icon = f"{Colors.YELLOW}⚠{Colors.RESET}"
                    total_warn += 1
                elif result.status == CheckStatus.FAIL:
                    icon = f"{Colors.RED}✗{Colors.RESET}"
                    total_fail += 1
                else:
                    icon = f"{Colors.BLUE}○{Colors.RESET}"
                    total_skip += 1
                
                # Print result
                print(f"  {icon} {result.name}: {result.message}")
                
                # Print details if verbose or failed
                if self.verbose or result.status == CheckStatus.FAIL:
                    if result.details:
                        print(f"      {Colors.YELLOW}{result.details}{Colors.RESET}")
                    if result.fix_instruction:
                        print(f"      {Colors.CYAN}→ {result.fix_instruction}{Colors.RESET}")
                    if result.fix_command:
                        print(f"      {Colors.GREEN}$ {result.fix_command}{Colors.RESET}")
            
            print()
        
        # Summary
        duration = time.time() - self.start_time
        print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}  SUMMARY{Colors.RESET}")
        print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
        print(f"  {Colors.GREEN}Passed:   {total_pass}{Colors.RESET}")
        print(f"  {Colors.YELLOW}Warnings: {total_warn}{Colors.RESET}")
        print(f"  {Colors.RED}Failed:   {total_fail}{Colors.RESET}")
        print(f"  {Colors.BLUE}Skipped:  {total_skip}{Colors.RESET}")
        print(f"  Duration: {duration:.1f}s")
        print()
        
        # Go/No-Go recommendation
        if total_fail == 0:
            if total_warn == 0:
                print(f"  {Colors.GREEN}{Colors.BOLD}✓ ALL CHECKS PASSED - Ready to run JARVIS{Colors.RESET}")
            else:
                print(f"  {Colors.YELLOW}{Colors.BOLD}⚠ READY WITH WARNINGS - Some features may be limited{Colors.RESET}")
        else:
            print(f"  {Colors.RED}{Colors.BOLD}✗ CHECKS FAILED - Please fix issues before running{Colors.RESET}")
        
        print()
    
    def to_json(self) -> Dict[str, Any]:
        """Convert results to JSON-serializable dict."""
        return {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": time.time() - self.start_time,
            "summary": {
                "passed": sum(c.passed for c in self.categories),
                "warnings": sum(c.warnings for c in self.categories),
                "failed": sum(c.failed for c in self.categories),
                "skipped": sum(c.skipped for c in self.categories),
            },
            "categories": [
                {
                    "name": cat.name,
                    "results": [
                        {
                            "name": r.name,
                            "status": r.status.value,
                            "message": r.message,
                            "details": r.details,
                            "fix_instruction": r.fix_instruction,
                            "fix_command": r.fix_command,
                            "duration_ms": r.duration_ms,
                        }
                        for r in cat.results
                    ],
                }
                for cat in self.categories
            ],
        }
    
    def save_log(self, path: Optional[Path] = None) -> Path:
        """Save detailed log to file."""
        if path is None:
            log_dir = self.project_root / "data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = log_dir / f"preflight_{timestamp}.json"
        
        with open(path, "w") as f:
            json.dump(self.to_json(), f, indent=2)
        
        return path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="JARVIS Pre-Flight Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--log", action="store_true", help="Save log file")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    
    args = parser.parse_args()
    
    # Disable colors if requested or not a TTY
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()
    
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Run checks
    checker = PreflightChecker(project_root, verbose=args.verbose)
    checker.run_all_checks()
    
    # Output results
    if args.json:
        print(json.dumps(checker.to_json(), indent=2))
    else:
        checker.print_results()
    
    # Save log if requested
    if args.log:
        log_path = checker.save_log()
        print(f"Log saved to: {log_path}")
    
    # Exit code based on failures
    total_fail = sum(c.failed for c in checker.categories)
    sys.exit(1 if total_fail > 0 else 0)


if __name__ == "__main__":
    main()
