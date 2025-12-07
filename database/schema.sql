-- JV Directory Database Schema for Supabase
-- Run this in the Supabase SQL Editor

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- CORE TABLES
-- ============================================

-- User profiles (extends Supabase auth.users)
CREATE TABLE public.profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    company TEXT,
    role TEXT DEFAULT 'member' CHECK (role IN ('admin', 'member', 'viewer')),
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- JV Directory contacts (main directory table)
CREATE TABLE public.contacts (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT NOT NULL,
    company TEXT,
    business_focus TEXT,
    status TEXT CHECK (status IN ('Member', 'Non Member Resource', 'Pending')),
    service_provided TEXT,
    list_size INTEGER DEFAULT 0,
    business_size TEXT,
    social_reach INTEGER DEFAULT 0,
    email TEXT,
    phone TEXT,
    website TEXT,
    linkedin TEXT,
    notes TEXT,
    tags TEXT[],
    created_by UUID REFERENCES public.profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Business focus categories (normalized)
CREATE TABLE public.business_categories (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Service types (normalized)
CREATE TABLE public.service_types (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contact-to-category mapping (many-to-many)
CREATE TABLE public.contact_categories (
    contact_id UUID REFERENCES public.contacts(id) ON DELETE CASCADE,
    category_id UUID REFERENCES public.business_categories(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, category_id)
);

-- Contact-to-service mapping (many-to-many)
CREATE TABLE public.contact_services (
    contact_id UUID REFERENCES public.contacts(id) ON DELETE CASCADE,
    service_id UUID REFERENCES public.service_types(id) ON DELETE CASCADE,
    PRIMARY KEY (contact_id, service_id)
);

-- User favorites/saved contacts
CREATE TABLE public.favorites (
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES public.contacts(id) ON DELETE CASCADE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, contact_id)
);

-- Contact interaction history
CREATE TABLE public.interactions (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES public.contacts(id) ON DELETE CASCADE,
    interaction_type TEXT CHECK (interaction_type IN ('email', 'call', 'meeting', 'note', 'other')),
    description TEXT,
    interaction_date TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Import history (track CSV imports)
CREATE TABLE public.import_history (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id UUID REFERENCES public.profiles(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    records_imported INTEGER DEFAULT 0,
    records_skipped INTEGER DEFAULT 0,
    status TEXT CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

CREATE INDEX idx_contacts_name ON public.contacts(name);
CREATE INDEX idx_contacts_company ON public.contacts(company);
CREATE INDEX idx_contacts_status ON public.contacts(status);
CREATE INDEX idx_contacts_business_focus ON public.contacts USING GIN(to_tsvector('english', business_focus));
CREATE INDEX idx_contacts_service_provided ON public.contacts USING GIN(to_tsvector('english', service_provided));
CREATE INDEX idx_contacts_tags ON public.contacts USING GIN(tags);
CREATE INDEX idx_favorites_user ON public.favorites(user_id);
CREATE INDEX idx_interactions_user ON public.interactions(user_id);
CREATE INDEX idx_interactions_contact ON public.interactions(contact_id);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.favorites ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_history ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can read all profiles, update their own
CREATE POLICY "Profiles are viewable by authenticated users"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (auth.uid() = id);

-- Contacts: All authenticated users can read, admins can write
CREATE POLICY "Contacts are viewable by authenticated users"
    ON public.contacts FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "Admins can insert contacts"
    ON public.contacts FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can update contacts"
    ON public.contacts FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

CREATE POLICY "Admins can delete contacts"
    ON public.contacts FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND role = 'admin'
        )
    );

-- Favorites: Users manage their own favorites
CREATE POLICY "Users can view their own favorites"
    ON public.favorites FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can add favorites"
    ON public.favorites FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can remove their favorites"
    ON public.favorites FOR DELETE
    TO authenticated
    USING (user_id = auth.uid());

-- Interactions: Users manage their own interactions
CREATE POLICY "Users can view their own interactions"
    ON public.interactions FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can add interactions"
    ON public.interactions FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can update their own interactions"
    ON public.interactions FOR UPDATE
    TO authenticated
    USING (user_id = auth.uid());

-- Import history: Users see their own imports
CREATE POLICY "Users can view their own imports"
    ON public.import_history FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

CREATE POLICY "Users can create imports"
    ON public.import_history FOR INSERT
    TO authenticated
    WITH CHECK (user_id = auth.uid());

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER contacts_updated_at
    BEFORE UPDATE ON public.contacts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Auto-create profile on user signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1))
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- Full-text search function
CREATE OR REPLACE FUNCTION search_contacts(search_query TEXT)
RETURNS SETOF public.contacts AS $$
BEGIN
    RETURN QUERY
    SELECT *
    FROM public.contacts
    WHERE
        name ILIKE '%' || search_query || '%'
        OR company ILIKE '%' || search_query || '%'
        OR business_focus ILIKE '%' || search_query || '%'
        OR service_provided ILIKE '%' || search_query || '%'
    ORDER BY name;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- DEFAULT DATA (Business Categories)
-- ============================================

INSERT INTO public.business_categories (name) VALUES
    ('Business Skills'),
    ('Self Improvement'),
    ('Success'),
    ('Health (Traditional)'),
    ('Mental Health'),
    ('Natural Health'),
    ('Fitness'),
    ('Lifestyle'),
    ('Personal Finances'),
    ('Relationships'),
    ('Spirituality'),
    ('Service Provider')
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- DEFAULT DATA (Service Types)
-- ============================================

INSERT INTO public.service_types (name) VALUES
    ('Business Coaching'),
    ('Business Consulting'),
    ('Marketing Expert'),
    ('Podcast Host'),
    ('Public Speaking'),
    ('Content Marketing'),
    ('Social Media Marketing'),
    ('Lead Generation'),
    ('Event Hosting'),
    ('Book Publishing'),
    ('Course Creation'),
    ('Affiliate Marketing'),
    ('Website Design'),
    ('Video Marketing'),
    ('Email Marketing'),
    ('Copywriting')
ON CONFLICT (name) DO NOTHING;
