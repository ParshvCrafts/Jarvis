# JARVIS Developer Guide

A comprehensive guide for developers working on or extending JARVIS.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Module Structure](#module-structure)
4. [Adding New Features](#adding-new-features)
5. [Testing](#testing)
6. [Code Style](#code-style)
7. [Contribution Guidelines](#contribution-guidelines)

---

## Architecture Overview

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams. Key points:

- **Modular Design**: Each feature is a separate module in `src/`
- **Enhanced vs Legacy**: `*_enhanced.py` files are canonical; legacy maintained for compatibility
- **Event-Driven**: Components communicate via internal event bus
- **Graceful Degradation**: System continues with reduced functionality if components fail

### Core Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Config | `src/core/config.py` | Configuration management |
| LLM | `src/core/llm.py` | Language model routing |
| Event Bus | `src/core/internal_api.py` | Inter-component communication |
| Health Monitor | `src/core/health_monitor.py` | Component health tracking |

### Data Flow

```
User Input → Voice Pipeline → Authentication → Intent Router → Agent → LLM → Response → TTS → Output
```

---

## Development Setup

### Prerequisites

```bash
# Python 3.9+
python --version

# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies
```

### Development Dependencies

```bash
pip install pytest pytest-asyncio pytest-cov
pip install black isort flake8 mypy
pip install pre-commit
```

### Pre-commit Hooks

```bash
pre-commit install
```

This runs linting and formatting on every commit.

### Environment Setup

```bash
# Copy example environment
cp .env.example .env

# Edit with your API keys
# At minimum, configure one LLM provider
```

### Running in Development

```bash
# Text mode (no audio hardware needed)
python run.py --text

# With debug logging
python run.py --text --debug

# Check configuration
python run.py --check-config

# Run pre-flight checks
python scripts/preflight_check.py --verbose
```

---

## Module Structure

### Directory Layout

```
src/
├── agents/                 # LangGraph agent system
│   ├── __init__.py
│   ├── supervisor.py       # Legacy supervisor
│   ├── supervisor_enhanced.py  # Enhanced supervisor
│   ├── research_agent.py
│   ├── system_agent.py
│   ├── coding_agent.py
│   └── tools/              # Agent tools
│
├── auth/                   # Authentication
│   ├── face_recognition.py
│   ├── voice_auth.py
│   └── liveness.py
│
├── core/                   # Core systems
│   ├── config.py           # Configuration
│   ├── llm.py              # LLM manager
│   ├── llm_router.py       # Intelligent routing
│   ├── internal_api.py     # Event bus
│   └── health_monitor.py   # Health tracking
│
├── iot/                    # IoT control
│   ├── esp32_enhanced.py   # Device controller
│   └── controller_enhanced.py  # Production controller
│
├── memory/                 # Memory systems
│   ├── conversation.py     # Short-term
│   ├── vector_store.py     # Long-term (ChromaDB)
│   └── episodic.py         # Historical (SQLite)
│
├── system/                 # System control
│   ├── app_manager.py
│   ├── browser.py
│   └── git_integration.py
│
├── telegram/               # Telegram bot
│   └── bot_enhanced.py
│
├── voice/                  # Voice pipeline
│   ├── pipeline_enhanced.py
│   ├── stt_enhanced.py
│   ├── wake_word_enhanced.py
│   ├── tts.py
│   ├── calibration.py
│   └── testing.py
│
└── jarvis_unified.py       # Main application
```

### Module Pattern

Each module follows this pattern:

```python
# src/feature/__init__.py

from loguru import logger

# Try enhanced module first
try:
    from .feature_enhanced import (
        EnhancedFeature,
        FeatureConfig,
    )
except ImportError as e:
    logger.warning(f"Enhanced feature not available: {e}")
    EnhancedFeature = None
    FeatureConfig = None

# Legacy fallback
try:
    from .feature import Feature as LegacyFeature
except ImportError:
    LegacyFeature = None

__all__ = [
    "EnhancedFeature",
    "FeatureConfig",
    "LegacyFeature",
]
```

---

## Adding New Features

### Adding a New Agent

1. **Create agent file** (`src/agents/my_agent.py`):

```python
"""My custom agent for JARVIS."""

from typing import Any, Dict
from langchain.tools import Tool
from langgraph.graph import StateGraph

class MyAgent:
    """Agent for handling specific tasks."""
    
    def __init__(self, llm_manager):
        self.llm = llm_manager
        self.tools = self._create_tools()
    
    def _create_tools(self) -> list[Tool]:
        return [
            Tool(
                name="my_tool",
                description="Does something useful",
                func=self._my_tool_func,
            ),
        ]
    
    def _my_tool_func(self, input: str) -> str:
        # Tool implementation
        return f"Processed: {input}"
    
    async def process(self, query: str) -> str:
        # Agent logic
        response = await self.llm.generate(query)
        return response.content
```

2. **Register in supervisor** (`src/agents/supervisor_enhanced.py`):

```python
from .my_agent import MyAgent

class EnhancedSupervisor:
    def __init__(self):
        # ... existing code ...
        self.my_agent = MyAgent(self.llm)
    
    async def _route_to_agent(self, intent: str, query: str):
        if intent == "my_intent":
            return await self.my_agent.process(query)
        # ... existing routing ...
```

3. **Export in `__init__.py`**:

```python
from .my_agent import MyAgent
__all__.append("MyAgent")
```

### Adding a New Tool

1. **Create tool** (`src/agents/tools/my_tool.py`):

```python
from langchain.tools import Tool

def create_my_tool() -> Tool:
    """Create my custom tool."""
    
    def _execute(input: str) -> str:
        # Tool logic
        return f"Result: {input}"
    
    return Tool(
        name="my_tool",
        description="Description for LLM to understand when to use this tool",
        func=_execute,
    )
```

2. **Add to agent's tool list**.

### Adding a New Voice Command

Voice commands are handled by intent classification. To add a new command:

1. **Update intent classifier** in supervisor:

```python
INTENT_PATTERNS = {
    "my_command": ["my keyword", "another trigger"],
    # ... existing patterns ...
}
```

2. **Add handler**:

```python
async def _handle_my_command(self, query: str) -> str:
    # Handle the command
    return "Command executed"
```

### Adding a New IoT Device Type

1. **Define device type** (`src/iot/esp32_enhanced.py`):

```python
class DeviceType(Enum):
    LIGHT = "light"
    DOOR = "door"
    MY_DEVICE = "my_device"  # Add new type
```

2. **Create firmware** (`firmware/esp32/my_device/`):
   - Follow existing light/door firmware patterns
   - Implement HTTP API endpoints
   - Use HMAC authentication

3. **Add controller methods**:

```python
async def my_device_action(self, device_id: str) -> CommandResult:
    device = self.get_device(device_id)
    return await self.client.send_command(
        device, "/my_endpoint", {"action": "do_something"}
    )
```

---

## Testing

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_llm.py -v

# Integration tests
pytest tests/integration/ -v

# Skip slow tests
pytest -m "not slow"
```

### Writing Tests

```python
# tests/unit/test_my_feature.py

import pytest
from src.feature import MyFeature

class TestMyFeature:
    @pytest.fixture
    def feature(self):
        return MyFeature()
    
    def test_basic_functionality(self, feature):
        result = feature.do_something("input")
        assert result == "expected"
    
    @pytest.mark.asyncio
    async def test_async_functionality(self, feature):
        result = await feature.async_method()
        assert result is not None
    
    @pytest.mark.slow
    def test_slow_operation(self, feature):
        # This test takes a while
        pass
```

### Test Categories

| Marker | Purpose | Location |
|--------|---------|----------|
| `unit` | Unit tests | `tests/unit/` |
| `integration` | Integration tests | `tests/integration/` |
| `slow` | Long-running tests | Any |
| `requires_api` | Needs API keys | Any |
| `requires_hardware` | Needs audio/camera | Any |

### Mocking

```python
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_with_mock_llm():
    with patch("src.core.llm.LLMManager") as mock_llm:
        mock_llm.return_value.generate = AsyncMock(
            return_value=MagicMock(content="mocked response")
        )
        # Test code using LLM
```

---

## Code Style

### Formatting

We use Black and isort:

```bash
# Format code
black src/ tests/
isort src/ tests/

# Check without modifying
black --check src/
isort --check src/
```

### Linting

```bash
# Flake8
flake8 src/ tests/

# Type checking
mypy src/
```

### Style Guidelines

1. **Type hints**: Use type hints for all function signatures
2. **Docstrings**: Google-style docstrings for all public functions
3. **Imports**: Group imports (stdlib, third-party, local)
4. **Line length**: 88 characters (Black default)
5. **Naming**: snake_case for functions/variables, PascalCase for classes

### Example

```python
"""Module docstring describing purpose."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.config import config


class MyClass:
    """
    Class description.
    
    Attributes:
        name: Description of name attribute.
    """
    
    def __init__(self, name: str) -> None:
        """
        Initialize MyClass.
        
        Args:
            name: The name to use.
        """
        self.name = name
    
    async def process(self, data: Dict[str, Any]) -> Optional[str]:
        """
        Process the data.
        
        Args:
            data: Input data dictionary.
            
        Returns:
            Processed result or None if failed.
            
        Raises:
            ValueError: If data is invalid.
        """
        if not data:
            raise ValueError("Data cannot be empty")
        
        logger.debug(f"Processing data for {self.name}")
        return str(data)
```

---

## Contribution Guidelines

### Workflow

1. **Fork** the repository
2. **Create branch**: `git checkout -b feature/my-feature`
3. **Make changes** with tests
4. **Run checks**: `pytest && black --check . && flake8`
5. **Commit**: Use conventional commits
6. **Push**: `git push origin feature/my-feature`
7. **PR**: Open pull request with description

### Commit Messages

Use conventional commits:

```
feat: add new voice command for weather
fix: resolve wake word detection on Linux
docs: update installation guide
test: add unit tests for LLM router
refactor: simplify agent routing logic
chore: update dependencies
```

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Conventional commit messages
- [ ] PR description explains changes

### Code Review

PRs require:
- Passing CI checks
- At least one approval
- No unresolved comments

---

## Debugging

### Logging

```python
from loguru import logger

# Different levels
logger.debug("Detailed info for debugging")
logger.info("General information")
logger.warning("Something unexpected")
logger.error("Error occurred")
logger.exception("Error with traceback")

# Structured logging
logger.info("Processing request", extra={"user": user_id, "action": action})
```

### Debug Mode

```bash
# Enable debug logging
python run.py --debug

# Or set environment variable
export JARVIS_DEBUG=1
```

### Common Issues

**Import Errors**:
```bash
# Check module can be imported
python -c "from src.module import Class"
```

**Async Issues**:
```python
# Use asyncio.run() for testing async code
import asyncio
asyncio.run(my_async_function())
```

**Configuration Issues**:
```bash
# Validate configuration
python run.py --check-config
python scripts/preflight_check.py --verbose
```

---

## Performance

### Benchmarking

```bash
# Run benchmarks
python scripts/benchmark.py

# Quick benchmark
python scripts/benchmark.py --quick

# Specific iterations
python scripts/benchmark.py --iterations 20
```

### Profiling

```python
import cProfile
import pstats

# Profile a function
cProfile.run('my_function()', 'output.prof')

# Analyze results
stats = pstats.Stats('output.prof')
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Optimization Tips

1. **LLM calls**: Minimize by caching, batching
2. **Audio processing**: Use appropriate chunk sizes
3. **Memory**: Clear conversation history periodically
4. **I/O**: Use async for network operations

---

## API Reference

### Event Bus Events

| Event | Payload | Description |
|-------|---------|-------------|
| `wake_word_detected` | `{confidence: float}` | Wake word triggered |
| `command_received` | `{text: str, source: str}` | Command input |
| `agent_started` | `{agent: str, query: str}` | Agent processing started |
| `agent_completed` | `{agent: str, result: str}` | Agent finished |
| `device_state_changed` | `{device_id: str, state: dict}` | IoT state change |
| `health_check` | `{component: str, status: str}` | Health status |

### Configuration Options

See `config/settings.yaml` for all options. Key settings:

```yaml
jarvis:
  name: "JARVIS"
  debug: false

voice:
  wake_word:
    phrase: "hey jarvis"
    threshold: 0.5
  stt:
    provider: "groq"  # groq, whisper, google
  tts:
    provider: "edge"  # edge, pyttsx3

llm:
  default_provider: "groq"
  fallback_providers: ["gemini", "ollama"]
  timeout: 30

agents:
  enabled: ["research", "system", "coding", "iot"]

iot:
  discovery_interval: 60
  command_timeout: 10
```

---

## Performance Architecture (Phase 5)

### Overview

The performance system consists of interconnected modules:

```
┌─────────────────────────────────────────────────────────────┐
│                  PerformanceIntegration                      │
│  (src/core/performance_integration.py)                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  Streaming  │  │    Cache    │  │  ProactiveCache     │  │
│  │ Integration │  │ Integration │  │     Manager         │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌──────────▼──────────┐  │
│  │  Streaming  │  │ Intelligent │  │  CommandPredictor   │  │
│  │  Handler    │  │    Cache    │  │                     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Adding Cacheable Queries

To make a new query type cacheable:

```python
from src.core.cache import CacheCategory

# In CacheIntegration.classify_query_category():
def classify_query_category(self, query: str) -> CacheCategory:
    query_lower = query.lower()
    
    # Add your new category detection
    if "stock" in query_lower or "market" in query_lower:
        return CacheCategory.NEWS  # Use appropriate category
    
    # ... existing logic
```

### Extending Prediction

To add new prediction patterns:

```python
from src.core.performance_integration import CommandPredictor

predictor = CommandPredictor()

# Log commands to build patterns
predictor.log_command("check stocks")
predictor.log_command("buy order")

# Get predictions
next_commands = predictor.predict_next("check stocks")
```

### Dashboard Customization

To add new metrics to the dashboard:

```python
from src.core.dashboard import MetricsCollector

collector = MetricsCollector()

# Record custom latency
collector.record_latency("custom_operation", 150.0)

# Record custom error
collector.record_error("Custom error message", "my_component")
```

### Registering Prefetch Callbacks

To add proactive pre-fetching for new data types:

```python
from src.core.performance_integration import get_performance_integration

perf = get_performance_integration()

async def fetch_stock_data():
    # Your async fetch logic
    return "Stock data..."

# Register the callback
perf.register_prefetch("stocks", fetch_stock_data)
```

### Performance Module Files

| File | Purpose |
|------|---------|
| `streaming.py` | LLM response streaming with sentence detection |
| `cache.py` | Multi-level caching (LRU, SQLite, Semantic) |
| `performance.py` | Parallel execution, resource monitoring |
| `dashboard.py` | Web-based metrics dashboard |
| `performance_integration.py` | Unified integration layer |

---

## Resources

- [Architecture Diagram](ARCHITECTURE.md)
- [User Guide](USER_GUIDE.md)
- [Hardware Setup](HARDWARE_SETUP.md)
- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)

---

*JARVIS Developer Guide - Phase 4.5*
