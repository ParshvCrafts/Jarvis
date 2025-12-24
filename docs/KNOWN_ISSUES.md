# JARVIS Known Issues

This document tracks known issues, limitations, and planned improvements.

## Current Issues

### Voice Pipeline

| Issue | Severity | Workaround | Status |
|-------|----------|------------|--------|
| Wake word may trigger on similar sounds | Low | Increase threshold in settings | Open |
| STT accuracy drops with background noise | Medium | Use noise-canceling mic, run calibration | Open |
| TTS may sound robotic with pyttsx3 | Low | Use Edge TTS provider instead | Open |
| Audio device switching requires restart | Low | Restart JARVIS after changing audio devices | Open |

### LLM Integration

| Issue | Severity | Workaround | Status |
|-------|----------|------------|--------|
| Groq rate limits on free tier | Medium | Configure fallback providers | By Design |
| Ollama slow on CPU-only systems | Low | Use cloud providers for faster response | By Design |
| Context window limits for long conversations | Medium | Conversation auto-truncates | Open |

### IoT / Hardware

| Issue | Severity | Workaround | Status |
|-------|----------|------------|--------|
| mDNS discovery may fail on some networks | Medium | Manually add devices by IP | Open |
| ESP32 WiFi reconnection can take 30+ seconds | Low | Ensure strong WiFi signal | Open |
| Servo calibration values may drift | Low | Re-run calibration periodically | Open |

### Authentication

| Issue | Severity | Workaround | Status |
|-------|----------|------------|--------|
| Face recognition requires good lighting | Medium | Ensure adequate lighting | By Design |
| Voice verification sensitive to colds/illness | Low | Use alternative auth method | By Design |

### Platform-Specific

#### Windows
| Issue | Severity | Workaround | Status |
|-------|----------|------------|--------|
| Some audio devices not detected | Low | Use specific device index in config | Open |
| NSSM service may not start on boot | Low | Check Windows Event Log | Open |

#### Linux
| Issue | Severity | Workaround | Status |
|-------|----------|------------|--------|
| PulseAudio conflicts with ALSA | Medium | Configure audio backend in settings | Open |
| Permissions for /dev/video0 | Low | Add user to video group | Open |

#### macOS
| Issue | Severity | Workaround | Status |
|-------|----------|------------|--------|
| Microphone permission prompts | Low | Grant in System Preferences | By Design |
| M1/M2 chip compatibility for some packages | Medium | Use Rosetta or native builds | Open |

---

## Limitations

### By Design

These are intentional limitations, not bugs:

1. **Single User**: JARVIS is designed for single-user operation. Multi-user support planned for Phase 7.

2. **Local Network IoT**: ESP32 devices must be on the same local network. Cloud IoT integration planned for future.

3. **English Only**: Voice recognition and TTS optimized for English. Other languages may work but are not officially supported.

4. **No Persistent Learning**: JARVIS doesn't learn from interactions automatically. Memory is session-based with optional persistence.

5. **API Dependency**: Most features require internet for LLM APIs. Offline mode limited to Ollama.

### Technical Limitations

1. **Memory Usage**: Long conversations increase RAM usage. Recommend clearing history periodically.

2. **Concurrent Requests**: Single-threaded command processing. Commands are queued, not parallel.

3. **Audio Latency**: Minimum ~100ms latency for wake word detection due to audio buffering.

4. **LLM Token Limits**: Responses truncated at provider's token limit.

---

## Planned Improvements

### Short Term (Next Release)

- [ ] Improve wake word false positive rejection
- [ ] Add audio device hot-swap support
- [ ] Better error messages for common issues
- [ ] Reduce memory footprint

### Medium Term

- [ ] Multi-language support
- [ ] Home Assistant integration
- [ ] Web dashboard for monitoring
- [ ] Mobile app (beyond Telegram)

### Long Term

- [ ] Multi-user profiles
- [ ] Cloud deployment option
- [ ] Custom wake word training
- [ ] Plugin system for extensions

---

## Reporting Issues

### Before Reporting

1. Run pre-flight check: `python scripts/preflight_check.py`
2. Check this document for known issues
3. Review logs in `data/logs/`
4. Try with `--debug` flag for more info

### Information to Include

When reporting a new issue, please include:

```
**Environment:**
- OS: [Windows 11 / Ubuntu 22.04 / macOS 14]
- Python version: [3.11.0]
- JARVIS version: [2.0.0]

**Description:**
[Clear description of the issue]

**Steps to Reproduce:**
1. [First step]
2. [Second step]
3. [What happens]

**Expected Behavior:**
[What should happen]

**Actual Behavior:**
[What actually happens]

**Logs:**
[Relevant log snippets from data/logs/]

**Pre-flight Check Output:**
[Output of python scripts/preflight_check.py]
```

### Where to Report

- GitHub Issues: [repository URL]
- Include label: `bug`, `enhancement`, or `question`

---

## Changelog of Fixes

### v2.0.0 (Phase 4.5)

- Fixed: Module import errors with graceful fallbacks
- Fixed: Event bus memory leak on long sessions
- Fixed: IoT command queue not persisting across restarts
- Improved: Voice calibration accuracy
- Improved: Health monitor restart logic

### v1.0.0 (Phase 3)

- Initial release with known limitations documented

---

*Last Updated: Phase 4.5 Validation*
