# JARVIS User Acceptance Test Checklist

Complete this checklist to validate JARVIS is working correctly.

## Test Environment

| Item | Value |
|------|-------|
| Date | _____________ |
| Tester | _____________ |
| OS | _____________ |
| Python Version | _____________ |
| JARVIS Version | _____________ |

## Pre-Test Validation

- [ ] Pre-flight check passes: `python scripts/preflight_check.py`
- [ ] Configuration validated: `python run.py --check-config`
- [ ] At least one LLM provider configured
- [ ] Audio devices detected (if testing voice)

---

## Part 1: Core Functionality

### 1.1 Startup & Shutdown

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Start in text mode | Starts without errors | ☐ | `python run.py --text` |
| Start in voice mode | Starts, shows "Ready" | ☐ | `python run.py` |
| Graceful shutdown | Exits cleanly on Ctrl+C | ☐ | |
| Config check | Shows enabled features | ☐ | `python run.py --check-config` |

### 1.2 Basic Queries (Text Mode)

| Test | Command | Expected Response | Pass/Fail |
|------|---------|-------------------|-----------|
| Greeting | "Hello" | Friendly greeting | ☐ |
| Time query | "What time is it?" | Current time | ☐ |
| Date query | "What's today's date?" | Current date | ☐ |
| Math | "What is 15 times 7?" | 105 | ☐ |
| Help | "What can you do?" | List of capabilities | ☐ |

---

## Part 2: Voice Pipeline

### 2.1 Wake Word Detection

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Say "Hey Jarvis" clearly | Activates, plays tone | ☐ | |
| Say "Hey Jarvis" quietly | Activates | ☐ | |
| Say similar phrase | Should NOT activate | ☐ | e.g., "Hey Travis" |
| Background noise | Should NOT activate | ☐ | |
| Multiple activations | Works each time | ☐ | Test 5 times |

**Wake Word Success Rate:** ___/5 activations

### 2.2 Speech Recognition

| Test | Command | Transcription Accurate? | Pass/Fail |
|------|---------|------------------------|-----------|
| Simple command | "What time is it" | ☐ | |
| Longer command | "Search for Python tutorials online" | ☐ | |
| Numbers | "Set timer for 5 minutes" | ☐ | |
| Names | "Open Google Chrome" | ☐ | |

**STT Accuracy:** ___/4 correct

### 2.3 Text-to-Speech

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Short response | Clear audio output | ☐ | |
| Long response | Complete playback | ☐ | |
| Interruption | Stops on new wake word | ☐ | |

### 2.4 Conversation Mode

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Follow-up without wake word | Responds | ☐ | Within 30s |
| "Goodbye" exits | Returns to listening | ☐ | |
| Timeout exits | Auto-exits after 30s silence | ☐ | |

---

## Part 3: Agent System

### 3.1 Research Agent

| Test | Command | Expected | Pass/Fail |
|------|---------|----------|-----------|
| Web search | "Search for climate change news" | Returns results | ☐ |
| Definition | "What is machine learning?" | Explanation | ☐ |
| Factual | "Who invented the telephone?" | Alexander Graham Bell | ☐ |

### 3.2 System Agent

| Test | Command | Expected | Pass/Fail |
|------|---------|----------|-----------|
| Open app | "Open Notepad" (Win) / "Open TextEdit" (Mac) | App opens | ☐ |
| Screenshot | "Take a screenshot" | Screenshot saved | ☐ |
| System info | "What's my system status?" | CPU/Memory info | ☐ |

### 3.3 Coding Agent

| Test | Command | Expected | Pass/Fail |
|------|---------|----------|-----------|
| Code generation | "Write a Python hello world" | Valid code | ☐ |
| Git status | "Git status" | Shows status | ☐ |
| Explain code | "Explain what a for loop does" | Explanation | ☐ |

### 3.4 IoT Agent (If Hardware Available)

| Test | Command | Expected | Pass/Fail |
|------|---------|----------|-----------|
| Device list | "What devices are online?" | Lists devices | ☐ |
| Light on | "Turn on the light" | Light turns on | ☐ |
| Light off | "Turn off the light" | Light turns off | ☐ |
| Door unlock | "Unlock the door" | Door unlocks | ☐ |

---

## Part 4: Memory & Context

### 4.1 Conversation Memory

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Remember context | Recalls previous message | ☐ | Ask follow-up |
| Clear memory | "Forget our conversation" works | ☐ | |

### 4.2 Long-term Memory (If Configured)

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Save information | "Remember that my favorite color is blue" | Confirms | ☐ |
| Recall information | "What's my favorite color?" | Blue | ☐ |

---

## Part 5: Telegram Integration (If Configured)

### 5.1 Basic Commands

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| /start | Welcome message | ☐ | |
| /help | Help text | ☐ | |
| /status | System status | ☐ | |
| Text command | Processes and responds | ☐ | |

### 5.2 Security

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Unauthorized user | Rejected | ☐ | Use different account |
| Sensitive command | Requires confirmation | ☐ | |

---

## Part 6: Error Handling

### 6.1 Graceful Degradation

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Invalid command | Helpful error message | ☐ | |
| Network timeout | Retries or informs user | ☐ | |
| LLM unavailable | Falls back or informs | ☐ | |

### 6.2 Recovery

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Restart after crash | Starts normally | ☐ | |
| State persistence | Remembers devices | ☐ | |

---

## Part 7: Performance

### 7.1 Response Times

| Metric | Target | Measured | Pass/Fail |
|--------|--------|----------|-----------|
| Wake word detection | < 500ms | ___ms | ☐ |
| Simple query E2E | < 3s | ___s | ☐ |
| Complex query E2E | < 8s | ___s | ☐ |

### 7.2 Stability

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| Run for 30 minutes | No crashes | ☐ | |
| Run for 1 hour | No crashes | ☐ | |
| Memory usage stable | No significant growth | ☐ | |

---

## Part 8: Security

### 8.1 Credential Security

| Test | Expected | Pass/Fail | Notes |
|------|----------|-----------|-------|
| .env not in git | Verified | ☐ | `git status` |
| API keys not logged | Verified | ☐ | Check logs |
| Security audit passes | No critical issues | ☐ | `python scripts/security_audit.py` |

---

## Summary

### Results

| Category | Passed | Failed | Skipped |
|----------|--------|--------|---------|
| Core Functionality | /4 | | |
| Voice Pipeline | /12 | | |
| Agent System | /10 | | |
| Memory | /4 | | |
| Telegram | /5 | | |
| Error Handling | /4 | | |
| Performance | /5 | | |
| Security | /3 | | |
| **TOTAL** | **/47** | | |

### Pass Rate

**___% passed** (Target: >90%)

### Critical Issues Found

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### Non-Critical Issues

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

### Recommendations

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Tester | | | |
| Reviewer | | | |

---

*JARVIS User Acceptance Test - Phase 4.5*
