-- =============================================
-- V1 Matching Schema: Intake + Scale Symmetry
-- Migration 004: Adds verified intake system and V1 scoring fields
-- =============================================

-- 1. INTAKE SUBMISSIONS (Verified Intent - Platinum Trust)
-- This is the critical "Verification Gate" table
CREATE TABLE IF NOT EXISTS public.intake_submissions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    event_id TEXT,                    -- e.g., "mastermind-dec-2025"
    event_name TEXT,                  -- "December JV Mastermind"
    event_date DATE,

    -- Verified data (max 2 each to force prioritization)
    verified_offers TEXT[] NOT NULL DEFAULT '{}',
    verified_needs TEXT[] NOT NULL DEFAULT '{}',

    -- Match preference drives Synergy Score logic
    -- Peer_Bundle: Same niche collaboration
    -- Referral_Upstream: They serve clients BEFORE they need you
    -- Referral_Downstream: They serve clients AFTER they work with you
    -- Service_Provider: Vendor/service relationship
    match_preference TEXT NOT NULL DEFAULT 'Peer_Bundle' CHECK (match_preference IN (
        'Peer_Bundle',
        'Referral_Upstream',
        'Referral_Downstream',
        'Service_Provider'
    )),

    -- AI suggestions (Bronze trust - for pre-fill only)
    suggested_offers TEXT[],
    suggested_needs TEXT[],

    -- Timestamps
    confirmed_at TIMESTAMPTZ,         -- NULL until user confirms
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Unique constraint: one intake per profile per event
    UNIQUE(profile_id, event_id)
);

-- 2. ADD MOMENTUM TRACKING TO PROFILES
-- last_active_at enables time-decay scoring: e^(-0.02 * days)
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ DEFAULT NOW();

-- niche: Normalized business category for Synergy scoring
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS niche TEXT;

-- audience_type: Who they serve (for Synergy calculation)
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS audience_type TEXT;

-- 3. EXTEND MATCH_SUGGESTIONS FOR V1 SCORING
-- score_ab: A→B directional score
ALTER TABLE public.match_suggestions
ADD COLUMN IF NOT EXISTS score_ab DECIMAL(5,2);

-- score_ba: B→A directional score
ALTER TABLE public.match_suggestions
ADD COLUMN IF NOT EXISTS score_ba DECIMAL(5,2);

-- harmonic_mean: Final reciprocal score = (2 * AB * BA) / (AB + BA)
ALTER TABLE public.match_suggestions
ADD COLUMN IF NOT EXISTS harmonic_mean DECIMAL(5,2);

-- scale_symmetry_score: For analytics - how well did their sizes match?
ALTER TABLE public.match_suggestions
ADD COLUMN IF NOT EXISTS scale_symmetry_score DECIMAL(5,2);

-- trust_level: Source of the match data
ALTER TABLE public.match_suggestions
ADD COLUMN IF NOT EXISTS trust_level TEXT DEFAULT 'legacy' CHECK (trust_level IN (
    'platinum',   -- Verified via Micro-Intake
    'gold',       -- Manual profile entry
    'bronze',     -- AI-extracted from transcripts
    'legacy'      -- Old data without trust tracking
));

-- 4. POPULARITY TRACKING (Fairness Constraints)
-- Prevents "rich get richer" bias - max 5 appearances in Top 3 per cycle
CREATE TABLE IF NOT EXISTS public.match_popularity (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    match_cycle_id TEXT NOT NULL,     -- e.g., "2025-01-cycle"
    top_3_appearances INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(profile_id, match_cycle_id)
);

-- 5. MATCH OUTCOMES (V2 Preparation - Learning Data)
-- Not used in V1, but schema ready for Learning-to-Rank
CREATE TABLE IF NOT EXISTS public.match_outcomes (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    match_id UUID REFERENCES public.match_suggestions(id) ON DELETE CASCADE,
    meeting_accepted BOOLEAN,
    meeting_happened BOOLEAN,
    star_rating INTEGER CHECK (star_rating BETWEEN 1 AND 5),
    no_show_flag BOOLEAN DEFAULT FALSE,
    deal_closed BOOLEAN,
    deal_value DECIMAL,
    feedback_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. INDEXES FOR PERFORMANCE
CREATE INDEX IF NOT EXISTS idx_intake_profile ON public.intake_submissions(profile_id);
CREATE INDEX IF NOT EXISTS idx_intake_event ON public.intake_submissions(event_id);
CREATE INDEX IF NOT EXISTS idx_intake_confirmed ON public.intake_submissions(confirmed_at);
CREATE INDEX IF NOT EXISTS idx_profiles_last_active ON public.profiles(last_active_at);
CREATE INDEX IF NOT EXISTS idx_profiles_niche ON public.profiles(niche);
CREATE INDEX IF NOT EXISTS idx_popularity_cycle ON public.match_popularity(match_cycle_id);
CREATE INDEX IF NOT EXISTS idx_match_suggestions_harmonic ON public.match_suggestions(harmonic_mean DESC);
CREATE INDEX IF NOT EXISTS idx_match_suggestions_trust ON public.match_suggestions(trust_level);
CREATE INDEX IF NOT EXISTS idx_match_outcomes_match ON public.match_outcomes(match_id);

-- 7. ROW LEVEL SECURITY FOR NEW TABLES
ALTER TABLE public.intake_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.match_popularity ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.match_outcomes ENABLE ROW LEVEL SECURITY;

-- Intake submissions: Users can view/edit their own
CREATE POLICY "Users can view their own intakes"
    ON public.intake_submissions FOR SELECT
    TO authenticated
    USING (
        profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

CREATE POLICY "Users can insert their own intakes"
    ON public.intake_submissions FOR INSERT
    TO authenticated
    WITH CHECK (
        profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

CREATE POLICY "Users can update their own intakes"
    ON public.intake_submissions FOR UPDATE
    TO authenticated
    USING (
        profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

-- Admins can manage all intakes
CREATE POLICY "Admins can manage all intakes"
    ON public.intake_submissions FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE auth_user_id = auth.uid() AND role = 'admin')
    );

-- Match outcomes: Users can view/add for their matches
CREATE POLICY "Users can view their match outcomes"
    ON public.match_outcomes FOR SELECT
    TO authenticated
    USING (
        match_id IN (
            SELECT id FROM public.match_suggestions
            WHERE profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
        )
    );

CREATE POLICY "Users can add match outcomes"
    ON public.match_outcomes FOR INSERT
    TO authenticated
    WITH CHECK (
        match_id IN (
            SELECT id FROM public.match_suggestions
            WHERE profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
        )
    );

-- 8. HELPER FUNCTION: Get latest verified intake for a profile
CREATE OR REPLACE FUNCTION get_latest_intake(p_profile_id UUID)
RETURNS TABLE (
    verified_offers TEXT[],
    verified_needs TEXT[],
    match_preference TEXT,
    event_id TEXT,
    confirmed_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        i.verified_offers,
        i.verified_needs,
        i.match_preference,
        i.event_id,
        i.confirmed_at
    FROM public.intake_submissions i
    WHERE i.profile_id = p_profile_id
      AND i.confirmed_at IS NOT NULL
    ORDER BY i.confirmed_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- 9. HELPER FUNCTION: Calculate momentum score
CREATE OR REPLACE FUNCTION calculate_momentum(p_last_active TIMESTAMPTZ)
RETURNS DECIMAL AS $$
DECLARE
    days_since INTEGER;
BEGIN
    IF p_last_active IS NULL THEN
        RETURN 0.5;  -- Neutral for unknown
    END IF;

    days_since := EXTRACT(DAY FROM (NOW() - p_last_active));
    RETURN EXP(-0.02 * GREATEST(0, days_since));
END;
$$ LANGUAGE plpgsql;

-- 10. COMMENTS FOR DOCUMENTATION
COMMENT ON TABLE public.intake_submissions IS 'Verified user intent - Platinum Trust level data for matching';
COMMENT ON COLUMN public.intake_submissions.verified_offers IS 'User-confirmed offers (max 2) - used for Intent scoring';
COMMENT ON COLUMN public.intake_submissions.verified_needs IS 'User-confirmed needs (max 2) - used for Intent scoring';
COMMENT ON COLUMN public.intake_submissions.match_preference IS 'Relationship type sought - drives Synergy score logic';
COMMENT ON COLUMN public.intake_submissions.confirmed_at IS 'NULL until user clicks Confirm - then becomes Platinum trust';

COMMENT ON TABLE public.match_popularity IS 'Fairness tracking - prevents popular users from dominating all match lists';
COMMENT ON COLUMN public.match_popularity.top_3_appearances IS 'How many Top 3 lists this profile appears in (max 5 per cycle)';

COMMENT ON COLUMN public.match_suggestions.harmonic_mean IS 'Reciprocal score: (2*AB*BA)/(AB+BA) - penalizes lopsided matches';
COMMENT ON COLUMN public.match_suggestions.trust_level IS 'Data source quality: platinum > gold > bronze > legacy';

COMMENT ON COLUMN public.profiles.last_active_at IS 'Used for Momentum scoring: e^(-0.02 * days_since_active)';
COMMENT ON COLUMN public.profiles.niche IS 'Normalized business category for Synergy score calculation';
