-- JV Directory Schema v2 - Unified Profiles
-- Contacts ARE profiles (same table)

-- Drop old tables if they exist
DROP TABLE IF EXISTS public.import_history CASCADE;
DROP TABLE IF EXISTS public.interactions CASCADE;
DROP TABLE IF EXISTS public.favorites CASCADE;
DROP TABLE IF EXISTS public.contact_services CASCADE;
DROP TABLE IF EXISTS public.contact_categories CASCADE;
DROP TABLE IF EXISTS public.contacts CASCADE;
DROP TABLE IF EXISTS public.service_types CASCADE;
DROP TABLE IF EXISTS public.business_categories CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- UNIFIED PROFILES TABLE
-- Each person in the directory = a profile
-- Can optionally be linked to auth.users for login
-- ============================================

CREATE TABLE public.profiles (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,

    -- Auth link (NULL if not a registered user yet)
    auth_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL UNIQUE,

    -- Basic info
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    website TEXT,
    linkedin TEXT,
    avatar_url TEXT,

    -- Directory fields
    business_focus TEXT,
    status TEXT DEFAULT 'Member' CHECK (status IN ('Member', 'Non Member Resource', 'Pending')),
    service_provided TEXT,
    list_size INTEGER DEFAULT 0,
    business_size TEXT,
    social_reach INTEGER DEFAULT 0,

    -- App role (for registered users)
    role TEXT DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),

    -- Extra
    bio TEXT,
    tags TEXT[],
    notes TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- CONNECTIONS (User saves/follows another user)
-- ============================================

CREATE TABLE public.connections (
    follower_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    following_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (follower_id, following_id)
);

-- ============================================
-- MATCH SUGGESTIONS (JV Partner Recommendations)
-- ============================================

CREATE TABLE public.match_suggestions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,        -- Who the match is FOR
    suggested_profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE, -- Who was suggested
    match_score DECIMAL(5,2),                  -- AI confidence score (0-100)
    match_reason TEXT,                         -- Why they were matched
    source TEXT,                               -- 'ai_matcher', 'manual', 'import'
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'viewed', 'contacted', 'connected', 'dismissed')),
    suggested_at TIMESTAMPTZ DEFAULT NOW(),
    viewed_at TIMESTAMPTZ,
    contacted_at TIMESTAMPTZ,
    notes TEXT,
    UNIQUE(profile_id, suggested_profile_id)
);

-- ============================================
-- INTERACTIONS (Communication log)
-- ============================================

CREATE TABLE public.interactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    from_profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    to_profile_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    interaction_type TEXT CHECK (interaction_type IN ('email', 'call', 'meeting', 'jv_deal', 'note', 'other')),
    description TEXT,
    interaction_date TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES
-- ============================================

CREATE INDEX idx_profiles_name ON public.profiles(name);
CREATE INDEX idx_profiles_email ON public.profiles(email);
CREATE INDEX idx_profiles_company ON public.profiles(company);
CREATE INDEX idx_profiles_status ON public.profiles(status);
CREATE INDEX idx_profiles_auth_user ON public.profiles(auth_user_id);
CREATE INDEX idx_profiles_search ON public.profiles USING GIN(
    to_tsvector('english', COALESCE(name, '') || ' ' || COALESCE(company, '') || ' ' || COALESCE(business_focus, ''))
);
CREATE INDEX idx_connections_follower ON public.connections(follower_id);
CREATE INDEX idx_connections_following ON public.connections(following_id);
CREATE INDEX idx_matches_profile ON public.match_suggestions(profile_id);
CREATE INDEX idx_matches_suggested ON public.match_suggestions(suggested_profile_id);
CREATE INDEX idx_matches_status ON public.match_suggestions(status);

-- ============================================
-- ROW LEVEL SECURITY
-- ============================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.match_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.interactions ENABLE ROW LEVEL SECURITY;

-- Profiles: Everyone can read, users can update their own, admins can update all
CREATE POLICY "Profiles are viewable by everyone"
    ON public.profiles FOR SELECT
    USING (true);

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (auth_user_id = auth.uid());

CREATE POLICY "Admins can insert profiles"
    ON public.profiles FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE auth_user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can update any profile"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE auth_user_id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can delete profiles"
    ON public.profiles FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE auth_user_id = auth.uid() AND role = 'admin'
        )
    );

-- Connections: Users manage their own
CREATE POLICY "Users can view their connections"
    ON public.connections FOR SELECT
    TO authenticated
    USING (
        follower_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

CREATE POLICY "Users can add connections"
    ON public.connections FOR INSERT
    TO authenticated
    WITH CHECK (
        follower_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

CREATE POLICY "Users can remove connections"
    ON public.connections FOR DELETE
    TO authenticated
    USING (
        follower_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

-- Match Suggestions: Users can see their own matches
CREATE POLICY "Users can view their match suggestions"
    ON public.match_suggestions FOR SELECT
    TO authenticated
    USING (
        profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

CREATE POLICY "Users can update their match suggestions"
    ON public.match_suggestions FOR UPDATE
    TO authenticated
    USING (
        profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

CREATE POLICY "Admins can manage all matches"
    ON public.match_suggestions FOR ALL
    TO authenticated
    USING (
        EXISTS (SELECT 1 FROM public.profiles WHERE auth_user_id = auth.uid() AND role = 'admin')
    );

-- Interactions: Users can see their own
CREATE POLICY "Users can view their interactions"
    ON public.interactions FOR SELECT
    TO authenticated
    USING (
        from_profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

CREATE POLICY "Users can add interactions"
    ON public.interactions FOR INSERT
    TO authenticated
    WITH CHECK (
        from_profile_id IN (SELECT id FROM public.profiles WHERE auth_user_id = auth.uid())
    );

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Link auth user to existing profile (by email) or create new
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- Try to link to existing profile by email
    UPDATE public.profiles
    SET auth_user_id = NEW.id
    WHERE email = NEW.email AND auth_user_id IS NULL;

    -- If no existing profile, create new one
    IF NOT FOUND THEN
        INSERT INTO public.profiles (auth_user_id, name, email)
        VALUES (
            NEW.id,
            COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
            NEW.email
        );
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- ============================================
-- VIEWS
-- ============================================

-- Registered users (profiles with auth)
CREATE OR REPLACE VIEW public.registered_users AS
SELECT * FROM public.profiles WHERE auth_user_id IS NOT NULL;

-- Directory entries (all profiles)
CREATE OR REPLACE VIEW public.directory AS
SELECT
    id,
    name,
    company,
    business_focus,
    status,
    service_provided,
    list_size,
    business_size,
    social_reach,
    email,
    website,
    linkedin
FROM public.profiles
ORDER BY name;
