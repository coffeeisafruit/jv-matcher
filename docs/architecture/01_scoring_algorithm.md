# V1 Scoring Algorithm & Math

## The Golden Rule: Reciprocity
We do NOT use arithmetic averages. We use the **Harmonic Mean** to penalize lopsided matches.

Why? If User A is a perfect match for User B (score 100), but User B has zero interest in User A (score 0), the arithmetic average gives 50 - a mediocre but passing score. The Harmonic Mean gives 0 - correctly identifying this as a worthless match.

## The Formula

### 1. Calculate Directional Score (A → B)

```
Score_AB = (0.45 * Intent) + (0.25 * Synergy) + (0.20 * Momentum) + (0.10 * Context)
```

### Component Breakdown

#### A. Intent (45% weight)
The most important signal: Does A need what B offers?

```python
def calculate_intent_score(profile_a_needs, profile_b_offers):
    """Binary intent matching - 1.0 if need matches offer, else 0.0"""
    if semantic_match(profile_a_needs, profile_b_offers):
        return 1.0
    return 0.0
```

- IF A.Need matches B.Offer (semantic) = **1.0**
- ELSE = **0.0**

Uses GPT-4o-mini for semantic matching. Falls back to keyword overlap if no API key.

#### B. Synergy (25% weight) - The "Upstream/Downstream" Logic

Synergy score depends on **relationship type requested** AND **niche comparison**.

```python
def calculate_synergy_score(niche_a, niche_b, match_preference, reach_a, reach_b):
    niche_score = calculate_niche_score(niche_a, niche_b, match_preference)
    scale_modifier = calculate_scale_symmetry(reach_a, reach_b, match_preference)
    return niche_score * scale_modifier
```

**Niche Logic:**

| Scenario | Match Preference | Niche Comparison | Score |
|----------|-----------------|------------------|-------|
| Health Coach ↔ Health Coach | Peer/Bundle | Identical | **1.0** |
| Health Coach ↔ Health Coach | Referral Partner | Identical | **0.1** (Competitor!) |
| Health Coach ↔ Lab Testing | Peer/Bundle | Different | **0.2** |
| Health Coach ↔ Lab Testing | Referral Partner | Client-Adjacent | **0.9** |

**Niche Score Rules:**
- **Peer/Bundle + Identical Niche** → Score 1.0
- **Referral + Client-Adjacent** (LLM semantic check) → Score 0.9
- **Referral + Identical Niche** → Score 0.1 (Competitor Penalty)
- **Service Provider** → Score 0.7 (Neutral)

#### Scale Symmetry Addendum

**Why:** B2B Partners usually want to match with peers of similar distribution power.

```python
def calculate_scale_symmetry(reach_a, reach_b, match_preference):
    """
    Ratio = Min(A,B) / Max(A,B)
    - R > 0.5 (similar): No penalty (1.0)
    - R < 0.1 (10x diff): Penalty (0.5)
    """
    if match_preference == 'Service_Provider':
        return 1.0  # Services don't need scale symmetry

    if reach_a == 0 or reach_b == 0:
        return 0.8  # Unknown - slight penalty

    ratio = min(reach_a, reach_b) / max(reach_a, reach_b)

    if ratio > 0.5:
        return 1.0  # Similar scale
    elif ratio < 0.1:
        return 0.5  # 10x+ difference - penalty
    else:
        return 0.5 + (ratio - 0.1) * (0.5 / 0.4)  # Linear interpolation
```

**Reach Calculation:**
```
Reach = List Size + Social Reach
```

#### C. Momentum (20% weight) - Time Decay

```python
import math

def calculate_momentum_score(last_active_at):
    """Time decay: e^(-0.02 * days_since_active)"""
    if not last_active_at:
        return 0.5  # Neutral for unknown

    days = (now - last_active_at).days
    return math.exp(-0.02 * max(0, days))
```

**Decay Curve:**
- User active today = **1.0**
- User active 30 days ago = **~0.55** (Gold Zone)
- User active 45 days ago = **~0.41**
- User active 90 days ago = **~0.17**

#### D. Context (10% weight)

```python
def calculate_context_score(profile_a_events, profile_b_events):
    """Bonus if attended the same Event ID or Breakout Room"""
    shared = profile_a_events.intersection(profile_b_events)
    return min(1.0, len(shared) * 0.25)  # +0.25 per shared event, max 1.0
```

### 2. Calculate Final Reciprocal Score

```python
def calculate_harmonic_mean(score_ab, score_ba):
    """Reciprocal scoring - penalizes lopsided matches"""
    if score_ab + score_ba == 0:
        return 0.0
    return (2 * score_ab * score_ba) / (score_ab + score_ba)
```

**Formula:**
```
FinalScore = (2 * Score_AB * Score_BA) / (Score_AB + Score_BA)
```

**Examples:**
- Both 80 → HM = 80
- 100 and 60 → HM = 75 (penalized from avg of 80)
- 100 and 0 → HM = 0 (correctly killed)

## Trust Level Weighting

The final score is multiplied by a trust modifier based on data source:

| Trust Level | Source | Modifier |
|-------------|--------|----------|
| Platinum | Verified Micro-Intake | 1.0x |
| Gold | Profile Fields (Manual Entry) | 0.5x |
| Bronze | AI-Extracted from Transcripts | 0.3x |
| None | No Data | 0.1x |

## Fairness Constraints (Post-Processing)

### 1. Popularity Cap

```python
POPULARITY_CAP = 5  # Max appearances in Top 3 per cycle

def apply_popularity_cap(all_matches, match_cycle_id):
    appearance_count = defaultdict(int)
    filtered = []

    for match in sorted(all_matches, key=lambda x: x['harmonic_mean'], reverse=True):
        suggested_id = match['suggested_profile_id']
        rank = match.get('rank', 99)

        if rank <= 3:
            if appearance_count[suggested_id] >= POPULARITY_CAP:
                continue  # Skip - over-represented
            appearance_count[suggested_id] += 1

        filtered.append(match)

    return filtered
```

**Rule:** A single User ID cannot appear in the "Top 3" recommendation list for more than 5 distinct users per cycle.

### 2. Diversity Injection (V2)

If a user has no strong 1:1 match, place them in a curated "Fallback Pod" rather than leaving them unmatched.

## Match Reason String

Every match must include an explainable reason:

```python
def generate_reason(target, candidate, components):
    parts = []

    if components['intent'] > 0.5:
        parts.append(f"You need what {candidate['name']} offers")

    if components['synergy'] > 0.7:
        parts.append("Strong business alignment")

    if components['momentum'] > 0.8:
        parts.append("Very active recently")

    if components['context'] > 0:
        parts.append("Attended same event(s)")

    if components['trust_level'] == 'platinum':
        parts.append("✅ Verified intent")

    return ". ".join(parts)
```

**Example Output:**
> "Matched because: You need [Podcast Booking] and they offer [Podcast Guest Coordination]. You share the [Health & Wellness] audience. ✅ Verified Active"
