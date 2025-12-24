"""
Prompt Templates for JARVIS Internship Automation Module.

Contains prompts for:
- Resume customization
- Cover letter generation
- ATS optimization
- Job analysis
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class PromptTemplate:
    """A prompt template with variables."""
    name: str
    template: str
    variables: List[str]
    description: str = ""


class InternshipPrompts:
    """Collection of prompts for internship automation."""
    
    # =========================================================================
    # Job Analysis Prompts
    # =========================================================================
    
    ANALYZE_JOB_POSTING = """You are an expert job posting analyzer. Extract key information from this job posting.

## Job Posting
{job_posting}

## Extract the following:
1. **Required Skills** - Technical skills that are mandatory
2. **Preferred Skills** - Nice-to-have skills
3. **Key Responsibilities** - Main job duties
4. **Keywords** - Important terms for ATS optimization
5. **Company Values** - Any mentioned company culture/values
6. **Experience Level** - Required experience
7. **Education Requirements** - Degree/major requirements

## Output Format (JSON):
{{
    "required_skills": ["skill1", "skill2"],
    "preferred_skills": ["skill1", "skill2"],
    "responsibilities": ["resp1", "resp2"],
    "keywords": ["keyword1", "keyword2"],
    "company_values": ["value1", "value2"],
    "experience_level": "entry/mid/senior",
    "education": "degree requirements"
}}

Extract only what is explicitly mentioned. Be thorough with keywords."""

    # =========================================================================
    # Resume Prompts
    # =========================================================================
    
    RESUME_SUMMARY = """You are an expert resume writer. Generate a compelling professional summary.

## Candidate Profile
- Name: {name}
- University: {university}
- Major: {major}
- Year: {year}
- GPA: {gpa}
- Key Skills: {skills}

## Target Position
- Company: {company}
- Role: {role}
- Key Requirements: {requirements}

## Instructions
Write a 2-3 sentence professional summary that:
1. Highlights the most relevant skills for this specific role
2. Shows unique value proposition
3. Demonstrates enthusiasm for the field
4. Naturally incorporates keywords from the job posting

Keep under 50 words. Make every word count. Do not use generic phrases.

## Output
Write only the summary paragraph, nothing else."""

    RESUME_PROJECTS_SECTION = """You are an experienced professional resume writer specializing in data science, AI, and tech resumes. You have deep expertise in crafting impactful, ATS-friendly resumes.

## Task
Write a compelling "Projects" section for a resume tailored to this specific job.

## Target Position
- Company: {company}
- Role: {role}
- Key Requirements: {requirements}
- Keywords to Include: {keywords}

## Available Projects (from candidate's portfolio)
{projects}

## Instructions
1. Select the 3-4 most relevant projects for this role
2. Write 2-3 bullet points per project
3. Begin each bullet with strong action verbs (Developed, Analyzed, Built, Engineered, Implemented)
4. Structure: Action + What + How + Impact
5. Include specific tools/technologies mentioned in job requirements
6. Quantify results wherever possible (%, numbers, scale)
7. Naturally incorporate job keywords for ATS optimization
8. Keep each bullet under 2 lines

## Output Format
For each project:
**Project Name** | Technologies Used
• Bullet point 1
• Bullet point 2
• Bullet point 3

Generate the complete Projects section now."""

    RESUME_EXPERIENCE_SECTION = """You are an expert resume writer. Tailor the work experience section for this job.

## Target Position
- Company: {company}
- Role: {role}
- Requirements: {requirements}

## Candidate's Experience
{experience}

## Instructions
1. Rewrite bullet points to emphasize relevant skills
2. Use action verbs that match the job description
3. Quantify achievements where possible
4. Include keywords from job posting naturally
5. Focus on transferable skills for internship roles

## Output
Generate the tailored Experience section with improved bullet points."""

    RESUME_SKILLS_SECTION = """You are an ATS optimization expert. Organize skills for maximum impact.

## Target Position
- Role: {role}
- Required Skills: {required_skills}
- Preferred Skills: {preferred_skills}

## Candidate's Skills
{candidate_skills}

## Instructions
1. Group skills into categories (Programming, Data Science, Tools, etc.)
2. Order skills by relevance to this specific job
3. Put required skills first within each category
4. Include exact keyword matches from job posting
5. Remove irrelevant skills that don't add value

## Output Format
**Technical Skills**
- Programming: Python, SQL, Java...
- Data Science: Machine Learning, Statistical Analysis...
- Tools: Git, Docker, AWS...

Generate the optimized Skills section."""

    ATS_OPTIMIZATION = """You are an ATS (Applicant Tracking System) optimization expert.

## Job Posting Keywords
{job_keywords}

## Current Resume Content
{resume_content}

## Task
1. Identify all keywords from the job posting
2. Check which keywords are present in the resume
3. Identify missing important keywords
4. Suggest natural ways to include missing keywords
5. Calculate an estimated ATS match score

## Output Format
**Keywords Analysis**
- Present: [list of found keywords]
- Missing: [list of missing keywords]

**Suggestions**
1. [Specific suggestion to add keyword naturally]
2. [Another suggestion]

**Estimated ATS Score**: XX/100

**Optimized Content**
[Provide optimized version of any sections that need keyword additions]"""

    # =========================================================================
    # Cover Letter Prompts
    # =========================================================================
    
    COVER_LETTER_FULL = """You are an expert cover letter writer who creates compelling, personalized cover letters that get interviews at top tech companies.

## Target Position
- Company: {company}
- Role: {role}
- Company Mission: {company_mission}
- Recent News: {company_news}
- Key Requirements: {requirements}

## Candidate Profile
- Name: {name}
- University: {university}
- Major: {major}
- Year: {year}
- Relevant Skills: {skills}

## Relevant Experience/Projects
{relevant_experience}

## Personal Story (from past essays)
{personal_story}

## Instructions
Write a compelling cover letter that:
1. Opens with a hook showing genuine interest in the company (not generic)
2. Connects candidate's experience directly to their needs
3. Includes a specific personal story that demonstrates relevant skills
4. Shows knowledge of the company (mission, products, recent news)
5. Maintains professional but authentic tone
6. Ends with clear call to action

## Requirements
- Length: 300-400 words
- Tone: Professional, enthusiastic, authentic
- Structure: 4 paragraphs (Hook, Experience, Story, Close)
- Do NOT use generic phrases like "I am writing to apply for..."

## Output
Write the complete cover letter."""

    COVER_LETTER_OPENING = """Write a compelling opening paragraph for a cover letter.

## Company: {company}
## Role: {role}
## Company Info: {company_info}

## Instructions
- Start with something specific about the company that excites you
- Connect it to your background/interests
- Make it clear why THIS company, not just any company
- Avoid generic openings like "I am writing to apply..."
- Keep to 2-3 sentences

## Output
Write only the opening paragraph."""

    COVER_LETTER_CLOSING = """Write a strong closing paragraph for a cover letter.

## Company: {company}
## Role: {role}
## Key Points Made: {key_points}

## Instructions
- Summarize your value proposition in one sentence
- Express genuine enthusiasm
- Include a clear call to action
- Thank them for their consideration
- Keep to 2-3 sentences

## Output
Write only the closing paragraph."""

    # =========================================================================
    # Company Research Prompts
    # =========================================================================
    
    COMPANY_RESEARCH = """Research this company for a job application.

## Company: {company}
## Search Results: {search_results}

## Extract:
1. Company Mission/Vision
2. Core Products/Services
3. Company Culture/Values
4. Recent News or Achievements
5. Why someone would want to work there

## Output Format (JSON):
{{
    "mission": "company mission statement",
    "products": ["product1", "product2"],
    "culture": ["value1", "value2"],
    "recent_news": ["news item 1"],
    "why_work_here": "compelling reason"
}}"""

    # =========================================================================
    # Interview Prep Prompts
    # =========================================================================
    
    INTERVIEW_QUESTIONS = """Generate likely interview questions for this role.

## Company: {company}
## Role: {role}
## Job Description: {job_description}

## Generate:
1. 5 Technical Questions (based on required skills)
2. 5 Behavioral Questions (STAR format expected)
3. 3 Company-Specific Questions
4. 2 Questions to Ask the Interviewer

## Output Format
**Technical Questions**
1. Question + What they're testing

**Behavioral Questions**
1. Question + What skill it assesses

**Company Questions**
1. Question + Why they might ask

**Questions to Ask**
1. Question + Why it's good to ask"""

    STAR_RESPONSE = """Help structure a STAR response for this interview question.

## Question: {question}
## Relevant Experience: {experience}

## STAR Format
- **Situation**: Set the context (1-2 sentences)
- **Task**: Describe your responsibility (1 sentence)
- **Action**: Explain what YOU did specifically (2-3 sentences)
- **Result**: Share the outcome with metrics if possible (1-2 sentences)

## Instructions
- Keep total response under 2 minutes when spoken
- Focus on YOUR individual contribution
- Include specific details and numbers
- End with what you learned

## Output
Write the complete STAR response."""

    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    @classmethod
    def get_template(cls, name: str) -> str:
        """Get a prompt template by name."""
        templates = {
            "analyze_job": cls.ANALYZE_JOB_POSTING,
            "resume_summary": cls.RESUME_SUMMARY,
            "resume_projects": cls.RESUME_PROJECTS_SECTION,
            "resume_experience": cls.RESUME_EXPERIENCE_SECTION,
            "resume_skills": cls.RESUME_SKILLS_SECTION,
            "ats_optimization": cls.ATS_OPTIMIZATION,
            "cover_letter": cls.COVER_LETTER_FULL,
            "cover_letter_opening": cls.COVER_LETTER_OPENING,
            "cover_letter_closing": cls.COVER_LETTER_CLOSING,
            "company_research": cls.COMPANY_RESEARCH,
            "interview_questions": cls.INTERVIEW_QUESTIONS,
            "star_response": cls.STAR_RESPONSE,
        }
        return templates.get(name, "")
    
    @classmethod
    def format_template(cls, name: str, **kwargs) -> str:
        """Get and format a template with variables."""
        template = cls.get_template(name)
        if not template:
            raise ValueError(f"Unknown template: {name}")
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")
    
    @classmethod
    def list_templates(cls) -> List[str]:
        """List all available template names."""
        return [
            "analyze_job",
            "resume_summary",
            "resume_projects",
            "resume_experience",
            "resume_skills",
            "ats_optimization",
            "cover_letter",
            "cover_letter_opening",
            "cover_letter_closing",
            "company_research",
            "interview_questions",
            "star_response",
        ]
