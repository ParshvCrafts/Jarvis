# 📄 Resume & Project Import Guide

**Complete beginner's guide to adding your resume and projects to JARVIS.**

---

## 🎯 What You Need

1. **Your current resume** (any format - Word, PDF, or just the text)
2. **Project descriptions** for each project you want to include
3. **5 minutes** to copy/paste into the templates

---

## 📁 Folder Structure

All your files go in `data/my_resume/`:

```
data/my_resume/
├── README.txt              ← Instructions (read this first)
├── MASTER_RESUME.txt       ← Your full resume goes here
├── SKILLS.txt              ← Your skills list
├── projects/               ← One file per project
│   ├── TEMPLATE_Project.txt
│   └── Your_Project.txt
├── experience/             ← One file per job/internship
│   ├── TEMPLATE_Experience.txt
│   └── Company_Role.txt
└── stories/                ← Personal stories for cover letters
    ├── TEMPLATE_Story.txt
    └── Your_Story.txt
```

---

## 📝 Step-by-Step Instructions

### Step 1: Add Your Master Resume

1. **Open** the file: `data/my_resume/MASTER_RESUME.txt`
2. **Delete** all the example content
3. **Copy** your resume content and paste it in
4. **Keep** the section headers (CONTACT:, EDUCATION:, etc.)
5. **Save** the file

**Example format:**
```
CONTACT:
Name: Parshv
Email: parshv@berkeley.edu
Phone: (555) 123-4567
LinkedIn: linkedin.com/in/parshv
GitHub: github.com/parshv

SUMMARY:
Data Science student at UC Berkeley passionate about machine learning...

EDUCATION:
University: UC Berkeley
Degree: Bachelor of Arts in Data Science
GPA: 4.0
Graduation: May 2028

SKILLS:
Programming: Python, SQL, R
Data Science: pandas, NumPy, scikit-learn, TensorFlow
Tools: Git, Jupyter, VS Code
```

---

### Step 2: Add Your Projects (Most Important!)

For **each project** you want JARVIS to use:

1. **Go to** the folder: `data/my_resume/projects/`
2. **Copy** the file `TEMPLATE_Project.txt`
3. **Rename** the copy to your project name (e.g., `JARVIS_Assistant.txt`)
4. **Open** your new file and fill in the details
5. **Save** the file

**Project file format:**
```
Name: JARVIS AI Personal Assistant

Description: A comprehensive AI-powered personal assistant with voice control.

Detailed Description:
Built an advanced personal AI assistant inspired by Iron Man's JARVIS. The system 
features intelligent LLM routing across 5 providers, voice-activated commands, 
and specialized modules for scholarship applications and internship automation.

Technologies: Python, LangChain, ChromaDB, Supabase, Groq API, Gemini API

Skills Demonstrated: AI/ML Engineering, System Architecture, API Integration

Impact Metrics:
- Integrated 5 LLM providers with intelligent routing
- Built RAG system processing 1000+ documents
- Achieved <2 second response time for voice commands

Start Date: 2024-09
End Date:
Is Ongoing: true

GitHub URL: https://github.com/parshv/jarvis

Resume Bullets:
- Engineered AI assistant with intelligent routing across 5 LLM providers
- Implemented RAG system using ChromaDB for semantic document retrieval
- Developed voice pipeline with wake word detection achieving <2s response time
```

**💡 Tips for Projects:**
- **Be specific** with numbers: "95% accuracy" not "high accuracy"
- **Include all technologies** you used
- **Write 2-4 resume bullets** - these will be used directly in generated resumes
- **Add impact metrics** - recruiters love quantified results

---

### Step 3: Add Your Skills

1. **Open** the file: `data/my_resume/SKILLS.txt`
2. **Add** your skills following the format
3. **Save** the file

**Skill format:**
```
SKILL:
Name: Python
Category: programming
Proficiency: advanced
Years: 3
Evidence: Built JARVIS AI assistant, ML projects, data analysis pipelines
Keywords: python, python3, scripting, automation

SKILL:
Name: Machine Learning
Category: data_science
Proficiency: intermediate
Years: 2
Evidence: Developed sentiment classifier with 95% accuracy
Keywords: ml, machine learning, deep learning, neural networks
```

**Categories:** `programming`, `data_science`, `tools`, `soft_skills`, `domain`, `other`

**Proficiency levels:** `beginner`, `intermediate`, `advanced`, `expert`

---

### Step 4: Add Work Experience (Optional)

If you have internships or jobs:

1. **Go to** the folder: `data/my_resume/experience/`
2. **Copy** the file `TEMPLATE_Experience.txt`
3. **Rename** it (e.g., `Google_SWE_Intern.txt`)
4. **Fill in** your experience details
5. **Save** the file

**Experience format:**
```
Company: Google
Role: Software Engineering Intern
Location: Mountain View, CA
Location Type: hybrid

Start Date: 2024-06
End Date: 2024-08
Is Current: false

Description:
Worked on the Search team improving query understanding using ML models.

Achievements:
- Improved search relevance by 15% through ML model optimization
- Developed data pipeline processing 1M+ queries daily
- Collaborated with team of 5 engineers on production deployment

Technologies: Python, TensorFlow, BigQuery, Kubernetes
```

---

### Step 5: Add Stories (Optional - For Cover Letters)

Stories make your cover letters personal and memorable:

1. **Go to** the folder: `data/my_resume/stories/`
2. **Copy** the file `TEMPLATE_Story.txt`
3. **Rename** it (e.g., `Hackathon_Win.txt`)
4. **Write** your story
5. **Save** the file

**Story format:**
```
Source: Berkeley Data Science Hackathon

Themes: problem-solving, teamwork, perseverance

Story:
During the Berkeley Data Science Hackathon, our team faced a critical setback 
when our data pipeline crashed 4 hours before the deadline. While others panicked, 
I quickly diagnosed the issue as a memory overflow and implemented a streaming 
solution. We not only recovered but won first place, teaching me that staying 
calm under pressure can turn disasters into victories.
```

---

## 🚀 Step 6: Import Everything

### Option A: Double-Click (Easiest)

Just double-click: **`import_my_resume.bat`**

### Option B: Command Line

```bash
python run.py --import-resume data/my_resume
```

---

## ✅ Verify Import

Check that everything was imported:

```bash
python run.py --internship-status
```

You should see:
```
💼 **Internship Module Status**

**Profile:** Parshv

**Resume RAG:**
  📁 Projects: 3
  💼 Experience: 1
  🔧 Skills: 7
  📖 Stories: 2
```

---

## 🎯 Using Your Data

Once imported, JARVIS will automatically use your projects and experience when:

1. **Generating resumes** - Matches relevant projects to job requirements
2. **Writing cover letters** - Uses your stories for personalization
3. **Optimizing for ATS** - Includes your skills as keywords

**Voice commands:**
- "Customize resume for Google data science intern"
- "Write cover letter for Amazon"
- "Find internships that match my skills"

---

## ❓ Troubleshooting

### "No projects found"
- Make sure your project files are in `data/my_resume/projects/`
- Make sure they end with `.txt`
- Don't name them starting with "TEMPLATE"

### "Import failed"
- Check that all required fields are filled in
- Make sure dates are in YYYY-MM format
- Check for typos in field names (must match exactly)

### "Skills not showing"
- Each skill needs the `SKILL:` header on its own line
- Check that Category and Proficiency are valid values

---

## 📋 Quick Checklist

- [ ] Filled in `MASTER_RESUME.txt` with my info
- [ ] Created at least 2-3 project files in `projects/`
- [ ] Added my skills to `SKILLS.txt`
- [ ] (Optional) Added work experience in `experience/`
- [ ] (Optional) Added stories in `stories/`
- [ ] Ran `python run.py --import-resume data/my_resume`
- [ ] Verified with `python run.py --internship-status`

---

## 💡 Pro Tips

1. **More projects = better matching** - Add all significant projects
2. **Write good resume bullets** - These are used directly in generated resumes
3. **Include metrics** - Numbers make your achievements concrete
4. **Add keywords** - Help JARVIS match your skills to job requirements
5. **Update regularly** - Re-import after adding new projects

---

## 🆘 Need Help?

- Check the example files in each folder
- Look at `TEMPLATE_*.txt` files for the exact format
- Run `python run.py --internship-status` to see what's imported

Good luck with your internship search! 🎯
