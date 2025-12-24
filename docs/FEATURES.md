# JARVIS Features Documentation

**Version:** 2.0.0  
**Last Updated:** December 2024

## Table of Contents

1. [Quick Start](#quick-start)
2. [Voice Commands](#voice-commands)
3. [Academic Features](#academic-features)
4. [Productivity Features](#productivity-features)
5. [Career Features](#career-features)
6. [Finance Features](#finance-features)
7. [System Features](#system-features)
8. [Configuration](#configuration)
9. [API Keys](#api-keys)
10. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Running JARVIS

```bash
# Text mode (recommended for testing)
python run.py --text

# Full voice mode
python run.py

# Check configuration
python run.py --check-config
```

### Essential Commands

| Command | Description |
|---------|-------------|
| "Good morning" | Comprehensive daily briefing |
| "JARVIS status" | System health check |
| "What can you do?" | List all capabilities |
| "Help with [category]" | Category-specific help |

---

## Voice Commands

### Academic Commands

| Command | Description |
|---------|-------------|
| "Good morning" / "Daily briefing" | Morning summary with assignments, weather, habits |
| "What's due today?" | Today's assignments |
| "What's due this week?" | Weekly assignment overview |
| "Start pomodoro" | Start 25-minute focus session |
| "Start pomodoro with focus music" | Timer + music |
| "Pomodoro status" | Check remaining time |
| "Stop pomodoro" | End current session |
| "Take a note: [content]" | Quick note |
| "Show my notes" | Recent notes |
| "Search notes for [topic]" | Find notes |
| "Add assignment [name] due [date]" | Track assignment |
| "GitHub status" | Repository overview |
| "My repositories" | List repos |
| "Search arXiv for [topic]" | Find papers |
| "Explain [concept]" | AI explanation |

### Productivity Commands

| Command | Description |
|---------|-------------|
| "Play focus music" | Lo-fi/study music |
| "Play [playlist]" | Specific playlist |
| "Play my liked songs" | Personal library |
| "Search [song] on YouTube Music" | Find and play |
| "Log learning: [content]" | Learning journal |
| "What did I learn this week?" | Learning summary |
| "Complete habit [name]" | Mark habit done |
| "My habits" | Habit status |
| "Add habit [name]" | New habit |
| "Show my projects" | Project list |
| "Add project [name]" | New project |
| "Show snippet [name]" | Code snippet |
| "Weekly review" | Productivity summary |
| "Start focus mode" | Block distractions |
| "Take a break" | Break reminder |

### Career Commands

| Command | Description |
|---------|-------------|
| "Practice interview" | Random question |
| "Give me a coding question" | Coding practice |
| "Give me an ML question" | ML concepts |
| "Interview stats" | Practice history |
| "Add experience [title] at [company]" | Resume entry |
| "Show my resume" | Resume overview |
| "My skills" | Skill list |
| "Add job application [company] for [role]" | Track application |
| "Application status" | All applications |
| "Pending applications" | Active apps |
| "Add expense $[amount] for [category]" | Track spending |
| "Monthly spending" | Expense summary |
| "Budget status" | Budget overview |
| "Add networking contact [name]" | New contact |
| "Follow-up reminders" | Who to contact |
| "Journal entry: [content]" | Voice journal |
| "Start learning path [topic]" | Begin path |

### Finance Commands

| Command | Description |
|---------|-------------|
| "Stock price of [symbol]" | Current price |
| "How's VTI?" | Quick quote |
| "Market summary" | Major indices |
| "My watchlist" | Tracked stocks |
| "Compare VTI vs VOO" | Side-by-side |
| "Investment advice" | General guidance |
| "Why index funds?" | Education |
| "Explain 401k matching" | Retirement |
| "Roth vs Traditional" | IRA comparison |
| "Best savings rates" | HYSA comparison |
| "Compare SoFi vs Ally" | Account comparison |
| "Tax tips for students" | Tax guidance |
| "How to build credit" | Credit education |
| "Best student cards" | Card recommendations |
| "Good debt vs bad debt" | Debt education |
| "Student discounts" | Savings list |
| "My financial health" | Dashboard |
| "Am I on track?" | Progress check |
| "Add 10 shares VTI at $220" | Portfolio entry |
| "My portfolio" | Holdings overview |
| "Asset allocation" | Allocation check |

### System Commands

| Command | Description |
|---------|-------------|
| "Open [app]" | Launch application |
| "Play [video] on YouTube" | YouTube search |
| "Add bookmark [name] at [url]" | Save bookmark |
| "List my apps" | Registered apps |
| "My bookmarks" | Saved bookmarks |
| "Send WhatsApp to [contact]: [message]" | WhatsApp message |
| "Add contact [name] [phone]" | New contact |
| "My contacts" | Contact list |
| "Switch to Hindi" | Language change |
| "Switch to Gujarati" | Language change |
| "Switch to English" | Language change |

---

## Academic Features

### Canvas LMS Integration

Connects to UC Berkeley's bCourses for:
- Upcoming assignments with due dates
- Grade tracking per course
- Course announcements
- Submission status

**Setup:** Set `CANVAS_API_TOKEN` in `.env`

### Pomodoro Timer

- Configurable work/break durations
- Session tracking and statistics
- Music integration
- Voice notifications

**Default Settings:**
- Work: 25 minutes
- Short break: 5 minutes
- Long break: 15 minutes
- Sessions before long break: 4

### Daily Briefing

Comprehensive morning summary including:
- Weather (if configured)
- Today's calendar events
- Assignments due today/tomorrow/this week
- Unread emails count
- Habit streak status
- Yesterday's study time
- Job application updates
- Financial tip
- Motivational quote

---

## Productivity Features

### Music Control

Supports YouTube Music with:
- Playlist playback
- Personal library access
- Search functionality
- Focus music presets

### Learning Journal

Track daily learning with:
- Timestamped entries
- Topic tagging
- Weekly summaries
- Search functionality

### Habit Tracker

Build habits with:
- Daily tracking
- Streak counting
- Default habits (exercise, reading, etc.)
- Progress visualization

### Project Tracker

Manage projects with:
- Milestone tracking
- Progress updates
- Deadline management
- Status overview

### Code Snippets

17 pre-loaded snippets including:
- Python basics
- Pandas operations
- ML templates
- Data visualization

---

## Career Features

### Interview Prep

25+ practice questions covering:
- Coding (arrays, strings, trees)
- ML concepts
- Behavioral questions
- Difficulty levels

### Resume Tracker

Track experiences and skills:
- Work experience
- Projects
- Skills with proficiency levels
- Resume generation

### Job Applications

Track applications with:
- Status tracking (applied, interview, offer)
- Deadline reminders
- Follow-up alerts
- Company notes

### Expense Tracker

Budget management:
- Expense logging by category
- Monthly summaries
- Budget alerts
- Spending trends

### Learning Paths

6 pre-built paths:
- Machine Learning
- Deep Learning
- NLP
- Computer Vision
- Data Engineering
- MLOps

---

## Finance Features

### Stock/Market Data

Real-time data via yfinance:
- Current prices
- Daily change
- 52-week range
- Market indices

**Default Watchlist:** VTI, VOO, VXUS, FNILX, FZROX, BND

### Investment Education

Comprehensive guidance on:
- Index funds vs individual stocks
- Dollar-cost averaging
- Compound interest
- Expense ratios
- Roth IRA benefits

### Retirement Guidance

401k and IRA education:
- Employer matching
- Roth vs Traditional
- Contribution limits
- Target date funds
- Vesting schedules

### Savings Optimization

High-yield savings comparison:
- Current APY rates
- Account features
- Emergency fund calculator
- Interest projections

### Tax Strategies

Student-focused tax tips:
- Education credits (AOTC)
- Tax-loss harvesting
- Capital gains brackets
- Deduction strategies

### Credit Building

Credit score education:
- Score factors and weights
- Student credit cards
- Utilization tips
- Path to 800

### Debt Strategies

Smart debt management:
- Good vs bad debt
- Student loan optimization
- Pay off vs invest decision
- Leverage strategies

### Financial Dashboard

Track financial health:
- Net worth tracking
- Savings rate
- Goal progress
- Health score

### Portfolio Tracker

Investment tracking:
- Holdings by account
- Real-time valuation
- Asset allocation
- Rebalancing suggestions

---

## Configuration

### settings.yaml Structure

```yaml
# Academic
academic:
  canvas:
    enabled: true
    base_url: "https://bcourses.berkeley.edu/api/v1"
  pomodoro:
    work_duration: 25
    short_break: 5
    long_break: 15

# Productivity
productivity:
  music:
    enabled: true
    preferred_service: "youtube_music"
  habits:
    enabled: true
    add_defaults: true

# Career
career:
  interview_prep:
    enabled: true
    default_difficulty: "medium"
  resume:
    university: "UC Berkeley"
    major: "Data Science"

# Finance
finance:
  investment:
    enabled: true
    default_watchlist:
      - VTI
      - VOO
      - VXUS
  portfolio:
    enabled: true
```

---

## API Keys

### Required Keys

| Key | Service | How to Get |
|-----|---------|------------|
| `GROQ_API_KEY` | Groq LLM | [console.groq.com](https://console.groq.com) |

### Optional Keys

| Key | Service | How to Get |
|-----|---------|------------|
| `GEMINI_API_KEY` | Google Gemini | [makersuite.google.com](https://makersuite.google.com) |
| `CANVAS_API_TOKEN` | Canvas LMS | bCourses → Account → Settings → New Access Token |
| `GITHUB_TOKEN` | GitHub | [github.com/settings/tokens](https://github.com/settings/tokens) |
| `TELEGRAM_BOT_TOKEN` | Telegram | Message @BotFather |
| `NOTION_API_KEY` | Notion | [notion.so/my-integrations](https://notion.so/my-integrations) |

### .env Example

```bash
# LLM Providers (at least one required)
GROQ_API_KEY=gsk_xxxxx
GEMINI_API_KEY=AIzaSyxxxxx

# Academic
CANVAS_API_TOKEN=xxxxx

# Integrations
GITHUB_TOKEN=ghp_xxxxx
TELEGRAM_BOT_TOKEN=xxxxx
NOTION_API_KEY=secret_xxxxx
```

---

## Troubleshooting

### Common Issues

#### "Canvas not configured"
```
Set CANVAS_API_TOKEN in your .env file.
Get token from: bCourses → Account → Settings → New Access Token
```

#### "Stock data unavailable"
```
Install yfinance: pip install yfinance
```

#### "Voice features unavailable"
```
Install voice dependencies:
pip install sounddevice numpy openwakeword faster-whisper edge-tts
```

#### "LLM not responding"
```
Check your API key is valid and has credits.
Try: python run.py --check-config
```

### Debug Commands

```bash
# Check configuration
python run.py --check-config

# Run in text mode
python run.py --text

# Run tests
python -m pytest tests/ -v

# Test specific module
python tests/test_finance.py
```

### Getting Help

1. Say "JARVIS status" to check system health
2. Say "Help with [category]" for specific commands
3. Check logs in `logs/jarvis.log`

---

## Version History

### v2.0.0 (December 2024)
- Added Finance module (10 features)
- Added Career module (8 features)
- Enhanced daily briefing with cross-module data
- Improved help system with categories
- Added comprehensive status command

### v1.0.0 (Initial)
- Core LLM integration
- Voice pipeline
- Academic features
- Productivity features
