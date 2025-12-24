# JARVIS Scholarship Module Setup Guide

This guide covers the complete setup and usage of the JARVIS Scholarship Automation Module.

## Overview

The Scholarship Module provides:
- **Scholarship Discovery** - Find scholarships matching your profile via Tavily/Serper
- **RAG-Powered Essay Generation** - Generate essays using your past winning essays as context
- **Application Tracking** - Track deadlines, submissions, and outcomes
- **Multi-Format Import** - Import essays from .txt, .docx, .pdf, and JSON
- **Google Docs Output** - Export formatted essays to Google Docs

## Quick Start

### 1. Install Dependencies

```bash
# One command installation
python run.py --install-scholarship-deps

# Or manually
pip install -r requirements-scholarship.txt
```

### 2. Configure API Keys

Add to your `.env` file:

```env
# Required for Supabase (cloud database)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Required for scholarship discovery (at least one)
TAVILY_API_KEY=your_tavily_key
SERPER_API_KEY=your_serper_key

# Optional - for cloud embeddings
COHERE_API_KEY=your_cohere_key
```

### 3. Check Status

```bash
python run.py --scholarship-status
```

Expected output:
```
🎓 **Scholarship Module Status**
========================================

**Dependencies:**
  ✅ supabase
  ✅ chromadb
  ✅ sentence-transformers
  ✅ tavily-python
  ✅ python-docx
  ✅ PyPDF2
  ✅ cohere

**Database:**
  ✅ ChromaDB: Active (Local Mode)

**APIs:**
  ✅ Tavily API
  ✅ Serper API

**Ready to use:** ✅
```

### 4. Setup Database (Optional - for Supabase)

```bash
python run.py --setup-scholarship
```

This generates SQL at `config/scholarship_setup.sql`. To use Supabase:
1. Open your Supabase Dashboard
2. Go to SQL Editor
3. Paste and run the SQL from the generated file

**Note:** The module works without Supabase using ChromaDB local storage.

### 5. Import Your Essays

```bash
python run.py --import-essays path/to/essays/folder
```

## Essay Import Formats

### Option A: Text Files with Metadata Header

```
Scholarship: Amazon Future Engineer
Question: Describe your leadership experience
Outcome: won

[Your essay text here...]
```

Supported outcomes: `won`, `lost`, `pending`, `submitted`, `draft`

### Option B: JSON Batch Import

Create a JSON file with multiple essays:

```json
[
  {
    "scholarship_name": "Amazon Future Engineer",
    "question": "Describe your leadership experience",
    "essay_text": "Throughout my freshman year...",
    "outcome": "won",
    "word_count": 298,
    "themes": ["leadership", "community", "technology"]
  },
  {
    "scholarship_name": "Gates Scholarship",
    "question": "What challenges have you overcome?",
    "essay_text": "Growing up as a first-generation...",
    "outcome": "won"
  }
]
```

Import with:
```python
from src.scholarship import EssayImporter
importer = EssayImporter()
await importer.import_from_json("essays.json")
```

### Option C: Folder Structure

```
essays/
├── Amazon_Future_Engineer_2023.txt
├── Gates_Scholarship_Leadership.txt
├── QuestBridge_Personal_Statement.txt
└── winning/
    ├── essay1.txt
    └── essay2.txt
```

## Voice Commands

Once JARVIS is running, use these commands:

### Discovery
- "Find scholarships for me"
- "Find STEM scholarships"
- "Find data science scholarships"
- "Search scholarships due this month"

### Essay Generation
- "Write essay for [scholarship name] about [topic], 250 words"
- "Generate scholarship essay on leadership"

### Application Tracking
- "Scholarship status"
- "What scholarships are due soon?"
- "Mark [scholarship] as submitted"
- "Mark [scholarship] as won"

### Import
- "Import essays from [folder]"
- "Import personal statement from [file]"

### Setup
- "Setup scholarship database"
- "Verify database"

## CLI Commands

```bash
# Check module status
python run.py --scholarship-status

# Install dependencies
python run.py --install-scholarship-deps

# Setup Supabase database
python run.py --setup-scholarship

# Import essays
python run.py --import-essays path/to/folder
```

## Configuration

### Eligibility Profile

Edit `config/settings.yaml`:

```yaml
scholarship:
  profile:
    name: "Your Name"
    major: "Data Science"
    university: "UC Berkeley"
    year: "Freshman"
    gpa: 4.0
    citizenship: "Permanent Resident"
    ethnicity: "Asian Indian"
    state: "California"
    financial_need: false
    first_generation: false
```

### Embedding Model

Default: `all-MiniLM-L6-v2` (384 dimensions, runs locally)

For cloud embeddings, set `COHERE_API_KEY` in `.env`.

## Database Modes

### 1. Supabase (Cloud) - Recommended for Production
- Persistent cloud storage
- Vector similarity search with pgvector
- Requires manual SQL setup

### 2. ChromaDB (Local) - Default
- Persistent local storage
- Automatic fallback when Supabase unavailable
- No setup required

### 3. In-Memory - Fallback
- Used when ChromaDB not installed
- Data lost on restart
- For testing only

## Troubleshooting

### "Supabase not connected"
1. Verify `SUPABASE_URL` and `SUPABASE_KEY` in `.env`
2. Run `python run.py --setup-scholarship`
3. Execute generated SQL in Supabase Dashboard

### "Tavily/Serper API not available"
1. Add API key to `.env`
2. Restart JARVIS
3. Run `python run.py --scholarship-status` to verify

### "Embeddings not working"
1. Ensure `sentence-transformers` is installed
2. First run downloads the model (~90MB)
3. Check for CUDA if using GPU

### "Import failed"
1. Check file format matches expected structure
2. Ensure metadata header is present for .txt files
3. Check file encoding (UTF-8 recommended)

## Architecture

```
src/scholarship/
├── models.py          # Data models (Profile, Scholarship, Essay)
├── discovery.py       # Scholarship search (Tavily, Serper)
├── rag.py            # RAG retrieval system
├── local_rag.py      # ChromaDB local fallback
├── embeddings.py     # Embedding generation
├── generator.py      # Essay generation workflow
├── tracker.py        # Application tracking
├── importer.py       # Essay import tools
├── docs_output.py    # Google Docs integration
├── setup.py          # Database setup
├── prompts.py        # Prompt templates
└── manager.py        # Main orchestrator
```

## API Keys Reference

| Key | Required | Purpose |
|-----|----------|---------|
| `SUPABASE_URL` | Optional | Cloud database URL |
| `SUPABASE_KEY` | Optional | Cloud database key |
| `TAVILY_API_KEY` | Recommended | Scholarship search |
| `SERPER_API_KEY` | Optional | Backup search |
| `COHERE_API_KEY` | Optional | Cloud embeddings |
| `GROQ_API_KEY` | Required | Essay generation LLM |

## Next Steps

1. **Import your essays** - The more winning essays, the better generation quality
2. **Set up your profile** - Accurate profile improves scholarship matching
3. **Find scholarships** - Use discovery to find matching opportunities
4. **Generate essays** - Let RAG help write personalized essays
5. **Track applications** - Never miss a deadline

---

For issues or feature requests, check the main JARVIS documentation or create an issue on GitHub.
