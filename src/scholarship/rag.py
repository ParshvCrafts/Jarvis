"""
RAG (Retrieval Augmented Generation) System for JARVIS Scholarship Module.

Retrieves relevant context from:
- Past winning essays
- Personal statement sections
- Personal profile (achievements, stories, goals)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .models import PastEssay, PersonalStatement, PersonalProfile, EssayOutcome
from .embeddings import EmbeddingGenerator, get_default_embedder
from .local_rag import LocalRAGStore, CHROMADB_AVAILABLE


@dataclass
class RAGContext:
    """Context retrieved for essay generation."""
    # Similar past essays
    similar_essays: List[Tuple[PastEssay, float]] = field(default_factory=list)
    
    # Relevant personal statement sections
    personal_statement_sections: List[Tuple[PersonalStatement, float]] = field(default_factory=list)
    
    # Relevant profile sections (achievements, stories)
    profile_sections: List[Tuple[PersonalProfile, float]] = field(default_factory=list)
    
    # Query used
    query: str = ""
    
    # Themes identified
    themes: List[str] = field(default_factory=list)
    
    def get_essays_text(self) -> str:
        """Get formatted text of similar essays."""
        if not self.similar_essays:
            return "No similar past essays found."
        
        lines = []
        for i, (essay, score) in enumerate(self.similar_essays, 1):
            outcome_emoji = "🏆" if essay.outcome == EssayOutcome.WON else "📝"
            lines.append(f"--- Essay {i} ({outcome_emoji} {essay.outcome.value}, {score:.0%} match) ---")
            lines.append(f"Scholarship: {essay.scholarship_name}")
            lines.append(f"Question: {essay.question}")
            lines.append(f"Essay ({essay.word_count} words):")
            lines.append(essay.essay_text)
            lines.append("")
        
        return "\n".join(lines)
    
    def get_personal_statement_text(self) -> str:
        """Get formatted personal statement sections."""
        if not self.personal_statement_sections:
            return "No personal statement sections found."
        
        lines = []
        for section, score in self.personal_statement_sections:
            lines.append(f"--- {section.section_name} ({score:.0%} relevant) ---")
            lines.append(section.content)
            lines.append("")
        
        return "\n".join(lines)
    
    def get_profile_text(self) -> str:
        """Get formatted profile sections."""
        if not self.profile_sections:
            return "No profile sections found."
        
        lines = []
        for profile, score in self.profile_sections:
            lines.append(f"--- {profile.section} ({score:.0%} relevant) ---")
            lines.append(profile.content)
            lines.append("")
        
        return "\n".join(lines)
    
    def to_prompt_context(self) -> Dict[str, str]:
        """Convert to dictionary for prompt templates."""
        return {
            "similar_essays": self.get_essays_text(),
            "personal_statement": self.get_personal_statement_text(),
            "profile": self.get_profile_text(),
            "themes": ", ".join(self.themes) if self.themes else "general",
        }


class ScholarshipRAG:
    """
    RAG system for scholarship essay generation.
    
    Retrieves relevant context from past essays and personal information
    to help generate personalized, high-quality essays.
    """
    
    def __init__(
        self,
        supabase_client=None,
        embedder: Optional[EmbeddingGenerator] = None,
        use_local_fallback: bool = True,
        local_store: Optional[LocalRAGStore] = None,
    ):
        """
        Initialize RAG system.
        
        Args:
            supabase_client: SupabaseClient for vector search
            embedder: Embedding generator
            use_local_fallback: Use local storage if Supabase unavailable
            local_store: LocalRAGStore for persistent local storage
        """
        self.supabase = supabase_client
        self.embedder = embedder
        self.use_local_fallback = use_local_fallback
        
        # Persistent local storage (ChromaDB)
        self._local_store = local_store or LocalRAGStore()
        
        # In-memory fallback (used when ChromaDB unavailable)
        self._local_essays: List[Tuple[PastEssay, List[float]]] = []
        self._local_statements: List[Tuple[PersonalStatement, List[float]]] = []
        self._local_profiles: List[Tuple[PersonalProfile, List[float]]] = []
        
        # Initialize embedder if not provided
        if self.embedder is None:
            try:
                self.embedder = get_default_embedder()
            except ImportError as e:
                logger.warning(f"Could not initialize embedder: {e}")
    
    def _extract_themes(self, text: str) -> List[str]:
        """Extract themes/keywords from text."""
        # Common scholarship essay themes
        theme_keywords = {
            "leadership": ["lead", "leader", "leadership", "captain", "president", "founded"],
            "community": ["community", "volunteer", "service", "help", "impact", "give back"],
            "academic": ["research", "study", "academic", "gpa", "honors", "scholar"],
            "diversity": ["diverse", "diversity", "culture", "background", "identity"],
            "challenge": ["challenge", "overcome", "obstacle", "struggle", "adversity"],
            "growth": ["grow", "growth", "learn", "develop", "improve", "change"],
            "passion": ["passion", "passionate", "love", "dedicate", "commit"],
            "innovation": ["innovate", "create", "invent", "new", "solution", "technology"],
            "career": ["career", "goal", "future", "aspire", "dream", "profession"],
            "family": ["family", "parent", "mother", "father", "sibling", "heritage"],
        }
        
        text_lower = text.lower()
        found_themes = []
        
        for theme, keywords in theme_keywords.items():
            if any(kw in text_lower for kw in keywords):
                found_themes.append(theme)
        
        return found_themes
    
    async def retrieve(
        self,
        question: str,
        scholarship_name: Optional[str] = None,
        num_essays: int = 5,
        num_statements: int = 3,
        num_profiles: int = 5,
        prefer_winners: bool = True,
    ) -> RAGContext:
        """
        Retrieve relevant context for a scholarship question.
        
        Args:
            question: The scholarship essay question
            scholarship_name: Name of the scholarship (for context)
            num_essays: Number of similar essays to retrieve
            num_statements: Number of personal statement sections
            num_profiles: Number of profile sections
            prefer_winners: Prioritize winning essays
            
        Returns:
            RAGContext with all retrieved information
        """
        context = RAGContext(query=question)
        
        # Extract themes from question
        context.themes = self._extract_themes(question)
        
        if not self.embedder:
            logger.warning("No embedder available for RAG")
            return context
        
        # Generate query embedding
        query_text = f"{question} {scholarship_name or ''}"
        query_embedding = self.embedder.embed_query(query_text)
        
        # Retrieve from Supabase or local storage
        if self.supabase and self.supabase.is_connected:
            context = await self._retrieve_from_supabase(
                query_embedding,
                context,
                num_essays,
                num_statements,
                num_profiles,
                prefer_winners,
            )
        elif self.use_local_fallback:
            context = self._retrieve_from_local(
                query_embedding,
                context,
                num_essays,
                num_statements,
                num_profiles,
            )
        
        logger.info(
            f"RAG retrieved: {len(context.similar_essays)} essays, "
            f"{len(context.personal_statement_sections)} PS sections, "
            f"{len(context.profile_sections)} profile sections"
        )
        
        return context
    
    async def _retrieve_from_supabase(
        self,
        query_embedding: List[float],
        context: RAGContext,
        num_essays: int,
        num_statements: int,
        num_profiles: int,
        prefer_winners: bool,
    ) -> RAGContext:
        """Retrieve from Supabase vector database."""
        # Search similar essays
        outcome_filter = EssayOutcome.WON if prefer_winners else None
        context.similar_essays = await self.supabase.search_similar_essays(
            query_embedding,
            limit=num_essays,
            outcome_filter=outcome_filter,
        )
        
        # If not enough winners, get more without filter
        if prefer_winners and len(context.similar_essays) < num_essays:
            more_essays = await self.supabase.search_similar_essays(
                query_embedding,
                limit=num_essays - len(context.similar_essays),
            )
            # Add non-duplicate essays
            existing_ids = {e[0].id for e in context.similar_essays}
            for essay, score in more_essays:
                if essay.id not in existing_ids:
                    context.similar_essays.append((essay, score))
        
        # Search personal statement
        context.personal_statement_sections = await self.supabase.search_personal_statement(
            query_embedding,
            limit=num_statements,
        )
        
        # Search profile
        context.profile_sections = await self.supabase.search_profile(
            query_embedding,
            limit=num_profiles,
        )
        
        return context
    
    def _retrieve_from_local(
        self,
        query_embedding: List[float],
        context: RAGContext,
        num_essays: int,
        num_statements: int,
        num_profiles: int,
    ) -> RAGContext:
        """Retrieve from local storage."""
        # Search essays
        if self._local_essays:
            essay_scores = [
                (essay, self.embedder.similarity(query_embedding, emb))
                for essay, emb in self._local_essays
            ]
            essay_scores.sort(key=lambda x: x[1], reverse=True)
            context.similar_essays = essay_scores[:num_essays]
        
        # Search statements
        if self._local_statements:
            stmt_scores = [
                (stmt, self.embedder.similarity(query_embedding, emb))
                for stmt, emb in self._local_statements
            ]
            stmt_scores.sort(key=lambda x: x[1], reverse=True)
            context.personal_statement_sections = stmt_scores[:num_statements]
        
        # Search profiles
        if self._local_profiles:
            profile_scores = [
                (profile, self.embedder.similarity(query_embedding, emb))
                for profile, emb in self._local_profiles
            ]
            profile_scores.sort(key=lambda x: x[1], reverse=True)
            context.profile_sections = profile_scores[:num_profiles]
        
        return context
    
    # =========================================================================
    # Local Storage Methods (Fallback)
    # =========================================================================
    
    def add_essay_local(self, essay: PastEssay) -> bool:
        """Add essay to local storage."""
        if not self.embedder:
            return False
        
        try:
            # Generate embedding from question + essay
            text = f"{essay.question}\n{essay.essay_text}"
            embedding = self.embedder.embed(text)
            self._local_essays.append((essay, embedding))
            return True
        except Exception as e:
            logger.error(f"Failed to add essay locally: {e}")
            return False
    
    def add_statement_local(self, statement: PersonalStatement) -> bool:
        """Add personal statement section to local storage."""
        if not self.embedder:
            return False
        
        try:
            embedding = self.embedder.embed(statement.content)
            self._local_statements.append((statement, embedding))
            return True
        except Exception as e:
            logger.error(f"Failed to add statement locally: {e}")
            return False
    
    def add_profile_local(self, profile: PersonalProfile) -> bool:
        """Add profile section to local storage."""
        if not self.embedder:
            return False
        
        try:
            embedding = self.embedder.embed(profile.content)
            self._local_profiles.append((profile, embedding))
            return True
        except Exception as e:
            logger.error(f"Failed to add profile locally: {e}")
            return False
    
    # =========================================================================
    # Supabase Storage Methods
    # =========================================================================
    
    async def add_essay(self, essay: PastEssay) -> Optional[str]:
        """Add essay to Supabase or local fallback."""
        if not self.embedder:
            logger.error("No embedder available")
            return None
        
        # Generate embedding first
        try:
            text = f"{essay.question}\n{essay.essay_text}"
            embedding = self.embedder.embed(text)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None
        
        # Try Supabase first
        if self.supabase and self.supabase.is_connected:
            try:
                essay_id = await self.supabase.add_past_essay(essay, embedding)
                if essay_id:
                    # Also add to persistent local for immediate availability
                    if self.use_local_fallback and self._local_store:
                        self._local_store.add_essay(essay, embedding)
                    return essay_id
            except Exception as e:
                logger.warning(f"Supabase add failed, falling back to local: {e}")
        
        # Fall back to persistent local storage (ChromaDB)
        if self.use_local_fallback and self._local_store:
            essay_id = self._local_store.add_essay(essay, embedding)
            if essay_id:
                logger.info(f"Essay stored in ChromaDB: {essay.scholarship_name}")
                return essay_id
        
        # Last resort: in-memory storage
        if self.use_local_fallback:
            self._local_essays.append((essay, embedding))
            logger.info(f"Essay stored in memory: {essay.scholarship_name}")
            return "memory"
        
        return None
    
    async def add_personal_statement(self, statement: PersonalStatement) -> Optional[str]:
        """Add personal statement section to Supabase."""
        if not self.embedder:
            return None
        
        if not self.supabase or not self.supabase.is_connected:
            if self.use_local_fallback:
                return "local" if self.add_statement_local(statement) else None
            return None
        
        try:
            embedding = self.embedder.embed(statement.content)
            stmt_id = await self.supabase.add_personal_statement_section(statement, embedding)
            
            if self.use_local_fallback:
                self._local_statements.append((statement, embedding))
            
            return stmt_id
        except Exception as e:
            logger.error(f"Failed to add statement: {e}")
            return None
    
    async def add_profile_section(self, profile: PersonalProfile) -> Optional[str]:
        """Add profile section to Supabase."""
        if not self.embedder:
            return None
        
        if not self.supabase or not self.supabase.is_connected:
            if self.use_local_fallback:
                return "local" if self.add_profile_local(profile) else None
            return None
        
        try:
            embedding = self.embedder.embed(profile.content)
            profile_id = await self.supabase.add_profile_section(profile, embedding)
            
            if self.use_local_fallback:
                self._local_profiles.append((profile, embedding))
            
            return profile_id
        except Exception as e:
            logger.error(f"Failed to add profile: {e}")
            return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about stored data."""
        # Get ChromaDB stats if available
        if self._local_store:
            chromadb_stats = self._local_store.get_stats()
            return {
                "local_essays": chromadb_stats.get("essays", 0) + len(self._local_essays),
                "local_statements": chromadb_stats.get("statements", 0) + len(self._local_statements),
                "local_profiles": chromadb_stats.get("profiles", 0) + len(self._local_profiles),
            }
        
        return {
            "local_essays": len(self._local_essays),
            "local_statements": len(self._local_statements),
            "local_profiles": len(self._local_profiles),
        }
