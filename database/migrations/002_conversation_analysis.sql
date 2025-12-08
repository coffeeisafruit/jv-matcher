-- Conversation Analysis Schema - Database Migration
-- Run this in Supabase SQL Editor
-- Date: 2025-12-08

-- ============================================
-- CONVERSATION TRANSCRIPTS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS conversation_transcripts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    event_name TEXT,                          -- e.g., "JV Mastermind Dec 2025"
    transcript_text TEXT NOT NULL,
    transcript_type VARCHAR(20) DEFAULT 'group', -- 'solo_intro' or 'group'
    participant_count INTEGER,
    analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- CONVERSATION SPEAKERS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS conversation_speakers (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    transcript_id UUID REFERENCES conversation_transcripts(id) ON DELETE CASCADE,
    speaker_name TEXT NOT NULL,
    matched_profile_id UUID REFERENCES profiles(id),
    match_confidence FLOAT,
    speaker_text TEXT,                        -- Everything they said
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_speakers_transcript ON conversation_speakers(transcript_id);
CREATE INDEX IF NOT EXISTS idx_conv_speakers_profile ON conversation_speakers(matched_profile_id);

-- ============================================
-- CONVERSATION TOPICS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS conversation_topics (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    transcript_id UUID REFERENCES conversation_transcripts(id) ON DELETE CASCADE,
    topic_name TEXT NOT NULL,                 -- e.g., "email marketing", "course launches"
    topic_category TEXT,                      -- e.g., "business", "health", "tech"
    relevance_score FLOAT,                    -- 0-100 how prominent in conversation
    mentioned_by UUID[],                      -- Array of speaker IDs who discussed this
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_topics_transcript ON conversation_topics(transcript_id);
CREATE INDEX IF NOT EXISTS idx_conv_topics_category ON conversation_topics(topic_category);

-- ============================================
-- CONVERSATION SIGNALS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS conversation_signals (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    transcript_id UUID REFERENCES conversation_transcripts(id) ON DELETE CASCADE,
    speaker_id UUID REFERENCES conversation_speakers(id) ON DELETE CASCADE,
    profile_id UUID REFERENCES profiles(id),  -- Resolved profile
    signal_type VARCHAR(30) NOT NULL,         -- 'need', 'interest', 'offer', 'connection'
    signal_text TEXT NOT NULL,                -- The actual statement
    target_speaker_id UUID REFERENCES conversation_speakers(id), -- For 'connection' signals
    target_profile_id UUID REFERENCES profiles(id),
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_signals_transcript ON conversation_signals(transcript_id);
CREATE INDEX IF NOT EXISTS idx_conv_signals_profile ON conversation_signals(profile_id);
CREATE INDEX IF NOT EXISTS idx_conv_signals_type ON conversation_signals(signal_type);
CREATE INDEX IF NOT EXISTS idx_conv_signals_target ON conversation_signals(target_profile_id);

-- ============================================
-- VERIFICATION
-- ============================================

-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_name IN (
    'conversation_transcripts',
    'conversation_speakers',
    'conversation_topics',
    'conversation_signals'
);
