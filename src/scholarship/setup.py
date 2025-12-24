"""
Supabase Database Setup for JARVIS Scholarship Module.

Creates and verifies all required tables and functions for:
- Past essays with vector embeddings
- Personal statements
- Personal profiles
- Prompt templates
- Scholarships and applications
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from loguru import logger

# SQL for creating tables
SQL_ENABLE_PGVECTOR = """
CREATE EXTENSION IF NOT EXISTS vector;
"""

SQL_CREATE_PAST_ESSAYS = """
CREATE TABLE IF NOT EXISTS past_essays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_name TEXT NOT NULL,
    question TEXT,
    essay_text TEXT NOT NULL,
    word_count INTEGER,
    outcome TEXT DEFAULT 'pending',
    themes TEXT[],
    date_written TIMESTAMP,
    provider TEXT,
    amount DECIMAL,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS past_essays_embedding_idx 
ON past_essays USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS past_essays_outcome_idx ON past_essays(outcome);
"""

SQL_CREATE_PERSONAL_STATEMENT = """
CREATE TABLE IF NOT EXISTS personal_statement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section_name TEXT NOT NULL,
    content TEXT NOT NULL,
    themes TEXT[],
    embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS personal_statement_embedding_idx 
ON personal_statement USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);
"""

SQL_CREATE_PERSONAL_PROFILE = """
CREATE TABLE IF NOT EXISTS personal_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT,
    embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS personal_profile_embedding_idx 
ON personal_profile USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);
"""

SQL_CREATE_PROMPT_TEMPLATES = """
CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL,
    template TEXT NOT NULL,
    description TEXT,
    variables TEXT[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

SQL_CREATE_SCHOLARSHIPS = """
CREATE TABLE IF NOT EXISTS scholarships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    provider TEXT,
    amount DECIMAL,
    deadline DATE,
    url TEXT,
    description TEXT,
    requirements TEXT,
    eligibility JSONB,
    questions JSONB,
    match_score DECIMAL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
"""

SQL_CREATE_APPLICATIONS = """
CREATE TABLE IF NOT EXISTS applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scholarship_id UUID REFERENCES scholarships(id),
    scholarship_name TEXT NOT NULL,
    status TEXT DEFAULT 'discovered',
    deadline DATE,
    amount DECIMAL,
    google_doc_url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    submitted_at TIMESTAMP,
    result_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS applications_status_idx ON applications(status);
CREATE INDEX IF NOT EXISTS applications_deadline_idx ON applications(deadline);
"""

SQL_CREATE_GENERATED_ESSAYS = """
CREATE TABLE IF NOT EXISTS generated_essays (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES applications(id),
    question_text TEXT,
    essay_text TEXT NOT NULL,
    word_count INTEGER,
    target_word_count INTEGER,
    quality_score DECIMAL,
    rag_sources JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

# Vector search functions
SQL_CREATE_MATCH_ESSAYS_FUNCTION = """
CREATE OR REPLACE FUNCTION match_past_essays(
    query_embedding vector(384),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 5,
    outcome_filter text DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    scholarship_name TEXT,
    question TEXT,
    essay_text TEXT,
    word_count INTEGER,
    outcome TEXT,
    themes TEXT[],
    date_written TIMESTAMP,
    similarity float
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
"""

SQL_CREATE_MATCH_STATEMENT_FUNCTION = """
CREATE OR REPLACE FUNCTION match_personal_statement(
    query_embedding vector(384),
    match_count int DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    section_name TEXT,
    content TEXT,
    themes TEXT[],
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ps.id,
        ps.section_name,
        ps.content,
        ps.themes,
        1 - (ps.embedding <=> query_embedding) AS similarity
    FROM personal_statement ps
    ORDER BY ps.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""

SQL_CREATE_MATCH_PROFILE_FUNCTION = """
CREATE OR REPLACE FUNCTION match_personal_profile(
    query_embedding vector(384),
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    section TEXT,
    content TEXT,
    category TEXT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        pp.id,
        pp.section,
        pp.content,
        pp.category,
        1 - (pp.embedding <=> query_embedding) AS similarity
    FROM personal_profile pp
    ORDER BY pp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
"""


class ScholarshipDatabaseSetup:
    """
    Setup and verify Supabase database for scholarship module.
    
    Handles:
    - Connection testing
    - Table creation
    - Function creation
    - Status reporting
    """
    
    REQUIRED_TABLES = [
        "past_essays",
        "personal_statement", 
        "personal_profile",
        "prompt_templates",
        "scholarships",
        "applications",
        "generated_essays",
    ]
    
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ):
        """Initialize setup with Supabase credentials."""
        self.url = supabase_url or os.getenv("SUPABASE_URL")
        self.key = supabase_key or os.getenv("SUPABASE_KEY")
        self.client = None
        self._connected = False
        self._status = {}
        
    def connect(self) -> bool:
        """Connect to Supabase."""
        if not self.url or not self.key:
            logger.error("Supabase credentials not configured")
            self._status["connection"] = "❌ Credentials missing"
            return False
        
        try:
            from supabase import create_client
            self.client = create_client(self.url, self.key)
            self._connected = True
            self._status["connection"] = "✅ Connected"
            logger.info("Connected to Supabase")
            return True
        except ImportError:
            logger.error("supabase-py not installed")
            self._status["connection"] = "❌ supabase-py not installed"
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._status["connection"] = f"❌ {str(e)[:50]}"
            return False
    
    def check_pgvector(self) -> bool:
        """Check if pgvector extension is enabled."""
        if not self._connected:
            return False
        
        try:
            # Try to query using vector type
            result = self.client.rpc("check_pgvector_exists", {}).execute()
            self._status["pgvector"] = "✅ Enabled"
            return True
        except Exception:
            # Extension might exist but function doesn't
            # Try creating a test
            try:
                self.client.postgrest.rpc("query", {
                    "query": "SELECT 1::vector(3)"
                }).execute()
                self._status["pgvector"] = "✅ Enabled"
                return True
            except Exception:
                self._status["pgvector"] = "⚠️ May need enabling"
                return False
    
    def check_tables(self) -> Dict[str, bool]:
        """Check which tables exist."""
        if not self._connected:
            return {}
        
        table_status = {}
        for table in self.REQUIRED_TABLES:
            try:
                # Try to select from table
                result = self.client.table(table).select("*").limit(1).execute()
                table_status[table] = True
            except Exception:
                table_status[table] = False
        
        self._status["tables"] = table_status
        return table_status
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get row counts for each table."""
        if not self._connected:
            return {}
        
        counts = {}
        for table in self.REQUIRED_TABLES:
            try:
                result = self.client.table(table).select("*", count="exact").execute()
                counts[table] = result.count or 0
            except Exception:
                counts[table] = -1
        
        return counts
    
    def setup_database(self, force: bool = False) -> Dict[str, str]:
        """
        Set up all required tables and functions.
        
        Args:
            force: Recreate tables even if they exist
            
        Returns:
            Status dict for each operation
        """
        results = {}
        
        if not self._connected:
            if not self.connect():
                return {"error": "Could not connect to Supabase"}
        
        # Note: These SQL statements need to be run via Supabase SQL Editor
        # or using the management API. The client library doesn't support DDL.
        
        sql_statements = [
            ("pgvector", SQL_ENABLE_PGVECTOR),
            ("past_essays", SQL_CREATE_PAST_ESSAYS),
            ("personal_statement", SQL_CREATE_PERSONAL_STATEMENT),
            ("personal_profile", SQL_CREATE_PERSONAL_PROFILE),
            ("prompt_templates", SQL_CREATE_PROMPT_TEMPLATES),
            ("scholarships", SQL_CREATE_SCHOLARSHIPS),
            ("applications", SQL_CREATE_APPLICATIONS),
            ("generated_essays", SQL_CREATE_GENERATED_ESSAYS),
            ("match_essays_fn", SQL_CREATE_MATCH_ESSAYS_FUNCTION),
            ("match_statement_fn", SQL_CREATE_MATCH_STATEMENT_FUNCTION),
            ("match_profile_fn", SQL_CREATE_MATCH_PROFILE_FUNCTION),
        ]
        
        # Generate SQL file for manual execution
        sql_file_content = "-- Scholarship Module Database Setup\n"
        sql_file_content += "-- Run this in Supabase SQL Editor\n\n"
        
        for name, sql in sql_statements:
            sql_file_content += f"-- {name}\n{sql}\n\n"
        
        # Save SQL file
        from pathlib import Path
        sql_path = Path(__file__).parent.parent.parent / "config" / "scholarship_setup.sql"
        sql_path.write_text(sql_file_content)
        results["sql_file"] = str(sql_path)
        
        # Try to execute via RPC if available
        for name, sql in sql_statements:
            try:
                # This may not work depending on Supabase setup
                self.client.rpc("exec_sql", {"sql": sql}).execute()
                results[name] = "✅ Created"
            except Exception as e:
                results[name] = f"⚠️ Manual setup needed"
        
        return results
    
    def verify_setup(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify the database setup is complete.
        
        Returns:
            (is_ready, status_dict)
        """
        status = {
            "connected": False,
            "pgvector": False,
            "tables": {},
            "counts": {},
            "ready": False,
        }
        
        # Check connection
        if not self._connected:
            if not self.connect():
                return False, status
        
        status["connected"] = True
        
        # Check tables
        table_status = self.check_tables()
        status["tables"] = table_status
        
        # Get counts
        status["counts"] = self.get_table_counts()
        
        # Check if all required tables exist
        all_tables_exist = all(table_status.get(t, False) for t in self.REQUIRED_TABLES)
        status["ready"] = all_tables_exist
        
        return all_tables_exist, status
    
    def get_status_report(self) -> str:
        """Get formatted status report."""
        is_ready, status = self.verify_setup()
        
        lines = ["📊 **Scholarship Database Status**", ""]
        
        # Connection
        if status["connected"]:
            lines.append("✅ **Connection:** Connected to Supabase")
        else:
            lines.append("❌ **Connection:** Not connected")
            return "\n".join(lines)
        
        # Tables
        lines.append("")
        lines.append("**Tables:**")
        for table, exists in status["tables"].items():
            count = status["counts"].get(table, 0)
            if exists:
                lines.append(f"  ✅ {table}: {count} rows")
            else:
                lines.append(f"  ❌ {table}: Not created")
        
        # Overall status
        lines.append("")
        if is_ready:
            lines.append("✅ **Status:** Database ready for use")
        else:
            lines.append("⚠️ **Status:** Setup incomplete - run setup command")
        
        return "\n".join(lines)
    
    def generate_setup_sql(self) -> str:
        """Generate SQL for manual setup in Supabase SQL Editor."""
        sql_parts = [
            "-- =====================================================",
            "-- JARVIS Scholarship Module - Database Setup",
            "-- =====================================================",
            "-- Run this script in Supabase SQL Editor",
            "-- Project Settings > SQL Editor > New Query",
            "-- =====================================================",
            "",
            SQL_ENABLE_PGVECTOR,
            SQL_CREATE_PAST_ESSAYS,
            SQL_CREATE_PERSONAL_STATEMENT,
            SQL_CREATE_PERSONAL_PROFILE,
            SQL_CREATE_PROMPT_TEMPLATES,
            SQL_CREATE_SCHOLARSHIPS,
            SQL_CREATE_APPLICATIONS,
            SQL_CREATE_GENERATED_ESSAYS,
            SQL_CREATE_MATCH_ESSAYS_FUNCTION,
            SQL_CREATE_MATCH_STATEMENT_FUNCTION,
            SQL_CREATE_MATCH_PROFILE_FUNCTION,
        ]
        return "\n".join(sql_parts)


async def setup_scholarship_database(
    supabase_url: Optional[str] = None,
    supabase_key: Optional[str] = None,
) -> str:
    """
    Main setup function for scholarship database.
    
    Returns status message.
    """
    setup = ScholarshipDatabaseSetup(supabase_url, supabase_key)
    
    # Check current status
    is_ready, status = setup.verify_setup()
    
    if is_ready:
        return setup.get_status_report()
    
    # Generate SQL file
    from pathlib import Path
    sql_content = setup.generate_setup_sql()
    sql_path = Path(__file__).parent.parent.parent / "config" / "scholarship_setup.sql"
    sql_path.parent.mkdir(parents=True, exist_ok=True)
    sql_path.write_text(sql_content)
    
    report = setup.get_status_report()
    report += f"\n\n📄 **Setup SQL saved to:** {sql_path}"
    report += "\n\nTo complete setup:"
    report += "\n1. Open Supabase Dashboard"
    report += "\n2. Go to SQL Editor"
    report += "\n3. Paste and run the SQL from the file above"
    
    return report


def get_database_mode() -> Tuple[str, str]:
    """
    Determine which database mode to use.
    
    Returns:
        (mode, description)
        mode: "cloud" or "local"
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if url and key:
        try:
            from supabase import create_client
            client = create_client(url, key)
            # Test connection
            client.table("past_essays").select("*").limit(1).execute()
            return "cloud", "Supabase (Cloud RAG)"
        except Exception:
            pass
    
    return "local", "ChromaDB (Local RAG)"
