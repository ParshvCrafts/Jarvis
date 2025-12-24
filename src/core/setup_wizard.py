"""
JARVIS First-Run Setup Wizard

Provides:
- Interactive first-run experience
- Pre-population of common apps and bookmarks
- Configuration validation
- System status checks
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


# =============================================================================
# Common Applications (Pre-populated)
# =============================================================================

WINDOWS_APPS = [
    # Development
    {"name": "VS Code", "command": "code", "category": "development"},
    {"name": "Terminal", "command": "wt", "category": "development"},
    {"name": "PowerShell", "command": "powershell", "category": "development"},
    {"name": "Command Prompt", "command": "cmd", "category": "development"},
    {"name": "Git Bash", "command": "git-bash", "category": "development"},
    
    # Productivity
    {"name": "Notepad", "command": "notepad", "category": "productivity"},
    {"name": "Calculator", "command": "calc", "category": "productivity"},
    {"name": "File Explorer", "command": "explorer", "category": "productivity"},
    {"name": "Task Manager", "command": "taskmgr", "category": "system"},
    {"name": "Control Panel", "command": "control", "category": "system"},
    {"name": "Settings", "command": "ms-settings:", "category": "system"},
    
    # Browsers
    {"name": "Edge", "command": "msedge", "category": "browser"},
    {"name": "Chrome", "command": "chrome", "category": "browser", 
     "paths": [
         "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
         "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
     ]},
    {"name": "Firefox", "command": "firefox", "category": "browser",
     "paths": [
         "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
         "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
     ]},
    
    # Media
    {"name": "Spotify", "command": "spotify", "category": "media"},
    {"name": "VLC", "command": "vlc", "category": "media",
     "paths": [
         "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
         "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
     ]},
    
    # Communication
    {"name": "Discord", "command": "discord", "category": "communication"},
    {"name": "Slack", "command": "slack", "category": "communication"},
    {"name": "Teams", "command": "teams", "category": "communication"},
    {"name": "Zoom", "command": "zoom", "category": "communication"},
]

MACOS_APPS = [
    # Development
    {"name": "VS Code", "command": "code", "category": "development"},
    {"name": "Terminal", "command": "open -a Terminal", "category": "development"},
    {"name": "iTerm", "command": "open -a iTerm", "category": "development"},
    
    # Productivity
    {"name": "Finder", "command": "open -a Finder", "category": "productivity"},
    {"name": "Notes", "command": "open -a Notes", "category": "productivity"},
    {"name": "Calculator", "command": "open -a Calculator", "category": "productivity"},
    
    # Browsers
    {"name": "Safari", "command": "open -a Safari", "category": "browser"},
    {"name": "Chrome", "command": "open -a 'Google Chrome'", "category": "browser"},
    {"name": "Firefox", "command": "open -a Firefox", "category": "browser"},
    
    # Media
    {"name": "Spotify", "command": "open -a Spotify", "category": "media"},
    {"name": "Music", "command": "open -a Music", "category": "media"},
]

LINUX_APPS = [
    # Development
    {"name": "VS Code", "command": "code", "category": "development"},
    {"name": "Terminal", "command": "gnome-terminal", "category": "development"},
    
    # Productivity
    {"name": "Files", "command": "nautilus", "category": "productivity"},
    {"name": "Calculator", "command": "gnome-calculator", "category": "productivity"},
    
    # Browsers
    {"name": "Firefox", "command": "firefox", "category": "browser"},
    {"name": "Chrome", "command": "google-chrome", "category": "browser"},
    
    # Media
    {"name": "Spotify", "command": "spotify", "category": "media"},
    {"name": "VLC", "command": "vlc", "category": "media"},
]

CROSS_PLATFORM_APPS = [
    {"name": "Python", "command": "python", "category": "development"},
    {"name": "Git", "command": "git", "category": "development"},
    {"name": "Node", "command": "node", "category": "development"},
    {"name": "NPM", "command": "npm", "category": "development"},
]


# =============================================================================
# Common Bookmarks (Pre-populated)
# =============================================================================

COMMON_BOOKMARKS = [
    # Productivity
    {"name": "Google", "url": "https://google.com", "category": "search", "keywords": ["search"]},
    {"name": "Gmail", "url": "https://mail.google.com", "category": "productivity", "keywords": ["email", "mail"]},
    {"name": "Google Drive", "url": "https://drive.google.com", "category": "productivity", "keywords": ["drive", "files"]},
    {"name": "Google Docs", "url": "https://docs.google.com", "category": "productivity", "keywords": ["docs", "documents"]},
    {"name": "Google Calendar", "url": "https://calendar.google.com", "category": "productivity", "keywords": ["calendar", "schedule"]},
    {"name": "Google Maps", "url": "https://maps.google.com", "category": "productivity", "keywords": ["maps", "directions"]},
    
    # Development
    {"name": "GitHub", "url": "https://github.com", "category": "development", "keywords": ["git", "code", "repos"]},
    {"name": "Stack Overflow", "url": "https://stackoverflow.com", "category": "development", "keywords": ["stackoverflow", "coding help"]},
    {"name": "ChatGPT", "url": "https://chat.openai.com", "category": "ai", "keywords": ["gpt", "openai", "ai chat"]},
    {"name": "Claude", "url": "https://claude.ai", "category": "ai", "keywords": ["anthropic", "ai"]},
    {"name": "Hugging Face", "url": "https://huggingface.co", "category": "development", "keywords": ["ml", "models"]},
    
    # Social/Entertainment
    {"name": "YouTube", "url": "https://youtube.com", "category": "entertainment", "keywords": ["videos", "yt"]},
    {"name": "Twitter", "url": "https://x.com", "category": "social", "keywords": ["x", "tweets"]},
    {"name": "LinkedIn", "url": "https://linkedin.com", "category": "social", "keywords": ["professional", "jobs"]},
    {"name": "Reddit", "url": "https://reddit.com", "category": "social", "keywords": ["forums"]},
    {"name": "Netflix", "url": "https://netflix.com", "category": "entertainment", "keywords": ["movies", "shows"]},
    {"name": "Spotify Web", "url": "https://open.spotify.com", "category": "entertainment", "keywords": ["music"]},
    
    # Tools
    {"name": "Canva", "url": "https://canva.com", "category": "design", "keywords": ["design", "graphics"]},
    {"name": "Figma", "url": "https://figma.com", "category": "design", "keywords": ["design", "ui"]},
    {"name": "Notion", "url": "https://notion.so", "category": "productivity", "keywords": ["notes", "wiki"]},
    {"name": "Trello", "url": "https://trello.com", "category": "productivity", "keywords": ["tasks", "boards"]},
    
    # Shopping
    {"name": "Amazon", "url": "https://amazon.com", "category": "shopping", "keywords": ["shop", "buy"]},
]


# =============================================================================
# Setup Functions
# =============================================================================

def get_platform_apps() -> List[Dict[str, Any]]:
    """Get apps for current platform."""
    system = platform.system().lower()
    
    if system == "windows":
        return WINDOWS_APPS + CROSS_PLATFORM_APPS
    elif system == "darwin":
        return MACOS_APPS + CROSS_PLATFORM_APPS
    else:
        return LINUX_APPS + CROSS_PLATFORM_APPS


def check_app_exists(app: Dict[str, Any]) -> bool:
    """Check if an application exists on the system."""
    # Check command in PATH
    if shutil.which(app.get("command", "")):
        return True
    
    # Check specific paths
    for path in app.get("paths", []):
        if os.path.exists(path):
            return True
    
    return False


def populate_default_apps(quick_launch_manager) -> Tuple[int, int]:
    """
    Populate default applications.
    
    Returns:
        Tuple of (added_count, skipped_count)
    """
    apps = get_platform_apps()
    added = 0
    skipped = 0
    
    for app in apps:
        # Check if already exists
        existing = quick_launch_manager.db.get_application(app["name"])
        if existing:
            skipped += 1
            continue
        
        # Check if app exists on system
        if not check_app_exists(app):
            skipped += 1
            continue
        
        # Get path if available
        path = None
        for p in app.get("paths", []):
            if os.path.exists(p):
                path = p
                break
        
        # Add to registry
        success, _ = quick_launch_manager.add_application(
            name=app["name"],
            command=app.get("command"),
            path=path,
            category=app.get("category", "general"),
        )
        
        if success:
            added += 1
        else:
            skipped += 1
    
    logger.info(f"Pre-populated {added} applications, skipped {skipped}")
    return added, skipped


def populate_default_bookmarks(quick_launch_manager) -> Tuple[int, int]:
    """
    Populate default bookmarks.
    
    Returns:
        Tuple of (added_count, skipped_count)
    """
    added = 0
    skipped = 0
    
    for bookmark in COMMON_BOOKMARKS:
        # Check if already exists
        existing = quick_launch_manager.db.get_bookmark(bookmark["name"])
        if existing:
            skipped += 1
            continue
        
        # Add bookmark
        success, _ = quick_launch_manager.add_bookmark(
            name=bookmark["name"],
            url=bookmark["url"],
            category=bookmark.get("category", "general"),
            keywords=bookmark.get("keywords", []),
        )
        
        if success:
            added += 1
        else:
            skipped += 1
    
    logger.info(f"Pre-populated {added} bookmarks, skipped {skipped}")
    return added, skipped


def is_first_run() -> bool:
    """Check if this is the first run of JARVIS."""
    first_run_flag = DATA_DIR / ".first_run_complete"
    return not first_run_flag.exists()


def add_api_key(key_name: str, key_value: str) -> bool:
    """
    Add or update an API key in the .env file.
    
    Args:
        key_name: Name of the environment variable
        key_value: Value of the API key
        
    Returns:
        True if successful
    """
    env_path = PROJECT_ROOT / ".env"
    
    try:
        # Read existing content
        if env_path.exists():
            content = env_path.read_text()
            lines = content.splitlines()
        else:
            lines = []
        
        # Check if key already exists
        key_found = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key_name}="):
                lines[i] = f"{key_name}={key_value}"
                key_found = True
                break
        
        # Add new key if not found
        if not key_found:
            lines.append(f"{key_name}={key_value}")
        
        # Write back
        env_path.write_text("\n".join(lines) + "\n")
        logger.info(f"Added/updated {key_name} in .env")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add API key: {e}")
        return False


def mark_first_run_complete() -> None:
    """Mark first run as complete."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    first_run_flag = DATA_DIR / ".first_run_complete"
    first_run_flag.write_text(f"First run completed on {__import__('datetime').datetime.now().isoformat()}")


def run_first_time_setup(interactive: bool = False) -> bool:
    """
    Run first-time setup.
    
    Args:
        interactive: Whether to run in interactive mode
        
    Returns:
        True if setup completed successfully
    """
    if not is_first_run():
        logger.debug("First run already completed")
        return True
    
    print("\n" + "=" * 60)
    print("  JARVIS First-Time Setup")
    print("=" * 60 + "\n")
    
    # Create directories
    print("Creating directories...")
    dirs = [
        DATA_DIR,
        DATA_DIR / "screenshots",
        DATA_DIR / "browser_data",
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "cache",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print("✓ Directories created\n")
    
    # Pre-populate Quick Launch
    print("Setting up Quick Launch...")
    try:
        from ..system.quick_launch import QuickLaunchManager
        
        manager = QuickLaunchManager(DATA_DIR / "quick_launch.db")
        
        # Populate apps
        apps_added, apps_skipped = populate_default_apps(manager)
        print(f"✓ Added {apps_added} applications")
        
        # Populate bookmarks
        bm_added, bm_skipped = populate_default_bookmarks(manager)
        print(f"✓ Added {bm_added} bookmarks")
        
    except ImportError as e:
        print(f"⚠ Quick Launch not available: {e}")
    except Exception as e:
        print(f"⚠ Quick Launch setup error: {e}")
    
    print()
    
    # Interactive setup (optional)
    if interactive:
        print("Interactive setup...")
        
        # Get user name
        name = input("What's your name? (press Enter to skip): ").strip()
        if name:
            try:
                from ..memory.episodic import EpisodicMemory
                memory = EpisodicMemory(DATA_DIR / "episodic.db")
                memory.set_preference("user_name", name, category="user")
                print(f"✓ Hello, {name}!")
            except Exception:
                pass
        
        # Language preference
        print("\nPreferred language:")
        print("  1. English (default)")
        print("  2. Hindi")
        print("  3. Gujarati")
        lang_choice = input("Choose (1-3, Enter for default): ").strip()
        lang_map = {"1": "en", "2": "hi", "3": "gu"}
        if lang_choice in lang_map:
            try:
                from ..memory.episodic import EpisodicMemory
                memory = EpisodicMemory(DATA_DIR / "episodic.db")
                memory.set_preference("language", lang_map[lang_choice], category="user")
                print(f"✓ Language set to {lang_map[lang_choice]}")
            except Exception:
                pass
    
    # Interactive API key setup
    if interactive:
        print("\n" + "-" * 40)
        print("API Key Setup")
        print("-" * 40)
        
        # Check if GROQ_API_KEY is set
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            if not os.getenv("GROQ_API_KEY"):
                print("\n⚠️  GROQ_API_KEY not found (required for LLM)")
                key = input("Enter your Groq API key (or press Enter to skip): ").strip()
                if key:
                    add_api_key("GROQ_API_KEY", key)
                    print("✓ Groq API key saved to .env")
            else:
                print("✓ Groq API key already configured")
        except Exception as e:
            print(f"⚠ Could not check API keys: {e}")
    
    # Mark complete
    mark_first_run_complete()
    
    print("\n" + "=" * 60)
    print("  First-Time Setup Complete!")
    print("=" * 60)
    
    # Show first command suggestions
    print("\nJARVIS is ready! Try these commands:")
    print("  • \"What's the weather in Chicago?\"")
    print("  • \"Open VS Code\"")
    print("  • \"Open GitHub\"")
    print("  • \"Play music on YouTube\"")
    print("  • \"Status\"")
    print("\nSay 'Hey Jarvis' to wake up!\n")
    
    return True


# =============================================================================
# Status Check
# =============================================================================

def get_system_status() -> Dict[str, Any]:
    """
    Get comprehensive system status.
    
    Returns:
        Dictionary with status information
    """
    status = {
        "version": "2.0.0",
        "platform": platform.system(),
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "features": {},
        "issues": [],
    }
    
    # Check LLM providers
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        if os.getenv("GROQ_API_KEY"):
            status["features"]["llm_groq"] = True
        else:
            status["features"]["llm_groq"] = False
            status["issues"].append("GROQ_API_KEY not set (required for LLM)")
        
        status["features"]["llm_gemini"] = bool(os.getenv("GEMINI_API_KEY"))
        status["features"]["llm_mistral"] = bool(os.getenv("MISTRAL_API_KEY"))
        status["features"]["llm_openrouter"] = bool(os.getenv("OPENROUTER_API_KEY"))
        
    except Exception:
        status["issues"].append("Could not load environment variables")
    
    # Check voice components
    try:
        import pvporcupine
        status["features"]["wake_word"] = True
    except ImportError:
        status["features"]["wake_word"] = False
    
    try:
        import edge_tts
        status["features"]["tts"] = True
    except ImportError:
        status["features"]["tts"] = False
    
    try:
        from faster_whisper import WhisperModel
        status["features"]["stt"] = True
    except ImportError:
        status["features"]["stt"] = False
    
    # Check Quick Launch
    try:
        from ..system.quick_launch import QuickLaunchManager
        manager = QuickLaunchManager(DATA_DIR / "quick_launch.db")
        apps = manager.list_applications()
        bookmarks = manager.list_bookmarks()
        status["features"]["quick_launch"] = True
        status["quick_launch_apps"] = len(apps)
        status["quick_launch_bookmarks"] = len(bookmarks)
    except Exception:
        status["features"]["quick_launch"] = False
    
    # Check config
    config_path = PROJECT_ROOT / "config" / "settings.yaml"
    if config_path.exists():
        status["features"]["config"] = True
    else:
        status["features"]["config"] = False
        status["issues"].append("config/settings.yaml not found")
    
    return status


def print_status() -> None:
    """Print formatted system status."""
    status = get_system_status()
    
    print("\n" + "=" * 60)
    print(f"  JARVIS v{status['version']} Status")
    print("=" * 60 + "\n")
    
    print(f"Platform: {status['platform']}")
    print(f"Python: {status['python']}")
    print()
    
    print("Features:")
    feature_names = {
        "llm_groq": "LLM: Groq",
        "llm_gemini": "LLM: Gemini",
        "llm_mistral": "LLM: Mistral",
        "llm_openrouter": "LLM: OpenRouter",
        "wake_word": "Wake Word Detection",
        "tts": "Text-to-Speech",
        "stt": "Speech-to-Text",
        "quick_launch": "Quick Launch",
        "config": "Configuration",
    }
    
    for key, name in feature_names.items():
        if status["features"].get(key):
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name}")
    
    if status.get("quick_launch_apps"):
        print(f"\nQuick Launch: {status['quick_launch_apps']} apps, {status['quick_launch_bookmarks']} bookmarks")
    
    if status["issues"]:
        print("\n⚠️  Issues:")
        for issue in status["issues"]:
            print(f"  - {issue}")
    else:
        print("\n✅ All systems operational")
    
    print()


def validate_configuration() -> Tuple[bool, List[str]]:
    """
    Validate JARVIS configuration.
    
    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    
    # Check .env exists
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        issues.append(".env file not found - copy from .env.example")
    
    # Check settings.yaml exists
    config_path = PROJECT_ROOT / "config" / "settings.yaml"
    if not config_path.exists():
        issues.append("config/settings.yaml not found")
    else:
        # Validate YAML syntax
        try:
            import yaml
            with open(config_path) as f:
                yaml.safe_load(f)
        except Exception as e:
            issues.append(f"config/settings.yaml has syntax error: {e}")
    
    # Check required API keys
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        if not os.getenv("GROQ_API_KEY"):
            issues.append("GROQ_API_KEY not set (required for LLM)")
        
    except ImportError:
        issues.append("python-dotenv not installed")
    
    # Check data directory
    if not DATA_DIR.exists():
        issues.append("data/ directory not found - run setup")
    
    is_valid = len(issues) == 0
    return is_valid, issues


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="JARVIS Setup Wizard")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--validate", action="store_true", help="Validate configuration")
    parser.add_argument("--setup", action="store_true", help="Run first-time setup")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--populate-apps", action="store_true", help="Populate default apps")
    parser.add_argument("--populate-bookmarks", action="store_true", help="Populate default bookmarks")
    
    args = parser.parse_args()
    
    if args.status:
        print_status()
    
    elif args.validate:
        is_valid, issues = validate_configuration()
        if is_valid:
            print("✅ Configuration is valid")
        else:
            print("❌ Configuration issues found:")
            for issue in issues:
                print(f"  - {issue}")
    
    elif args.setup:
        run_first_time_setup(interactive=args.interactive)
    
    elif args.populate_apps or args.populate_bookmarks:
        from ..system.quick_launch import QuickLaunchManager
        manager = QuickLaunchManager(DATA_DIR / "quick_launch.db")
        
        if args.populate_apps:
            added, skipped = populate_default_apps(manager)
            print(f"Added {added} apps, skipped {skipped}")
        
        if args.populate_bookmarks:
            added, skipped = populate_default_bookmarks(manager)
            print(f"Added {added} bookmarks, skipped {skipped}")
    
    else:
        parser.print_help()
