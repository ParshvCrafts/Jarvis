# 💼 JARVIS Internship Automation Module

Complete guide for setting up and using the Internship Automation Module.

## Overview

The Internship Module automates your entire job search process:
- **Multi-Source Discovery** - Search RemoteOK, The Muse, Tavily, Serper, Adzuna, JSearch
- **Resume Customization** - RAG-powered resume tailoring for each job
- **Cover Letter Generation** - Company-researched, personalized letters
- **Application Tracking** - Full lifecycle tracking with analytics
- **ATS Optimization** - Keyword optimization for applicant tracking systems

---

## Quick Start

### 1. Install Dependencies

```bash
python run.py --install-internship-deps
```

Or manually:
```bash
pip install -r requirements-internship.txt
```

### 2. Check Status

```bash
python run.py --internship-status
```

### 3. Search for Internships

```bash
python run.py --find-internships "data science remote"
```

---

## Configuration

### API Keys (`.env`)

```env
# Required for job discovery (at least one)
TAVILY_API_KEY=your_tavily_key
SERPER_API_KEY=your_serper_key

# Optional - additional job sources
ADZUNA_APP_ID=your_adzuna_app_id
ADZUNA_API_KEY=your_adzuna_api_key
RAPIDAPI_KEY=your_rapidapi_key  # For JSearch
```

### Profile Settings (`config/settings.yaml`)

```yaml
internship:
  enabled: true
  
  profile:
    name: "Your Name"
    university: "UC Berkeley"
    major: "Data Science"
    year: "Freshman"
    gpa: 4.0
    target_roles:
      - "Data Science Intern"
      - "ML Intern"
      - "Software Engineering Intern"
    preferred_location: "remote"
    target_companies:
      - "Google"
      - "Meta"
      - "Amazon"
    primary_skills:
      - "Python"
      - "SQL"
      - "Machine Learning"
```

---

## Features

### 1. Job Discovery

Search across multiple free APIs:

| Source | API Key Required | Best For |
|--------|------------------|----------|
| RemoteOK | No | Remote tech jobs |
| The Muse | No | Company profiles, curated jobs |
| Tavily | Yes | Custom web search |
| Serper | Yes | Google search results |
| Adzuna | Yes | Large job database |
| JSearch | Yes (RapidAPI) | LinkedIn, Indeed, Glassdoor |

**CLI Commands:**
```bash
python run.py --find-internships                    # Default search
python run.py --find-internships "ML intern"        # Custom query
python run.py --find-internships "Google intern"    # Company-specific
```

### 2. Resume Customization

The module uses RAG to match your projects and experience to job requirements:

1. **Analyzes** job posting for keywords and requirements
2. **Retrieves** matching projects from your portfolio
3. **Generates** tailored resume sections
4. **Optimizes** for ATS with keyword matching
5. **Outputs** PDF, DOCX, and Markdown formats

### 3. Cover Letter Generation

Personalized cover letters with:
- Company research via Tavily
- Story matching from your scholarship essays
- Professional tone with authentic voice
- 300-400 word target length

### 4. Application Tracking

Track applications through their lifecycle:

```
SAVED → APPLIED → PHONE_SCREEN → INTERVIEW → OFFER → ACCEPTED
                                    ↓
                                REJECTED
```

---

## Voice Commands

Once JARVIS is running:

### Discovery
- "Find internships for me"
- "Find data science internships"
- "Find internships at Google"
- "Remote ML internships"
- "FAANG internships"

### Resume
- "Customize resume for Google"
- "Generate resume for data science intern"

### Cover Letter
- "Write cover letter for Google"
- "Cover letter for Amazon internship"

### Tracking
- "Track Google application"
- "Mark Google as applied"
- "Update Amazon to interview"
- "Mark Meta as rejected"
- "Application status"
- "Follow up reminders"
- "My statistics"

---

## CLI Commands

```bash
# Status
python run.py --internship-status

# Search
python run.py --find-internships
python run.py --find-internships "query"

# Dependencies
python run.py --install-internship-deps
```

---

## Adding Your Projects

To get the best resume customization, add your projects to the RAG system:

### Option 1: Programmatically

```python
from src.internship import InternshipManager, Project

manager = InternshipManager()

project = Project(
    name="ML Classifier Project",
    description="Built a machine learning classifier for sentiment analysis",
    technologies=["Python", "TensorFlow", "pandas", "scikit-learn"],
    skills_demonstrated=["Machine Learning", "NLP", "Data Analysis"],
    impact_metrics=["95% accuracy", "Processed 100K+ reviews"],
    resume_bullets=[
        "Developed sentiment analysis classifier achieving 95% accuracy on 100K+ product reviews",
        "Implemented TensorFlow neural network with custom preprocessing pipeline",
        "Reduced inference time by 40% through model optimization techniques",
    ],
)

manager.add_project(project)
```

### Option 2: Import from Scholarship Essays

Your scholarship essays can provide stories for cover letters:

```python
# Stories are automatically extracted from scholarship module
# if you've imported essays there
```

---

## Database Schema

For Supabase users, run the SQL in `config/internship_setup.sql`:

**Tables:**
- `master_resume` - Your master resume content
- `resume_projects` - Projects with embeddings
- `resume_skills` - Skills with evidence
- `work_experience` - Work history with embeddings
- `internship_listings` - Discovered jobs
- `internship_applications` - Application tracking
- `generated_resumes` - Generated resume versions
- `generated_cover_letters` - Generated cover letters
- `resume_stories` - Stories for cover letters

---

## Output Files

Generated documents are saved to `data/generated_documents/`:

```
data/generated_documents/
├── Google_Data_Science_Intern_20241223.pdf
├── Google_Data_Science_Intern_20241223.docx
├── Google_Data_Science_Intern_20241223.md
├── CL_Google_Data_Science_Intern_20241223.txt
└── CL_Google_Data_Science_Intern_20241223.docx
```

---

## Architecture

```
src/internship/
├── __init__.py          # Module exports
├── models.py            # Data models
├── discovery.py         # Multi-source job search
├── resume_rag.py        # RAG for projects/experience
├── resume_generator.py  # Resume customization
├── cover_letter.py      # Cover letter generation
├── tracker.py           # Application tracking
├── prompts.py           # LLM prompt templates
└── manager.py           # Main orchestrator
```

---

## API Keys Reference

| Key | Required | Purpose | Free Tier |
|-----|----------|---------|-----------|
| `TAVILY_API_KEY` | Recommended | Job search, company research | 1000 req/month |
| `SERPER_API_KEY` | Optional | Google search backup | 2500 req/month |
| `ADZUNA_APP_ID` | Optional | Large job database | 250 req/day |
| `ADZUNA_API_KEY` | Optional | (with APP_ID) | |
| `RAPIDAPI_KEY` | Optional | JSearch (LinkedIn, Indeed) | 500 req/month |

---

## Tips for Best Results

1. **Add your projects** - More projects = better resume matching
2. **Include metrics** - Quantified results improve resume quality
3. **Write resume bullets** - Pre-written bullets speed up generation
4. **Import scholarship essays** - Stories enhance cover letters
5. **Track all applications** - Analytics help optimize your strategy

---

## Troubleshooting

### "No internships found"
- Check API keys in `.env`
- Try different search queries
- Some APIs have rate limits

### "Resume generation failed"
- Ensure you have projects in the RAG
- Check LLM router is configured
- Verify output directory exists

### "Cover letter too short"
- Add more stories to the system
- Check company research is working
- Verify Tavily API key

---

## Example Workflow

```bash
# 1. Check status
python run.py --internship-status

# 2. Search for internships
python run.py --find-internships "data science intern remote"

# 3. In JARVIS voice mode:
"Customize resume for Google data science intern"
"Write cover letter for Google"
"Track Google application"

# 4. After applying:
"Mark Google as applied"

# 5. After interview:
"Update Google to interview"

# 6. Check progress:
"My application statistics"
```

---

---

## New Features (v2.0)

### API Diagnostics

Check which job search APIs are working:

```bash
python run.py --diagnose-apis
```

Output:
```
📊 **Internship API Status**
✅ **RemoteOK**: Working (98 jobs available)
✅ **The Muse**: Working (20 jobs/page)
✅ **Adzuna**: Working (450 total jobs)
⚠️ **JSearch**: Not configured (need RAPIDAPI_KEY)
✅ **Tavily**: Working (5 results)
✅ **Serper**: Working (10 results)
```

### GitHub Project Import

Automatically import your GitHub projects into the RAG:

```bash
python run.py --import-github
python run.py --import-github username  # For a specific user
```

This extracts:
- Project name and description
- Technologies used
- Auto-generated resume bullets
- GitHub stars and metrics

### Application Dashboard

View comprehensive analytics:

```bash
python run.py --internship-dashboard
```

Features:
- Application funnel visualization
- Response/Interview/Offer rates
- Time metrics
- Action items (follow-ups needed)
- HTML dashboard saved to `data/internship_dashboard.html`

### Skill Gap Analysis

Analyze what skills you're missing for a job:

**Voice command:** "What skills am I missing for Google?"

Returns:
- Required skills you have ✅
- Required skills you're missing ❌
- Preferred skills status
- Learning resource recommendations
- Overall match percentage

### Resume Quality Check

After generating a resume, get quality metrics:
- ATS Score (0-100)
- Keyword coverage percentage
- Format analysis
- Improvement suggestions

---

## CLI Commands Summary

| Command | Description |
|---------|-------------|
| `--internship-status` | Show module status |
| `--find-internships "query"` | Search for internships |
| `--diagnose-apis` | Check API status |
| `--internship-dashboard` | Show analytics dashboard |
| `--import-github` | Import projects from GitHub |
| `--import-resume folder` | Import resume from text files |
| `--install-internship-deps` | Install dependencies |

---

## Voice Commands Summary

| Category | Commands |
|----------|----------|
| **Discovery** | "Find internships", "Find data science internships at Google" |
| **Resume** | "Customize resume for Google", "Generate resume for ML intern" |
| **Cover Letter** | "Write cover letter for Amazon" |
| **Tracking** | "Track Google application", "Mark Google as applied" |
| **Status Updates** | "Update Amazon to interview", "Mark Meta as rejected" |
| **Analytics** | "Application status", "Dashboard", "My statistics" |
| **Skills** | "Skill gap for Google", "What skills am I missing?" |
| **Import** | "Import from GitHub", "Diagnose APIs" |
| **Reminders** | "Follow up reminders", "Pending applications" |

---

## Next Steps

1. **Configure your profile** in `config/settings.yaml`
2. **Add API keys** to `.env`
3. **Import your projects**: `python run.py --import-github`
4. **Check APIs**: `python run.py --diagnose-apis`
5. **Start searching**: `python run.py --find-internships`
6. **Generate applications** using voice commands
7. **Track progress**: `python run.py --internship-dashboard`

Good luck with your internship search! 🎯
