-- =============================================
-- Migration 008: Data Freshness & Activation View
-- Creates view for identifying stale profiles and activation opportunities
-- =============================================

-- Drop existing view if it exists (for re-running migration)
DROP VIEW IF EXISTS public.view_profile_freshness;

-- Create the freshness view
CREATE VIEW public.view_profile_freshness AS
SELECT
    p.id AS profile_id,
    p.name,
    p.company,
    p.email,
    p.business_focus AS niche,
    p.offering AS bronze_offer_preview,
    p.list_size,
    p.social_reach,
    p.last_active_at,
    p.created_at AS profile_created_at,

    -- Latest intake submission data
    latest_intake.confirmed_at AS last_intake_confirmed_at,
    latest_intake.id AS latest_intake_id,

    -- Days since last intake (NULL if never submitted)
    CASE
        WHEN latest_intake.confirmed_at IS NOT NULL
        THEN EXTRACT(DAY FROM (NOW() - latest_intake.confirmed_at))::INTEGER
        ELSE NULL
    END AS days_since_last_intake,

    -- Days since last active (NULL if never active)
    CASE
        WHEN p.last_active_at IS NOT NULL
        THEN EXTRACT(DAY FROM (NOW() - p.last_active_at))::INTEGER
        ELSE NULL
    END AS days_since_last_active,

    -- Current trust status classification
    CASE
        -- Platinum: Confirmed intake within last 30 days
        WHEN latest_intake.confirmed_at IS NOT NULL
             AND latest_intake.confirmed_at > NOW() - INTERVAL '30 days'
        THEN 'Platinum'

        -- Bronze: Active in last 30 days but NO confirmed intake (or stale intake)
        WHEN p.last_active_at IS NOT NULL
             AND p.last_active_at > NOW() - INTERVAL '30 days'
             AND (latest_intake.confirmed_at IS NULL
                  OR latest_intake.confirmed_at <= NOW() - INTERVAL '30 days')
        THEN 'Bronze'

        -- Legacy: Inactive > 30 days (or never active)
        ELSE 'Legacy'
    END AS current_trust_status,

    -- Impact score: list_size + social_reach (NULL-safe)
    COALESCE(p.list_size, 0) + COALESCE(p.social_reach, 0) AS impact_score,

    -- Flag for "Sleeping Giants" (High reach + Legacy status)
    CASE
        WHEN (COALESCE(p.list_size, 0) + COALESCE(p.social_reach, 0)) > 5000
             AND (p.last_active_at IS NULL OR p.last_active_at <= NOW() - INTERVAL '30 days')
             AND (latest_intake.confirmed_at IS NULL OR latest_intake.confirmed_at <= NOW() - INTERVAL '30 days')
        THEN TRUE
        ELSE FALSE
    END AS is_sleeping_giant

FROM public.profiles p

-- Left join to get the most recent intake submission per profile
LEFT JOIN LATERAL (
    SELECT
        i.id,
        i.confirmed_at
    FROM public.intake_submissions i
    WHERE i.profile_id = p.id
    ORDER BY i.confirmed_at DESC NULLS LAST, i.created_at DESC
    LIMIT 1
) latest_intake ON TRUE;

-- Add comment for documentation
COMMENT ON VIEW public.view_profile_freshness IS
'Data freshness view for activation campaigns. Classifies users as Platinum (verified), Bronze (active but unverified), or Legacy (stale). Identifies Sleeping Giants (high-value inactive users).';

-- Create indexes on profiles table to optimize the view (if not exists)
CREATE INDEX IF NOT EXISTS idx_profiles_last_active_at
ON public.profiles(last_active_at);

CREATE INDEX IF NOT EXISTS idx_intake_profile_confirmed
ON public.intake_submissions(profile_id, confirmed_at DESC);
