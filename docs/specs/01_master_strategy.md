# JV MatchMaker - Master Strategy & Research Synthesis

## The Core Thesis
We are shifting from a "Directory" (Passive) to an "Active Orchestration Engine."
Research confirms that B2B collaboration requires "Reciprocal Recommendation," not simple search.

## The "Extract → Verify → Match → Learn" Loop

### 1. Extract
Use LLMs to parse transcripts/chat for *potential* intent.
- Input: Raw VTT/transcript files from networking events
- Output: Suggested offers, needs, and context per speaker
- Trust Level: Bronze (inferred, not verified)

### 2. Verify
Use a 60-second Micro-Intake to confirm intent.
- **CRITICAL:** Do not match on inferred data alone. Verified data > Inferred data.
- Pre-fill the form with AI suggestions
- User confirms/edits to create Platinum-level data
- Triggered per-event (not monthly)

### 3. Match
Use a Hybrid Rule-Based engine (V1) prioritizing "Mutual Fit" (Harmonic Mean).
- Calculate bidirectional scores (A→B and B→A)
- Apply Harmonic Mean to penalize lopsided matches
- Enforce Popularity Cap to prevent "rich get richer" bias
- Generate explainable match reasons

### 4. Learn (V2+)
Use feedback loops to train future Ranking Models.
- Track match outcomes (Accepted/Rejected, Star Rating)
- Train XGBoost to learn personalized weights
- Graduate to Graph Neural Networks for network effects

## Validated Assumptions (Research Findings)

### Recency
30 days is the "Gold Zone." Use time-decay scoring (Half-Life), not binary cutoffs.
- Formula: `e^(-0.02 * days_since_active)`
- Active today = 1.0
- 30 days ago = ~0.55
- 90 days ago = ~0.17

### Fairness
"Popularity Bias" kills retention. We must cap the number of times a popular user appears in matches.
- Rule: Max 5 appearances in Top 3 per match cycle
- Fallback: Place unmatched users in curated pods

### Trust
Explainability is mandatory. Users must see "Why" they matched.
- Every match includes a human-readable reason string
- Score breakdown available on request

### Scale Symmetry
B2B partners prefer peers of similar distribution power.
- 50k+ list owner won't partner well with 100-person list
- Apply penalty when reach ratio < 0.1 (10x difference)
- Exception: Service Provider relationships ignore scale

## The Definition of "World Class"

### V1: Foundation (Now)
- 100% Verified Intent (No hallucinations)
- Explainable matches with reason strings
- Reciprocal scoring via Harmonic Mean
- Scale Symmetry checks

### V2: Learning (Months 4-8)
- Learning-to-Rank (XGBoost) based on meeting outcomes
- Personalized weight optimization per user
- Dynamic "Reliability Scores"

### V3: Network Intelligence (Month 9+)
- Graph Neural Networks (GNN) for latent link prediction
- "Cold Start" elimination via follow patterns
- Ecosystem mapping and bridge detection
