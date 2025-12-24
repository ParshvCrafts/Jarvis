"""
Skill Gap Analysis for JARVIS Internship Module.

Analyzes user's skills against job requirements and provides recommendations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from .models import InternshipListing, Skill, SkillCategory


@dataclass
class SkillMatch:
    """A skill match result."""
    skill: str
    matched: bool
    user_level: Optional[str] = None
    required_level: Optional[str] = None
    category: str = "technical"


@dataclass
class SkillGapAnalysis:
    """Complete skill gap analysis result."""
    job_title: str
    company: str
    
    # Matched skills
    matched_required: List[SkillMatch] = field(default_factory=list)
    matched_preferred: List[SkillMatch] = field(default_factory=list)
    
    # Missing skills
    missing_required: List[str] = field(default_factory=list)
    missing_preferred: List[str] = field(default_factory=list)
    
    # Overall scores
    required_match_score: float = 0.0
    preferred_match_score: float = 0.0
    overall_match_score: float = 0.0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    learning_resources: List[Dict[str, str]] = field(default_factory=list)


class SkillAnalyzer:
    """
    Analyze skill gaps between user profile and job requirements.
    
    Features:
    - Extract skills from job descriptions
    - Match against user's skills
    - Calculate match scores
    - Provide learning recommendations
    """
    
    # Common skill synonyms and variations
    SKILL_SYNONYMS = {
        "python": ["python3", "py"],
        "javascript": ["js", "es6", "ecmascript"],
        "typescript": ["ts"],
        "machine learning": ["ml", "machine-learning"],
        "deep learning": ["dl", "deep-learning", "neural networks"],
        "natural language processing": ["nlp", "text processing"],
        "computer vision": ["cv", "image processing"],
        "sql": ["mysql", "postgresql", "postgres", "sqlite"],
        "nosql": ["mongodb", "dynamodb", "cassandra"],
        "aws": ["amazon web services", "ec2", "s3", "lambda"],
        "gcp": ["google cloud", "google cloud platform"],
        "azure": ["microsoft azure"],
        "docker": ["containerization", "containers"],
        "kubernetes": ["k8s", "container orchestration"],
        "react": ["reactjs", "react.js"],
        "node": ["nodejs", "node.js"],
        "tensorflow": ["tf"],
        "pytorch": ["torch"],
        "pandas": ["dataframes"],
        "scikit-learn": ["sklearn", "scikit learn"],
        "data analysis": ["data analytics", "analytics"],
        "data visualization": ["visualization", "dashboards"],
        "git": ["github", "gitlab", "version control"],
        "agile": ["scrum", "kanban"],
        "ci/cd": ["continuous integration", "continuous deployment", "devops"],
    }
    
    # Learning resources by skill
    LEARNING_RESOURCES = {
        "python": {"name": "Python for Data Science", "url": "https://www.coursera.org/learn/python-for-applied-data-science-ai"},
        "machine learning": {"name": "Machine Learning by Andrew Ng", "url": "https://www.coursera.org/learn/machine-learning"},
        "deep learning": {"name": "Deep Learning Specialization", "url": "https://www.coursera.org/specializations/deep-learning"},
        "tensorflow": {"name": "TensorFlow Developer Certificate", "url": "https://www.tensorflow.org/certificate"},
        "pytorch": {"name": "PyTorch Tutorials", "url": "https://pytorch.org/tutorials/"},
        "sql": {"name": "SQL for Data Science", "url": "https://www.coursera.org/learn/sql-for-data-science"},
        "aws": {"name": "AWS Cloud Practitioner", "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/"},
        "docker": {"name": "Docker Getting Started", "url": "https://docs.docker.com/get-started/"},
        "kubernetes": {"name": "Kubernetes Basics", "url": "https://kubernetes.io/docs/tutorials/kubernetes-basics/"},
        "react": {"name": "React Official Tutorial", "url": "https://react.dev/learn"},
        "nlp": {"name": "NLP Specialization", "url": "https://www.coursera.org/specializations/natural-language-processing"},
        "spark": {"name": "Apache Spark Tutorial", "url": "https://spark.apache.org/docs/latest/quick-start.html"},
        "data visualization": {"name": "Data Visualization with Python", "url": "https://www.coursera.org/learn/python-for-data-visualization"},
    }
    
    def __init__(self, user_skills: List[Skill] = None):
        self.user_skills = user_skills or []
        self._build_skill_index()
    
    def _build_skill_index(self):
        """Build an index of user skills for fast lookup."""
        self.skill_index: Dict[str, Skill] = {}
        
        for skill in self.user_skills:
            # Index by name
            self.skill_index[skill.name.lower()] = skill
            
            # Index by keywords
            for keyword in skill.keywords:
                self.skill_index[keyword.lower()] = skill
    
    def set_user_skills(self, skills: List[Skill]):
        """Update user skills."""
        self.user_skills = skills
        self._build_skill_index()
    
    def extract_skills_from_job(
        self,
        job: InternshipListing,
    ) -> Tuple[List[str], List[str]]:
        """
        Extract required and preferred skills from job listing.
        
        Returns:
            Tuple of (required_skills, preferred_skills)
        """
        required = set()
        preferred = set()
        
        # Common technical skills to look for
        tech_skills = [
            "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
            "sql", "nosql", "mongodb", "postgresql", "mysql",
            "machine learning", "deep learning", "nlp", "computer vision",
            "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
            "aws", "gcp", "azure", "docker", "kubernetes",
            "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
            "git", "linux", "bash", "shell",
            "data analysis", "data visualization", "statistics", "excel",
            "spark", "hadoop", "airflow", "kafka",
            "agile", "scrum", "jira",
            "r", "matlab", "sas", "tableau", "power bi",
        ]
        
        # Combine all text
        text = f"{job.description} {' '.join(job.requirements)}".lower()
        
        # Extract skills mentioned
        for skill in tech_skills:
            if skill in text:
                # Check if it's in requirements section (more likely required)
                req_text = " ".join(job.requirements).lower()
                if skill in req_text:
                    required.add(skill)
                else:
                    preferred.add(skill)
        
        # Also check for explicit requirement patterns
        for req in job.requirements:
            req_lower = req.lower()
            if any(word in req_lower for word in ["required", "must have", "essential"]):
                for skill in tech_skills:
                    if skill in req_lower:
                        required.add(skill)
            elif any(word in req_lower for word in ["preferred", "nice to have", "bonus"]):
                for skill in tech_skills:
                    if skill in req_lower:
                        preferred.add(skill)
        
        return list(required), list(preferred - required)
    
    def _normalize_skill(self, skill: str) -> str:
        """Normalize a skill name for matching."""
        skill_lower = skill.lower().strip()
        
        # Check synonyms
        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            if skill_lower == canonical or skill_lower in synonyms:
                return canonical
        
        return skill_lower
    
    def _user_has_skill(self, skill: str) -> Tuple[bool, Optional[Skill]]:
        """Check if user has a skill."""
        normalized = self._normalize_skill(skill)
        
        # Direct match
        if normalized in self.skill_index:
            return True, self.skill_index[normalized]
        
        # Check synonyms
        for canonical, synonyms in self.SKILL_SYNONYMS.items():
            if normalized == canonical or normalized in synonyms:
                if canonical in self.skill_index:
                    return True, self.skill_index[canonical]
                for syn in synonyms:
                    if syn in self.skill_index:
                        return True, self.skill_index[syn]
        
        # Partial match
        for skill_name, skill_obj in self.skill_index.items():
            if normalized in skill_name or skill_name in normalized:
                return True, skill_obj
        
        return False, None
    
    def analyze(self, job: InternshipListing) -> SkillGapAnalysis:
        """
        Perform skill gap analysis for a job.
        
        Args:
            job: InternshipListing to analyze
            
        Returns:
            SkillGapAnalysis with detailed results
        """
        analysis = SkillGapAnalysis(
            job_title=job.role,
            company=job.company,
        )
        
        # Extract skills from job
        required_skills, preferred_skills = self.extract_skills_from_job(job)
        
        # Match required skills
        for skill in required_skills:
            has_skill, user_skill = self._user_has_skill(skill)
            if has_skill:
                analysis.matched_required.append(SkillMatch(
                    skill=skill,
                    matched=True,
                    user_level=user_skill.proficiency.value if user_skill else None,
                ))
            else:
                analysis.missing_required.append(skill)
        
        # Match preferred skills
        for skill in preferred_skills:
            has_skill, user_skill = self._user_has_skill(skill)
            if has_skill:
                analysis.matched_preferred.append(SkillMatch(
                    skill=skill,
                    matched=True,
                    user_level=user_skill.proficiency.value if user_skill else None,
                ))
            else:
                analysis.missing_preferred.append(skill)
        
        # Calculate scores
        if required_skills:
            analysis.required_match_score = len(analysis.matched_required) / len(required_skills)
        else:
            analysis.required_match_score = 1.0
        
        if preferred_skills:
            analysis.preferred_match_score = len(analysis.matched_preferred) / len(preferred_skills)
        else:
            analysis.preferred_match_score = 1.0
        
        # Overall score (required weighted more heavily)
        analysis.overall_match_score = (
            analysis.required_match_score * 0.7 +
            analysis.preferred_match_score * 0.3
        )
        
        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(analysis)
        analysis.learning_resources = self._get_learning_resources(analysis.missing_required)
        
        return analysis
    
    def _generate_recommendations(self, analysis: SkillGapAnalysis) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Missing required skills
        if analysis.missing_required:
            if len(analysis.missing_required) <= 2:
                recommendations.append(
                    f"Focus on learning {' and '.join(analysis.missing_required)} - "
                    "these are required skills"
                )
            else:
                recommendations.append(
                    f"Prioritize learning: {', '.join(analysis.missing_required[:3])}"
                )
        
        # Highlight transferable skills
        if analysis.matched_required:
            recommendations.append(
                f"Highlight your {', '.join(s.skill for s in analysis.matched_required[:3])} "
                "experience prominently in your resume"
            )
        
        # Missing preferred skills
        if analysis.missing_preferred and not analysis.missing_required:
            recommendations.append(
                f"Consider adding {analysis.missing_preferred[0]} to strengthen your application"
            )
        
        # Good match
        if analysis.overall_match_score >= 0.8:
            recommendations.append(
                "Strong match! Focus on tailoring your resume to highlight relevant projects"
            )
        elif analysis.overall_match_score >= 0.6:
            recommendations.append(
                "Good foundation - emphasize your transferable skills and willingness to learn"
            )
        else:
            recommendations.append(
                "Consider building a project using the required technologies before applying"
            )
        
        return recommendations
    
    def _get_learning_resources(self, missing_skills: List[str]) -> List[Dict[str, str]]:
        """Get learning resources for missing skills."""
        resources = []
        
        for skill in missing_skills[:5]:
            normalized = self._normalize_skill(skill)
            if normalized in self.LEARNING_RESOURCES:
                resources.append({
                    "skill": skill,
                    **self.LEARNING_RESOURCES[normalized]
                })
        
        return resources


def format_skill_gap_analysis(analysis: SkillGapAnalysis) -> str:
    """Format skill gap analysis as a readable report."""
    lines = [
        f"📊 **Skill Gap Analysis: {analysis.company} - {analysis.job_title}**",
        "",
        f"**Overall Match: {analysis.overall_match_score:.0%}**",
        "",
    ]
    
    # Required skills
    if analysis.matched_required or analysis.missing_required:
        lines.append("**Required Skills:**")
        for match in analysis.matched_required:
            level = f" ({match.user_level})" if match.user_level else ""
            lines.append(f"  ✅ {match.skill.title()}{level}")
        for skill in analysis.missing_required:
            lines.append(f"  ❌ {skill.title()} - Missing")
        lines.append("")
    
    # Preferred skills
    if analysis.matched_preferred or analysis.missing_preferred:
        lines.append("**Preferred Skills:**")
        for match in analysis.matched_preferred:
            lines.append(f"  ✅ {match.skill.title()}")
        for skill in analysis.missing_preferred:
            lines.append(f"  ⚠️ {skill.title()} - Nice to have")
        lines.append("")
    
    # Recommendations
    if analysis.recommendations:
        lines.append("**Recommendations:**")
        for i, rec in enumerate(analysis.recommendations, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")
    
    # Learning resources
    if analysis.learning_resources:
        lines.append("**Learning Resources:**")
        for resource in analysis.learning_resources[:3]:
            lines.append(f"  📚 {resource['skill'].title()}: {resource['name']}")
    
    return "\n".join(lines)
