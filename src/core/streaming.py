"""
Streaming Response Handler for JARVIS.

Provides real-time processing of LLM streaming responses with:
- Sentence boundary detection for chunked TTS
- Buffered sentence queue for smooth playback
- Interruption handling for user input
- Metrics collection for latency tracking

Usage:
    handler = StreamingResponseHandler(tts_callback=speak_sentence)
    async for sentence in handler.process_stream(llm_stream):
        # Each sentence is ready for TTS
        pass
"""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Coroutine,
    Dict,
    Iterator,
    List,
    Optional,
    Union,
)

from loguru import logger


class StreamState(Enum):
    """State of the streaming handler."""
    IDLE = "idle"
    STREAMING = "streaming"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StreamMetrics:
    """Metrics for streaming performance."""
    start_time: float = 0.0
    first_token_time: float = 0.0
    first_sentence_time: float = 0.0
    end_time: float = 0.0
    total_tokens: int = 0
    total_sentences: int = 0
    total_characters: int = 0
    
    @property
    def time_to_first_token(self) -> float:
        """Time from start to first token in ms."""
        if self.first_token_time and self.start_time:
            return (self.first_token_time - self.start_time) * 1000
        return 0.0
    
    @property
    def time_to_first_sentence(self) -> float:
        """Time from start to first complete sentence in ms."""
        if self.first_sentence_time and self.start_time:
            return (self.first_sentence_time - self.start_time) * 1000
        return 0.0
    
    @property
    def total_time(self) -> float:
        """Total streaming time in ms."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0
    
    @property
    def tokens_per_second(self) -> float:
        """Tokens received per second."""
        total_seconds = self.total_time / 1000
        if total_seconds > 0:
            return self.total_tokens / total_seconds
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_to_first_token_ms": round(self.time_to_first_token, 2),
            "time_to_first_sentence_ms": round(self.time_to_first_sentence, 2),
            "total_time_ms": round(self.total_time, 2),
            "total_tokens": self.total_tokens,
            "total_sentences": self.total_sentences,
            "total_characters": self.total_characters,
            "tokens_per_second": round(self.tokens_per_second, 2),
        }


@dataclass
class SentenceChunk:
    """A chunk of text ready for TTS."""
    text: str
    index: int
    is_final: bool = False
    timestamp: float = field(default_factory=time.time)


class SentenceDetector:
    """
    Detects sentence boundaries in streaming text.
    
    Handles:
    - Standard punctuation (. ! ?)
    - Abbreviations (Mr., Dr., etc.)
    - Numbers with decimals (3.14)
    - URLs and emails
    - Quoted text
    - Lists and bullet points
    """
    
    # Common abbreviations that don't end sentences
    ABBREVIATIONS = {
        "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "vs", "etc", "inc", "ltd",
        "co", "corp", "st", "ave", "blvd", "rd", "apt", "no", "vol", "pg",
        "fig", "e.g", "i.e", "a.m", "p.m", "b.c", "a.d", "ph.d", "m.d",
    }
    
    # Sentence-ending punctuation
    SENTENCE_ENDERS = ".!?"
    
    # Pattern for detecting sentence boundaries
    SENTENCE_PATTERN = re.compile(
        r'(?<=[.!?])\s+(?=[A-Z])|'  # Standard sentence boundary
        r'(?<=[.!?])\s*$|'          # End of text
        r'(?<=\n)\s*(?=\S)',        # After newline
        re.MULTILINE
    )
    
    def __init__(self, min_sentence_length: int = 10):
        """
        Initialize sentence detector.
        
        Args:
            min_sentence_length: Minimum characters for a valid sentence.
        """
        self.min_sentence_length = min_sentence_length
        self.buffer = ""
        self.sentences: List[str] = []
    
    def add_text(self, text: str) -> List[str]:
        """
        Add text to buffer and extract complete sentences.
        
        Args:
            text: New text chunk to process.
            
        Returns:
            List of complete sentences extracted.
        """
        self.buffer += text
        return self._extract_sentences()
    
    def _extract_sentences(self) -> List[str]:
        """Extract complete sentences from buffer."""
        extracted = []
        
        while True:
            sentence, remaining = self._find_sentence_boundary()
            if sentence:
                # Clean up the sentence
                sentence = sentence.strip()
                if len(sentence) >= self.min_sentence_length:
                    extracted.append(sentence)
                    self.sentences.append(sentence)
                self.buffer = remaining
            else:
                break
        
        return extracted
    
    def _find_sentence_boundary(self) -> tuple[Optional[str], str]:
        """
        Find the next sentence boundary in the buffer.
        
        Returns:
            Tuple of (sentence, remaining_buffer) or (None, buffer) if no boundary found.
        """
        if not self.buffer:
            return None, ""
        
        # Look for sentence-ending punctuation
        for i, char in enumerate(self.buffer):
            if char in self.SENTENCE_ENDERS:
                # Check if this is a real sentence boundary
                if self._is_sentence_boundary(i):
                    # Include the punctuation
                    sentence = self.buffer[:i + 1]
                    remaining = self.buffer[i + 1:].lstrip()
                    return sentence, remaining
        
        # Check for newline boundaries (for lists, code, etc.)
        newline_pos = self.buffer.find('\n')
        if newline_pos > self.min_sentence_length:
            sentence = self.buffer[:newline_pos]
            remaining = self.buffer[newline_pos + 1:]
            return sentence, remaining
        
        return None, self.buffer
    
    def _is_sentence_boundary(self, pos: int) -> bool:
        """
        Check if position is a real sentence boundary.
        
        Args:
            pos: Position of potential sentence-ending punctuation.
            
        Returns:
            True if this is a real sentence boundary.
        """
        if pos >= len(self.buffer) - 1:
            # End of buffer - might be end of sentence
            return len(self.buffer) > self.min_sentence_length
        
        char = self.buffer[pos]
        next_char = self.buffer[pos + 1] if pos + 1 < len(self.buffer) else ""
        
        # Must be followed by space or end of text
        if next_char and not next_char.isspace():
            # Could be decimal number (3.14) or abbreviation
            if char == "." and next_char.isdigit():
                return False
            # Could be part of ellipsis (...)
            if char == "." and next_char == ".":
                return False
        
        # Check for abbreviations
        if char == ".":
            # Find the word before the period
            word_start = pos
            while word_start > 0 and self.buffer[word_start - 1].isalpha():
                word_start -= 1
            word = self.buffer[word_start:pos].lower()
            
            if word in self.ABBREVIATIONS:
                return False
            
            # Check for initials (single letter)
            if len(word) == 1 and word.isupper():
                return False
        
        # Check if next non-space character is uppercase (new sentence)
        remaining = self.buffer[pos + 1:].lstrip()
        if remaining and remaining[0].isupper():
            return True
        
        # If followed by space and we have enough content, consider it a boundary
        if next_char.isspace() and pos > self.min_sentence_length:
            return True
        
        return False
    
    def flush(self) -> Optional[str]:
        """
        Flush any remaining text in buffer as final sentence.
        
        Returns:
            Remaining text or None if buffer is empty.
        """
        if self.buffer.strip():
            sentence = self.buffer.strip()
            self.buffer = ""
            if len(sentence) >= 3:  # Allow shorter final sentences
                self.sentences.append(sentence)
                return sentence
        return None
    
    def reset(self) -> None:
        """Reset the detector state."""
        self.buffer = ""
        self.sentences = []


class StreamingResponseHandler:
    """
    Handles streaming LLM responses with sentence-chunked output.
    
    Features:
    - Real-time sentence extraction from token stream
    - Async queue for TTS playback
    - Interruption handling
    - Performance metrics
    """
    
    def __init__(
        self,
        tts_callback: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None,
        min_sentence_length: int = 10,
        max_buffer_sentences: int = 5,
        enable_metrics: bool = True,
    ):
        """
        Initialize the streaming handler.
        
        Args:
            tts_callback: Async callback to speak each sentence.
            min_sentence_length: Minimum characters for a sentence.
            max_buffer_sentences: Maximum sentences to buffer.
            enable_metrics: Whether to collect performance metrics.
        """
        self.tts_callback = tts_callback
        self.min_sentence_length = min_sentence_length
        self.max_buffer_sentences = max_buffer_sentences
        self.enable_metrics = enable_metrics
        
        self.state = StreamState.IDLE
        self.metrics = StreamMetrics()
        self.sentence_detector = SentenceDetector(min_sentence_length)
        
        # Sentence queue for TTS
        self._sentence_queue: asyncio.Queue[SentenceChunk] = asyncio.Queue()
        self._full_response = ""
        self._sentence_index = 0
        self._interrupted = False
        
        # TTS task
        self._tts_task: Optional[asyncio.Task] = None
    
    @property
    def full_response(self) -> str:
        """Get the full accumulated response."""
        return self._full_response
    
    @property
    def is_streaming(self) -> bool:
        """Check if currently streaming."""
        return self.state == StreamState.STREAMING
    
    async def process_stream(
        self,
        stream: AsyncIterator[str],
        start_tts: bool = True,
    ) -> AsyncIterator[SentenceChunk]:
        """
        Process a streaming LLM response.
        
        Args:
            stream: Async iterator of token chunks.
            start_tts: Whether to start TTS playback automatically.
            
        Yields:
            SentenceChunk for each complete sentence.
        """
        self._reset()
        self.state = StreamState.STREAMING
        self.metrics.start_time = time.time()
        
        # Start TTS consumer if callback provided
        if start_tts and self.tts_callback:
            self._tts_task = asyncio.create_task(self._tts_consumer())
        
        try:
            async for token in stream:
                if self._interrupted:
                    self.state = StreamState.INTERRUPTED
                    break
                
                # Record first token time
                if self.metrics.total_tokens == 0:
                    self.metrics.first_token_time = time.time()
                
                self.metrics.total_tokens += 1
                self._full_response += token
                
                # Extract sentences
                sentences = self.sentence_detector.add_text(token)
                
                for sentence in sentences:
                    # Record first sentence time
                    if self.metrics.total_sentences == 0:
                        self.metrics.first_sentence_time = time.time()
                    
                    self.metrics.total_sentences += 1
                    self.metrics.total_characters += len(sentence)
                    
                    chunk = SentenceChunk(
                        text=sentence,
                        index=self._sentence_index,
                        is_final=False,
                    )
                    self._sentence_index += 1
                    
                    # Add to TTS queue
                    await self._sentence_queue.put(chunk)
                    
                    yield chunk
            
            # Flush remaining buffer
            final_sentence = self.sentence_detector.flush()
            if final_sentence:
                if self.metrics.total_sentences == 0:
                    self.metrics.first_sentence_time = time.time()
                
                self.metrics.total_sentences += 1
                self.metrics.total_characters += len(final_sentence)
                
                chunk = SentenceChunk(
                    text=final_sentence,
                    index=self._sentence_index,
                    is_final=True,
                )
                self._sentence_index += 1
                
                await self._sentence_queue.put(chunk)
                yield chunk
            
            # Signal end of stream
            await self._sentence_queue.put(SentenceChunk(text="", index=-1, is_final=True))
            
            if not self._interrupted:
                self.state = StreamState.COMPLETED
            
        except Exception as e:
            self.state = StreamState.ERROR
            logger.error(f"Streaming error: {e}")
            raise
        
        finally:
            self.metrics.end_time = time.time()
            
            # Wait for TTS to finish
            if self._tts_task:
                try:
                    await asyncio.wait_for(self._tts_task, timeout=30.0)
                except asyncio.TimeoutError:
                    self._tts_task.cancel()
            
            if self.enable_metrics:
                logger.debug(f"Streaming metrics: {self.metrics.to_dict()}")
    
    async def process_stream_sync(
        self,
        stream: Iterator[str],
    ) -> AsyncIterator[SentenceChunk]:
        """
        Process a synchronous stream (wraps in async).
        
        Args:
            stream: Sync iterator of token chunks.
            
        Yields:
            SentenceChunk for each complete sentence.
        """
        async def async_wrapper():
            for token in stream:
                yield token
                await asyncio.sleep(0)  # Yield control
        
        async for chunk in self.process_stream(async_wrapper()):
            yield chunk
    
    async def _tts_consumer(self) -> None:
        """Consume sentences from queue and speak them."""
        while True:
            try:
                chunk = await self._sentence_queue.get()
                
                # Check for end signal
                if chunk.index == -1:
                    break
                
                # Check for interruption
                if self._interrupted:
                    break
                
                # Speak the sentence
                if self.tts_callback and chunk.text:
                    try:
                        await self.tts_callback(chunk.text)
                    except Exception as e:
                        logger.error(f"TTS callback error: {e}")
                
                self._sentence_queue.task_done()
                
            except asyncio.CancelledError:
                break
    
    def interrupt(self) -> None:
        """Interrupt the current stream."""
        self._interrupted = True
        self.state = StreamState.INTERRUPTED
        logger.debug("Stream interrupted by user")
    
    def _reset(self) -> None:
        """Reset handler state for new stream."""
        self.state = StreamState.IDLE
        self.metrics = StreamMetrics()
        self.sentence_detector.reset()
        self._sentence_queue = asyncio.Queue()
        self._full_response = ""
        self._sentence_index = 0
        self._interrupted = False
        self._tts_task = None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.to_dict()


class StreamingTTSQueue:
    """
    Manages TTS playback queue for streaming responses.
    
    Features:
    - Non-blocking sentence queuing
    - Playback state management
    - Interruption support
    - Overlap prevention
    """
    
    def __init__(
        self,
        speak_func: Callable[[str, bool], Coroutine[Any, Any, None]],
        max_queue_size: int = 10,
    ):
        """
        Initialize TTS queue.
        
        Args:
            speak_func: Async function to speak text. Args: (text, blocking).
            max_queue_size: Maximum sentences to queue.
        """
        self.speak_func = speak_func
        self.max_queue_size = max_queue_size
        
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=max_queue_size)
        self._is_speaking = False
        self._should_stop = False
        self._consumer_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """Start the TTS consumer."""
        self._should_stop = False
        self._consumer_task = asyncio.create_task(self._consume())
    
    async def stop(self) -> None:
        """Stop the TTS consumer."""
        self._should_stop = True
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
    
    async def add(self, text: str) -> bool:
        """
        Add text to the queue.
        
        Args:
            text: Text to speak.
            
        Returns:
            True if added, False if queue is full.
        """
        try:
            self._queue.put_nowait(text)
            return True
        except asyncio.QueueFull:
            logger.warning("TTS queue full, dropping sentence")
            return False
    
    async def _consume(self) -> None:
        """Consume and speak queued sentences."""
        while not self._should_stop:
            try:
                text = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                
                if self._should_stop:
                    break
                
                self._is_speaking = True
                try:
                    await self.speak_func(text, True)
                except Exception as e:
                    logger.error(f"TTS error: {e}")
                finally:
                    self._is_speaking = False
                    self._queue.task_done()
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
    
    def interrupt(self) -> None:
        """Interrupt current playback and clear queue."""
        self._should_stop = True
        # Clear the queue
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    @property
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking
    
    @property
    def queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()


async def create_streaming_response(
    llm_stream: AsyncIterator[str],
    tts_speak: Optional[Callable[[str], Coroutine[Any, Any, None]]] = None,
) -> tuple[str, StreamMetrics]:
    """
    Convenience function to process a streaming response with TTS.
    
    Args:
        llm_stream: Async iterator of LLM tokens.
        tts_speak: Optional async function to speak sentences.
        
    Returns:
        Tuple of (full_response, metrics).
    """
    handler = StreamingResponseHandler(tts_callback=tts_speak)
    
    async for _ in handler.process_stream(llm_stream):
        pass  # Sentences are handled by the TTS callback
    
    return handler.full_response, handler.metrics
