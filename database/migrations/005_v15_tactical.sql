-- =============================================
-- V1.5 Tactical Upgrade Schema
-- Migration 005: Anti-personas, expiration, feedback enhancements
-- =============================================

-- 1. ADD expires_at TO match_suggestions
-- Default 7-day expiration for match relevance (FOMO timer)
ALTER TABLE public.match_suggestions
ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days');

-- 2. ADD anti_personas TO intake_submissions
-- Stores user exclusion preferences: no_beginners, no_service_providers, no_competitors
ALTER TABLE public.intake_submissions
ADD COLUMN IF NOT EXISTS anti_personas TEXT[] DEFAULT '{}';

-- 3. ADD feedback_tags TO match_outcomes
-- For detailed feedback categorization (e.g., "Great conversation", "Ghosted")
ALTER TABLE public.match_outcomes
ADD COLUMN IF NOT EXISTS feedback_tags TEXT[] DEFAULT '{}';

-- 4. ADD Index for expiration queries
-- Enables efficient filtering of expired matches
CREATE INDEX IF NOT EXISTS idx_match_suggestions_expires_at
ON public.match_suggestions(expires_at);

-- 5. COMMENTS for documentation
COMMENT ON COLUMN public.match_suggestions.expires_at IS 'Match expires after 7 days for freshness - drives urgency';
COMMENT ON COLUMN public.intake_submissions.anti_personas IS 'User exclusion preferences: no_beginners, no_service_providers, no_competitors';
COMMENT ON COLUMN public.match_outcomes.feedback_tags IS 'Categorized feedback tags for learning loop';
