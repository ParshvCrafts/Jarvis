# JARVIS Academic Features

Academic features designed for UC Berkeley Data Science students, providing comprehensive support for coursework, study sessions, and research.

## Features Overview

| Feature | Description | Status |
|---------|-------------|--------|
| Canvas LMS | Assignments, grades, announcements | ✅ Ready |
| Pomodoro Timer | Voice-controlled study sessions | ✅ Ready |
| Daily Briefing | Morning summary command | ✅ Ready |
| Assignment Tracker | Local + Canvas tracking | ✅ Ready |
| Quick Notes | Voice-to-text note capture | ✅ Ready |
| GitHub Integration | Repository management | ✅ Ready |
| arXiv Search | Research paper discovery | ✅ Ready |
| Concept Explainer | DS/ML learning help | ✅ Ready |

## Setup

### 1. Canvas LMS (bCourses)

Generate an API token from Canvas:
1. Log in to [bCourses](https://bcourses.berkeley.edu)
2. Go to **Account** → **Settings**
3. Scroll to **Approved Integrations**
4. Click **+ New Access Token**
5. Give it a name (e.g., "JARVIS") and generate

Add to your `.env` file:
```bash
CANVAS_API_TOKEN=your_token_here
```

### 2. GitHub Integration

Generate a Personal Access Token:
1. Go to [GitHub Settings](https://github.com/settings/tokens)
2. Click **Generate new token (classic)**
3. Select scopes: `repo`, `read:user`
4. Generate and copy the token

Add to your `.env` file:
```bash
GITHUB_TOKEN=your_github_token_here
```

### 3. Configuration

The academic features are configured in `config/settings.yaml`:

```yaml
academic:
  enabled: true
  university: "UC Berkeley"
  
  canvas:
    enabled: true
    base_url: "https://bcourses.berkeley.edu/api/v1/"
    
  pomodoro:
    work_duration: 25  # minutes
    short_break: 5
    long_break: 15
    sessions_before_long_break: 4
    
  github:
    enabled: true
    
  arxiv:
    enabled: true
    default_categories: ["cs.LG", "cs.AI", "stat.ML"]
```

## Voice Commands

### Canvas LMS

```
"What's due this week?"
"What assignments are due tomorrow?"
"Show my grades"
"Show my grades for Data 8"
"Any new announcements?"
"What's due for CS 61A?"
```

### Pomodoro Timer

```
"Start pomodoro"
"Start pomodoro for Data 8 homework"
"Start study session for 45 minutes"
"How much time left?"
"Pause timer"
"Resume timer"
"Stop studying"
"Take a break"
"How many pomodoros today?"
"Show study stats"
```

### Daily Briefing

```
"Good morning"
"Daily briefing"
"What's my day look like?"
"Evening summary"
"What did I accomplish today?"
```

### Quick Notes

```
"Quick note: Review chapter 5 before class"
"Note for Data 8: Look up gradient descent"
"Show my notes"
"Search notes for gradient descent"
"Notes for CS 61A"
```

### Assignment Tracker

```
"Add assignment ML project due next Friday for CS 189"
"Mark Data 8 lab as complete"
"What's my most urgent assignment?"
"Show my assignments"
```

### GitHub

```
"Show my GitHub repos"
"Any open issues on JARVIS?"
"What did I commit today?"
"Show commits for my-project"
```

### arXiv Research

```
"Find papers about transformer architecture"
"Search arXiv for attention mechanism"
"What's new in reinforcement learning?"
"Show my reading list"
```

### Concept Explainer

```
"Explain gradient descent"
"What is backpropagation?"
"Explain random forest like I'm 5"
"How does cross-validation work?"
"What's the difference between L1 and L2 regularization?"
```

## Example Interactions

### Morning Briefing
```
You: "Good morning"

JARVIS: "Good morning! Here's your briefing for Monday, December 23:

🌤️ Weather: 58°F, partly cloudy

📅 Today's schedule:
   • 10:00 AM - Data 8 Lecture
   • 2:00 PM - CS 61A Discussion

🔴 Due TODAY:
   • Data 8 Lab 5 (Data 8) - 11:59 PM

🟡 Due tomorrow:
   • CS 61A Homework 3 (CS 61A)

📋 This week:
   • Data 8 Midterm - Thursday
   • CS 61A Project 1 - Friday

📧 You have 3 unread emails.

💡 "The only way to do great work is to love what you do." - Steve Jobs

Have a productive day!"
```

### Study Session
```
You: "Start pomodoro for Data 8 homework"

JARVIS: "Starting 25-minute focus session for Data 8 homework. 
        I'll notify you when it's time for a break."

[25 minutes later]

JARVIS: "Focus session complete! Time for a 5-minute break."
```

### Assignment Check
```
You: "What's due this week?"

JARVIS: "Due this week:
• Data 8 Lab 5 (Data 8) - TODAY at 11:59 PM
• CS 61A Homework 3 (CS 61A) - Tomorrow
• Data 8 Midterm (Data 8) - Thursday
• CS 61A Project 1 (CS 61A) - Friday"
```

### Concept Explanation
```
You: "Explain gradient descent like I'm 5"

JARVIS: "Imagine you're blindfolded on a hilly field and want to find 
the lowest point. You can feel which way the ground slopes under your 
feet. Gradient descent is like taking small steps downhill - always 
going in the direction that feels steepest downward.

In machine learning, the 'hill' is our error - how wrong our predictions 
are. We want to find the lowest error. The gradient tells us which 
direction is 'downhill', and we take small steps that way until we 
reach the bottom."
```

## Data Storage

Academic features store data in SQLite databases:

| Database | Location | Purpose |
|----------|----------|---------|
| `pomodoro.db` | `data/pomodoro.db` | Study session history |
| `notes.db` | `data/notes.db` | Quick notes storage |
| `assignments.db` | `data/assignments.db` | Local assignment tracking |
| `reading_list.db` | `data/reading_list.db` | arXiv paper reading list |

## API Endpoints

If using the Mobile API, these endpoints are available:

```
GET  /api/v1/academic/canvas/assignments
GET  /api/v1/academic/canvas/grades
GET  /api/v1/academic/pomodoro/status
POST /api/v1/academic/pomodoro/start
POST /api/v1/academic/pomodoro/stop
GET  /api/v1/academic/notes
POST /api/v1/academic/notes
GET  /api/v1/academic/github/repos
```

## Troubleshooting

### Canvas Not Working

1. **Check token**: Ensure `CANVAS_API_TOKEN` is set in `.env`
2. **Verify URL**: UC Berkeley uses `bcourses.berkeley.edu`
3. **Token permissions**: Regenerate token if expired

### GitHub Not Connecting

1. **Check token**: Ensure `GITHUB_TOKEN` is set in `.env`
2. **Token scopes**: Needs `repo` and `read:user` permissions
3. **Rate limits**: GitHub has API rate limits (5000 req/hour with token)

### Pomodoro Timer Issues

1. **Sound not playing**: Check audio settings in `settings.yaml`
2. **Timer not starting**: Ensure academic features are enabled

### Notes Not Saving

1. **Database permissions**: Check write access to `data/` directory
2. **Disk space**: Ensure sufficient storage

## Best Practices

1. **Morning Routine**: Start each day with "Good morning" for a briefing
2. **Study Sessions**: Use Pomodoro for focused work blocks
3. **Quick Notes**: Capture ideas immediately with voice
4. **Regular Checks**: Ask "What's due this week?" frequently
5. **Research**: Use arXiv search for paper discovery

## Future Enhancements

- [ ] Google Drive integration for document access
- [ ] Calendar sync for class schedules
- [ ] Spaced repetition for concept review
- [ ] Study group coordination
- [ ] Grade prediction/tracking
