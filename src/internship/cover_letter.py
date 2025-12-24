"""
Cover Letter Generator for JARVIS Internship Automation Module.

Generates personalized cover letters with:
- Company research integration
- Story/experience matching from RAG
- Professional formatting
- Multiple output formats
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from .models import (
    InternshipListing,
    CoverLetter,
    UserProfile,
)
from .resume_rag import ResumeRAG
from .prompts import InternshipPrompts

# Try importing Tavily for company research
TAVILY_AVAILABLE = False
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    pass


@dataclass
class CoverLetterConfig:
    """Configuration for cover letter generation."""
    target_word_count: int = 350
    min_word_count: int = 280
    max_word_count: int = 420
    
    include_company_research: bool = True
    include_personal_story: bool = True
    
    output_directory: str = "data/generated_cover_letters"


class CoverLetterGenerator:
    """
    Generate personalized cover letters for job applications.
    
    Features:
    - Company research via Tavily/Serper
    - Story matching from scholarship essays
    - Professional tone with authentic voice
    - ATS-friendly formatting
    """
    
    def __init__(
        self,
        profile: Optional[UserProfile] = None,
        resume_rag: Optional[ResumeRAG] = None,
        llm_router=None,
        tavily_api_key: Optional[str] = None,
        serper_api_key: Optional[str] = None,
        config: Optional[CoverLetterConfig] = None,
    ):
        self.profile = profile or UserProfile()
        self.rag = resume_rag or ResumeRAG()
        self.llm = llm_router
        self.config = config or CoverLetterConfig()
        
        # API keys
        self.tavily_api_key = tavily_api_key or os.getenv("TAVILY_API_KEY")
        self.serper_api_key = serper_api_key or os.getenv("SERPER_API_KEY")
        
        # Initialize Tavily
        self._tavily_client = None
        if TAVILY_AVAILABLE and self.tavily_api_key:
            try:
                self._tavily_client = TavilyClient(api_key=self.tavily_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily: {e}")
        
        # Ensure output directory
        os.makedirs(self.config.output_directory, exist_ok=True)
    
    # =========================================================================
    # Main Generation
    # =========================================================================
    
    async def generate(
        self,
        job: InternshipListing,
        custom_points: Optional[List[str]] = None,
    ) -> CoverLetter:
        """
        Generate a cover letter for a job application.
        
        Args:
            job: The internship listing
            custom_points: Optional custom points to include
            
        Returns:
            CoverLetter object with generated content
        """
        logger.info(f"Generating cover letter for {job.company} - {job.role}")
        
        # Step 1: Research company
        company_info = {}
        if self.config.include_company_research:
            company_info = await self._research_company(job.company)
        
        # Step 2: Find relevant stories/experiences
        stories = []
        if self.config.include_personal_story:
            stories = self._find_relevant_stories(job)
        
        # Step 3: Generate cover letter
        content = await self._generate_content(job, company_info, stories, custom_points)
        
        # Step 4: Create CoverLetter object
        cover_letter = CoverLetter(
            company=job.company,
            role=job.role,
            content=content,
            word_count=len(content.split()),
            company_info=company_info,
            stories_used=[s[0] for s in stories[:2]] if stories else [],
        )
        
        # Step 5: Save to file
        cover_letter = await self._save_cover_letter(cover_letter, job)
        
        logger.info(f"Cover letter generated: {cover_letter.word_count} words")
        
        return cover_letter
    
    # =========================================================================
    # Company Research
    # =========================================================================
    
    async def _research_company(self, company: str) -> Dict[str, str]:
        """Research company for personalization."""
        info = {
            "mission": "",
            "products": "",
            "culture": "",
            "recent_news": "",
            "why_work_here": "",
        }
        
        if not self._tavily_client:
            logger.debug("Tavily not available for company research")
            return info
        
        try:
            # Search for company info
            queries = [
                f"{company} company mission values",
                f"{company} recent news 2024 2025",
                f"{company} company culture work environment",
            ]
            
            all_content = []
            
            for query in queries:
                try:
                    response = self._tavily_client.search(
                        query=query,
                        search_depth="basic",
                        max_results=3,
                    )
                    
                    for result in response.get("results", []):
                        all_content.append(result.get("content", ""))
                        
                except Exception as e:
                    logger.debug(f"Search failed for '{query}': {e}")
            
            # Use LLM to extract structured info
            if self.llm and all_content:
                combined = "\n\n".join(all_content[:5])
                
                prompt = InternshipPrompts.format_template(
                    "company_research",
                    company=company,
                    search_results=combined[:3000],
                )
                
                response = await self.llm.generate(prompt)
                
                try:
                    parsed = json.loads(response)
                    info.update(parsed)
                except json.JSONDecodeError:
                    # Extract key info manually
                    info["recent_news"] = combined[:500]
            
            logger.info(f"Company research completed for {company}")
            
        except Exception as e:
            logger.error(f"Company research failed: {e}")
        
        return info
    
    # =========================================================================
    # Story Matching
    # =========================================================================
    
    def _find_relevant_stories(
        self,
        job: InternshipListing,
    ) -> List[tuple]:
        """Find relevant stories from RAG for the cover letter."""
        # Build query from job info
        query = f"{job.role} {job.description[:200]} {' '.join(job.requirements[:3])}"
        
        # Search for matching stories
        stories = self.rag.search_stories(query, n_results=3)
        
        # Also search projects for additional context
        projects = self.rag.search_projects(query, n_results=2)
        
        # Combine and return
        all_stories = []
        
        for story_id, text, score in stories:
            all_stories.append((story_id, text, score, "story"))
        
        for project, score in projects:
            if project.detailed_description:
                all_stories.append((
                    project.id,
                    project.detailed_description,
                    score,
                    "project"
                ))
        
        # Sort by score
        all_stories.sort(key=lambda x: x[2], reverse=True)
        
        return all_stories[:3]
    
    # =========================================================================
    # Content Generation
    # =========================================================================
    
    async def _generate_content(
        self,
        job: InternshipListing,
        company_info: Dict[str, str],
        stories: List[tuple],
        custom_points: Optional[List[str]] = None,
    ) -> str:
        """Generate the cover letter content."""
        
        # Prepare story text
        story_text = ""
        if stories:
            best_story = stories[0]
            story_text = best_story[1][:500] if len(best_story) > 1 else ""
        
        # Prepare experience text
        experience_text = ""
        projects = self.rag.search_projects(job.role, n_results=2)
        if projects:
            exp_parts = []
            for proj, _ in projects:
                exp_parts.append(f"- {proj.name}: {proj.description}")
            experience_text = "\n".join(exp_parts)
        
        if self.llm:
            try:
                prompt = InternshipPrompts.format_template(
                    "cover_letter",
                    company=job.company,
                    role=job.role,
                    company_mission=company_info.get("mission", ""),
                    company_news=company_info.get("recent_news", ""),
                    requirements=", ".join(job.requirements[:5]),
                    name=self.profile.name,
                    university=self.profile.university,
                    major=self.profile.major,
                    year=self.profile.year,
                    skills=", ".join(self.profile.primary_skills),
                    relevant_experience=experience_text,
                    personal_story=story_text,
                )
                
                content = await self.llm.generate(prompt)
                
                # Validate word count
                word_count = len(content.split())
                if word_count < self.config.min_word_count:
                    logger.warning(f"Cover letter too short: {word_count} words")
                elif word_count > self.config.max_word_count:
                    logger.warning(f"Cover letter too long: {word_count} words")
                
                return content
                
            except Exception as e:
                logger.error(f"LLM cover letter generation failed: {e}")
        
        # Fallback to template
        return self._generate_template_cover_letter(job, company_info, stories)
    
    def _generate_template_cover_letter(
        self,
        job: InternshipListing,
        company_info: Dict[str, str],
        stories: List[tuple],
    ) -> str:
        """Generate cover letter from template (fallback)."""
        
        # Opening
        opening = f"Dear Hiring Manager,\n\n"
        
        if company_info.get("mission"):
            opening += (
                f"I am excited to apply for the {job.role} position at {job.company}. "
                f"Your mission to {company_info['mission'][:100]} resonates deeply with my "
                f"passion for using technology to create meaningful impact."
            )
        else:
            opening += (
                f"I am writing to express my strong interest in the {job.role} position "
                f"at {job.company}. As a {self.profile.year} {self.profile.major} student "
                f"at {self.profile.university}, I am eager to contribute my skills to your team."
            )
        
        # Skills paragraph
        skills_para = (
            f"\n\nMy academic background in {self.profile.major} has equipped me with "
            f"strong skills in {', '.join(self.profile.primary_skills[:3])}. "
            f"Through coursework and personal projects, I have developed practical experience "
            f"in applying these skills to real-world problems."
        )
        
        # Story paragraph
        story_para = ""
        if stories:
            story_para = (
                f"\n\nOne experience that particularly shaped my approach to problem-solving "
                f"was {stories[0][1][:200]}..."
            )
        
        # Closing
        closing = (
            f"\n\nI am excited about the opportunity to bring my technical skills and "
            f"enthusiasm to {job.company}. I would welcome the chance to discuss how my "
            f"background aligns with your team's needs.\n\n"
            f"Thank you for considering my application.\n\n"
            f"Sincerely,\n{self.profile.name}"
        )
        
        return opening + skills_para + story_para + closing
    
    # =========================================================================
    # Output
    # =========================================================================
    
    async def _save_cover_letter(
        self,
        cover_letter: CoverLetter,
        job: InternshipListing,
    ) -> CoverLetter:
        """Save cover letter to files."""
        # Create filename
        safe_company = "".join(c if c.isalnum() else "_" for c in job.company)
        safe_role = "".join(c if c.isalnum() else "_" for c in job.role)
        timestamp = datetime.now().strftime("%Y%m%d")
        filename_base = f"CL_{safe_company}_{safe_role}_{timestamp}"
        
        output_dir = Path(self.config.output_directory)
        
        # Save as text
        txt_path = output_dir / f"{filename_base}.txt"
        txt_path.write_text(cover_letter.content, encoding="utf-8")
        
        # Save as markdown
        md_path = output_dir / f"{filename_base}.md"
        md_content = f"# Cover Letter - {job.company}\n\n"
        md_content += f"**Position:** {job.role}\n"
        md_content += f"**Date:** {datetime.now().strftime('%B %d, %Y')}\n\n"
        md_content += "---\n\n"
        md_content += cover_letter.content
        md_path.write_text(md_content, encoding="utf-8")
        
        # Try to save as DOCX
        try:
            from docx import Document
            from docx.shared import Pt
            
            doc = Document()
            
            # Add content
            for para in cover_letter.content.split("\n\n"):
                if para.strip():
                    p = doc.add_paragraph(para.strip())
                    p.style.font.size = Pt(11)
            
            docx_path = output_dir / f"{filename_base}.docx"
            doc.save(str(docx_path))
            cover_letter.docx_path = str(docx_path)
            
        except ImportError:
            logger.debug("python-docx not available for DOCX generation")
        except Exception as e:
            logger.error(f"DOCX generation failed: {e}")
        
        logger.info(f"Cover letter saved to {output_dir}")
        
        return cover_letter
    
    # =========================================================================
    # Utility
    # =========================================================================
    
    def get_generation_summary(self, cover_letter: CoverLetter) -> str:
        """Get summary of generated cover letter."""
        lines = [
            f"✍️ **Cover Letter Generated**",
            "",
            f"**Company:** {cover_letter.company}",
            f"**Role:** {cover_letter.role}",
            f"**Word Count:** {cover_letter.word_count}",
            "",
        ]
        
        if cover_letter.company_info:
            lines.append("**Company Research Used:**")
            if cover_letter.company_info.get("mission"):
                lines.append(f"  - Mission: {cover_letter.company_info['mission'][:50]}...")
            if cover_letter.company_info.get("recent_news"):
                lines.append(f"  - Recent news included")
        
        if cover_letter.stories_used:
            lines.append(f"\n**Stories/Experiences Used:** {len(cover_letter.stories_used)}")
        
        lines.extend([
            "",
            "**Preview:**",
            f"```",
            cover_letter.content[:300] + "...",
            f"```",
        ])
        
        return "\n".join(lines)
