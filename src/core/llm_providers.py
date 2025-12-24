"""
Extended LLM Provider Clients for JARVIS.

Adds support for:
- Google Gemini (free tier: 1M tokens/minute)
- Mistral AI (free tier: 1B tokens/month)
- OpenRouter (30+ free models)
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional

from loguru import logger

from .llm import BaseLLMClient, LLMProvider, LLMResponse, Message


class ExtendedLLMProvider(Enum):
    """Extended LLM providers (FREE ONLY)."""
    GROQ = "groq"
    GEMINI = "gemini"
    OLLAMA = "ollama"


@dataclass
class RateLimitInfo:
    """Rate limit tracking for a provider."""
    requests_made: int = 0
    tokens_used: int = 0
    last_reset: float = field(default_factory=time.time)
    reset_interval: int = 60  # seconds
    max_requests: int = 1000
    max_tokens: int = 100000
    
    def can_make_request(self, estimated_tokens: int = 1000) -> bool:
        """Check if we can make a request within rate limits."""
        self._maybe_reset()
        return (
            self.requests_made < self.max_requests and
            self.tokens_used + estimated_tokens < self.max_tokens
        )
    
    def record_request(self, tokens: int = 0) -> None:
        """Record a request."""
        self._maybe_reset()
        self.requests_made += 1
        self.tokens_used += tokens
    
    def _maybe_reset(self) -> None:
        """Reset counters if interval has passed."""
        now = time.time()
        if now - self.last_reset > self.reset_interval:
            self.requests_made = 0
            self.tokens_used = 0
            self.last_reset = now
    
    def time_until_reset(self) -> float:
        """Get seconds until rate limit resets."""
        return max(0, self.reset_interval - (time.time() - self.last_reset))


class GeminiClient(BaseLLMClient):
    """
    Google Gemini API client.
    
    Free tier: 1,500 requests/day, 1M tokens/minute
    Models: gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        timeout: int = 60,
    ):
        super().__init__(model, temperature, max_tokens, timeout)
        self.api_key = api_key
        self._client = None
        self.rate_limit = RateLimitInfo(
            max_requests=1500,  # per day
            max_tokens=1000000,  # per minute
            reset_interval=60,
        )
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI  # Use OPENAI as placeholder, will add GEMINI to enum
    
    def _get_client(self):
        if self._client is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model)
            except ImportError:
                logger.error("google-generativeai package not installed")
                return None
        return self._client
    
    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import google.generativeai
            return self.rate_limit.can_make_request()
        except ImportError:
            return False
    
    def _convert_messages(self, messages: List[Message]) -> tuple:
        """Convert messages to Gemini format."""
        system_instruction = None
        history = []
        
        for msg in messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                history.append({"role": "user", "parts": [msg.content]})
            elif msg.role == "assistant":
                history.append({"role": "model", "parts": [msg.content]})
        
        return system_instruction, history
    
    def generate(self, messages: List[Message], **kwargs) -> LLMResponse:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Gemini client not available")
        
        system_instruction, history = self._convert_messages(messages)
        
        # Get the last user message
        last_message = history[-1]["parts"][0] if history else ""
        chat_history = history[:-1] if len(history) > 1 else []
        
        try:
            import google.generativeai as genai
            
            # Create model with system instruction if provided
            if system_instruction:
                model = genai.GenerativeModel(
                    self.model,
                    system_instruction=system_instruction,
                )
            else:
                model = client
            
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(
                last_message,
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get("temperature", self.temperature),
                    max_output_tokens=kwargs.get("max_tokens", self.max_tokens),
                ),
            )
            
            self.rate_limit.record_request(response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0)
            
            return LLMResponse(
                content=response.text,
                provider=self.provider,
                model=self.model,
                tokens_used=response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None,
                finish_reason="stop",
                metadata={"provider_name": "gemini"},
            )
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            raise
    
    async def agenerate(self, messages: List[Message], **kwargs) -> LLMResponse:
        # Gemini SDK is sync, run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.generate(messages, **kwargs))
    
    def stream(self, messages: List[Message], **kwargs) -> Iterator[str]:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Gemini client not available")
        
        system_instruction, history = self._convert_messages(messages)
        last_message = history[-1]["parts"][0] if history else ""
        chat_history = history[:-1] if len(history) > 1 else []
        
        try:
            import google.generativeai as genai
            
            if system_instruction:
                model = genai.GenerativeModel(
                    self.model,
                    system_instruction=system_instruction,
                )
            else:
                model = client
            
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(
                last_message,
                generation_config=genai.types.GenerationConfig(
                    temperature=kwargs.get("temperature", self.temperature),
                    max_output_tokens=kwargs.get("max_tokens", self.max_tokens),
                ),
                stream=True,
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            logger.error(f"Gemini streaming failed: {e}")
            raise
    
    async def astream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        # Run sync stream in executor
        loop = asyncio.get_event_loop()
        
        def sync_stream():
            return list(self.stream(messages, **kwargs))
        
        chunks = await loop.run_in_executor(None, sync_stream)
        for chunk in chunks:
            yield chunk


class MistralClient(BaseLLMClient):
    """
    Mistral AI API client.
    
    Free tier: 1B tokens/month
    Models: mistral-large-latest, mistral-small-latest, codestral-latest
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "mistral-small-latest",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
    ):
        super().__init__(model, temperature, max_tokens, timeout)
        self.api_key = api_key
        self._client = None
        self._async_client = None
        self.rate_limit = RateLimitInfo(
            max_requests=10000,
            max_tokens=1000000000 // 30,  # ~33M tokens/day
            reset_interval=86400,  # daily
        )
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI  # Placeholder
    
    def _get_client(self):
        if self._client is None:
            try:
                from mistralai import Mistral
                self._client = Mistral(api_key=self.api_key)
            except ImportError:
                logger.error("mistralai package not installed")
                return None
        return self._client
    
    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            from mistralai import Mistral
            return self.rate_limit.can_make_request()
        except ImportError:
            return False
    
    def generate(self, messages: List[Message], **kwargs) -> LLMResponse:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Mistral client not available")
        
        response = client.chat.complete(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        
        tokens = response.usage.total_tokens if response.usage else 0
        self.rate_limit.record_request(tokens)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=self.provider,
            model=self.model,
            tokens_used=tokens,
            finish_reason=response.choices[0].finish_reason,
            metadata={"provider_name": "mistral"},
        )
    
    async def agenerate(self, messages: List[Message], **kwargs) -> LLMResponse:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Mistral client not available")
        
        response = await client.chat.complete_async(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        
        tokens = response.usage.total_tokens if response.usage else 0
        self.rate_limit.record_request(tokens)
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=self.provider,
            model=self.model,
            tokens_used=tokens,
            finish_reason=response.choices[0].finish_reason,
            metadata={"provider_name": "mistral"},
        )
    
    def stream(self, messages: List[Message], **kwargs) -> Iterator[str]:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Mistral client not available")
        
        stream = client.chat.stream(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        
        for chunk in stream:
            if chunk.data.choices[0].delta.content:
                yield chunk.data.choices[0].delta.content
    
    async def astream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        client = self._get_client()
        if client is None:
            raise RuntimeError("Mistral client not available")
        
        stream = await client.chat.stream_async(
            model=self.model,
            messages=[m.to_dict() for m in messages],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        
        async for chunk in stream:
            if chunk.data.choices[0].delta.content:
                yield chunk.data.choices[0].delta.content


class OpenRouterClient(BaseLLMClient):
    """
    OpenRouter API client.
    
    Access to 30+ free models as emergency fallback.
    Free models include: meta-llama/llama-3.2-3b-instruct:free, etc.
    """
    
    FREE_MODELS = [
        "meta-llama/llama-3.2-3b-instruct:free",
        "meta-llama/llama-3.2-1b-instruct:free",
        "google/gemma-2-9b-it:free",
        "microsoft/phi-3-mini-128k-instruct:free",
        "qwen/qwen-2-7b-instruct:free",
    ]
    
    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-3.2-3b-instruct:free",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: int = 60,
        site_url: str = "https://jarvis.local",
        site_name: str = "JARVIS",
    ):
        super().__init__(model, temperature, max_tokens, timeout)
        self.api_key = api_key
        self.site_url = site_url
        self.site_name = site_name
        self.base_url = "https://openrouter.ai/api/v1"
    
    @property
    def provider(self) -> LLMProvider:
        return LLMProvider.OPENAI  # Uses OpenAI-compatible API
    
    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            import httpx
            return True
        except ImportError:
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
            "Content-Type": "application/json",
        }
    
    def generate(self, messages: List[Message], **kwargs) -> LLMResponse:
        import httpx
        
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers=self._get_headers(),
            json={
                "model": self.model,
                "messages": [m.to_dict() for m in messages],
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            },
            timeout=self.timeout,
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter error: {response.text}")
        
        data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            provider=self.provider,
            model=self.model,
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=data["choices"][0].get("finish_reason"),
            metadata={"provider_name": "openrouter"},
        )
    
    async def agenerate(self, messages: List[Message], **kwargs) -> LLMResponse:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "messages": [m.to_dict() for m in messages],
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                },
                timeout=self.timeout,
            )
        
        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter error: {response.text}")
        
        data = response.json()
        
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            provider=self.provider,
            model=self.model,
            tokens_used=data.get("usage", {}).get("total_tokens"),
            finish_reason=data["choices"][0].get("finish_reason"),
            metadata={"provider_name": "openrouter"},
        )
    
    def stream(self, messages: List[Message], **kwargs) -> Iterator[str]:
        import httpx
        
        with httpx.stream(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self._get_headers(),
            json={
                "model": self.model,
                "messages": [m.to_dict() for m in messages],
                "temperature": kwargs.get("temperature", self.temperature),
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "stream": True,
            },
            timeout=self.timeout,
        ) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
    
    async def astream(self, messages: List[Message], **kwargs) -> AsyncIterator[str]:
        import httpx
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json={
                    "model": self.model,
                    "messages": [m.to_dict() for m in messages],
                    "temperature": kwargs.get("temperature", self.temperature),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "stream": True,
                },
                timeout=self.timeout,
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
