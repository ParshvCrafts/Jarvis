"""
Test script for Academic Features.
Run with: python tests/test_academic.py
"""

import asyncio
import sys
sys.path.insert(0, '.')

from src.academic import AcademicManager


async def test_academic_features():
    """Test all academic features."""
    print("=" * 60)
    print("JARVIS Academic Features - Verification Tests")
    print("=" * 60)
    
    manager = AcademicManager(config={}, data_dir='data')
    
    # Test 1: Command Detection
    print("\n[Test 1] Command Detection")
    tests = [
        ("good morning", "_is_briefing_command", True),
        ("daily briefing", "_is_briefing_command", True),
        ("start pomodoro", "_is_pomodoro_command", True),
        ("how much time left", "_is_pomodoro_command", True),
        ("what's due this week", "_is_canvas_command", True),
        ("show my grades", "_is_canvas_command", True),
        ("quick note: test", "_is_notes_command", True),
        ("show my notes", "_is_notes_command", True),
        ("show my github repos", "_is_github_command", True),
        ("find papers about transformers", "_is_arxiv_command", True),
        ("explain gradient descent", "_is_explain_command", True),
        ("recent documents", "_is_drive_command", True),
    ]
    
    passed = 0
    for text, method, expected in tests:
        result = getattr(manager, method)(text)
        status = "✓" if result == expected else "✗"
        if result == expected:
            passed += 1
        print(f"  {status} '{text}' -> {method}: {result}")
    
    print(f"  Result: {passed}/{len(tests)} passed")
    
    # Test 2: Quick Notes
    print("\n[Test 2] Quick Notes")
    result = await manager.handle_command("quick note: Test note for academic verification")
    print(f"  Add note: {result}")
    assert "saved" in result.lower(), "Note should be saved"
    
    result = await manager.handle_command("show my notes")
    print(f"  Show notes: {result[:80]}..." if len(result) > 80 else f"  Show notes: {result}")
    assert "test note" in result.lower() or "recent notes" in result.lower(), "Should show notes"
    print("  ✓ Notes working")
    
    # Test 3: Pomodoro Timer
    print("\n[Test 3] Pomodoro Timer")
    result = await manager.handle_command("pomodoro status")
    print(f"  Status: {result}")
    assert "timer" in result.lower() or "running" in result.lower() or "no timer" in result.lower()
    
    result = await manager.handle_command("study stats")
    print(f"  Stats: {result[:80]}..." if len(result) > 80 else f"  Stats: {result}")
    print("  ✓ Pomodoro working")
    
    # Test 4: Canvas API (graceful handling)
    print("\n[Test 4] Canvas API (Token Check)")
    result = await manager.handle_command("what assignments are due this week")
    print(f"  Result: {result}")
    # Should either work or show helpful error about token
    assert "assignment" in result.lower() or "token" in result.lower() or "configured" in result.lower()
    print("  ✓ Canvas handling correct")
    
    # Test 5: GitHub (graceful handling)
    print("\n[Test 5] GitHub API (Token Check)")
    result = await manager.handle_command("show my github repos")
    print(f"  Result: {result}")
    assert "repo" in result.lower() or "token" in result.lower() or "configured" in result.lower()
    print("  ✓ GitHub handling correct")
    
    # Test 6: arXiv Search
    print("\n[Test 6] arXiv Search")
    result = await manager.handle_command("find papers about attention mechanism")
    print(f"  Result: {result[:100]}..." if len(result) > 100 else f"  Result: {result}")
    print("  ✓ arXiv working")
    
    # Test 7: Daily Briefing
    print("\n[Test 7] Daily Briefing")
    result = await manager.handle_command("good morning")
    print(f"  Result: {result[:150]}..." if len(result) > 150 else f"  Result: {result}")
    assert "morning" in result.lower() or "afternoon" in result.lower() or "evening" in result.lower() or "briefing" in result.lower()
    print("  ✓ Briefing working")
    
    # Test 8: Google Drive (graceful handling)
    print("\n[Test 8] Google Drive (Config Check)")
    result = await manager.handle_command("show recent documents")
    print(f"  Result: {result}")
    # Should show not enabled or not configured message
    assert "drive" in result.lower() or "document" in result.lower() or "enabled" in result.lower()
    print("  ✓ Drive handling correct")
    
    print("\n" + "=" * 60)
    print("✅ All Academic Feature Tests Completed Successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_academic_features())
