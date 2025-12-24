"""
Unit tests for the streaming module.

Tests:
- SentenceDetector with edge cases
- StreamingResponseHandler
- StreamingTTSQueue
- Interruption handling
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.streaming import (
    SentenceDetector,
    StreamingResponseHandler,
    StreamingTTSQueue,
    StreamMetrics,
    SentenceChunk,
    StreamState,
)


class TestSentenceDetector:
    """Tests for SentenceDetector class."""
    
    def test_simple_sentence(self):
        """Test detection of simple sentences."""
        detector = SentenceDetector(min_sentence_length=5)
        
        sentences = detector.add_text("Hello world. ")
        assert len(sentences) == 1
        assert sentences[0] == "Hello world."
    
    def test_multiple_sentences(self):
        """Test detection of multiple sentences."""
        detector = SentenceDetector(min_sentence_length=5)
        
        sentences = detector.add_text("First sentence. Second sentence. ")
        assert len(sentences) == 2
        assert sentences[0] == "First sentence."
        assert sentences[1] == "Second sentence."
    
    def test_streaming_tokens(self):
        """Test sentence detection with streaming tokens."""
        detector = SentenceDetector(min_sentence_length=5)
        
        # Simulate streaming tokens
        all_sentences = []
        for token in ["Hello", " ", "world", ".", " ", "How", " ", "are", " ", "you", "?", " "]:
            sentences = detector.add_text(token)
            all_sentences.extend(sentences)
        
        assert len(all_sentences) == 2
        assert all_sentences[0] == "Hello world."
        assert all_sentences[1] == "How are you?"
    
    def test_abbreviations(self):
        """Test that abbreviations don't trigger sentence breaks."""
        detector = SentenceDetector(min_sentence_length=5)
        
        sentences = detector.add_text("Dr. Smith went to the store. ")
        assert len(sentences) == 1
        assert "Dr." in sentences[0]
    
    def test_numbers_with_decimals(self):
        """Test that decimal numbers don't trigger sentence breaks."""
        detector = SentenceDetector(min_sentence_length=5)
        
        sentences = detector.add_text("The value is 3.14 approximately. ")
        assert len(sentences) == 1
        assert "3.14" in sentences[0]
    
    def test_exclamation_and_question(self):
        """Test detection with ! and ? punctuation."""
        detector = SentenceDetector(min_sentence_length=5)
        
        sentences = detector.add_text("Hello! How are you? I'm fine. ")
        assert len(sentences) == 3
    
    def test_flush_remaining(self):
        """Test flushing remaining buffer."""
        detector = SentenceDetector(min_sentence_length=3)
        
        detector.add_text("Hello world")  # No period
        remaining = detector.flush()
        
        assert remaining == "Hello world"
    
    def test_min_sentence_length(self):
        """Test minimum sentence length filtering."""
        detector = SentenceDetector(min_sentence_length=10)
        
        # "Hi." is too short
        sentences = detector.add_text("Hi. This is a longer sentence. ")
        assert len(sentences) == 1
        assert "longer" in sentences[0]
    
    def test_newline_boundary(self):
        """Test newline as sentence boundary."""
        detector = SentenceDetector(min_sentence_length=5)
        
        sentences = detector.add_text("First line\nSecond line\n")
        assert len(sentences) >= 1
    
    def test_reset(self):
        """Test detector reset."""
        detector = SentenceDetector()
        
        detector.add_text("Some text")
        detector.reset()
        
        assert detector.buffer == ""
        assert len(detector.sentences) == 0


class TestStreamMetrics:
    """Tests for StreamMetrics class."""
    
    def test_time_to_first_token(self):
        """Test TTFT calculation."""
        metrics = StreamMetrics()
        metrics.start_time = 1000.0
        metrics.first_token_time = 1000.5
        
        assert metrics.time_to_first_token == 500.0  # 500ms
    
    def test_time_to_first_sentence(self):
        """Test TTFS calculation."""
        metrics = StreamMetrics()
        metrics.start_time = 1000.0
        metrics.first_sentence_time = 1001.0
        
        assert metrics.time_to_first_sentence == 1000.0  # 1000ms
    
    def test_tokens_per_second(self):
        """Test tokens/second calculation."""
        metrics = StreamMetrics()
        metrics.start_time = 1000.0
        metrics.end_time = 1002.0  # 2 seconds
        metrics.total_tokens = 100
        
        assert metrics.tokens_per_second == 50.0
    
    def test_to_dict(self):
        """Test metrics serialization."""
        metrics = StreamMetrics()
        metrics.start_time = 1000.0
        metrics.end_time = 1001.0
        metrics.total_tokens = 50
        metrics.total_sentences = 3
        
        data = metrics.to_dict()
        
        assert "time_to_first_token_ms" in data
        assert "total_tokens" in data
        assert data["total_sentences"] == 3


class TestStreamingResponseHandler:
    """Tests for StreamingResponseHandler class."""
    
    @pytest.mark.asyncio
    async def test_basic_streaming(self):
        """Test basic streaming processing."""
        handler = StreamingResponseHandler(min_sentence_length=5)
        
        async def mock_stream():
            for token in ["Hello", " ", "world", ".", " ", "Goodbye", ".", " "]:
                yield token
        
        sentences = []
        async for chunk in handler.process_stream(mock_stream()):
            sentences.append(chunk.text)
        
        assert len(sentences) >= 1
        assert handler.state == StreamState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_full_response_accumulation(self):
        """Test that full response is accumulated."""
        handler = StreamingResponseHandler(min_sentence_length=5)
        
        async def mock_stream():
            for token in ["Hello", " ", "world", "."]:
                yield token
        
        async for _ in handler.process_stream(mock_stream()):
            pass
        
        assert handler.full_response == "Hello world."
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test that metrics are collected."""
        handler = StreamingResponseHandler(enable_metrics=True)
        
        async def mock_stream():
            for token in ["Test", " ", "sentence", ".", " "]:
                yield token
                await asyncio.sleep(0.01)
        
        async for _ in handler.process_stream(mock_stream()):
            pass
        
        metrics = handler.get_metrics()
        assert metrics["total_tokens"] > 0
        assert metrics["total_time_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_tts_callback(self):
        """Test TTS callback is called for each sentence."""
        spoken = []
        
        async def mock_tts(text):
            spoken.append(text)
        
        handler = StreamingResponseHandler(
            tts_callback=mock_tts,
            min_sentence_length=5,
        )
        
        async def mock_stream():
            for token in ["First", " ", "sentence", ".", " ", "Second", " ", "one", ".", " "]:
                yield token
        
        async for _ in handler.process_stream(mock_stream(), start_tts=True):
            pass
        
        # Wait for TTS consumer
        await asyncio.sleep(0.1)
        
        assert len(spoken) >= 1
    
    @pytest.mark.asyncio
    async def test_interruption(self):
        """Test stream interruption."""
        handler = StreamingResponseHandler()
        
        async def slow_stream():
            for i in range(100):
                yield f"token{i} "
                await asyncio.sleep(0.01)
                if i == 5:
                    handler.interrupt()
        
        chunks = []
        async for chunk in handler.process_stream(slow_stream()):
            chunks.append(chunk)
        
        assert handler.state == StreamState.INTERRUPTED
        assert len(chunks) < 100


class TestStreamingTTSQueue:
    """Tests for StreamingTTSQueue class."""
    
    @pytest.mark.asyncio
    async def test_queue_add(self):
        """Test adding to queue."""
        async def mock_speak(text, blocking):
            pass
        
        queue = StreamingTTSQueue(mock_speak, max_queue_size=5)
        
        result = await queue.add("Hello")
        assert result is True
        assert queue.queue_size == 1
    
    @pytest.mark.asyncio
    async def test_queue_full(self):
        """Test queue full behavior."""
        async def slow_speak(text, blocking):
            await asyncio.sleep(1)
        
        queue = StreamingTTSQueue(slow_speak, max_queue_size=2)
        
        await queue.add("First")
        await queue.add("Second")
        result = await queue.add("Third")  # Should fail
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_interrupt(self):
        """Test queue interruption."""
        spoken = []
        
        async def mock_speak(text, blocking):
            spoken.append(text)
            await asyncio.sleep(0.1)
        
        queue = StreamingTTSQueue(mock_speak, max_queue_size=10)
        await queue.start()
        
        await queue.add("First")
        await queue.add("Second")
        await queue.add("Third")
        
        await asyncio.sleep(0.05)
        queue.interrupt()
        await queue.stop()
        
        # Should have been interrupted before speaking all
        assert len(spoken) < 3


class TestSentenceChunk:
    """Tests for SentenceChunk dataclass."""
    
    def test_creation(self):
        """Test chunk creation."""
        chunk = SentenceChunk(text="Hello", index=0, is_final=False)
        
        assert chunk.text == "Hello"
        assert chunk.index == 0
        assert chunk.is_final is False
        assert chunk.timestamp > 0
    
    def test_final_chunk(self):
        """Test final chunk marker."""
        chunk = SentenceChunk(text="Goodbye", index=5, is_final=True)
        
        assert chunk.is_final is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
