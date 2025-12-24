# JARVIS Quick Launch System

Launch applications, open bookmarks, and play YouTube videos by voice.

## Features

### 1. Application Registry
Store and launch applications by friendly name.

```
You: "Open VS Code"
JARVIS: "Opened VS Code"

You: "Open Android Studio"
JARVIS: "Opened Android Studio"
```

### 2. Web Bookmarks
Save and open favorite websites quickly.

```
You: "Open Canva"
JARVIS: "Opened Canva in your browser"

You: "Open GitHub"
JARVIS: "Opened GitHub in your browser"
```

### 3. YouTube Search & Play
Search and play YouTube videos by voice.

```
You: "Play Bohemian Rhapsody on YouTube"
JARVIS: "Searching YouTube for 'Bohemian Rhapsody'"

You: "Search YouTube for Python tutorial"
JARVIS: "Searching YouTube for 'Python tutorial'"
```

## Voice Commands

### Opening Apps/Sites

| Command | Action |
|---------|--------|
| "Open [name]" | Opens app, bookmark, or website |
| "Launch [name]" | Same as open |
| "Start [name]" | Same as open |

### YouTube

| Command | Action |
|---------|--------|
| "Play [query] on YouTube" | Searches and opens YouTube |
| "Search YouTube for [query]" | Opens YouTube search |
| "YouTube [query]" | Opens YouTube search |

### Managing Applications

| Command | Action |
|---------|--------|
| "Add application [name] at [path]" | Registers an app |
| "Remove application [name]" | Removes an app |
| "List apps" / "My apps" | Shows registered apps |

### Managing Bookmarks

| Command | Action |
|---------|--------|
| "Add bookmark [name] at [url]" | Saves a bookmark |
| "Remove bookmark [name]" | Removes a bookmark |
| "List bookmarks" / "My bookmarks" | Shows saved bookmarks |

## Configuration

In `config/settings.yaml`:

```yaml
quick_launch:
  enabled: true
  db_path: "data/quick_launch.db"
  
  applications:
    enabled: true
    auto_discover: false
  
  bookmarks:
    enabled: true
    default_browser: null  # Uses system default
  
  youtube:
    enabled: true
    auto_play: false
    use_playwright: false
  
  learning:
    track_usage: true
    suggest_frequent: true
```

## API Usage

```python
from src.system.quick_launch import QuickLaunchManager

# Initialize
manager = QuickLaunchManager("data/quick_launch.db")

# Add application
manager.add_application("VS Code", command="code")
manager.add_application("Figma", path="C:\\Users\\...\\Figma.exe")

# Add bookmark
manager.add_bookmark("Canva", "canva.com", category="design")
manager.add_bookmark("GitHub", "github.com", keywords=["git", "code"])

# Open (smart routing)
result = manager.open("VS Code")  # Launches app
result = manager.open("Canva")    # Opens bookmark
result = manager.open("google.com")  # Opens URL directly

# YouTube
result = manager.play_youtube("lofi hip hop")
result = manager.search_youtube("python tutorial")

# List
apps = manager.list_applications()
bookmarks = manager.list_bookmarks()
```

## Database Schema

### Applications Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Friendly name (unique) |
| path | TEXT | Executable path |
| command | TEXT | CLI command |
| category | TEXT | Category |
| platform | TEXT | windows/macos/linux/all |
| use_count | INTEGER | Usage tracking |

### Bookmarks Table

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| name | TEXT | Friendly name (unique) |
| url | TEXT | Full URL |
| category | TEXT | Category |
| keywords | TEXT | JSON array of aliases |
| use_count | INTEGER | Usage tracking |

## Smart Routing

When you say "Open [something]", JARVIS checks in order:

1. **Application Registry** - Registered apps by name
2. **Bookmarks** - Saved bookmarks by name or keyword
3. **Common Services** - YouTube, Gmail, GitHub, etc.
4. **Direct URL** - If it looks like a URL
5. **Fallback** - Try launching as system command

## Common Services (Built-in)

These work without adding bookmarks:

- YouTube, Google, Gmail
- GitHub, Twitter/X, Facebook
- Instagram, LinkedIn, Reddit
- Amazon, Netflix, Spotify
- ChatGPT, Claude

## Examples

```
# Applications
"Add application Android Studio at C:\Program Files\Android\Android Studio\bin\studio64.exe"
"Open Android Studio"

# Bookmarks
"Add bookmark Figma at figma.com"
"Open Figma"

# YouTube
"Play some jazz music on YouTube"
"Search YouTube for cooking recipes"

# Lists
"What apps do I have?"
"Show my bookmarks"
```

## Notes

- Application paths are platform-specific
- URLs automatically get `https://` prefix
- Usage is tracked for future suggestions
- Database is SQLite (portable)
