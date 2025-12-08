-- Rich JV Matching System - Database Migration
-- Run this in Supabase SQL Editor
-- Date: 2025-12-08

-- ============================================
-- PROFILES TABLE - Add Rich Profile Fields
-- ============================================

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS what_you_do TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS who_you_serve TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS seeking TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS offering TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS current_projects TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS profile_updated_at TIMESTAMPTZ DEFAULT NOW();

-- Trigger to auto-update profile_updated_at
CREATE OR REPLACE FUNCTION update_profile_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.profile_updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS profiles_timestamp_update ON profiles;
CREATE TRIGGER profiles_timestamp_update
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_profile_timestamp();

-- ============================================
-- MATCH_SUGGESTIONS TABLE - Add Rich Analysis & Tracking
-- ============================================

ALTER TABLE match_suggestions ADD COLUMN IF NOT EXISTS rich_analysis TEXT;
ALTER TABLE match_suggestions ADD COLUMN IF NOT EXISTS analysis_generated_at TIMESTAMPTZ;
ALTER TABLE match_suggestions ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMPTZ;
ALTER TABLE match_suggestions ADD COLUMN IF NOT EXISTS user_feedback VARCHAR(20);
ALTER TABLE match_suggestions ADD COLUMN IF NOT EXISTS feedback_at TIMESTAMPTZ;

-- ============================================
-- ANALYTICS EVENTS TABLE - New
-- ============================================

CREATE TABLE IF NOT EXISTS analytics_events (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    user_id UUID REFERENCES profiles(id),
    match_id UUID,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX IF NOT EXISTS idx_analytics_user ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_created ON analytics_events(created_at);

-- ============================================
-- PROFILE REVIEW QUEUE TABLE - New
-- ============================================

CREATE TABLE IF NOT EXISTS profile_review_queue (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    extracted_name TEXT NOT NULL,
    extracted_data JSONB,
    candidate_profile_id UUID REFERENCES profiles(id),
    confidence_score FLOAT,
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_by UUID REFERENCES profiles(id),
    reviewed_at TIMESTAMPTZ,
    source_transcript TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_review_queue_status ON profile_review_queue(status);

-- ============================================
-- VERIFICATION
-- ============================================

-- Check profiles table has new columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'profiles'
AND column_name IN ('what_you_do', 'who_you_serve', 'seeking', 'offering', 'current_projects', 'profile_updated_at');

-- Check match_suggestions table has new columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'match_suggestions'
AND column_name IN ('rich_analysis', 'analysis_generated_at', 'email_sent_at', 'user_feedback', 'feedback_at');

-- Check new tables exist
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('analytics_events', 'profile_review_queue');
