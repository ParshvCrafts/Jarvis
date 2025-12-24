"""
Supabase Client for JARVIS Scholarship Module.

Handles:
- Connection to Supabase
- Vector operations with pgvector
- CRUD operations for essays, profiles, scholarships
- Vector similarity search
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from loguru import logger

# Try importing supabase
try:
    from supabase import create_client, Client
    SUPABASE_INSTALLED = True
except ImportError:
    SUPABASE_INSTALLED = False
    logger.warning("supabase-py not installed. Run: pip install supabase")

from .models import (
    PastEssay,
    PersonalStatement,
    PersonalProfile,
    Scholarship,
    Application,
    PromptTemplate,
    GeneratedEssay,
    EssayOutcome,
)


class SupabaseClient:
    """
    Supabase client for scholarship RAG system.
    
    Manages vector storage and retrieval for:
    - Past essays
    - Personal statements
    - Personal profile sections
    - Prompt templates
    """
    
    # Table names
    TABLE_PAST_ESSAYS = "past_essays"
    TABLE_PERSONAL_STATEMENT = "personal_statement"
    TABLE_PERSONAL_PROFILE = "personal_profile"
    TABLE_PROMPT_TEMPLATES = "prompt_templates"
    TABLE_SCHOLARSHIPS = "scholarships"
    TABLE_APPLICATIONS = "applications"
    TABLE_GENERATED_ESSAYS = "generated_essays"
    
    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
    ):
        """
        Initialize Supabase client.
        
        Args:
            url: Supabase project URL (or from SUPABASE_URL env var)
            key: Supabase anon key (or from SUPABASE_KEY env var)
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_KEY")
        self.client: Optional[Client] = None
        self._connected = False
        
        if not SUPABASE_INSTALLED:
            logger.error("Supabase client not available - package not installed")
            return
        
        if not self.url or not self.key:
            logger.warning("Supabase credentials not configured")
            return
        
        try:
            self.client = create_client(self.url, self.key)
            self._connected = True
            logger.info("Supabase client connected")
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Supabase."""
        return self._connected and self.client is not None
    
    # =========================================================================
    # Past Essays Operations
    # =========================================================================
    
    async def add_past_essay(
        self,
        essay: PastEssay,
        embedding: List[float],
    ) -> Optional[str]:
        """
        Add a past essay with its embedding.
        
        Args:
            essay: PastEssay object
            embedding: Vector embedding of the essay
            
        Returns:
            Essay ID if successful
        """
        if not self.is_connected:
            logger.error("Not connected to Supabase")
            return None
        
        try:
            data = essay.to_dict()
            data["embedding"] = embedding
            
            result = self.client.table(self.TABLE_PAST_ESSAYS).insert(data).execute()
            
            if result.data:
                logger.info(f"Added past essay: {essay.scholarship_name}")
                return result.data[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to add past essay: {e}")
            return None
    
    async def search_similar_essays(
        self,
        query_embedding: List[float],
        limit: int = 5,
        outcome_filter: Optional[EssayOutcome] = None,
        similarity_threshold: float = 0.7,
    ) -> List[Tuple[PastEssay, float]]:
        """
        Search for similar past essays using vector similarity.
        
        Args:
            query_embedding: Embedding of the query/question
            limit: Maximum results to return
            outcome_filter: Filter by outcome (e.g., only winning essays)
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of (essay, similarity_score) tuples
        """
        if not self.is_connected:
            logger.error("Not connected to Supabase")
            return []
        
        try:
            # Use Supabase RPC for vector similarity search
            params = {
                "query_embedding": query_embedding,
                "match_threshold": similarity_threshold,
                "match_count": limit,
            }
            
            if outcome_filter:
                params["outcome_filter"] = outcome_filter.value
            
            result = self.client.rpc(
                "match_past_essays",
                params
            ).execute()
            
            essays = []
            for row in result.data or []:
                essay = PastEssay.from_dict(row)
                similarity = row.get("similarity", 0.0)
                essays.append((essay, similarity))
            
            return essays
        except Exception as e:
            logger.error(f"Failed to search similar essays: {e}")
            # Fallback to basic query if RPC not available
            return await self._fallback_essay_search(query_embedding, limit)
    
    async def _fallback_essay_search(
        self,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Tuple[PastEssay, float]]:
        """Fallback essay search without vector similarity."""
        try:
            result = self.client.table(self.TABLE_PAST_ESSAYS)\
                .select("*")\
                .eq("outcome", "won")\
                .limit(limit)\
                .execute()
            
            return [(PastEssay.from_dict(row), 0.8) for row in result.data or []]
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []
    
    async def get_winning_essays(self, limit: int = 10) -> List[PastEssay]:
        """Get all winning essays."""
        if not self.is_connected:
            return []
        
        try:
            result = self.client.table(self.TABLE_PAST_ESSAYS)\
                .select("*")\
                .eq("outcome", "won")\
                .limit(limit)\
                .execute()
            
            return [PastEssay.from_dict(row) for row in result.data or []]
        except Exception as e:
            logger.error(f"Failed to get winning essays: {e}")
            return []
    
    async def get_all_past_essays(self) -> List[PastEssay]:
        """Get all past essays."""
        if not self.is_connected:
            return []
        
        try:
            result = self.client.table(self.TABLE_PAST_ESSAYS)\
                .select("*")\
                .execute()
            
            return [PastEssay.from_dict(row) for row in result.data or []]
        except Exception as e:
            logger.error(f"Failed to get all essays: {e}")
            return []
    
    async def update_essay_outcome(
        self,
        essay_id: str,
        outcome: EssayOutcome,
    ) -> bool:
        """Update the outcome of an essay."""
        if not self.is_connected:
            return False
        
        try:
            self.client.table(self.TABLE_PAST_ESSAYS)\
                .update({"outcome": outcome.value})\
                .eq("id", essay_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update essay outcome: {e}")
            return False
    
    # =========================================================================
    # Personal Statement Operations
    # =========================================================================
    
    async def add_personal_statement_section(
        self,
        section: PersonalStatement,
        embedding: List[float],
    ) -> Optional[str]:
        """Add a personal statement section."""
        if not self.is_connected:
            return None
        
        try:
            data = section.to_dict()
            data["embedding"] = embedding
            
            result = self.client.table(self.TABLE_PERSONAL_STATEMENT)\
                .insert(data)\
                .execute()
            
            if result.data:
                return result.data[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to add personal statement section: {e}")
            return None
    
    async def search_personal_statement(
        self,
        query_embedding: List[float],
        limit: int = 3,
    ) -> List[Tuple[PersonalStatement, float]]:
        """Search personal statement sections by similarity."""
        if not self.is_connected:
            return []
        
        try:
            result = self.client.rpc(
                "match_personal_statement",
                {
                    "query_embedding": query_embedding,
                    "match_count": limit,
                }
            ).execute()
            
            sections = []
            for row in result.data or []:
                section = PersonalStatement(
                    id=row.get("id"),
                    version=row.get("version", 1),
                    section_name=row.get("section_name", ""),
                    content=row.get("content", ""),
                    themes=row.get("themes", []),
                )
                similarity = row.get("similarity", 0.0)
                sections.append((section, similarity))
            
            return sections
        except Exception as e:
            logger.error(f"Failed to search personal statement: {e}")
            return []
    
    # =========================================================================
    # Personal Profile Operations
    # =========================================================================
    
    async def add_profile_section(
        self,
        profile: PersonalProfile,
        embedding: List[float],
    ) -> Optional[str]:
        """Add a personal profile section."""
        if not self.is_connected:
            return None
        
        try:
            data = profile.to_dict()
            data["embedding"] = embedding
            
            result = self.client.table(self.TABLE_PERSONAL_PROFILE)\
                .insert(data)\
                .execute()
            
            if result.data:
                return result.data[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to add profile section: {e}")
            return None
    
    async def search_profile(
        self,
        query_embedding: List[float],
        limit: int = 5,
    ) -> List[Tuple[PersonalProfile, float]]:
        """Search profile sections by similarity."""
        if not self.is_connected:
            return []
        
        try:
            result = self.client.rpc(
                "match_personal_profile",
                {
                    "query_embedding": query_embedding,
                    "match_count": limit,
                }
            ).execute()
            
            profiles = []
            for row in result.data or []:
                profile = PersonalProfile(
                    id=row.get("id"),
                    section=row.get("section", ""),
                    content=row.get("content", ""),
                )
                similarity = row.get("similarity", 0.0)
                profiles.append((profile, similarity))
            
            return profiles
        except Exception as e:
            logger.error(f"Failed to search profile: {e}")
            return []
    
    # =========================================================================
    # Prompt Templates Operations
    # =========================================================================
    
    async def add_prompt_template(self, template: PromptTemplate) -> Optional[str]:
        """Add a prompt template."""
        if not self.is_connected:
            return None
        
        try:
            result = self.client.table(self.TABLE_PROMPT_TEMPLATES)\
                .insert(template.to_dict())\
                .execute()
            
            if result.data:
                return result.data[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to add prompt template: {e}")
            return None
    
    async def get_prompt_template(
        self,
        name: Optional[str] = None,
        category: Optional[str] = None,
    ) -> Optional[PromptTemplate]:
        """Get a prompt template by name or category."""
        if not self.is_connected:
            return None
        
        try:
            query = self.client.table(self.TABLE_PROMPT_TEMPLATES).select("*")
            
            if name:
                query = query.eq("name", name)
            if category:
                query = query.eq("category", category)
            
            result = query.limit(1).execute()
            
            if result.data:
                data = result.data[0]
                return PromptTemplate(
                    id=data.get("id"),
                    name=data.get("name", ""),
                    category=data.get("category", ""),
                    prompt_text=data.get("prompt_text", ""),
                    variables=data.get("variables", []),
                    effectiveness_score=data.get("effectiveness_score", 0.0),
                    usage_count=data.get("usage_count", 0),
                )
            return None
        except Exception as e:
            logger.error(f"Failed to get prompt template: {e}")
            return None
    
    async def increment_template_usage(self, template_id: str) -> bool:
        """Increment usage count for a template."""
        if not self.is_connected:
            return False
        
        try:
            # Get current count
            result = self.client.table(self.TABLE_PROMPT_TEMPLATES)\
                .select("usage_count")\
                .eq("id", template_id)\
                .single()\
                .execute()
            
            current = result.data.get("usage_count", 0) if result.data else 0
            
            # Update
            self.client.table(self.TABLE_PROMPT_TEMPLATES)\
                .update({"usage_count": current + 1})\
                .eq("id", template_id)\
                .execute()
            
            return True
        except Exception as e:
            logger.error(f"Failed to increment template usage: {e}")
            return False
    
    # =========================================================================
    # Scholarship Operations
    # =========================================================================
    
    async def save_scholarship(self, scholarship: Scholarship) -> Optional[str]:
        """Save a scholarship to the database."""
        if not self.is_connected:
            return None
        
        try:
            result = self.client.table(self.TABLE_SCHOLARSHIPS)\
                .upsert(scholarship.to_dict())\
                .execute()
            
            if result.data:
                return result.data[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to save scholarship: {e}")
            return None
    
    async def get_scholarships(
        self,
        source: Optional[str] = None,
        min_match: float = 0.0,
    ) -> List[Scholarship]:
        """Get scholarships from database."""
        if not self.is_connected:
            return []
        
        try:
            query = self.client.table(self.TABLE_SCHOLARSHIPS).select("*")
            
            if source:
                query = query.eq("source", source)
            if min_match > 0:
                query = query.gte("match_percentage", min_match)
            
            result = query.execute()
            
            return [Scholarship.from_dict(row) for row in result.data or []]
        except Exception as e:
            logger.error(f"Failed to get scholarships: {e}")
            return []
    
    # =========================================================================
    # Application Tracking Operations
    # =========================================================================
    
    async def save_application(self, application: Application) -> Optional[str]:
        """Save an application."""
        if not self.is_connected:
            return None
        
        try:
            result = self.client.table(self.TABLE_APPLICATIONS)\
                .upsert(application.to_dict())\
                .execute()
            
            if result.data:
                return result.data[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to save application: {e}")
            return None
    
    async def get_applications(
        self,
        status: Optional[str] = None,
    ) -> List[Application]:
        """Get applications."""
        if not self.is_connected:
            return []
        
        try:
            query = self.client.table(self.TABLE_APPLICATIONS).select("*")
            
            if status:
                query = query.eq("status", status)
            
            result = query.execute()
            
            return [Application.from_dict(row) for row in result.data or []]
        except Exception as e:
            logger.error(f"Failed to get applications: {e}")
            return []
    
    async def update_application_status(
        self,
        application_id: str,
        status: str,
    ) -> bool:
        """Update application status."""
        if not self.is_connected:
            return False
        
        try:
            self.client.table(self.TABLE_APPLICATIONS)\
                .update({"status": status})\
                .eq("id", application_id)\
                .execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update application status: {e}")
            return False
    
    # =========================================================================
    # Generated Essays Operations
    # =========================================================================
    
    async def save_generated_essay(self, essay: GeneratedEssay) -> Optional[str]:
        """Save a generated essay."""
        if not self.is_connected:
            return None
        
        try:
            result = self.client.table(self.TABLE_GENERATED_ESSAYS)\
                .insert(essay.to_dict())\
                .execute()
            
            if result.data:
                return result.data[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Failed to save generated essay: {e}")
            return None
    
    # =========================================================================
    # Database Setup
    # =========================================================================
    
    def get_setup_sql(self) -> str:
        """
        Get SQL to set up the database tables.
        
        Run this in Supabase SQL Editor to create tables.
        """
        return """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Past Essays table
CREATE TABLE IF NOT EXISTS past_essays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_name TEXT NOT NULL,
    question TEXT NOT NULL,
    essay_text TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    outcome TEXT DEFAULT 'pending',
    themes TEXT[] DEFAULT '{}',
    key_points TEXT[] DEFAULT '{}',
    tone TEXT DEFAULT '',
    date_written TIMESTAMPTZ DEFAULT NOW(),
    date_submitted TIMESTAMPTZ,
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Personal Statement table
CREATE TABLE IF NOT EXISTS personal_statement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version INTEGER DEFAULT 1,
    section_name TEXT NOT NULL,
    content TEXT NOT NULL,
    themes TEXT[] DEFAULT '{}',
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Personal Profile table
CREATE TABLE IF NOT EXISTS personal_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prompt Templates table
CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    variables TEXT[] DEFAULT '{}',
    effectiveness_score FLOAT DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Scholarships table
CREATE TABLE IF NOT EXISTS scholarships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    provider TEXT,
    description TEXT,
    amount FLOAT DEFAULT 0,
    amount_text TEXT,
    is_renewable BOOLEAN DEFAULT FALSE,
    deadline DATE,
    open_date DATE,
    eligibility_requirements JSONB DEFAULT '{}',
    required_criteria TEXT[] DEFAULT '{}',
    preferred_criteria TEXT[] DEFAULT '{}',
    questions JSONB DEFAULT '[]',
    required_materials TEXT[] DEFAULT '{}',
    url TEXT,
    application_url TEXT,
    source TEXT,
    match_percentage FLOAT DEFAULT 0,
    match_details JSONB DEFAULT '{}',
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

-- Applications table
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_id UUID REFERENCES scholarships(id),
    scholarship_name TEXT NOT NULL,
    status TEXT DEFAULT 'discovered',
    deadline DATE,
    started_at TIMESTAMPTZ,
    submitted_at TIMESTAMPTZ,
    result_at TIMESTAMPTZ,
    essay_ids TEXT[] DEFAULT '{}',
    essays_complete BOOLEAN DEFAULT FALSE,
    google_doc_url TEXT,
    google_doc_id TEXT,
    notes TEXT DEFAULT '',
    award_amount FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generated Essays table
CREATE TABLE IF NOT EXISTS generated_essays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_id TEXT,
    scholarship_name TEXT,
    question_id TEXT,
    question_text TEXT,
    essay_text TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    target_word_count INTEGER DEFAULT 0,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    llm_used TEXT,
    prompt_template TEXT,
    similar_essays_used TEXT[] DEFAULT '{}',
    profile_sections_used TEXT[] DEFAULT '{}',
    revision_count INTEGER DEFAULT 0,
    quality_score FLOAT
);

-- Create indexes for vector similarity search
CREATE INDEX IF NOT EXISTS past_essays_embedding_idx ON past_essays 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS personal_statement_embedding_idx ON personal_statement 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS personal_profile_embedding_idx ON personal_profile 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Function to match past essays
CREATE OR REPLACE FUNCTION match_past_essays(
    query_embedding vector(384),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5,
    outcome_filter TEXT DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    scholarship_name TEXT,
    question TEXT,
    essay_text TEXT,
    word_count INTEGER,
    outcome TEXT,
    themes TEXT[],
    key_points TEXT[],
    tone TEXT,
    date_written TIMESTAMPTZ,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pe.id,
        pe.scholarship_name,
        pe.question,
        pe.essay_text,
        pe.word_count,
        pe.outcome,
        pe.themes,
        pe.key_points,
        pe.tone,
        pe.date_written,
        1 - (pe.embedding <=> query_embedding) AS similarity
    FROM past_essays pe
    WHERE 
        (outcome_filter IS NULL OR pe.outcome = outcome_filter)
        AND 1 - (pe.embedding <=> query_embedding) > match_threshold
    ORDER BY pe.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to match personal statement
CREATE OR REPLACE FUNCTION match_personal_statement(
    query_embedding vector(384),
    match_count INT DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    version INTEGER,
    section_name TEXT,
    content TEXT,
    themes TEXT[],
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ps.id,
        ps.version,
        ps.section_name,
        ps.content,
        ps.themes,
        1 - (ps.embedding <=> query_embedding) AS similarity
    FROM personal_statement ps
    ORDER BY ps.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to match personal profile
CREATE OR REPLACE FUNCTION match_personal_profile(
    query_embedding vector(384),
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    section TEXT,
    content TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pp.id,
        pp.section,
        pp.content,
        1 - (pp.embedding <=> query_embedding) AS similarity
    FROM personal_profile pp
    ORDER BY pp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""
