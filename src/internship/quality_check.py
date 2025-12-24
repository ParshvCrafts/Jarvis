"""
Resume Quality Check for JARVIS Internship Module.

Analyzes generated resumes for ATS compatibility and keyword coverage.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from loguru import logger

from .models import GeneratedResume, InternshipListing


@dataclass
class KeywordAnalysis:
    """Keyword analysis result."""
    keyword: str
    found: bool
    count: int = 0
    importance: str = "required"  # required, preferred, nice-to-have


@dataclass
class ATSCheck:
    """ATS compatibility check result."""
    check_name: str
    passed: bool
    message: str
    severity: str = "warning"  # error, warning, info


@dataclass
class QualityReport:
    """Complete quality report for a resume."""
    # Scores
    ats_score: float = 0.0
    keyword_score: float = 0.0
    format_score: float = 0.0
    overall_score: float = 0.0
    
    # Keyword analysis
    keywords_found: List[KeywordAnalysis] = field(default_factory=list)
    keywords_missing: List[KeywordAnalysis] = field(default_factory=list)
    keyword_coverage: float = 0.0
    
    # ATS checks
    ats_checks: List[ATSCheck] = field(default_factory=list)
    
    # Format analysis
    page_count: int = 1
    word_count: int = 0
    bullet_count: int = 0
    
    # Suggestions
    suggestions: List[str] = field(default_factory=list)


class ResumeQualityChecker:
    """
    Check resume quality for ATS compatibility and keyword coverage.
    
    Features:
    - ATS compatibility checks
    - Keyword extraction and matching
    - Format analysis
    - Improvement suggestions
    """
    
    # Common ATS-unfriendly elements
    ATS_RED_FLAGS = [
        (r'<table', "Tables detected - ATS may not parse correctly"),
        (r'<img', "Images detected - ATS cannot read images"),
        (r'[│┌┐└┘├┤┬┴┼]', "Box-drawing characters detected"),
        (r'[\u2500-\u257F]', "Special line characters detected"),
    ]
    
    # Important keywords by category
    KEYWORD_CATEGORIES = {
        "programming": [
            "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
            "sql", "r", "scala", "kotlin", "swift",
        ],
        "data_science": [
            "machine learning", "deep learning", "data analysis", "statistics",
            "data visualization", "nlp", "computer vision", "ai", "artificial intelligence",
            "neural network", "regression", "classification", "clustering",
        ],
        "frameworks": [
            "tensorflow", "pytorch", "keras", "scikit-learn", "pandas", "numpy",
            "spark", "hadoop", "airflow", "dbt",
            "react", "angular", "vue", "node.js", "django", "flask", "fastapi",
        ],
        "tools": [
            "git", "docker", "kubernetes", "aws", "gcp", "azure",
            "jenkins", "ci/cd", "linux", "bash",
            "jupyter", "tableau", "power bi", "excel",
        ],
        "soft_skills": [
            "leadership", "communication", "teamwork", "problem-solving",
            "analytical", "detail-oriented", "self-motivated",
        ],
    }
    
    def __init__(self):
        pass
    
    def check_resume(
        self,
        resume: GeneratedResume,
        job: Optional[InternshipListing] = None,
    ) -> QualityReport:
        """
        Perform comprehensive quality check on a resume.
        
        Args:
            resume: Generated resume to check
            job: Optional job listing for keyword matching
            
        Returns:
            QualityReport with detailed analysis
        """
        report = QualityReport()
        
        # Get resume text
        resume_text = self._get_resume_text(resume)
        
        # ATS checks
        report.ats_checks = self._run_ats_checks(resume_text, resume)
        ats_passed = sum(1 for c in report.ats_checks if c.passed)
        report.ats_score = (ats_passed / len(report.ats_checks)) * 100 if report.ats_checks else 100
        
        # Keyword analysis
        if job:
            job_keywords = self._extract_job_keywords(job)
            report.keywords_found, report.keywords_missing = self._analyze_keywords(
                resume_text, job_keywords
            )
            total_keywords = len(report.keywords_found) + len(report.keywords_missing)
            if total_keywords > 0:
                report.keyword_coverage = len(report.keywords_found) / total_keywords
                report.keyword_score = report.keyword_coverage * 100
        else:
            report.keyword_score = self._check_general_keywords(resume_text)
        
        # Format analysis
        report.word_count = len(resume_text.split())
        report.bullet_count = resume_text.count("•") + resume_text.count("-")
        report.page_count = 1 if report.word_count < 600 else 2
        
        # Format score
        format_checks = [
            report.word_count >= 200,  # Minimum content
            report.word_count <= 800,  # Not too long
            report.bullet_count >= 5,  # Has bullet points
            report.page_count == 1,    # One page
        ]
        report.format_score = (sum(format_checks) / len(format_checks)) * 100
        
        # Overall score
        report.overall_score = (
            report.ats_score * 0.3 +
            report.keyword_score * 0.5 +
            report.format_score * 0.2
        )
        
        # Generate suggestions
        report.suggestions = self._generate_suggestions(report, job)
        
        return report
    
    def _get_resume_text(self, resume: GeneratedResume) -> str:
        """Extract text content from resume."""
        parts = []
        
        if resume.summary:
            parts.append(resume.summary)
        
        if resume.skills_section:
            parts.append(resume.skills_section)
        
        if resume.projects_section:
            parts.append(resume.projects_section)
        
        if resume.experience_section:
            parts.append(resume.experience_section)
        
        return "\n".join(parts)
    
    def _run_ats_checks(
        self,
        text: str,
        resume: GeneratedResume,
    ) -> List[ATSCheck]:
        """Run ATS compatibility checks."""
        checks = []
        
        # Check for red flags
        for pattern, message in self.ATS_RED_FLAGS:
            if re.search(pattern, text, re.IGNORECASE):
                checks.append(ATSCheck(
                    check_name="Content Format",
                    passed=False,
                    message=message,
                    severity="error",
                ))
        
        # Check file format
        if resume.pdf_path:
            checks.append(ATSCheck(
                check_name="PDF Format",
                passed=True,
                message="PDF format is ATS-compatible",
                severity="info",
            ))
        
        # Check for standard sections
        standard_sections = ["education", "experience", "skills", "projects"]
        text_lower = text.lower()
        for section in standard_sections:
            found = section in text_lower
            checks.append(ATSCheck(
                check_name=f"{section.title()} Section",
                passed=found,
                message=f"{section.title()} section {'found' if found else 'missing'}",
                severity="warning" if not found else "info",
            ))
        
        # Check for contact info
        has_email = bool(re.search(r'[\w\.-]+@[\w\.-]+', text))
        checks.append(ATSCheck(
            check_name="Contact Email",
            passed=has_email,
            message="Email address " + ("found" if has_email else "missing"),
            severity="error" if not has_email else "info",
        ))
        
        # Check for simple formatting
        has_complex_chars = bool(re.search(r'[★☆●○◆◇▪▫]', text))
        checks.append(ATSCheck(
            check_name="Simple Characters",
            passed=not has_complex_chars,
            message="Uses " + ("complex" if has_complex_chars else "simple") + " characters",
            severity="warning" if has_complex_chars else "info",
        ))
        
        return checks
    
    def _extract_job_keywords(self, job: InternshipListing) -> List[Tuple[str, str]]:
        """Extract keywords from job listing with importance."""
        keywords = []
        
        # From requirements (required)
        req_text = " ".join(job.requirements).lower()
        for category, kw_list in self.KEYWORD_CATEGORIES.items():
            for kw in kw_list:
                if kw in req_text:
                    keywords.append((kw, "required"))
        
        # From description (preferred)
        desc_lower = job.description.lower()
        for category, kw_list in self.KEYWORD_CATEGORIES.items():
            for kw in kw_list:
                if kw in desc_lower and (kw, "required") not in keywords:
                    keywords.append((kw, "preferred"))
        
        # From job keywords
        for kw in job.keywords:
            if (kw.lower(), "required") not in keywords and (kw.lower(), "preferred") not in keywords:
                keywords.append((kw.lower(), "nice-to-have"))
        
        return keywords
    
    def _analyze_keywords(
        self,
        resume_text: str,
        job_keywords: List[Tuple[str, str]],
    ) -> Tuple[List[KeywordAnalysis], List[KeywordAnalysis]]:
        """Analyze keyword coverage."""
        found = []
        missing = []
        
        resume_lower = resume_text.lower()
        
        for keyword, importance in job_keywords:
            count = resume_lower.count(keyword)
            analysis = KeywordAnalysis(
                keyword=keyword,
                found=count > 0,
                count=count,
                importance=importance,
            )
            
            if count > 0:
                found.append(analysis)
            else:
                missing.append(analysis)
        
        return found, missing
    
    def _check_general_keywords(self, resume_text: str) -> float:
        """Check for general important keywords without a job listing."""
        resume_lower = resume_text.lower()
        
        important_keywords = [
            "python", "sql", "data", "analysis", "machine learning",
            "project", "developed", "implemented", "achieved", "improved",
        ]
        
        found = sum(1 for kw in important_keywords if kw in resume_lower)
        return (found / len(important_keywords)) * 100
    
    def _generate_suggestions(
        self,
        report: QualityReport,
        job: Optional[InternshipListing],
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        # ATS suggestions
        failed_ats = [c for c in report.ats_checks if not c.passed and c.severity == "error"]
        for check in failed_ats[:2]:
            suggestions.append(f"Fix: {check.message}")
        
        # Keyword suggestions
        required_missing = [k for k in report.keywords_missing if k.importance == "required"]
        if required_missing:
            keywords = ", ".join(k.keyword for k in required_missing[:3])
            suggestions.append(f"Add missing required keywords: {keywords}")
        
        # Format suggestions
        if report.word_count < 200:
            suggestions.append("Add more content - resume seems too short")
        elif report.word_count > 800:
            suggestions.append("Consider condensing - resume may be too long")
        
        if report.bullet_count < 5:
            suggestions.append("Add more bullet points to highlight achievements")
        
        # Score-based suggestions
        if report.overall_score >= 90:
            suggestions.append("✅ Excellent resume! Ready to submit")
        elif report.overall_score >= 75:
            suggestions.append("Good resume - minor improvements suggested above")
        elif report.overall_score >= 60:
            suggestions.append("Decent resume - address the suggestions above")
        else:
            suggestions.append("Resume needs significant improvements")
        
        return suggestions


def format_quality_report(report: QualityReport, job: Optional[InternshipListing] = None) -> str:
    """Format quality report as a readable message."""
    lines = [
        f"📄 **Resume Quality Report**",
    ]
    
    if job:
        lines.append(f"*For: {job.company} - {job.role}*")
    
    lines.extend([
        "",
        "**Quality Metrics:**",
        f"  🎯 Overall Score: {report.overall_score:.0f}/100",
        f"  📊 ATS Score: {report.ats_score:.0f}/100",
        f"  🔑 Keyword Score: {report.keyword_score:.0f}/100",
        f"  📝 Format Score: {report.format_score:.0f}/100",
        "",
    ])
    
    # Keyword coverage
    if report.keywords_found or report.keywords_missing:
        lines.append(f"**Keyword Coverage: {report.keyword_coverage:.0%}**")
        
        if report.keywords_found:
            found_str = ", ".join(
                f"{k.keyword} ({k.count}x)" 
                for k in sorted(report.keywords_found, key=lambda x: x.count, reverse=True)[:5]
            )
            lines.append(f"  ✅ Found: {found_str}")
        
        if report.keywords_missing:
            required_missing = [k for k in report.keywords_missing if k.importance == "required"]
            if required_missing:
                missing_str = ", ".join(k.keyword for k in required_missing[:5])
                lines.append(f"  ❌ Missing (required): {missing_str}")
            
            preferred_missing = [k for k in report.keywords_missing if k.importance == "preferred"]
            if preferred_missing:
                missing_str = ", ".join(k.keyword for k in preferred_missing[:3])
                lines.append(f"  ⚠️ Missing (preferred): {missing_str}")
        
        lines.append("")
    
    # ATS checks
    failed_checks = [c for c in report.ats_checks if not c.passed]
    if failed_checks:
        lines.append("**ATS Issues:**")
        for check in failed_checks[:3]:
            emoji = "❌" if check.severity == "error" else "⚠️"
            lines.append(f"  {emoji} {check.message}")
        lines.append("")
    
    # Format info
    lines.extend([
        "**Format:**",
        f"  📏 Word Count: {report.word_count}",
        f"  📋 Bullet Points: {report.bullet_count}",
        f"  📄 Pages: {report.page_count}",
        "",
    ])
    
    # Suggestions
    if report.suggestions:
        lines.append("**Suggestions:**")
        for i, suggestion in enumerate(report.suggestions, 1):
            lines.append(f"  {i}. {suggestion}")
    
    return "\n".join(lines)
