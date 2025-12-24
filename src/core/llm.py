"""
LLM Integration Module for JARVIS.

Provides a unified interface to multiple LLM providers with automatic
fallback, retry logic, and streaming support.

Supported providers (FREE ONLY):
- Groq (Primary - fast, free tier)
- Gemini (Secondary - complex reasoning, free tier)
- Ollama (Tertiary - local, offline)
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Union

from loguru import logger


class LLMProvider(Enum):
    """Supported LLM providers (FREE ONLY)."""
    GROQ = "groq"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class LLMResponse:
    """Response from an LLM."""
    content: str
    provider: LLMProvider
    model: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Message:
    """A chat message."""
    role: str  # "system", "user", "assistant"
    content: str
    
    def to_dict(self) -> Dict[str, str]:
        return {"role": self.role, "content": self.content}


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(
        self,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 30,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
    
    @property
    @abstractmethod
    def provider(self) -> LLMProvider:
        """Get the provider type."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available."""
        pass
    
    @abstractmethod
    def generate(
        self,
        messages: List[Message],
        **kwargs,
    ) -> LLMResponse:
        """Generate a response synchronously."""
        pass
    
    @abstractmethod
    async def agenerate(
        self,
        messages: List[Message],
        **kwargs,
    ) -> LLMResponse:
        """Generate a response asynchronously."""
        pass
    
    @abstractmethod
    def stream(
        self,
        messages: List[Message],
        **kwargs,
    ) -> Iterator[str]:
        """Stream a response synchronously."""
        pass
    
    @abstractmethod
    async def astream(
        self,
        messages: List[Message],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Stream a response asynchronously."""
        pass


class GroqClient(BaseLLMClient):
    """Groq API client."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 30,
    ):
        super().__init__(model, temperature, max_tokens, timeout)
        self.api_key = api_key
        self._client = None
        self._async_client = None
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.GROQ
    
    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key, timeout=self.timeout)
            except ImportError:
                logger.error("groq package not installed")
                return None
        return self._client
    
    def _get_async_client(self):
        if self._async_client is None:
            try:
                from groq import AsyncGroq
                self._async_client = AsyncGroq(api_key=self.api_key, timeout=self.timeout)
            except ImportError:
                logger.error("groq package not installed")
                return None
        return self._async_client
    
    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            from groq import Groq
            return True
        except ImportError:
            return False
    
    def generate(self, messages: List[Message], **kwargs) -> LLMResponse:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Groq client not available")
        
        response = client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=self.provider,
            model=self.model,
            tokens_used=response.usage.total_tokens if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
        )
    
    async def agenerate(self, messages: List[Message], **kwargs) -> LLMResponse:
        client = self._get_async_client()
        if client is None:
            raise RuntimeError("Groq async client not available")
        
        response = await client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=self.provider,
            model=self.model,
            tokens_used=response.usage.total_tokens if response.usage else None,
            finish_reason=response.choices[0].finish_reason,
        )
    
    def stream(self, messages: List[Message], **kwargs) -> Iterator[str]:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Groq client not available")
        
        stream = client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    async def astream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        client = self._get_async_client()
        if client is None:
            raise RuntimeError("Groq async client not available")
        
        stream = await client.chat.completions.create(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class OllamaClient(BaseLLMClient):
    """Ollama local LLM client."""
    
    def __init__(
        self,
        model: str = "llama3.2",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
    ):
        super().__init__(model, temperature, max_tokens, timeout)
        self.base_url = base_url
        self._client = None
        self._async_client = None
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OLLAMA
    
    def _get_client(self):
        if self._client is None:
            try:
                from ollama import Client
                self._client = Client(host=self.base_url, timeout=self.timeout)
            except ImportError:
                logger.error("ollama package not installed")
                return None
        return self._client
    
    def _get_async_client(self):
        if self._async_client is None:
            try:
                from ollama import AsyncClient
                self._async_client = AsyncClient(host=self.base_url, timeout=self.timeout)
            except ImportError:
                logger.error("ollama package not installed")
                return None
        return self._async_client
    
    def is_available(self) -> bool:
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate(self, messages: List[Message], **kwargs) -> LLMResponse:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Ollama client not available")
        
        response = client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            options={
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        )
        
        return LLMResponse(
            content=response["message"]["content"],
            provider=self.provider,
            model=self.model,
            tokens_used=response.get("eval_count"),
            finish_reason="stop",
        )
    
    async def agenerate(self, messages: List[Message], **kwargs) -> LLMResponse:
        client = self._get_async_client()
        if client is None:
            raise RuntimeError("Ollama async client not available")
        
        response = await client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            options={
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        )
        
        return LLMResponse(
            content=response["message"]["content"],
            provider=self.provider,
            model=self.model,
            tokens_used=response.get("eval_count"),
            finish_reason="stop",
        )
    
    def stream(self, messages: List[Message], **kwargs) -> Iterator[str]:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Ollama client not available")
        
        stream = client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            options={
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
            stream=True,
        )
        
        for chunk in stream:
            if chunk["message"]["content"]:
                yield chunk["message"]["content"]
    
    async def astream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        client = self._get_async_client()
        if client is None:
            raise RuntimeError("Ollama async client not available")
        
        stream = await client.chat(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            options={
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
            stream=True,
        )
        
        async for chunk in stream:
            if chunk["message"]["content"]:
                yield chunk["message"]["content"]


class LLMManager:
    """
    Manages multiple LLM providers with automatic fallback.
    
    Provides a unified interface that automatically falls back to
    secondary providers when the primary fails.
    """
    
    def __init__(
        self,
        primary: BaseLLMClient,
        secondary: Optional[BaseLLMClient] = None,
        tertiary: Optional[BaseLLMClient] = None,
        retry_attempts: int = 2,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the LLM manager.
        
        Args:
            primary: Primary LLM client (e.g., Groq).
            secondary: Secondary fallback client (e.g., Ollama).
            tertiary: Tertiary fallback client (e.g., Anthropic).
            retry_attempts: Number of retry attempts per provider.
            retry_delay: Delay between retries in seconds.
        """
        self.clients = [c for c in [primary, secondary, tertiary] if c is not None]
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        
        if not self.clients:
            raise ValueError("At least one LLM client must be provided")
        
        logger.info(f"LLM Manager initialized with {len(self.clients)} providers")
    
    def get_available_providers(self) -> List[LLMProvider]:
        """Get list of currently available providers."""
        return [c.provider for c in self.clients if c.is_available()]
    
    def generate(
        self,
        messages: List[Message],
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a response with automatic fallback.
        
        Args:
            messages: List of chat messages.
            preferred_provider: Optional preferred provider to try first.
            **kwargs: Additional arguments passed to the LLM.
            
        Returns:
            LLMResponse from the first successful provider.
            
        Raises:
            RuntimeError: If all providers fail.
        """
        # Reorder clients if preferred provider specified
        clients = self.clients.copy()
        if preferred_provider:
            clients.sort(key=lambda c: c.provider != preferred_provider)
        
        last_error = None
        
        for client in clients:
            if not client.is_available():
                logger.debug(f"Provider {client.provider.value} not available, skipping")
                continue
            
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"Trying {client.provider.value} (attempt {attempt + 1})")
                    response = client.generate(messages, **kwargs)
                    logger.info(f"Generated response using {client.provider.value}")
                    return response
                except Exception as e:
                    last_error = e
                    logger.warning(f"{client.provider.value} failed: {e}")
                    if attempt < self.retry_attempts - 1:
                        import time
                        time.sleep(self.retry_delay)
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    async def agenerate(
        self,
        messages: List[Message],
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a response asynchronously with automatic fallback.
        """
        clients = self.clients.copy()
        if preferred_provider:
            clients.sort(key=lambda c: c.provider != preferred_provider)
        
        last_error = None
        
        for client in clients:
            if not client.is_available():
                continue
            
            for attempt in range(self.retry_attempts):
                try:
                    response = await client.agenerate(messages, **kwargs)
                    logger.info(f"Generated response using {client.provider.value}")
                    return response
                except Exception as e:
                    last_error = e
                    logger.warning(f"{client.provider.value} failed: {e}")
                    if attempt < self.retry_attempts - 1:
                        await asyncio.sleep(self.retry_delay)
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    def stream(
        self,
        messages: List[Message],
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs,
    ) -> Iterator[str]:
        """
        Stream a response with automatic fallback.
        """
        clients = self.clients.copy()
        if preferred_provider:
            clients.sort(key=lambda c: c.provider != preferred_provider)
        
        last_error = None
        
        for client in clients:
            if not client.is_available():
                continue
            
            try:
                logger.info(f"Streaming from {client.provider.value}")
                yield from client.stream(messages, **kwargs)
                return
            except Exception as e:
                last_error = e
                logger.warning(f"{client.provider.value} streaming failed: {e}")
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")
    
    async def astream(
        self,
        messages: List[Message],
        preferred_provider: Optional[LLMProvider] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Stream a response asynchronously with automatic fallback.
        """
        clients = self.clients.copy()
        if preferred_provider:
            clients.sort(key=lambda c: c.provider != preferred_provider)
        
        last_error = None
        
        for client in clients:
            if not client.is_available():
                continue
            
            try:
                logger.info(f"Streaming from {client.provider.value}")
                async for chunk in client.astream(messages, **kwargs):
                    yield chunk
                return
            except Exception as e:
                last_error = e
                logger.warning(f"{client.provider.value} streaming failed: {e}")
        
        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")


def create_llm_manager(
    groq_api_key: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    ollama_base_url: str = "http://localhost:11434",
    primary_model: str = "llama-3.3-70b-versatile",
    secondary_model: str = "llama3.2",
    tertiary_model: str = "claude-3-5-sonnet-20241022",
    **kwargs,
) -> LLMManager:
    """
    Factory function to create an LLM manager with configured clients.
    
    Args:
        groq_api_key: Groq API key.
        anthropic_api_key: Anthropic API key.
        ollama_base_url: Ollama server URL.
        primary_model: Model for Groq.
        secondary_model: Model for Ollama.
        tertiary_model: Model for Anthropic.
        **kwargs: Additional configuration.
        
    Returns:
        Configured LLMManager instance.
    """
    clients = []
    
    # Primary: Groq
    if groq_api_key:
        clients.append(GroqClient(
            api_key=groq_api_key,
            model=primary_model,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            timeout=kwargs.get("groq_timeout", 30),
        ))
        logger.info("Groq client configured as primary")
    
    # Secondary: Ollama
    ollama_client = OllamaClient(
        model=secondary_model,
        base_url=ollama_base_url,
        temperature=kwargs.get("temperature", 0.7),
        max_tokens=kwargs.get("max_tokens", 4096),
        timeout=kwargs.get("ollama_timeout", 60),
    )
    if ollama_client.is_available():
        clients.append(ollama_client)
        logger.info("Ollama client configured as secondary")
    else:
        logger.warning("Ollama not available")
    
    # Tertiary: Anthropic
    if anthropic_api_key:
        clients.append(AnthropicClient(
            api_key=anthropic_api_key,
            model=tertiary_model,
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            timeout=kwargs.get("anthropic_timeout", 60),
        ))
        logger.info("Anthropic client configured as tertiary")
    
    if not clients:
        raise ValueError("No LLM providers available. Please configure at least one API key or start Ollama.")
    
    return LLMManager(
        primary=clients[0],
        secondary=clients[1] if len(clients) > 1 else None,
        tertiary=clients[2] if len(clients) > 2 else None,
        retry_attempts=kwargs.get("retry_attempts", 2),
        retry_delay=kwargs.get("retry_delay", 1.0),
    )
