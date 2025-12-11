# Data Signal Blueprint

## The "Holy Trinity" of Matching Data

A world-class matching engine requires three data sources:

1. **Structured Truth (Database/CSV):** Demographics, Niche, List Size, Social Reach
2. **Unstructured Context (Transcripts):** Current sentiment, urgent needs, voice
3. **Verified Intent (Micro-Intake):** User confirmation of offers/needs per event

## Signal Matrix

| Signal Source | Data Type | Trust Level | Weight Modifier | Usage |
|:--- |:--- |:--- |:--- |:--- |
| **Micro-Intake** | Verified Offer/Need | Platinum | 1.0x | Hard Filter (Primary Key) |
| **Micro-Intake** | Relationship Type | Platinum | 1.0x | Determines Scoring Logic (Peer vs. Referral) |
| **Directory/CSV** | Niche/Audience | Gold | 0.5x | Constraint Matching |
| **Directory/CSV** | List Size / Social Reach | Gold | 0.5x | Scale Symmetry Check |
| **Attendance** | Last Active Date | Silver | N/A | Momentum Weighting |
| **Transcripts** | Inferred Interests | Bronze | 0.3x | Suggestion for Intake Form (Pre-fill) |

## Trust Level Definitions

### Platinum Trust (1.0x)
- **Source:** User explicitly confirmed via Micro-Intake form
- **Confidence:** 100% - User said "Yes, this is what I want"
- **Refresh:** Per-event (triggered after each networking session)
- **Example:** "I am offering podcast guest spots. I am seeking a video editor."

### Gold Trust (0.5x)
- **Source:** Directory CSV / Manual profile entry
- **Confidence:** 70% - Data is real but may be outdated
- **Refresh:** Whenever user updates profile
- **Example:** Company name, business focus, list size

### Silver Trust (N/A - used for momentum only)
- **Source:** Event attendance records, login timestamps
- **Confidence:** 90% - System-generated, accurate
- **Usage:** Momentum decay calculation only
- **Example:** "Last attended December 5, 2025"

### Bronze Trust (0.3x)
- **Source:** AI extraction from transcripts
- **Confidence:** 40% - Inferred, may have errors
- **Usage:** Pre-fill suggestions, NOT for direct matching
- **Example:** "Based on your conversation, you mentioned seeking a publisher"

## Required Database Entities

### profiles (Extended)
```sql
-- Base fields (existing)
id UUID PRIMARY KEY
name TEXT NOT NULL
email TEXT
company TEXT
business_focus TEXT
service_provided TEXT
status TEXT  -- 'Member', 'Non Member Resource', 'Pending'

-- Scale Symmetry fields (for B2B tiering)
list_size INTEGER DEFAULT 0
social_reach INTEGER DEFAULT 0
business_size TEXT

-- Rich profile fields (for matching)
what_you_do TEXT
who_you_serve TEXT
seeking TEXT
offering TEXT
current_projects TEXT

-- V1 Additions
niche TEXT                    -- Normalized business category
audience_type TEXT            -- Who they serve (for Synergy calculation)
last_active_at TIMESTAMPTZ    -- For Momentum scoring
```

### intake_submissions (NEW - Platinum Data)
```sql
id UUID PRIMARY KEY
profile_id UUID REFERENCES profiles(id)
event_id TEXT                 -- e.g., "mastermind-dec-2025"
event_name TEXT               -- "December JV Mastermind"
event_date DATE

-- Verified data (max 2 each to force prioritization)
verified_offers TEXT[] CHECK (array_length(verified_offers, 1) <= 2)
verified_needs TEXT[] CHECK (array_length(verified_needs, 1) <= 2)

-- Match preference drives Synergy Score logic
match_preference TEXT CHECK (match_preference IN (
    'Peer_Bundle',
    'Referral_Upstream',
    'Referral_Downstream',
    'Service_Provider'
))

-- AI suggestions (Bronze trust - for pre-fill)
suggested_offers TEXT[]
suggested_needs TEXT[]

-- Timestamps
confirmed_at TIMESTAMPTZ      -- NULL until user confirms
created_at TIMESTAMPTZ
```

### match_suggestions (Extended)
```sql
-- Existing fields
id UUID PRIMARY KEY
profile_id UUID               -- Who the match is FOR
suggested_profile_id UUID     -- Who was suggested
match_score DECIMAL(5,2)      -- Final score (0-100)
match_reason TEXT             -- The "Why" string
source TEXT                   -- 'v1_matcher', 'hybrid_matcher'
status TEXT                   -- 'pending', 'viewed', 'contacted', 'connected', 'dismissed'

-- V1 Additions
score_ab DECIMAL(5,2)         -- A→B directional score
score_ba DECIMAL(5,2)         -- B→A directional score
harmonic_mean DECIMAL(5,2)    -- Final reciprocal score
scale_symmetry_score DECIMAL(5,2)  -- For analytics
trust_level TEXT              -- 'platinum', 'gold', 'bronze', 'legacy'
```

### match_popularity (NEW - Fairness Tracking)
```sql
id UUID PRIMARY KEY
profile_id UUID REFERENCES profiles(id)
match_cycle_id TEXT           -- e.g., "2025-01-cycle"
top_3_appearances INTEGER     -- How many Top 3 lists they appear in
created_at TIMESTAMPTZ
```

## Entity Resolution (Fuzzy Matching)

The challenge: CSV says "Robert Smith" but Zoom transcript says "Bob Smith"

### Resolution Strategy

```python
from difflib import SequenceMatcher

FUZZY_THRESHOLD = 0.80  # 80% similarity required

def normalize_name(name: str) -> str:
    """Normalize for matching"""
    return " ".join(name.lower().strip().split())

def fuzzy_match(name1: str, name2: str) -> float:
    """Calculate name similarity (0-1)"""
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    return SequenceMatcher(None, n1, n2).ratio()
```

### Match Priority

1. **Email Match** (100% confidence) - Same email = same person
2. **Name + Company Match** (90% confidence) - Both match
3. **Exact Name Match** (70% confidence) - Names identical
4. **Fuzzy Name Match** (50-70% confidence) - Names similar
5. **No Match** → Flag for manual review (don't create duplicates)

## Data Flow Summary

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Raw VTT Files  │────▶│  batch_extract   │────▶│ processed.json  │
│  (data/raw/)    │     │  (GPT-4o-mini)   │     │ (Bronze Trust)  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
┌─────────────────┐     ┌──────────────────┐              │
│  members.csv    │────▶│  seed_and_fuse   │◀─────────────┘
│  (Gold Trust)   │     │  (Fuzzy Match)   │
└─────────────────┘     └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │    profiles DB   │
                        │  (Base Records)  │
                        └────────┬─────────┘
                                 │
                                 ▼
┌─────────────────┐     ┌──────────────────┐
│  Micro-Intake   │────▶│ intake_submissions│
│  (User Confirms)│     │ (Platinum Trust) │
└─────────────────┘     └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ V1MatchGenerator │
                        │ (Harmonic Mean)  │
                        └────────┬─────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │ match_suggestions│
                        │  (Final Output)  │
                        └──────────────────┘
```
