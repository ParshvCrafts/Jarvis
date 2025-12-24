"""
Tests for authentication modules.
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile


class TestSessionManager:
    """Tests for session management."""
    
    def test_create_session(self):
        """Test session creation."""
        from src.auth.session import SessionManager, AuthLevel
        
        manager = SessionManager(session_timeout=300)
        session = manager.create_session(user_id="test_user")
        
        assert session is not None
        assert session.user_id == "test_user"
        assert not session.is_expired
    
    def test_session_expiry(self):
        """Test session expiration."""
        from src.auth.session import SessionManager
        
        manager = SessionManager(session_timeout=1)  # 1 second timeout
        session = manager.create_session()
        
        import time
        time.sleep(2)
        
        assert session.is_expired
    
    def test_failed_attempts_lockout(self):
        """Test lockout after failed attempts."""
        from src.auth.session import SessionManager
        
        manager = SessionManager(max_failed_attempts=3, lockout_duration=60)
        
        # Record failed attempts
        manager.record_failed_attempt("test_user")
        manager.record_failed_attempt("test_user")
        locked = manager.record_failed_attempt("test_user")
        
        assert locked
        assert manager.is_locked_out("test_user")
    
    def test_authorization_levels(self):
        """Test command authorization."""
        from src.auth.session import SessionManager, AuthLevel
        
        manager = SessionManager()
        manager.configure_command_levels(
            low=["query"],
            medium=["app_control"],
            high=["door_unlock"],
        )
        
        # Create low-level session
        session = manager.create_session(auth_level=AuthLevel.LOW)
        
        # Should pass for low-level command
        authorized, _ = manager.check_authorization(session.session_id, "query")
        assert authorized
        
        # Should fail for high-level command
        authorized, _ = manager.check_authorization(session.session_id, "door_unlock")
        assert not authorized


class TestConversationMemory:
    """Tests for conversation memory."""
    
    def test_add_message(self):
        """Test adding messages."""
        from src.memory.conversation import ConversationMemory
        
        memory = ConversationMemory(max_messages=10)
        memory.create_conversation("test")
        
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there!")
        
        messages = memory.get_context_messages()
        assert len(messages) == 2
    
    def test_sliding_window(self):
        """Test sliding window behavior."""
        from src.memory.conversation import ConversationMemory
        
        memory = ConversationMemory(max_messages=5, window_size=3)
        memory.create_conversation("test")
        
        for i in range(10):
            memory.add_message("user", f"Message {i}")
        
        messages = memory.get_context_messages()
        # Should only have window_size messages
        assert len(messages) <= 3


class TestEpisodicMemory:
    """Tests for episodic memory."""
    
    def test_preferences(self):
        """Test preference storage."""
        from src.memory.episodic import EpisodicMemory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            memory = EpisodicMemory(db_path)
            
            # Set preference
            memory.set_preference("theme", "dark", category="ui")
            
            # Get preference
            value = memory.get_preference("theme")
            assert value == "dark"
    
    def test_command_history(self):
        """Test command logging."""
        from src.memory.episodic import EpisodicMemory
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            memory = EpisodicMemory(db_path)
            
            # Log command
            cmd_id = memory.log_command("test command", "test response", success=True)
            assert cmd_id is not None
            
            # Get history
            history = memory.get_command_history(limit=10)
            assert len(history) == 1
            assert history[0]["command"] == "test command"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
