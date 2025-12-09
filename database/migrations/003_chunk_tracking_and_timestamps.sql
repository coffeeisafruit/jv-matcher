-- Chunk Tracking and Time-Stamped Profile History
-- Run this in Supabase SQL Editor
-- Date: 2025-12-09

-- ============================================
-- TRANSCRIPT CHUNKS TABLE
-- Stores each chunk processed from a transcript
-- Enables debugging, reprocessing, and failure recovery
-- ============================================

CREATE TABLE IF NOT EXISTS transcript_chunks (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    transcript_id UUID REFERENCES conversation_transcripts(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,              -- Order in the transcript (0, 1, 2...)
    chunk_text TEXT NOT NULL,                  -- The actual chunk content
    char_start INTEGER,                        -- Starting character position in original
    char_end INTEGER,                          -- Ending character position in original

    -- Processing status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'success', 'failed', 'retry')),
    profiles_extracted INTEGER DEFAULT 0,      -- Count of profiles found in this chunk
    error_message TEXT,                        -- Error details if failed
    retry_count INTEGER DEFAULT 0,             -- Number of retry attempts

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,

    UNIQUE(transcript_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS idx_chunks_transcript ON transcript_chunks(transcript_id);
CREATE INDEX IF NOT EXISTS idx_chunks_status ON transcript_chunks(status);

-- ============================================
-- PROFILE FIELD HISTORY TABLE
-- Tracks when each piece of information was added to a profile
-- Enables time-based matching context
-- ============================================

CREATE TABLE IF NOT EXISTS profile_field_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES profiles(id) ON DELETE CASCADE,

    -- What was added
    field_name VARCHAR(50) NOT NULL,           -- 'what_you_do', 'seeking', 'offering', etc.
    field_value TEXT NOT NULL,                 -- The actual content added

    -- When and where it came from
    event_date DATE,                           -- Date of the networking event
    event_name TEXT,                           -- e.g., "JV Mastermind December 2025"
    transcript_id UUID REFERENCES conversation_transcripts(id) ON DELETE SET NULL,
    chunk_id UUID REFERENCES transcript_chunks(id) ON DELETE SET NULL,
    timestamp_in_transcript TEXT,              -- e.g., "10:35:12" - when they said it

    -- Metadata
    confidence FLOAT,                          -- AI confidence in extraction
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_field_history_profile ON profile_field_history(profile_id);
CREATE INDEX IF NOT EXISTS idx_field_history_field ON profile_field_history(field_name);
CREATE INDEX IF NOT EXISTS idx_field_history_event_date ON profile_field_history(event_date);
CREATE INDEX IF NOT EXISTS idx_field_history_transcript ON profile_field_history(transcript_id);

-- ============================================
-- PROCESSING ERRORS TABLE
-- Tracks all processing errors for visibility
-- No more silent fails!
-- ============================================

CREATE TABLE IF NOT EXISTS processing_errors (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,

    -- What failed
    error_type VARCHAR(50) NOT NULL,           -- 'chunk_extraction', 'profile_match', 'match_generation', etc.
    error_message TEXT NOT NULL,
    error_details JSONB,                       -- Full error context

    -- Related entities
    transcript_id UUID REFERENCES conversation_transcripts(id) ON DELETE SET NULL,
    chunk_id UUID REFERENCES transcript_chunks(id) ON DELETE SET NULL,
    profile_id UUID REFERENCES profiles(id) ON DELETE SET NULL,

    -- Status
    status VARCHAR(20) DEFAULT 'new' CHECK (status IN ('new', 'acknowledged', 'resolved', 'ignored')),
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    resolution_notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_errors_type ON processing_errors(error_type);
CREATE INDEX IF NOT EXISTS idx_errors_status ON processing_errors(status);
CREATE INDEX IF NOT EXISTS idx_errors_created ON processing_errors(created_at DESC);

-- ============================================
-- ADD EVENT DATE TO CONVERSATION TRANSCRIPTS
-- ============================================

ALTER TABLE conversation_transcripts
ADD COLUMN IF NOT EXISTS event_date DATE;

-- ============================================
-- UPDATE MATCH SUGGESTIONS FOR TIME CONTEXT
-- ============================================

-- Add columns for time-based matching context
ALTER TABLE match_suggestions
ADD COLUMN IF NOT EXISTS match_context JSONB;
-- match_context will store:
-- {
--   "seeker_mentioned": {"field": "seeking", "value": "publisher", "event_date": "2025-03-15", "event_name": "March Mastermind"},
--   "match_mentioned": {"field": "offering", "value": "publishing services", "event_date": "2025-01-20", "event_name": "January Kickoff"}
-- }

-- ============================================
-- HELPER FUNCTION: Get profile field with dates
-- ============================================

CREATE OR REPLACE FUNCTION get_profile_field_with_history(
    p_profile_id UUID,
    p_field_name VARCHAR(50)
)
RETURNS TABLE (
    field_value TEXT,
    event_date DATE,
    event_name TEXT,
    added_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        pfh.field_value,
        pfh.event_date,
        pfh.event_name,
        pfh.created_at as added_at
    FROM profile_field_history pfh
    WHERE pfh.profile_id = p_profile_id
      AND pfh.field_name = p_field_name
    ORDER BY pfh.event_date DESC NULLS LAST, pfh.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- HELPER FUNCTION: Get unresolved errors count
-- ============================================

CREATE OR REPLACE FUNCTION get_unresolved_error_count()
RETURNS INTEGER AS $$
BEGIN
    RETURN (SELECT COUNT(*) FROM processing_errors WHERE status = 'new');
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- HELPER FUNCTION: Get failed chunks for retry
-- ============================================

CREATE OR REPLACE FUNCTION get_failed_chunks_for_retry(max_retries INTEGER DEFAULT 3)
RETURNS TABLE (
    chunk_id UUID,
    transcript_id UUID,
    chunk_index INTEGER,
    chunk_text TEXT,
    retry_count INTEGER,
    error_message TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        tc.id as chunk_id,
        tc.transcript_id,
        tc.chunk_index,
        tc.chunk_text,
        tc.retry_count,
        tc.error_message
    FROM transcript_chunks tc
    WHERE tc.status = 'failed'
      AND tc.retry_count < max_retries
    ORDER BY tc.created_at;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VERIFICATION
-- ============================================

SELECT table_name FROM information_schema.tables
WHERE table_name IN (
    'transcript_chunks',
    'profile_field_history',
    'processing_errors'
);
