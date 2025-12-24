"""
Intelligent LLM Router for JARVIS.

Provides:
- Task-based model selection (fast queries → Groq, complex → Gemini, coding → Mistral)
- Rate limit tracking per provider
- Response caching with SQLite
- Exponential backoff for failover
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Tuple

from loguru import logger

from .llm import BaseLLMClient, LLMProvider, LLMResponse, Message, GroqClient, OllamaClient
from .llm_providers import GeminiClient, RateLimitInfo


class TaskType(Enum):
    """Types of tasks for intelligent routing."""
    FAST_QUERY = "fast_query"  # Simple questions, quick responses
    COMPLEX_REASONING = "complex_reasoning"  # Multi-step reasoning, analysis
    CODING = "coding"  # Code generation, debugging
    CREATIVE = "creative"  # Writing, brainstorming
    CONVERSATION = "conversation"  # General chat
    UNKNOWN = "unknown"


@dataclass
class ProviderStatus:
    """Status of an LLM provider."""
    name: str
    available: bool
    rate_limit: Optional[RateLimitInfo] = None
    last_error: Optional[str] = None
    last_error_time: float = 0
    consecutive_failures: int = 0
    total_requests: int = 0
    total_tokens: int = 0


class ResponseCache:
    """
    SQLite-based response cache for LLM queries.
    
    Caches responses to avoid redundant API calls for identical queries.
    """
    
    def __init__(self, db_path: Path, max_age_hours: int = 24, max_entries: int = 10000):
        """
        Initialize the response cache.
        
        Args:
            db_path: Path to SQLite database.
            max_age_hours: Maximum age of cached entries in hours.
            max_entries: Maximum number of cached entries.
        """
        self.db_path = db_path
        self.max_age_seconds = max_age_hours * 3600
        self.max_entries = max_entries
        
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self) -> None:
        """Initialize the cache database."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS response_cache (
                    query_hash TEXT PRIMARY KEY,
                    messages_json TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    access_count INTEGER DEFAULT 1
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created ON response_cache(created_at)")
    
    def _hash_messages(self, messages: List[Message]) -> str:
        """Create a hash of the messages for cache lookup."""
        content = json.dumps([m.to_dict() for m in messages], sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get(self, messages: List[Message]) -> Optional[LLMResponse]:
        """
        Get a cached response if available.
        
        Args:
            messages: The messages to look up.
            
        Returns:
            Cached LLMResponse or None.
        """
        query_hash = self._hash_messages(messages)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                """SELECT response_json, provider, model, created_at 
                   FROM response_cache WHERE query_hash = ?""",
                (query_hash,)
            )
            row = cursor.fetchone()
            
            if row:
                # Check if expired
                if time.time() - row["created_at"] > self.max_age_seconds:
                    conn.execute("DELETE FROM response_cache WHERE query_hash = ?", (query_hash,))
                    return None
                
                # Update access count
                conn.execute(
                    "UPDATE response_cache SET access_count = access_count + 1 WHERE query_hash = ?",
                    (query_hash,)
                )
                
                response_data = json.loads(row["response_json"])
                return LLMResponse(
                    content=response_data["content"],
                    provider=LLMProvider(row["provider"]) if row["provider"] in [p.value for p in LLMProvider] else LLMProvider.OPENAI,
                    model=row["model"],
                    tokens_used=response_data.get("tokens_used"),
                    finish_reason=response_data.get("finish_reason"),
                    metadata={"cached": True, **response_data.get("metadata", {})},
                )
        
        return None
    
    def set(self, messages: List[Message], response: LLMResponse) -> None:
        """
        Cache a response.
        
        Args:
            messages: The messages that generated this response.
            response: The response to cache.
        """
        query_hash = self._hash_messages(messages)
        messages_json = json.dumps([m.to_dict() for m in messages])
        response_json = json.dumps({
            "content": response.content,
            "tokens_used": response.tokens_used,
            "finish_reason": response.finish_reason,
            "metadata": response.metadata,
        })
        
        with self._get_connection() as conn:
            # Clean up old entries if needed
            count = conn.execute("SELECT COUNT(*) FROM response_cache").fetchone()[0]
            if count >= self.max_entries:
                # Delete oldest 10%
                conn.execute("""
                    DELETE FROM response_cache WHERE query_hash IN (
                        SELECT query_hash FROM response_cache 
                        ORDER BY created_at ASC LIMIT ?
                    )
                """, (self.max_entries // 10,))
            
            conn.execute("""
                INSERT OR REPLACE INTO response_cache 
                (query_hash, messages_json, response_json, provider, model, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                query_hash,
                messages_json,
                response_json,
                response.provider.value,
                response.model,
                time.time(),
            ))
    
    def clear(self) -> int:
        """Clear all cached entries. Returns number deleted."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM response_cache")
            return cursor.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM response_cache").fetchone()[0]
            total_accesses = conn.execute("SELECT SUM(access_count) FROM response_cache").fetchone()[0] or 0
            
            return {
                "total_entries": total,
                "total_accesses": total_accesses,
                "max_entries": self.max_entries,
                "max_age_hours": self.max_age_seconds // 3600,
            }


class TaskClassifier:
    """
    Classifies user queries into task types for intelligent routing.
    """
    
    # Keywords for task classification
    CODING_KEYWORDS = [
        "code", "function", "class", "debug", "error", "bug", "python", "javascript",
        "typescript", "java", "c++", "rust", "go", "sql", "html", "css", "api",
        "implement", "refactor", "optimize", "algorithm", "data structure",
        "compile", "runtime", "exception", "syntax", "variable", "loop",
    ]
    
    COMPLEX_KEYWORDS = [
        "analyze", "compare", "evaluate", "explain why", "reason", "think through",
        "step by step", "pros and cons", "implications", "consequences",
        "research", "investigate", "deep dive", "comprehensive", "detailed",
        "strategy", "plan", "design", "architecture",
    ]
    
    CREATIVE_KEYWORDS = [
        "write", "story", "poem", "creative", "imagine", "brainstorm",
        "ideas", "suggest", "compose", "draft", "narrative", "fiction",
    ]
    
    FAST_KEYWORDS = [
        "what is", "who is", "when", "where", "how many", "define",
        "quick", "brief", "short", "simple", "just tell me",
        "yes or no", "true or false",
    ]
    
    @classmethod
    def classify(cls, text: str) -> TaskType:
        """
        Classify a query into a task type.
        
        Args:
            text: The user's query text.
            
        Returns:
            TaskType for routing.
        """
        text_lower = text.lower()
        
        # Check for coding tasks
        coding_score = sum(1 for kw in cls.CODING_KEYWORDS if kw in text_lower)
        if coding_score >= 2 or any(kw in text_lower for kw in ["```", "def ", "class ", "function "]):
            return TaskType.CODING
        
        # Check for complex reasoning
        complex_score = sum(1 for kw in cls.COMPLEX_KEYWORDS if kw in text_lower)
        if complex_score >= 2 or len(text) > 500:
            return TaskType.COMPLEX_REASONING
        
        # Check for creative tasks
        creative_score = sum(1 for kw in cls.CREATIVE_KEYWORDS if kw in text_lower)
        if creative_score >= 2:
            return TaskType.CREATIVE
        
        # Check for fast queries
        fast_score = sum(1 for kw in cls.FAST_KEYWORDS if kw in text_lower)
        if fast_score >= 1 or len(text) < 50:
            return TaskType.FAST_QUERY
        
        # Default to conversation
        return TaskType.CONVERSATION


class IntelligentLLMRouter:
    """
    Intelligent LLM router with task-based selection and automatic failover.
    
    Features:
    - Task-based model selection
    - Rate limit tracking
    - Response caching
    - Exponential backoff
    - Provider health monitoring
    """
    
    # Default routing preferences by task type (FREE PROVIDERS ONLY)
    TASK_ROUTING = {
        TaskType.FAST_QUERY: ["groq", "gemini", "ollama"],
        TaskType.COMPLEX_REASONING: ["gemini", "groq", "ollama"],
        TaskType.CODING: ["groq", "gemini", "ollama"],
        TaskType.CREATIVE: ["gemini", "groq", "ollama"],
        TaskType.CONVERSATION: ["groq", "gemini", "ollama"],
        TaskType.UNKNOWN: ["groq", "gemini", "ollama"],
    }
    
    def __init__(
        self,
        groq_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        ollama_base_url: str = "http://localhost:11434",
        cache_dir: Optional[Path] = None,
        enable_cache: bool = True,
        max_retries: int = 3,
        base_backoff: float = 1.0,
    ):
        """
        Initialize the intelligent router (FREE PROVIDERS ONLY).
        
        Args:
            groq_api_key: Groq API key (free tier).
            gemini_api_key: Google AI Studio API key (free tier).
            ollama_base_url: Ollama server URL (local, free).
            cache_dir: Directory for response cache.
            enable_cache: Whether to enable response caching.
            max_retries: Maximum retry attempts per provider.
            base_backoff: Base backoff time in seconds.
        """
        self.max_retries = max_retries
        self.base_backoff = base_backoff
        
        # Initialize clients (FREE PROVIDERS ONLY)
        self.clients: Dict[str, BaseLLMClient] = {}
        self.provider_status: Dict[str, ProviderStatus] = {}
        
        # Groq (Primary - fast, free tier: 14,400 req/day)
        if groq_api_key:
            self.clients["groq"] = GroqClient(
                api_key=groq_api_key,
                model="llama-3.3-70b-versatile",
            )
            self.provider_status["groq"] = ProviderStatus(
                name="groq",
                available=True,
                rate_limit=RateLimitInfo(max_requests=14400, reset_interval=86400),
            )
        
        # Gemini (Secondary - complex reasoning, free tier: 1,500 req/day)
        if gemini_api_key:
            self.clients["gemini"] = GeminiClient(
                api_key=gemini_api_key,
                model="gemini-2.0-flash-exp",
            )
            self.provider_status["gemini"] = ProviderStatus(
                name="gemini",
                available=True,
                rate_limit=RateLimitInfo(max_requests=1500, max_tokens=1000000, reset_interval=60),
            )
        
        # Ollama (Tertiary - offline, completely free)
        ollama_client = OllamaClient(
            model="llama3.2",
            base_url=ollama_base_url,
        )
        if ollama_client.is_available():
            self.clients["ollama"] = ollama_client
            self.provider_status["ollama"] = ProviderStatus(
                name="ollama",
                available=True,
            )
        
        # Initialize cache
        self.cache: Optional[ResponseCache] = None
        if enable_cache and cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache = ResponseCache(cache_dir / "llm_cache.db")
        
        logger.info(f"LLM Router initialized with {len(self.clients)} providers: {list(self.clients.keys())}")
    
    def _get_provider_order(self, task_type: TaskType) -> List[str]:
        """Get ordered list of providers for a task type."""
        preferred = self.TASK_ROUTING.get(task_type, self.TASK_ROUTING[TaskType.UNKNOWN])
        
        # Filter to available providers
        available = []
        for provider in preferred:
            if provider in self.clients:
                status = self.provider_status.get(provider)
                if status and status.available:
                    # Check if in backoff period
                    if status.consecutive_failures > 0:
                        backoff_time = self.base_backoff * (2 ** status.consecutive_failures)
                        if time.time() - status.last_error_time < backoff_time:
                            continue
                    available.append(provider)
        
        return available
    
    def _calculate_backoff(self, failures: int) -> float:
        """Calculate exponential backoff time."""
        return min(self.base_backoff * (2 ** failures), 60.0)  # Max 60 seconds
    
    def _record_success(self, provider: str, tokens: int = 0) -> None:
        """Record a successful request."""
        status = self.provider_status.get(provider)
        if status:
            status.consecutive_failures = 0
            status.total_requests += 1
            status.total_tokens += tokens
            if status.rate_limit:
                status.rate_limit.record_request(tokens)
    
    def _record_failure(self, provider: str, error: str) -> None:
        """Record a failed request."""
        status = self.provider_status.get(provider)
        if status:
            status.consecutive_failures += 1
            status.last_error = error
            status.last_error_time = time.time()
            
            # Mark as unavailable after too many failures
            if status.consecutive_failures >= self.max_retries:
                status.available = False
                logger.warning(f"Provider {provider} marked unavailable after {status.consecutive_failures} failures")
    
    def generate(
        self,
        messages: List[Message],
        task_type: Optional[TaskType] = None,
        preferred_provider: Optional[str] = None,
        use_cache: bool = True,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a response with intelligent routing.
        
        Args:
            messages: Chat messages.
            task_type: Optional task type (auto-detected if not provided).
            preferred_provider: Optional preferred provider.
            use_cache: Whether to use response cache.
            **kwargs: Additional arguments for the LLM.
            
        Returns:
            LLMResponse from the best available provider.
        """
        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(messages)
            if cached:
                logger.debug("Returning cached response")
                return cached
        
        # Auto-detect task type if not provided
        if task_type is None:
            user_messages = [m for m in messages if m.role == "user"]
            if user_messages:
                task_type = TaskClassifier.classify(user_messages[-1].content)
            else:
                task_type = TaskType.UNKNOWN
        
        logger.debug(f"Task type: {task_type.value}")
        
        # Get provider order
        if preferred_provider and preferred_provider in self.clients:
            providers = [preferred_provider] + [p for p in self._get_provider_order(task_type) if p != preferred_provider]
        else:
            providers = self._get_provider_order(task_type)
        
        if not providers:
            raise RuntimeError("No LLM providers available")
        
        last_error = None
        
        for provider in providers:
            client = self.clients[provider]
            
            for attempt in range(self.max_retries):
                try:
                    logger.debug(f"Trying {provider} (attempt {attempt + 1})")
                    response = client.generate(messages, **kwargs)
                    
                    # Record success
                    self._record_success(provider, response.tokens_used or 0)
                    
                    # Update metadata
                    response.metadata = response.metadata or {}
                    response.metadata["provider_name"] = provider
                    response.metadata["task_type"] = task_type.value
                    
                    # Cache response
                    if use_cache and self.cache:
                        self.cache.set(messages, response)
                    
                    logger.info(f"Generated response using {provider}")
                    return response
                
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"{provider} failed (attempt {attempt + 1}): {e}")
                    
                    if attempt < self.max_retries - 1:
                        backoff = self._calculate_backoff(attempt)
                        time.sleep(backoff)
            
            # Record failure after all retries
            self._record_failure(provider, last_error or "Unknown error")
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    async def agenerate(
        self,
        messages: List[Message],
        task_type: Optional[TaskType] = None,
        preferred_provider: Optional[str] = None,
        use_cache: bool = True,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response asynchronously with intelligent routing."""
        # Check cache first
        if use_cache and self.cache:
            cached = self.cache.get(messages)
            if cached:
                return cached
        
        if task_type is None:
            user_messages = [m for m in messages if m.role == "user"]
            if user_messages:
                task_type = TaskClassifier.classify(user_messages[-1].content)
            else:
                task_type = TaskType.UNKNOWN
        
        if preferred_provider and preferred_provider in self.clients:
            providers = [preferred_provider] + [p for p in self._get_provider_order(task_type) if p != preferred_provider]
        else:
            providers = self._get_provider_order(task_type)
        
        if not providers:
            raise RuntimeError("No LLM providers available")
        
        last_error = None
        
        for provider in providers:
            client = self.clients[provider]
            
            for attempt in range(self.max_retries):
                try:
                    response = await client.agenerate(messages, **kwargs)
                    self._record_success(provider, response.tokens_used or 0)
                    
                    response.metadata = response.metadata or {}
                    response.metadata["provider_name"] = provider
                    response.metadata["task_type"] = task_type.value
                    
                    if use_cache and self.cache:
                        self.cache.set(messages, response)
                    
                    return response
                
                except Exception as e:
                    last_error = str(e)
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self._calculate_backoff(attempt))
            
            self._record_failure(provider, last_error or "Unknown error")
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    def stream(
        self,
        messages: List[Message],
        task_type: Optional[TaskType] = None,
        preferred_provider: Optional[str] = None,
        **kwargs,
    ) -> Iterator[str]:
        """Stream a response with intelligent routing."""
        if task_type is None:
            user_messages = [m for m in messages if m.role == "user"]
            if user_messages:
                task_type = TaskClassifier.classify(user_messages[-1].content)
            else:
                task_type = TaskType.UNKNOWN
        
        if preferred_provider and preferred_provider in self.clients:
            providers = [preferred_provider] + [p for p in self._get_provider_order(task_type) if p != preferred_provider]
        else:
            providers = self._get_provider_order(task_type)
        
        if not providers:
            raise RuntimeError("No LLM providers available")
        
        last_error = None
        
        for provider in providers:
            client = self.clients[provider]
            
            try:
                logger.info(f"Streaming from {provider}")
                yield from client.stream(messages, **kwargs)
                self._record_success(provider)
                return
            except Exception as e:
                last_error = str(e)
                self._record_failure(provider, last_error)
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    async def astream(
        self,
        messages: List[Message],
        task_type: Optional[TaskType] = None,
        preferred_provider: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream a response asynchronously with intelligent routing."""
        if task_type is None:
            user_messages = [m for m in messages if m.role == "user"]
            if user_messages:
                task_type = TaskClassifier.classify(user_messages[-1].content)
            else:
                task_type = TaskType.UNKNOWN
        
        if preferred_provider and preferred_provider in self.clients:
            providers = [preferred_provider] + [p for p in self._get_provider_order(task_type) if p != preferred_provider]
        else:
            providers = self._get_provider_order(task_type)
        
        if not providers:
            raise RuntimeError("No LLM providers available")
        
        last_error = None
        
        for provider in providers:
            client = self.clients[provider]
            
            try:
                async for chunk in client.astream(messages, **kwargs):
                    yield chunk
                self._record_success(provider)
                return
            except Exception as e:
                last_error = str(e)
                self._record_failure(provider, last_error)
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get router status and statistics."""
        return {
            "providers": {
                name: {
                    "available": status.available,
                    "consecutive_failures": status.consecutive_failures,
                    "total_requests": status.total_requests,
                    "total_tokens": status.total_tokens,
                    "last_error": status.last_error,
                }
                for name, status in self.provider_status.items()
            },
            "cache_stats": self.cache.get_stats() if self.cache else None,
        }
    
    def reset_provider(self, provider: str) -> bool:
        """Reset a provider's failure state."""
        if provider in self.provider_status:
            status = self.provider_status[provider]
            status.available = True
            status.consecutive_failures = 0
            status.last_error = None
            logger.info(f"Reset provider: {provider}")
            return True
        return False


def create_intelligent_router(
    cache_dir: Optional[Path] = None,
    **api_keys,
) -> IntelligentLLMRouter:
    """
    Factory function to create an intelligent LLM router.
    
    Args:
        cache_dir: Directory for response cache.
        **api_keys: API keys for providers.
        
    Returns:
        Configured IntelligentLLMRouter (FREE PROVIDERS ONLY).
    """
    return IntelligentLLMRouter(
        groq_api_key=api_keys.get("groq_api_key"),
        gemini_api_key=api_keys.get("gemini_api_key"),
        ollama_base_url=api_keys.get("ollama_base_url", "http://localhost:11434"),
        cache_dir=cache_dir,
    )
