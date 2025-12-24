-- =====================================================
-- JARVIS Internship Module - Database Setup
-- =====================================================
-- Run this script in Supabase SQL Editor
-- Project Settings > SQL Editor > New Query
-- =====================================================

-- Enable vector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- =====================================================
-- Master Resume Table
-- =====================================================
CREATE TABLE IF NOT EXISTS master_resume (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version INTEGER DEFAULT 1,
    full_content TEXT,
    sections JSONB,
    contact JSONB,
    summary TEXT,
    certifications TEXT[],
    awards TEXT[],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- Resume Projects Table
-- =====================================================
CREATE TABLE IF NOT EXISTS resume_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    detailed_description TEXT,
    technologies TEXT[],
    skills_demonstrated TEXT[],
    impact_metrics TEXT[],
    quantified_results TEXT[],
    start_date DATE,
    end_date DATE,
    is_ongoing BOOLEAN DEFAULT false,
    github_url TEXT,
    demo_url TEXT,
    paper_url TEXT,
    resume_bullets TEXT[],
    embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS resume_projects_embedding_idx 
ON resume_projects USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- =====================================================
-- Resume Skills Table
-- =====================================================
CREATE TABLE IF NOT EXISTS resume_skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    category TEXT,
    proficiency TEXT,
    years_experience DECIMAL,
    evidence TEXT[],
    keywords TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS resume_skills_category_idx ON resume_skills(category);

-- =====================================================
-- Work Experience Table
-- =====================================================
CREATE TABLE IF NOT EXISTS work_experience (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    location TEXT,
    location_type TEXT,
    start_date DATE,
    end_date DATE,
    is_current BOOLEAN DEFAULT false,
    description TEXT,
    achievements TEXT[],
    technologies TEXT[],
    embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS work_experience_embedding_idx 
ON work_experience USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- =====================================================
-- Internship Listings Table
-- =====================================================
CREATE TABLE IF NOT EXISTS internship_listings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    location TEXT,
    location_type TEXT,
    job_type TEXT DEFAULT 'internship',
    description TEXT,
    requirements TEXT[],
    preferred_qualifications TEXT[],
    responsibilities TEXT[],
    salary_min INTEGER,
    salary_max INTEGER,
    salary_type TEXT DEFAULT 'hourly',
    benefits TEXT[],
    deadline DATE,
    url TEXT,
    application_url TEXT,
    source_api TEXT,
    source_id TEXT,
    match_score DECIMAL,
    matched_skills TEXT[],
    missing_skills TEXT[],
    keywords TEXT[],
    status TEXT DEFAULT 'new',
    posted_date DATE,
    discovered_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS internship_listings_company_idx ON internship_listings(company);
CREATE INDEX IF NOT EXISTS internship_listings_status_idx ON internship_listings(status);
CREATE INDEX IF NOT EXISTS internship_listings_deadline_idx ON internship_listings(deadline);

-- =====================================================
-- Applications Table
-- =====================================================
CREATE TABLE IF NOT EXISTS internship_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    internship_id UUID REFERENCES internship_listings(id),
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT DEFAULT 'saved',
    resume_version_id UUID,
    cover_letter_id UUID,
    date_saved TIMESTAMP DEFAULT NOW(),
    date_applied TIMESTAMP,
    follow_up_date DATE,
    response_date TIMESTAMP,
    notes TEXT,
    contact_person TEXT,
    contact_email TEXT,
    interviews JSONB DEFAULT '[]',
    outcome_notes TEXT,
    salary_offered INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS internship_applications_status_idx ON internship_applications(status);
CREATE INDEX IF NOT EXISTS internship_applications_company_idx ON internship_applications(company);
CREATE INDEX IF NOT EXISTS internship_applications_follow_up_idx ON internship_applications(follow_up_date);

-- =====================================================
-- Generated Resumes Table
-- =====================================================
CREATE TABLE IF NOT EXISTS generated_resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES internship_applications(id),
    internship_id UUID REFERENCES internship_listings(id),
    company TEXT,
    role TEXT,
    content JSONB,
    full_text TEXT,
    pdf_path TEXT,
    docx_path TEXT,
    google_doc_url TEXT,
    ats_score DECIMAL,
    keywords_included TEXT[],
    keywords_missing TEXT[],
    projects_used TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- Generated Cover Letters Table
-- =====================================================
CREATE TABLE IF NOT EXISTS generated_cover_letters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID REFERENCES internship_applications(id),
    company TEXT,
    role TEXT,
    content TEXT,
    word_count INTEGER,
    company_info JSONB,
    stories_used TEXT[],
    pdf_path TEXT,
    docx_path TEXT,
    google_doc_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================================================
-- Stories Table (from scholarship essays)
-- =====================================================
CREATE TABLE IF NOT EXISTS resume_stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT,
    content TEXT NOT NULL,
    themes TEXT[],
    embedding vector(384),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS resume_stories_embedding_idx 
ON resume_stories USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 50);

-- =====================================================
-- Vector Search Functions
-- =====================================================

-- Search similar projects
CREATE OR REPLACE FUNCTION match_resume_projects(
    query_embedding vector(384),
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    description TEXT,
    technologies TEXT[],
    resume_bullets TEXT[],
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rp.id,
        rp.name,
        rp.description,
        rp.technologies,
        rp.resume_bullets,
        1 - (rp.embedding <=> query_embedding) AS similarity
    FROM resume_projects rp
    WHERE rp.embedding IS NOT NULL
    ORDER BY rp.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search similar work experience
CREATE OR REPLACE FUNCTION match_work_experience(
    query_embedding vector(384),
    match_count int DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    company TEXT,
    role TEXT,
    description TEXT,
    achievements TEXT[],
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        we.id,
        we.company,
        we.role,
        we.description,
        we.achievements,
        1 - (we.embedding <=> query_embedding) AS similarity
    FROM work_experience we
    WHERE we.embedding IS NOT NULL
    ORDER BY we.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Search similar stories
CREATE OR REPLACE FUNCTION match_resume_stories(
    query_embedding vector(384),
    match_count int DEFAULT 3
)
RETURNS TABLE (
    id UUID,
    source TEXT,
    content TEXT,
    themes TEXT[],
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        rs.id,
        rs.source,
        rs.content,
        rs.themes,
        1 - (rs.embedding <=> query_embedding) AS similarity
    FROM resume_stories rs
    WHERE rs.embedding IS NOT NULL
    ORDER BY rs.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- =====================================================
-- Application Statistics View
-- =====================================================
CREATE OR REPLACE VIEW application_statistics AS
SELECT
    COUNT(*) as total_applications,
    COUNT(*) FILTER (WHERE status = 'saved') as saved,
    COUNT(*) FILTER (WHERE status = 'applied') as applied,
    COUNT(*) FILTER (WHERE status IN ('phone_screen', 'technical', 'interview', 'final_round')) as interviewing,
    COUNT(*) FILTER (WHERE status = 'offer') as offers,
    COUNT(*) FILTER (WHERE status = 'accepted') as accepted,
    COUNT(*) FILTER (WHERE status = 'rejected') as rejected,
    ROUND(
        COUNT(*) FILTER (WHERE status IN ('phone_screen', 'technical', 'interview', 'final_round', 'offer', 'accepted'))::numeric / 
        NULLIF(COUNT(*) FILTER (WHERE status != 'saved'), 0) * 100, 1
    ) as interview_rate,
    ROUND(
        COUNT(*) FILTER (WHERE status IN ('offer', 'accepted'))::numeric / 
        NULLIF(COUNT(*) FILTER (WHERE status != 'saved'), 0) * 100, 1
    ) as offer_rate
FROM internship_applications;
