"""
Resume RAG System for JARVIS Internship Automation Module.

Stores and retrieves:
- Projects with embeddings
- Work experience with embeddings
- Skills with evidence
- Stories from scholarship essays
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import (
    Project,
    WorkExperience,
    Skill,
    MasterResume,
    SkillCategory,
    ProficiencyLevel,
)

# Try importing embedding dependencies
EMBEDDINGS_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    logger.debug("sentence-transformers not installed")

# Try importing ChromaDB
CHROMADB_AVAILABLE = False
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    logger.debug("chromadb not installed")


@dataclass
class ResumeRAGContext:
    """Context retrieved for resume customization."""
    matched_projects: List[Tuple[Project, float]] = field(default_factory=list)
    matched_experience: List[Tuple[WorkExperience, float]] = field(default_factory=list)
    matched_skills: List[Skill] = field(default_factory=list)
    matched_stories: List[Tuple[str, float]] = field(default_factory=list)  # From scholarship essays
    
    job_keywords: List[str] = field(default_factory=list)
    missing_keywords: List[str] = field(default_factory=list)
    
    def get_top_projects(self, n: int = 4) -> List[Project]:
        """Get top N matching projects."""
        return [p for p, _ in self.matched_projects[:n]]
    
    def get_project_bullets(self, n: int = 4) -> List[str]:
        """Get resume bullets from top projects."""
        bullets = []
        for project, _ in self.matched_projects[:n]:
            bullets.extend(project.resume_bullets[:3])
        return bullets


class ResumeRAG:
    """
    RAG system for resume content.
    
    Stores projects, experience, and skills with embeddings
    for semantic retrieval when customizing resumes.
    """
    
    def __init__(
        self,
        persist_directory: str = "data/resume_rag",
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.persist_directory = persist_directory
        self.model_name = model_name
        
        # Initialize embedding model
        self._embedder = None
        self._dimensions = 384
        
        # ChromaDB collections
        self._chroma_client = None
        self._projects_collection = None
        self._experience_collection = None
        self._stories_collection = None
        
        # In-memory fallback
        self._projects: List[Tuple[Project, List[float]]] = []
        self._experience: List[Tuple[WorkExperience, List[float]]] = []
        self._skills: List[Skill] = []
        self._stories: List[Tuple[str, str, List[float]]] = []  # (id, text, embedding)
        
        # Initialize
        self._initialize()
    
    def _initialize(self):
        """Initialize embedding model and storage."""
        # Initialize embedder
        if EMBEDDINGS_AVAILABLE:
            try:
                self._embedder = SentenceTransformer(self.model_name)
                self._dimensions = self._embedder.get_sentence_embedding_dimension()
                logger.info(f"Resume RAG embedder loaded: {self.model_name} ({self._dimensions}D)")
            except Exception as e:
                logger.error(f"Failed to load embedder: {e}")
        
        # Initialize ChromaDB
        if CHROMADB_AVAILABLE:
            try:
                os.makedirs(self.persist_directory, exist_ok=True)
                
                self._chroma_client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(anonymized_telemetry=False)
                )
                
                # Create collections
                self._projects_collection = self._chroma_client.get_or_create_collection(
                    name="resume_projects",
                    metadata={"hnsw:space": "cosine"}
                )
                
                self._experience_collection = self._chroma_client.get_or_create_collection(
                    name="resume_experience",
                    metadata={"hnsw:space": "cosine"}
                )
                
                self._stories_collection = self._chroma_client.get_or_create_collection(
                    name="resume_stories",
                    metadata={"hnsw:space": "cosine"}
                )
                
                logger.info(f"Resume RAG ChromaDB initialized at {self.persist_directory}")
                logger.info(f"Collections: {self._projects_collection.count()} projects, "
                           f"{self._experience_collection.count()} experiences, "
                           f"{self._stories_collection.count()} stories")
                
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
    
    def _embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        if not self._embedder:
            raise ValueError("Embedder not available")
        
        embedding = self._embedder.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    # =========================================================================
    # Project Management
    # =========================================================================
    
    def add_project(self, project: Project) -> Optional[str]:
        """Add a project to the RAG system."""
        if not self._embedder:
            logger.warning("No embedder available")
            return None
        
        try:
            # Generate embedding
            text = project.get_searchable_text()
            embedding = self._embed(text)
            
            # Store in ChromaDB
            if self._projects_collection:
                self._projects_collection.add(
                    ids=[project.id],
                    embeddings=[embedding],
                    metadatas=[{
                        "name": project.name,
                        "technologies": ",".join(project.technologies),
                        "skills": ",".join(project.skills_demonstrated),
                    }],
                    documents=[text]
                )
                logger.debug(f"Added project to ChromaDB: {project.name}")
            
            # Also store in memory
            self._projects.append((project, embedding))
            
            return project.id
            
        except Exception as e:
            logger.error(f"Failed to add project: {e}")
            return None
    
    def search_projects(
        self,
        query: str,
        n_results: int = 5,
        filter_technologies: Optional[List[str]] = None,
    ) -> List[Tuple[Project, float]]:
        """Search for projects matching a query."""
        if not self._embedder:
            return []
        
        try:
            query_embedding = self._embed(query)
            
            # Search ChromaDB
            if self._projects_collection and self._projects_collection.count() > 0:
                results = self._projects_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, self._projects_collection.count()),
                )
                
                matched = []
                for i, doc_id in enumerate(results["ids"][0]):
                    # Find project in memory
                    for project, _ in self._projects:
                        if project.id == doc_id:
                            score = 1 - results["distances"][0][i] if results["distances"] else 0.8
                            matched.append((project, score))
                            break
                
                return matched
            
            # Fallback to in-memory search
            return self._search_projects_memory(query_embedding, n_results)
            
        except Exception as e:
            logger.error(f"Project search failed: {e}")
            return []
    
    def _search_projects_memory(
        self,
        query_embedding: List[float],
        n_results: int,
    ) -> List[Tuple[Project, float]]:
        """Search projects in memory."""
        import numpy as np
        
        if not self._projects:
            return []
        
        scores = []
        for project, embedding in self._projects:
            # Cosine similarity
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            scores.append((project, float(similarity)))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n_results]
    
    # =========================================================================
    # Experience Management
    # =========================================================================
    
    def add_experience(self, experience: WorkExperience) -> Optional[str]:
        """Add work experience to the RAG system."""
        if not self._embedder:
            return None
        
        try:
            text = experience.get_searchable_text()
            embedding = self._embed(text)
            
            if self._experience_collection:
                self._experience_collection.add(
                    ids=[experience.id],
                    embeddings=[embedding],
                    metadatas=[{
                        "company": experience.company,
                        "role": experience.role,
                        "technologies": ",".join(experience.technologies),
                    }],
                    documents=[text]
                )
            
            self._experience.append((experience, embedding))
            return experience.id
            
        except Exception as e:
            logger.error(f"Failed to add experience: {e}")
            return None
    
    def search_experience(
        self,
        query: str,
        n_results: int = 3,
    ) -> List[Tuple[WorkExperience, float]]:
        """Search for relevant work experience."""
        if not self._embedder:
            return []
        
        try:
            query_embedding = self._embed(query)
            
            if self._experience_collection and self._experience_collection.count() > 0:
                results = self._experience_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, self._experience_collection.count()),
                )
                
                matched = []
                for i, doc_id in enumerate(results["ids"][0]):
                    for exp, _ in self._experience:
                        if exp.id == doc_id:
                            score = 1 - results["distances"][0][i] if results["distances"] else 0.8
                            matched.append((exp, score))
                            break
                
                return matched
            
            # Memory fallback
            return self._search_experience_memory(query_embedding, n_results)
            
        except Exception as e:
            logger.error(f"Experience search failed: {e}")
            return []
    
    def _search_experience_memory(
        self,
        query_embedding: List[float],
        n_results: int,
    ) -> List[Tuple[WorkExperience, float]]:
        """Search experience in memory."""
        import numpy as np
        
        if not self._experience:
            return []
        
        scores = []
        for exp, embedding in self._experience:
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            scores.append((exp, float(similarity)))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n_results]
    
    # =========================================================================
    # Skills Management
    # =========================================================================
    
    def add_skill(self, skill: Skill) -> str:
        """Add a skill to the system."""
        self._skills.append(skill)
        return skill.id
    
    def get_skills_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get skills by category."""
        return [s for s in self._skills if s.category == category]
    
    def get_skills_for_keywords(self, keywords: List[str]) -> List[Skill]:
        """Get skills that match given keywords."""
        matched = []
        keywords_lower = [k.lower() for k in keywords]
        
        for skill in self._skills:
            skill_text = f"{skill.name} {' '.join(skill.keywords)}".lower()
            if any(kw in skill_text for kw in keywords_lower):
                matched.append(skill)
        
        return matched
    
    def rank_skills_for_job(
        self,
        job_keywords: List[str],
    ) -> List[Tuple[Skill, int]]:
        """Rank skills by relevance to job keywords."""
        ranked = []
        keywords_lower = [k.lower() for k in job_keywords]
        
        for skill in self._skills:
            # Count keyword matches
            skill_text = f"{skill.name} {' '.join(skill.keywords)}".lower()
            matches = sum(1 for kw in keywords_lower if kw in skill_text)
            
            if matches > 0:
                ranked.append((skill, matches))
        
        # Sort by match count
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked
    
    # =========================================================================
    # Story Management (from scholarship essays)
    # =========================================================================
    
    def add_story(self, story_id: str, story_text: str) -> Optional[str]:
        """Add a story/anecdote for cover letters."""
        if not self._embedder:
            return None
        
        try:
            embedding = self._embed(story_text)
            
            if self._stories_collection:
                self._stories_collection.add(
                    ids=[story_id],
                    embeddings=[embedding],
                    documents=[story_text]
                )
            
            self._stories.append((story_id, story_text, embedding))
            return story_id
            
        except Exception as e:
            logger.error(f"Failed to add story: {e}")
            return None
    
    def search_stories(
        self,
        query: str,
        n_results: int = 3,
    ) -> List[Tuple[str, str, float]]:
        """Search for relevant stories."""
        if not self._embedder:
            return []
        
        try:
            query_embedding = self._embed(query)
            
            if self._stories_collection and self._stories_collection.count() > 0:
                results = self._stories_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(n_results, self._stories_collection.count()),
                )
                
                matched = []
                for i, doc_id in enumerate(results["ids"][0]):
                    text = results["documents"][0][i] if results["documents"] else ""
                    score = 1 - results["distances"][0][i] if results["distances"] else 0.8
                    matched.append((doc_id, text, score))
                
                return matched
            
            # Memory fallback
            return self._search_stories_memory(query_embedding, n_results)
            
        except Exception as e:
            logger.error(f"Story search failed: {e}")
            return []
    
    def _search_stories_memory(
        self,
        query_embedding: List[float],
        n_results: int,
    ) -> List[Tuple[str, str, float]]:
        """Search stories in memory."""
        import numpy as np
        
        if not self._stories:
            return []
        
        scores = []
        for story_id, text, embedding in self._stories:
            similarity = np.dot(query_embedding, embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(embedding)
            )
            scores.append((story_id, text, float(similarity)))
        
        scores.sort(key=lambda x: x[2], reverse=True)
        return scores[:n_results]
    
    # =========================================================================
    # Combined Retrieval
    # =========================================================================
    
    def retrieve_for_job(
        self,
        job_description: str,
        job_requirements: List[str],
        n_projects: int = 4,
        n_experience: int = 3,
        n_stories: int = 2,
    ) -> ResumeRAGContext:
        """
        Retrieve all relevant content for a job application.
        
        Args:
            job_description: Full job description text
            job_requirements: List of requirements
            n_projects: Number of projects to retrieve
            n_experience: Number of experiences to retrieve
            n_stories: Number of stories to retrieve
            
        Returns:
            ResumeRAGContext with all matched content
        """
        context = ResumeRAGContext()
        
        # Extract keywords
        context.job_keywords = self._extract_keywords(
            f"{job_description} {' '.join(job_requirements)}"
        )
        
        # Build query from job info
        query = f"{job_description[:500]} {' '.join(job_requirements[:5])}"
        
        # Search projects
        context.matched_projects = self.search_projects(query, n_projects)
        
        # Search experience
        context.matched_experience = self.search_experience(query, n_experience)
        
        # Get matching skills
        context.matched_skills = self.get_skills_for_keywords(context.job_keywords)
        
        # Search stories
        story_results = self.search_stories(query, n_stories)
        context.matched_stories = [(text, score) for _, text, score in story_results]
        
        # Find missing keywords
        covered_keywords = set()
        for project, _ in context.matched_projects:
            covered_keywords.update(t.lower() for t in project.technologies)
            covered_keywords.update(s.lower() for s in project.skills_demonstrated)
        
        for skill in context.matched_skills:
            covered_keywords.add(skill.name.lower())
            covered_keywords.update(k.lower() for k in skill.keywords)
        
        context.missing_keywords = [
            kw for kw in context.job_keywords
            if kw.lower() not in covered_keywords
        ]
        
        logger.info(
            f"RAG retrieved: {len(context.matched_projects)} projects, "
            f"{len(context.matched_experience)} experiences, "
            f"{len(context.matched_skills)} skills, "
            f"{len(context.matched_stories)} stories"
        )
        
        return context
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        # Common tech keywords to look for
        tech_keywords = [
            "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
            "sql", "nosql", "mongodb", "postgresql", "mysql",
            "machine learning", "ml", "deep learning", "ai", "artificial intelligence",
            "data science", "data analysis", "analytics", "statistics",
            "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
            "pandas", "numpy", "scipy", "matplotlib",
            "spark", "hadoop", "kafka", "airflow",
            "aws", "gcp", "azure", "cloud",
            "docker", "kubernetes", "k8s", "ci/cd",
            "git", "github", "gitlab",
            "react", "angular", "vue", "node.js",
            "api", "rest", "graphql",
            "agile", "scrum",
            "nlp", "computer vision", "cv",
            "regression", "classification", "clustering",
        ]
        
        found = []
        text_lower = text.lower()
        
        for keyword in tech_keywords:
            if keyword in text_lower:
                found.append(keyword)
        
        return found
    
    # =========================================================================
    # Stats and Management
    # =========================================================================
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about stored content."""
        # Prefer ChromaDB counts if available, fallback to in-memory
        projects_count = 0
        experience_count = 0
        stories_count = 0
        
        if self._projects_collection:
            projects_count = self._projects_collection.count()
        else:
            projects_count = len(self._projects)
            
        if self._experience_collection:
            experience_count = self._experience_collection.count()
        else:
            experience_count = len(self._experience)
            
        if self._stories_collection:
            stories_count = self._stories_collection.count()
        else:
            stories_count = len(self._stories)
        
        stats = {
            "projects": projects_count,
            "experience": experience_count,
            "skills": len(self._skills),
            "stories": stories_count,
        }
        
        return stats
    
    def clear_all(self):
        """Clear all stored content."""
        self._projects.clear()
        self._experience.clear()
        self._skills.clear()
        self._stories.clear()
        
        if self._chroma_client:
            try:
                self._chroma_client.delete_collection("resume_projects")
                self._chroma_client.delete_collection("resume_experience")
                self._chroma_client.delete_collection("resume_stories")
                self._initialize()
            except Exception as e:
                logger.error(f"Failed to clear ChromaDB: {e}")
