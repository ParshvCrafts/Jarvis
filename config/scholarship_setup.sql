-- =====================================================
-- JARVIS Scholarship Module - Database Setup
-- =====================================================
-- Run this script in Supabase SQL Editor
-- Project Settings > SQL Editor > New Query
-- =====================================================


CREATE EXTENSION IF NOT EXISTS vector;


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
