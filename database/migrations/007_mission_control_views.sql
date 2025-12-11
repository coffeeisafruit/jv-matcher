-- =============================================
-- Migration 007: Mission Control Dashboard Infrastructure
-- Adds tracking column and indexes for admin dashboard KPIs
-- =============================================

-- 1. Add tracking column for Action Rate (Draft Intro clicks)
ALTER TABLE public.match_suggestions
ADD COLUMN IF NOT EXISTS draft_intro_clicked_at TIMESTAMPTZ;

-- 2. Indexes for fast KPI queries
-- Status + Trust for filtering matches
CREATE INDEX IF NOT EXISTS idx_match_suggestions_status_trust
ON public.match_suggestions(status, trust_level);

-- Confirmed intakes for Platinum Ratio
CREATE INDEX IF NOT EXISTS idx_intake_confirmed
ON public.intake_submissions(confirmed_at) WHERE confirmed_at IS NOT NULL;

-- Profile matches for orphan detection
CREATE INDEX IF NOT EXISTS idx_match_suggestions_profile_id
ON public.match_suggestions(profile_id);

-- 3. Comments for documentation
COMMENT ON COLUMN public.match_suggestions.draft_intro_clicked_at IS 'Tracks when Draft Intro button was clicked for Action Rate KPI';
