"""
Resume and Project Importer for JARVIS Internship Module.

Imports resume data, projects, experience, skills, and stories from text files.
Designed for beginners - simple text file format with clear headers.
"""

import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    Project,
    Skill,
    SkillCategory,
    ProficiencyLevel,
    WorkExperience,
    LocationType,
    MasterResume,
)
from .resume_rag import ResumeRAG


@dataclass
class ImportResult:
    """Result of an import operation."""
    success: bool
    item_type: str
    name: str
    message: str


class ResumeImporter:
    """
    Import resume data from simple text files.
    
    Supports:
    - Master resume (MASTER_RESUME.txt)
    - Projects (projects/*.txt)
    - Work experience (experience/*.txt)
    - Skills (SKILLS.txt)
    - Stories (stories/*.txt)
    """
    
    def __init__(self, resume_rag: ResumeRAG):
        self.rag = resume_rag
        self.results: List[ImportResult] = []
    
    # =========================================================================
    # Main Import Methods
    # =========================================================================
    
    def import_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Import all resume data from a folder.
        
        Expected structure:
        folder/
        ├── MASTER_RESUME.txt
        ├── SKILLS.txt
        ├── projects/
        │   ├── Project1.txt
        │   └── Project2.txt
        ├── experience/
        │   └── Company_Role.txt
        └── stories/
            └── Story1.txt
        """
        folder = Path(folder_path)
        self.results = []
        
        if not folder.exists():
            logger.error(f"Folder not found: {folder_path}")
            return {"success": False, "error": f"Folder not found: {folder_path}"}
        
        logger.info(f"Importing resume data from: {folder_path}")
        
        # Import master resume
        master_resume_path = folder / "MASTER_RESUME.txt"
        if master_resume_path.exists():
            self._import_master_resume(master_resume_path)
        
        # Import skills
        skills_path = folder / "SKILLS.txt"
        if skills_path.exists():
            self._import_skills_file(skills_path)
        
        # Import projects
        projects_folder = folder / "projects"
        if projects_folder.exists():
            for file in projects_folder.glob("*.txt"):
                if not file.name.startswith("TEMPLATE"):
                    self._import_project_file(file)
        
        # Import experience
        experience_folder = folder / "experience"
        if experience_folder.exists():
            for file in experience_folder.glob("*.txt"):
                if not file.name.startswith("TEMPLATE"):
                    self._import_experience_file(file)
        
        # Import stories
        stories_folder = folder / "stories"
        if stories_folder.exists():
            for file in stories_folder.glob("*.txt"):
                if not file.name.startswith("TEMPLATE"):
                    self._import_story_file(file)
        
        return self._get_import_summary()
    
    def _get_import_summary(self) -> Dict[str, Any]:
        """Get summary of import results."""
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        by_type = {}
        for r in successful:
            by_type[r.item_type] = by_type.get(r.item_type, 0) + 1
        
        return {
            "success": len(failed) == 0,
            "total_imported": len(successful),
            "total_failed": len(failed),
            "by_type": by_type,
            "results": self.results,
            "failed_items": [(r.name, r.message) for r in failed],
        }
    
    # =========================================================================
    # File Parsers
    # =========================================================================
    
    def _parse_file(self, file_path: Path) -> Dict[str, str]:
        """
        Parse a text file with key: value format.
        
        Handles multi-line values (indented or until next key).
        """
        content = file_path.read_text(encoding="utf-8")
        
        # Remove instruction blocks
        content = re.sub(r'={50,}.*?={50,}', '', content, flags=re.DOTALL)
        
        data = {}
        current_key = None
        current_value = []
        
        for line in content.split('\n'):
            # Check for new key
            match = re.match(r'^([A-Za-z][A-Za-z\s]+):\s*(.*)', line)
            
            if match:
                # Save previous key-value
                if current_key:
                    data[current_key] = '\n'.join(current_value).strip()
                
                current_key = match.group(1).strip().lower().replace(' ', '_')
                value = match.group(2).strip()
                current_value = [value] if value else []
            elif current_key and line.strip():
                # Continue multi-line value
                current_value.append(line.strip('- ').strip())
        
        # Save last key-value
        if current_key:
            data[current_key] = '\n'.join(current_value).strip()
        
        return data
    
    def _parse_list(self, value: str) -> List[str]:
        """Parse a comma-separated or newline-separated list."""
        if not value:
            return []
        
        # Try comma-separated first
        if ',' in value:
            return [item.strip() for item in value.split(',') if item.strip()]
        
        # Try newline-separated
        return [item.strip() for item in value.split('\n') if item.strip()]
    
    def _parse_date(self, value: str) -> Optional[date]:
        """Parse a date string (YYYY-MM or YYYY-MM-DD)."""
        if not value:
            return None
        
        try:
            if len(value) == 7:  # YYYY-MM
                return date.fromisoformat(f"{value}-01")
            return date.fromisoformat(value)
        except ValueError:
            return None
    
    # =========================================================================
    # Import Individual Items
    # =========================================================================
    
    def _import_master_resume(self, file_path: Path):
        """Import master resume."""
        try:
            data = self._parse_file(file_path)
            full_content = file_path.read_text(encoding="utf-8")
            
            # Extract contact info
            contact = {
                "name": data.get("name", ""),
                "email": data.get("email", ""),
                "phone": data.get("phone", ""),
                "linkedin": data.get("linkedin", ""),
                "github": data.get("github", ""),
                "location": data.get("location", ""),
            }
            
            # Create master resume (without full_content - not in model)
            resume = MasterResume(
                contact=contact,
                summary=data.get("summary", ""),
                certifications=self._parse_list(data.get("certifications", "")),
                awards=self._parse_list(data.get("awards", "")),
            )
            
            # Store full content in RAG as a story for retrieval
            self.rag.add_story("master_resume", full_content)
            
            self.results.append(ImportResult(
                success=True,
                item_type="resume",
                name="Master Resume",
                message="Imported successfully",
            ))
            logger.info("Imported master resume")
            
        except Exception as e:
            self.results.append(ImportResult(
                success=False,
                item_type="resume",
                name="Master Resume",
                message=str(e),
            ))
            logger.error(f"Failed to import master resume: {e}")
    
    def _import_project_file(self, file_path: Path):
        """Import a project from file."""
        try:
            data = self._parse_file(file_path)
            
            name = data.get("name", file_path.stem)
            
            project = Project(
                name=name,
                description=data.get("description", ""),
                detailed_description=data.get("detailed_description", ""),
                technologies=self._parse_list(data.get("technologies", "")),
                skills_demonstrated=self._parse_list(data.get("skills_demonstrated", "")),
                impact_metrics=self._parse_list(data.get("impact_metrics", "")),
                start_date=self._parse_date(data.get("start_date", "")),
                end_date=self._parse_date(data.get("end_date", "")),
                is_ongoing=data.get("is_ongoing", "").lower() == "true",
                github_url=data.get("github_url", ""),
                demo_url=data.get("demo_url", ""),
                resume_bullets=self._parse_list(data.get("resume_bullets", "")),
            )
            
            # Add to RAG
            self.rag.add_project(project)
            
            self.results.append(ImportResult(
                success=True,
                item_type="project",
                name=name,
                message="Imported successfully",
            ))
            logger.info(f"Imported project: {name}")
            
        except Exception as e:
            self.results.append(ImportResult(
                success=False,
                item_type="project",
                name=file_path.stem,
                message=str(e),
            ))
            logger.error(f"Failed to import project {file_path.name}: {e}")
    
    def _import_experience_file(self, file_path: Path):
        """Import work experience from file."""
        try:
            data = self._parse_file(file_path)
            
            company = data.get("company", file_path.stem.split("_")[0])
            role = data.get("role", "")
            
            # Parse location type
            loc_type_str = data.get("location_type", "onsite").lower()
            loc_type_map = {
                "remote": LocationType.REMOTE,
                "hybrid": LocationType.HYBRID,
                "onsite": LocationType.ONSITE,
            }
            location_type = loc_type_map.get(loc_type_str, LocationType.ONSITE)
            
            experience = WorkExperience(
                company=company,
                role=role,
                location=data.get("location", ""),
                location_type=location_type,
                start_date=self._parse_date(data.get("start_date", "")),
                end_date=self._parse_date(data.get("end_date", "")),
                is_current=data.get("is_current", "").lower() == "true",
                description=data.get("description", ""),
                achievements=self._parse_list(data.get("achievements", "")),
                technologies=self._parse_list(data.get("technologies", "")),
            )
            
            # Add to RAG
            self.rag.add_experience(experience)
            
            self.results.append(ImportResult(
                success=True,
                item_type="experience",
                name=f"{company} - {role}",
                message="Imported successfully",
            ))
            logger.info(f"Imported experience: {company} - {role}")
            
        except Exception as e:
            self.results.append(ImportResult(
                success=False,
                item_type="experience",
                name=file_path.stem,
                message=str(e),
            ))
            logger.error(f"Failed to import experience {file_path.name}: {e}")
    
    def _import_skills_file(self, file_path: Path):
        """Import skills from file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Split by SKILL: markers (handle different line endings)
            skill_blocks = re.split(r'\nSKILL:\s*\n', content)
            
            skills_imported = 0
            for block in skill_blocks[1:]:  # Skip first empty block
                lines = block.strip().split('\n')
                data = {}
                
                for line in lines:
                    if ':' in line and not line.startswith('='):
                        key, value = line.split(':', 1)
                        data[key.strip().lower()] = value.strip()
                
                if not data.get("name"):
                    continue
                
                # Parse category - handle case variations
                cat_str = data.get("category", "other").lower().strip()
                cat_map = {
                    "programming": SkillCategory.PROGRAMMING,
                    "data_science": SkillCategory.DATA_SCIENCE,
                    "tools": SkillCategory.TOOLS,
                    "soft_skills": SkillCategory.SOFT_SKILLS,
                    "domain": SkillCategory.DOMAIN,
                    "other": SkillCategory.OTHER,
                }
                category = cat_map.get(cat_str, SkillCategory.OTHER)
                
                # Parse proficiency
                prof_str = data.get("proficiency", "intermediate").lower().strip()
                prof_map = {
                    "beginner": ProficiencyLevel.BEGINNER,
                    "intermediate": ProficiencyLevel.INTERMEDIATE,
                    "advanced": ProficiencyLevel.ADVANCED,
                    "expert": ProficiencyLevel.EXPERT,
                }
                proficiency = prof_map.get(prof_str, ProficiencyLevel.INTERMEDIATE)
                
                # Parse years safely
                years_str = data.get("years", "0")
                try:
                    years = float(years_str) if years_str else 0
                except ValueError:
                    years = 0
                
                skill = Skill(
                    name=data.get("name", ""),
                    category=category,
                    proficiency=proficiency,
                    years_experience=years,
                    evidence=self._parse_list(data.get("evidence", "")),
                    keywords=self._parse_list(data.get("keywords", "")),
                )
                
                # Add to RAG
                self.rag.add_skill(skill)
                skills_imported += 1
                
                self.results.append(ImportResult(
                    success=True,
                    item_type="skill",
                    name=skill.name,
                    message="Imported successfully",
                ))
                logger.debug(f"Imported skill: {skill.name}")
            
            if skills_imported == 0:
                logger.warning("No skills found in skills file")
            else:
                logger.info(f"Imported {skills_imported} skills")
            
        except Exception as e:
            self.results.append(ImportResult(
                success=False,
                item_type="skill",
                name="Skills file",
                message=str(e),
            ))
            logger.error(f"Failed to import skills: {e}")
    
    def _import_story_file(self, file_path: Path):
        """Import a story from file."""
        try:
            data = self._parse_file(file_path)
            
            source = data.get("source", file_path.stem)
            story_content = data.get("story", "")
            themes = self._parse_list(data.get("themes", ""))
            
            if not story_content:
                raise ValueError("Story content is empty")
            
            # Create story ID
            story_id = f"story_{source.lower().replace(' ', '_')}"
            
            # Add to RAG
            self.rag.add_story(story_id, story_content)
            
            self.results.append(ImportResult(
                success=True,
                item_type="story",
                name=source,
                message="Imported successfully",
            ))
            logger.info(f"Imported story: {source}")
            
        except Exception as e:
            self.results.append(ImportResult(
                success=False,
                item_type="story",
                name=file_path.stem,
                message=str(e),
            ))
            logger.error(f"Failed to import story {file_path.name}: {e}")


def import_resume_data(folder_path: str, rag: ResumeRAG) -> Dict[str, Any]:
    """
    Convenience function to import all resume data from a folder.
    
    Args:
        folder_path: Path to folder containing resume data
        rag: ResumeRAG instance to store data
    
    Returns:
        Import summary dictionary
    """
    importer = ResumeImporter(rag)
    return importer.import_folder(folder_path)


def get_import_status_message(result: Dict[str, Any]) -> str:
    """Get a formatted status message from import result."""
    lines = [
        "📄 **Resume Import Results**",
        "",
    ]
    
    if result.get("success"):
        lines.append(f"✅ Successfully imported {result['total_imported']} items")
    else:
        lines.append(f"⚠️ Imported {result['total_imported']} items with {result['total_failed']} failures")
    
    lines.append("")
    
    # By type
    by_type = result.get("by_type", {})
    if by_type:
        lines.append("**Imported:**")
        for item_type, count in by_type.items():
            emoji = {
                "resume": "📋",
                "project": "🚀",
                "experience": "💼",
                "skill": "🔧",
                "story": "📖",
            }.get(item_type, "📄")
            lines.append(f"  {emoji} {item_type.title()}: {count}")
    
    # Failed items
    failed = result.get("failed_items", [])
    if failed:
        lines.extend(["", "**Failed:**"])
        for name, message in failed[:5]:
            lines.append(f"  ❌ {name}: {message}")
    
    return "\n".join(lines)
