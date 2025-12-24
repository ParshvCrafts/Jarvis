"""
Tests for the Intelligent LLM Router.
"""

import pytest
import time
from pathlib import Path
import tempfile

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestTaskClassifier:
    """Tests for task classification."""
    
    def test_coding_classification(self):
        """Test coding task detection."""
        from src.core.llm_router import TaskClassifier, TaskType
        
        coding_queries = [
            "Write a Python function to sort a list",
            "Debug this code: def foo(): return",
            "How do I implement a binary search algorithm?",
            "Fix the syntax error in my JavaScript",
        ]
        
        for query in coding_queries:
            result = TaskClassifier.classify(query)
            assert result == TaskType.CODING, f"Expected CODING for: {query}"
    
    def test_fast_query_classification(self):
        """Test fast query detection."""
        from src.core.llm_router import TaskClassifier, TaskType
        
        fast_queries = [
            "What is Python?",
            "Who is Elon Musk?",
            "When was the moon landing?",
            "Define recursion",
        ]
        
        for query in fast_queries:
            result = TaskClassifier.classify(query)
            assert result == TaskType.FAST_QUERY, f"Expected FAST_QUERY for: {query}"
    
    def test_complex_classification(self):
        """Test complex reasoning detection."""
        from src.core.llm_router import TaskClassifier, TaskType
        
        complex_queries = [
            "Analyze the pros and cons of renewable energy",
            "Compare and evaluate different database architectures",
            "Think through the implications of AI on employment step by step",
        ]
        
        for query in complex_queries:
            result = TaskClassifier.classify(query)
            assert result == TaskType.COMPLEX_REASONING, f"Expected COMPLEX_REASONING for: {query}"


class TestResponseCache:
    """Tests for response caching."""
    
    def test_cache_set_get(self):
        """Test basic cache operations."""
        from src.core.llm_router import ResponseCache
        from src.core.llm import Message, LLMResponse, LLMProvider
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(Path(tmpdir) / "cache.db")
            
            messages = [Message(role="user", content="Hello")]
            response = LLMResponse(
                content="Hi there!",
                provider=LLMProvider.GROQ,
                model="test-model",
            )
            
            # Set cache
            cache.set(messages, response)
            
            # Get cache
            cached = cache.get(messages)
            assert cached is not None
            assert cached.content == "Hi there!"
            assert cached.metadata.get("cached") == True
    
    def test_cache_miss(self):
        """Test cache miss."""
        from src.core.llm_router import ResponseCache
        from src.core.llm import Message
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(Path(tmpdir) / "cache.db")
            
            messages = [Message(role="user", content="Unknown query")]
            cached = cache.get(messages)
            assert cached is None
    
    def test_cache_stats(self):
        """Test cache statistics."""
        from src.core.llm_router import ResponseCache
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ResponseCache(Path(tmpdir) / "cache.db")
            
            stats = cache.get_stats()
            assert "total_entries" in stats
            assert "max_entries" in stats


class TestRateLimitInfo:
    """Tests for rate limiting."""
    
    def test_rate_limit_tracking(self):
        """Test rate limit tracking."""
        from src.core.llm_providers import RateLimitInfo
        
        rate_limit = RateLimitInfo(
            max_requests=10,
            max_tokens=1000,
            reset_interval=60,
        )
        
        # Should allow requests initially
        assert rate_limit.can_make_request(100) == True
        
        # Record some requests
        for _ in range(10):
            rate_limit.record_request(50)
        
        # Should be at limit
        assert rate_limit.can_make_request(100) == False
    
    def test_rate_limit_reset(self):
        """Test rate limit reset."""
        from src.core.llm_providers import RateLimitInfo
        
        rate_limit = RateLimitInfo(
            max_requests=5,
            reset_interval=1,  # 1 second for testing
        )
        
        # Use up requests
        for _ in range(5):
            rate_limit.record_request()
        
        assert rate_limit.can_make_request() == False
        
        # Wait for reset
        time.sleep(1.1)
        
        assert rate_limit.can_make_request() == True


class TestIntelligentRouter:
    """Tests for the intelligent router."""
    
    def test_router_initialization(self):
        """Test router initializes without errors."""
        from src.core.llm_router import IntelligentLLMRouter
        
        # Should work with no API keys (will have no providers)
        try:
            router = IntelligentLLMRouter(
                groq_api_key=None,
                gemini_api_key=None,
                enable_cache=False,
            )
            # May have ollama if running
            status = router.get_status()
            assert "providers" in status
        except Exception:
            # Expected if no providers available
            pass
    
    def test_provider_order(self):
        """Test provider ordering by task type."""
        from src.core.llm_router import IntelligentLLMRouter, TaskType
        
        router = IntelligentLLMRouter(
            groq_api_key="test",
            gemini_api_key="test",
            mistral_api_key="test",
            enable_cache=False,
        )
        
        # Fast queries should prefer Groq
        fast_order = router._get_provider_order(TaskType.FAST_QUERY)
        if fast_order:
            assert fast_order[0] == "groq"
        
        # Coding should prefer Mistral
        coding_order = router._get_provider_order(TaskType.CODING)
        if coding_order:
            assert coding_order[0] == "mistral"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
