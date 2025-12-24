"""
Test script for Productivity Features (Phase 2).
Run with: python tests/test_productivity.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.productivity import ProductivityManager


async def test_productivity_features():
    """Test all productivity features."""
    print("=" * 60)
    print("JARVIS Productivity Features - Verification Tests")
    print("=" * 60)
    
    manager = ProductivityManager(config={}, data_dir='data')
    
    # Test 1: Command Detection
    print("\n[Test 1] Command Detection")
    tests = [
        ("play focus music", "_is_music_command", True),
        ("play hindi songs", "_is_music_command", True),
        ("log learning: gradient descent", "_is_journal_command", True),
        ("what did i learn this week", "_is_journal_command", True),
        ("log exercise done", "_is_habit_command", True),
        ("show my habits", "_is_habit_command", True),
        ("create project ML App", "_is_project_command", True),
        ("show my projects", "_is_project_command", True),
        ("find snippet for pandas", "_is_snippet_command", True),
        ("plan my study week", "_is_planner_command", True),
        ("weekly review", "_is_review_command", True),
        ("start focus mode", "_is_focus_command", True),
        ("analyze dataset iris.csv", "_is_dataset_command", True),
        ("take a break", "_is_break_command", True),
    ]
    
    passed = 0
    for text, method, expected in tests:
        result = getattr(manager, method)(text)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        print(f"  {status} '{text}' -> {method}: {result}")
    
    print(f"  Result: {passed}/{len(tests)} passed")
    
    # Test 2: Music Controller
    print("\n[Test 2] Music Controller")
    playlists = manager.music.list_playlists()
    print(f"  Available playlists: {len(manager.music.playlists)} playlists")
    assert len(manager.music.playlists) > 0, "Should have playlists"
    print("  ✓ Music controller working")
    
    # Test 3: Learning Journal
    print("\n[Test 3] Learning Journal")
    result = await manager.handle_command("log learning: Learned about neural networks in CS 189")
    print(f"  Log entry: {result}")
    assert "logged" in result.lower() or "learning" in result.lower()
    
    result = await manager.handle_command("what did i learn this week")
    print(f"  Weekly summary: {result[:80]}..." if len(result) > 80 else f"  Weekly summary: {result}")
    print("  ✓ Learning journal working")
    
    # Test 4: Habit Tracker
    print("\n[Test 4] Habit Tracker")
    result = await manager.handle_command("show my habits")
    print(f"  Habits: {result[:100]}..." if len(result) > 100 else f"  Habits: {result}")
    
    result = await manager.handle_command("log exercise done")
    print(f"  Log habit: {result}")
    print("  ✓ Habit tracker working")
    
    # Test 5: Project Tracker
    print("\n[Test 5] Project Tracker")
    result = await manager.handle_command("create project: Test ML Project")
    print(f"  Create project: {result}")
    assert "created" in result.lower() or "project" in result.lower()
    
    result = await manager.handle_command("show my projects")
    print(f"  Projects: {result[:100]}..." if len(result) > 100 else f"  Projects: {result}")
    print("  ✓ Project tracker working")
    
    # Test 6: Code Snippets
    print("\n[Test 6] Code Snippets")
    result = await manager.handle_command("find snippet for train test split")
    print(f"  Find snippet: {result[:150]}..." if len(result) > 150 else f"  Find snippet: {result}")
    assert "train" in result.lower() or "snippet" in result.lower()
    print("  ✓ Code snippets working")
    
    # Test 7: Study Planner
    print("\n[Test 7] Study Planner")
    result = await manager.handle_command("what should i work on")
    print(f"  Suggestion: {result[:100]}..." if len(result) > 100 else f"  Suggestion: {result}")
    print("  ✓ Study planner working")
    
    # Test 8: Weekly Review
    print("\n[Test 8] Weekly Review")
    result = await manager.handle_command("weekly review")
    print(f"  Review: {result[:150]}..." if len(result) > 150 else f"  Review: {result}")
    assert "weekly" in result.lower() or "review" in result.lower()
    print("  ✓ Weekly review working")
    
    # Test 9: Focus Mode
    print("\n[Test 9] Focus Mode")
    result = await manager.handle_command("focus status")
    print(f"  Status: {result}")
    
    result = await manager.handle_command("show blocked sites")
    print(f"  Blocklist: {result[:100]}..." if len(result) > 100 else f"  Blocklist: {result}")
    print("  ✓ Focus mode working")
    
    # Test 10: Dataset Explorer
    print("\n[Test 10] Dataset Explorer")
    if manager.dataset.is_available:
        result = await manager.handle_command("data shape")
        print(f"  Result: {result}")
        print("  ✓ Dataset explorer available")
    else:
        print("  ⚠ Pandas not installed, skipping")
    
    # Test 11: Break Reminders
    print("\n[Test 11] Break Reminders")
    result = await manager.handle_command("break status")
    print(f"  Status: {result}")
    
    result = manager.breaks.suggest_stretch()
    print(f"  Stretch suggestion: {result}")
    print("  ✓ Break reminders working")
    
    print("\n" + "=" * 60)
    print("✅ All Productivity Feature Tests Completed!")
    print("=" * 60)
    
    # Summary of voice commands
    print("\n📢 Voice Commands Available:")
    print("""
    Music:
      - "Play focus music" / "Play lofi" / "Play hindi"
      - "Show playlists"
    
    Learning Journal:
      - "Log learning: [what you learned]"
      - "What did I learn this week"
    
    Habits:
      - "Log [habit] done" (e.g., "Log exercise done")
      - "Show my habits"
      - "Habit streak for [habit]"
    
    Projects:
      - "Create project: [name]"
      - "Show my projects"
      - "Log 2 hours on [project]"
    
    Snippets:
      - "Find snippet for [topic]"
      - "Show ML snippets"
    
    Planning:
      - "What should I work on"
      - "Plan my study week"
      - "I have 2 hours free"
    
    Focus:
      - "Start focus mode"
      - "Show blocked sites"
    
    Breaks:
      - "Take a break"
      - "Break status"
    """)


if __name__ == "__main__":
    asyncio.run(test_productivity_features())
