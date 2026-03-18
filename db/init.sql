-- Jobber: Job Aggregation & Tracking System
-- Database schema v1.0

CREATE TABLE IF NOT EXISTS jobs (
    id              SERIAL PRIMARY KEY,
    job_id          VARCHAR(128) UNIQUE NOT NULL,
    source          VARCHAR(32) NOT NULL,        -- 'linkedin', 'dice', etc.
    title           VARCHAR(256),
    company         VARCHAR(256),
    location        VARCHAR(256),
    remote          BOOLEAN DEFAULT FALSE,
    url             TEXT,
    description     TEXT,
    llm_summary     TEXT,                        -- 3-bullet LLM-generated summary
    relevance_score INTEGER DEFAULT 0,           -- 1-10 LLM relevance score
    skills          TEXT[],                       -- extracted skill tags
    date_posted     DATE,
    date_scraped    TIMESTAMPTZ DEFAULT NOW(),
    date_applied    DATE,
    status          VARCHAR(32) DEFAULT 'new',   -- new|reviewed|applied|interview|offer|rejected|archived
    notes           TEXT,
    raw_data        JSONB
);

CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_relevance ON jobs(relevance_score DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_date_scraped ON jobs(date_scraped DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company);
