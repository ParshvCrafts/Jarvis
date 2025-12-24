"""
Resume & Experience Tracker for JARVIS.

Track experiences and generate resume content:
- Projects (personal, class, hackathon)
- Work (internships, part-time, research)
- Leadership (clubs, organizations)
- Skills (technical, tools)
- Achievements (awards, certifications)
- Education (courses, GPA)
"""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class ExperienceType(Enum):
    PROJECT = "project"
    WORK = "work"
    LEADERSHIP = "leadership"
    ACHIEVEMENT = "achievement"
    EDUCATION = "education"


class SkillCategory(Enum):
    PROGRAMMING = "programming"
    ML_AI = "ml_ai"
    DATA = "data"
    TOOLS = "tools"
    SOFT_SKILLS = "soft_skills"
    OTHER = "other"


class SkillLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class Experience:
    id: Optional[int] = None
    type: ExperienceType = ExperienceType.PROJECT
    title: str = ""
    organization: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    description: str = ""
    bullets: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    impact_metrics: str = ""
    url: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "organization": self.organization,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "is_current": self.is_current,
            "description": self.description,
            "bullets": json.dumps(self.bullets),
            "skills": json.dumps(self.skills),
            "impact_metrics": self.impact_metrics,
            "url": self.url,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Experience":
        return cls(
            id=row["id"],
            type=ExperienceType(row["type"]),
            title=row["title"],
            organization=row["organization"] or "",
            start_date=date.fromisoformat(row["start_date"]) if row["start_date"] else None,
            end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
            is_current=bool(row["is_current"]),
            description=row["description"] or "",
            bullets=json.loads(row["bullets"]) if row["bullets"] else [],
            skills=json.loads(row["skills"]) if row["skills"] else [],
            impact_metrics=row["impact_metrics"] or "",
            url=row["url"] or "",
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now(),
        )


@dataclass
class Skill:
    id: Optional[int] = None
    name: str = ""
    category: SkillCategory = SkillCategory.OTHER
    level: SkillLevel = SkillLevel.INTERMEDIATE
    years_experience: float = 0.0
    last_used: Optional[date] = None
    notes: str = ""
    
    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Skill":
        return cls(
            id=row["id"],
            name=row["name"],
            category=SkillCategory(row["category"]),
            level=SkillLevel(row["level"]),
            years_experience=row["years_experience"] or 0.0,
            last_used=date.fromisoformat(row["last_used"]) if row["last_used"] else None,
            notes=row["notes"] or "",
        )


class ResumeTracker:
    """
    Resume and experience tracking system.
    
    Features:
    - Add/edit experiences
    - Track skills with proficiency
    - Generate resume bullets
    - STAR format guidance
    - Export to markdown
    """
    
    # Action verbs for resume bullets
    ACTION_VERBS = {
        "technical": [
            "Developed", "Implemented", "Engineered", "Designed", "Built",
            "Created", "Optimized", "Automated", "Integrated", "Deployed",
            "Architected", "Programmed", "Debugged", "Refactored", "Scaled",
        ],
        "analysis": [
            "Analyzed", "Evaluated", "Assessed", "Researched", "Investigated",
            "Identified", "Discovered", "Measured", "Quantified", "Tested",
        ],
        "leadership": [
            "Led", "Managed", "Coordinated", "Directed", "Supervised",
            "Mentored", "Trained", "Organized", "Facilitated", "Spearheaded",
        ],
        "achievement": [
            "Achieved", "Improved", "Increased", "Reduced", "Exceeded",
            "Delivered", "Accomplished", "Completed", "Launched", "Won",
        ],
    }
    
    def __init__(
        self,
        data_dir: str = "data",
        name: str = "",
        university: str = "UC Berkeley",
        major: str = "Data Science",
        graduation: str = "2028",
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "resume.db"
        
        self.name = name
        self.university = university
        self.major = major
        self.graduation = graduation
        
        self._init_db()
        logger.info("Resume Tracker initialized")
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    organization TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    is_current INTEGER DEFAULT 0,
                    description TEXT,
                    bullets TEXT,
                    skills TEXT,
                    impact_metrics TEXT,
                    url TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    level TEXT NOT NULL,
                    years_experience REAL DEFAULT 0,
                    last_used TEXT,
                    notes TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS profile (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()
    
    def add_experience(
        self,
        title: str,
        exp_type: str = "project",
        organization: str = "",
        description: str = "",
        skills: Optional[List[str]] = None,
        impact: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_current: bool = False,
        url: str = "",
    ) -> Experience:
        """Add a new experience."""
        try:
            etype = ExperienceType(exp_type.lower())
        except ValueError:
            etype = ExperienceType.PROJECT
        
        exp = Experience(
            type=etype,
            title=title,
            organization=organization,
            description=description,
            skills=skills or [],
            impact_metrics=impact,
            start_date=date.fromisoformat(start_date) if start_date else None,
            end_date=date.fromisoformat(end_date) if end_date else None,
            is_current=is_current,
            url=url,
        )
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO experiences (type, title, organization, start_date, end_date,
                    is_current, description, bullets, skills, impact_metrics, url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                exp.type.value, exp.title, exp.organization,
                exp.start_date.isoformat() if exp.start_date else None,
                exp.end_date.isoformat() if exp.end_date else None,
                int(exp.is_current), exp.description, json.dumps(exp.bullets),
                json.dumps(exp.skills), exp.impact_metrics, exp.url,
                exp.created_at.isoformat()
            ))
            exp.id = cursor.lastrowid
            conn.commit()
        
        # Auto-add skills
        for skill in exp.skills:
            self.add_skill(skill)
        
        logger.info(f"Added experience: {title}")
        return exp
    
    def add_skill(
        self,
        name: str,
        category: str = "other",
        level: str = "intermediate",
        years: float = 0.0,
    ) -> Skill:
        """Add or update a skill."""
        try:
            cat = SkillCategory(category.lower())
        except ValueError:
            cat = SkillCategory.OTHER
        
        try:
            lvl = SkillLevel(level.lower())
        except ValueError:
            lvl = SkillLevel.INTERMEDIATE
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO skills (name, category, level, years_experience, last_used)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    level = excluded.level,
                    years_experience = excluded.years_experience,
                    last_used = excluded.last_used
            """, (name, cat.value, lvl.value, years, date.today().isoformat()))
            conn.commit()
        
        return Skill(name=name, category=cat, level=lvl, years_experience=years)
    
    def get_experiences(
        self,
        exp_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Experience]:
        """Get experiences, optionally filtered by type."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if exp_type:
                rows = conn.execute(
                    "SELECT * FROM experiences WHERE type = ? ORDER BY created_at DESC LIMIT ?",
                    (exp_type, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM experiences ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        
        return [Experience.from_row(row) for row in rows]
    
    def get_skills(self, category: Optional[str] = None) -> List[Skill]:
        """Get skills, optionally filtered by category."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if category:
                rows = conn.execute(
                    "SELECT * FROM skills WHERE category = ? ORDER BY level DESC, name",
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM skills ORDER BY category, level DESC, name"
                ).fetchall()
        
        return [Skill.from_row(row) for row in rows]
    
    def generate_bullet(self, experience_id: int) -> str:
        """Generate a resume bullet for an experience."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM experiences WHERE id = ?", (experience_id,)
            ).fetchone()
        
        if not row:
            return "Experience not found."
        
        exp = Experience.from_row(row)
        
        # Select appropriate action verb
        if exp.type == ExperienceType.PROJECT:
            verb = self.ACTION_VERBS["technical"][0]
        elif exp.type == ExperienceType.WORK:
            verb = self.ACTION_VERBS["achievement"][0]
        elif exp.type == ExperienceType.LEADERSHIP:
            verb = self.ACTION_VERBS["leadership"][0]
        else:
            verb = self.ACTION_VERBS["achievement"][0]
        
        # Build bullet
        bullet = f"{verb} {exp.title}"
        
        if exp.skills:
            bullet += f" using {', '.join(exp.skills[:3])}"
        
        if exp.impact_metrics:
            bullet += f", {exp.impact_metrics}"
        
        return bullet
    
    def format_experiences(self, experiences: List[Experience]) -> str:
        """Format experiences for display."""
        if not experiences:
            return "No experiences recorded yet."
        
        lines = ["📋 **Your Experiences**\n"]
        
        by_type = {}
        for exp in experiences:
            if exp.type not in by_type:
                by_type[exp.type] = []
            by_type[exp.type].append(exp)
        
        type_emoji = {
            ExperienceType.PROJECT: "💻",
            ExperienceType.WORK: "💼",
            ExperienceType.LEADERSHIP: "👥",
            ExperienceType.ACHIEVEMENT: "🏆",
            ExperienceType.EDUCATION: "📚",
        }
        
        for exp_type, exps in by_type.items():
            emoji = type_emoji.get(exp_type, "📌")
            lines.append(f"\n{emoji} **{exp_type.value.title()}**")
            
            for exp in exps:
                date_str = ""
                if exp.start_date:
                    date_str = f" ({exp.start_date.strftime('%b %Y')}"
                    if exp.is_current:
                        date_str += " - Present)"
                    elif exp.end_date:
                        date_str += f" - {exp.end_date.strftime('%b %Y')})"
                    else:
                        date_str += ")"
                
                lines.append(f"  • **{exp.title}**{date_str}")
                if exp.organization:
                    lines.append(f"    {exp.organization}")
                if exp.description:
                    lines.append(f"    {exp.description[:100]}...")
                if exp.skills:
                    lines.append(f"    Skills: {', '.join(exp.skills[:5])}")
        
        return "\n".join(lines)
    
    def format_skills(self, skills: List[Skill]) -> str:
        """Format skills for display."""
        if not skills:
            return "No skills recorded yet."
        
        lines = ["🛠️ **Your Skills**\n"]
        
        by_category = {}
        for skill in skills:
            if skill.category not in by_category:
                by_category[skill.category] = []
            by_category[skill.category].append(skill)
        
        level_emoji = {
            SkillLevel.BEGINNER: "🟢",
            SkillLevel.INTERMEDIATE: "🟡",
            SkillLevel.ADVANCED: "🟠",
            SkillLevel.EXPERT: "🔴",
        }
        
        for category, cat_skills in by_category.items():
            lines.append(f"\n**{category.value.replace('_', ' ').title()}:**")
            for skill in cat_skills:
                emoji = level_emoji.get(skill.level, "⚪")
                lines.append(f"  {emoji} {skill.name} ({skill.level.value})")
        
        return "\n".join(lines)
    
    def update_gpa(self, gpa: float) -> str:
        """Update GPA in profile."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO profile (key, value) VALUES (?, ?)",
                ("gpa", str(gpa))
            )
            conn.commit()
        return f"✅ GPA updated to {gpa}"
    
    def get_resume_summary(self) -> str:
        """Get a summary of resume content."""
        experiences = self.get_experiences()
        skills = self.get_skills()
        
        with sqlite3.connect(self.db_path) as conn:
            gpa_row = conn.execute(
                "SELECT value FROM profile WHERE key = 'gpa'"
            ).fetchone()
            gpa = gpa_row[0] if gpa_row else "N/A"
        
        exp_counts = {}
        for exp in experiences:
            exp_counts[exp.type.value] = exp_counts.get(exp.type.value, 0) + 1
        
        lines = [
            f"📄 **Resume Summary for {self.name or 'Student'}**\n",
            f"🎓 {self.university} - {self.major}",
            f"   Expected Graduation: {self.graduation}",
            f"   GPA: {gpa}\n",
            f"📊 **Experience Count:**",
        ]
        
        for exp_type, count in exp_counts.items():
            lines.append(f"  • {exp_type.title()}: {count}")
        
        lines.append(f"\n🛠️ **Skills:** {len(skills)} recorded")
        
        # Top skills by category
        skill_cats = {}
        for s in skills:
            if s.category.value not in skill_cats:
                skill_cats[s.category.value] = []
            skill_cats[s.category.value].append(s.name)
        
        for cat, names in list(skill_cats.items())[:3]:
            lines.append(f"  • {cat}: {', '.join(names[:4])}")
        
        return "\n".join(lines)
    
    def export_markdown(self) -> str:
        """Export resume to markdown format."""
        experiences = self.get_experiences()
        skills = self.get_skills()
        
        with sqlite3.connect(self.db_path) as conn:
            gpa_row = conn.execute(
                "SELECT value FROM profile WHERE key = 'gpa'"
            ).fetchone()
            gpa = gpa_row[0] if gpa_row else None
        
        lines = [
            f"# {self.name or 'Resume'}\n",
            "## Education\n",
            f"**{self.university}** - {self.major}",
            f"Expected Graduation: {self.graduation}",
        ]
        
        if gpa:
            lines.append(f"GPA: {gpa}")
        
        # Group experiences by type
        by_type = {}
        for exp in experiences:
            if exp.type not in by_type:
                by_type[exp.type] = []
            by_type[exp.type].append(exp)
        
        type_headers = {
            ExperienceType.WORK: "## Work Experience",
            ExperienceType.PROJECT: "## Projects",
            ExperienceType.LEADERSHIP: "## Leadership",
            ExperienceType.ACHIEVEMENT: "## Achievements",
        }
        
        for exp_type, header in type_headers.items():
            if exp_type in by_type:
                lines.append(f"\n{header}\n")
                for exp in by_type[exp_type]:
                    lines.append(f"### {exp.title}")
                    if exp.organization:
                        lines.append(f"*{exp.organization}*")
                    if exp.description:
                        lines.append(f"\n{exp.description}")
                    if exp.bullets:
                        for bullet in exp.bullets:
                            lines.append(f"- {bullet}")
                    if exp.skills:
                        lines.append(f"\n**Technologies:** {', '.join(exp.skills)}")
                    lines.append("")
        
        # Skills section
        lines.append("\n## Skills\n")
        by_category = {}
        for skill in skills:
            if skill.category not in by_category:
                by_category[skill.category] = []
            by_category[skill.category].append(skill.name)
        
        for category, names in by_category.items():
            lines.append(f"**{category.value.replace('_', ' ').title()}:** {', '.join(names)}")
        
        return "\n".join(lines)
    
    def suggest_action_verbs(self, exp_type: str = "technical") -> List[str]:
        """Suggest action verbs for resume bullets."""
        return self.ACTION_VERBS.get(exp_type, self.ACTION_VERBS["achievement"])
