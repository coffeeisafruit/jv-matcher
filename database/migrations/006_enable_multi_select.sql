-- =============================================
-- Migration 006: Enable Multi-Select Preferences
-- Converts match_preference from single string to array
-- =============================================

-- 1. Drop the old "Single Choice Only" constraint
ALTER TABLE public.intake_submissions
DROP CONSTRAINT IF EXISTS intake_submissions_match_preference_check;

-- 2. Drop the existing default FIRST (required before type change)
ALTER TABLE public.intake_submissions
ALTER COLUMN match_preference DROP DEFAULT;

-- 3. Convert the column from Text to Array of Text
-- (This preserves existing data by wrapping it in brackets: "Peer" -> ["Peer"])
ALTER TABLE public.intake_submissions
ALTER COLUMN match_preference TYPE TEXT[]
USING ARRAY[match_preference];

-- 4. Set a new default of empty array
ALTER TABLE public.intake_submissions
ALTER COLUMN match_preference SET DEFAULT '{}';

-- 5. Add comment for documentation
COMMENT ON COLUMN public.intake_submissions.match_preference IS 'Array of selected match preferences (V1.5 multi-select upgrade)';
