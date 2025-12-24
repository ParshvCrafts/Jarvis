"""
Test script for Enhanced YouTube Music Integration.
Run with: python tests/test_music_enhanced.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.productivity import ProductivityManager
from src.productivity.music import MusicController


async def test_music_features():
    """Test enhanced YouTube Music features."""
    print("=" * 60)
    print("YouTube Music Premium Integration - Tests")
    print("=" * 60)
    
    # Test MusicController directly
    print("\n[Test 1] MusicController Personal URLs")
    m = MusicController()
    
    print(f"  Personal URLs available: {list(m.YOUTUBE_MUSIC_PERSONAL.keys())}")
    print(f"  Total playlists: {len(m.playlists)}")
    
    # Check methods exist
    methods = [
        'play_liked_songs', 'play_library', 'play_history',
        'play_my_mix', 'play_discover_mix', 'play_new_releases',
        'play_charts', 'browse_moods', 'search_youtube_music'
    ]
    
    for method in methods:
        has_method = hasattr(m, method)
        status = "✓" if has_method else "✗"
        print(f"  {status} {method}")
    
    # Test ProductivityManager command detection
    print("\n[Test 2] Command Detection")
    pm = ProductivityManager(config={}, data_dir='data')
    
    tests = [
        ("play my liked songs", True),
        ("play my mix", True),
        ("my library", True),
        ("discover mix", True),
        ("search youtube music for arijit singh", True),
        ("find song kesariya", True),
        ("new releases", True),
        ("music charts", True),
        ("recently played", True),
    ]
    
    passed = 0
    for cmd, expected in tests:
        result = pm._is_music_command(cmd)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        print(f"  {status} '{cmd}' -> {result}")
    
    print(f"  Result: {passed}/{len(tests)} passed")
    
    # Test command handling (without opening browser)
    print("\n[Test 3] Command Handling (messages only)")
    
    # Mock the webbrowser.open to prevent actual browser opening
    import webbrowser
    original_open = webbrowser.open
    opened_urls = []
    
    def mock_open(url):
        opened_urls.append(url)
        return True
    
    webbrowser.open = mock_open
    
    try:
        # Test personal library commands
        result = await pm.handle_command("play my liked songs")
        print(f"  Liked songs: {result}")
        
        result = await pm.handle_command("play my mix")
        print(f"  My mix: {result}")
        
        result = await pm.handle_command("discover mix")
        print(f"  Discover: {result}")
        
        result = await pm.handle_command("search youtube music for arijit singh")
        print(f"  Search: {result}")
        
        result = await pm.handle_command("new releases")
        print(f"  New releases: {result}")
        
        print(f"\n  URLs that would be opened: {len(opened_urls)}")
        for url in opened_urls:
            print(f"    • {url[:60]}...")
            
    finally:
        webbrowser.open = original_open
    
    print("\n" + "=" * 60)
    print("✅ YouTube Music Enhancement Tests Complete!")
    print("=" * 60)
    
    # Voice commands summary
    print("\n📢 New Voice Commands Available:")
    print("""
    Personal Library (YouTube Music Premium):
      - "Play my liked songs"
      - "Play my library"
      - "Play my mix" / "Play my YouTube mix"
      - "Play discover mix" / "Discover weekly"
      - "Play history" / "Recently played"
      - "New releases" / "New music"
      - "Music charts" / "Top charts"
      - "Browse moods"
    
    Search:
      - "Search YouTube Music for [query]"
      - "Find song [name]"
    
    Pomodoro + Music:
      - "Start pomodoro with lofi"
      - "Start focus session with hindi"
      - "Start studying with my mix"
      - "Start pomodoro with liked songs"
    """)


if __name__ == "__main__":
    asyncio.run(test_music_features())
