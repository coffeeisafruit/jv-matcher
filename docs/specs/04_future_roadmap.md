# Future Roadmap (V2 & V3)

## Evolution Path

| Phase | Theme | Timeline | Core Tech |
|-------|-------|----------|-----------|
| V1 | Trust & Accuracy | Now | Rule-based + Harmonic Mean |
| V2 | Learning & Optimization | Months 4-8 | XGBoost (Learning-to-Rank) |
| V3 | Network Intelligence | Month 9+ | Graph Neural Networks |

---

## Phase 2: The Learning Engine (Target: Months 4-8)

### Goal
Replace hard-coded weights with Machine Learning to create personalized matching.

### The Shift

| Component | V1 (Current) | V2 (Future) |
|-----------|--------------|-------------|
| Weights | Hard-coded (Intent=0.45, etc.) | Learned per-user via XGBoost |
| Pods | Manual/random fallback | K-Means clustering (skills + audience) |
| Fairness | Static popularity cap | Dynamic "Reliability Score" |

### 1. The Data Fuel: "Outcome Labels"

We stop just tracking "Matches Created" and start tracking "Successful Outcomes."

**New Data Points:**
- Did they accept the meeting? (Binary: 0/1)
- Did they rate it 4+ stars? (Quality Score: 1-5)
- Did they flag "No Show"? (Reliability Score)
- Did a deal result? (Revenue outcome)

**New Table: `match_outcomes`**
```sql
CREATE TABLE match_outcomes (
    id UUID PRIMARY KEY,
    match_id UUID REFERENCES match_suggestions(id),
    meeting_accepted BOOLEAN,
    meeting_happened BOOLEAN,
    star_rating INTEGER CHECK (star_rating BETWEEN 1 AND 5),
    no_show_flag BOOLEAN DEFAULT FALSE,
    deal_closed BOOLEAN,
    deal_value DECIMAL,
    feedback_text TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. The Engine Upgrade: Learning-to-Rank (LTR)

**Technology:** XGBoost / LightGBM Gradient Boosting

**How it works:**
1. Collect features: Intent match, Synergy score, Momentum, Context, Scale ratio
2. Collect labels: Meeting accepted (Y/N), Star rating
3. Train model to predict P(Accept) based on features
4. Weights become personalized per user

**Example:**
- If User A ignores "Peer Bundles" but always accepts "Service Providers"
- The model lowers Synergy weight and raises Intent weight for User A specifically
- Evolution from "One Algorithm for Everyone" to "Personalized Ranking"

### 3. New Feature: "Smart Pods"

**V1 Pods:** Manual/random fallback for unmatched users

**V2 Pods:** Clustering Algorithms (K-Means) to automatically group 3 people who have:
- Different Skills (Writer + Designer + Marketer)
- Same Audience (e.g., "SaaS Founders")
- Compatible Timezones

**Algorithm:**
```python
from sklearn.cluster import KMeans

features = [skill_embedding, audience_embedding, timezone_offset]
kmeans = KMeans(n_clusters=num_pods)
pod_assignments = kmeans.fit_predict(features)
```

---

## Phase 3: The Graph Mind (Target: Month 9+)

### Goal
Latent Link Prediction & Community Structure using Graph Science.

### The Shift

| Component | V2 | V3 |
|-----------|-----|-----|
| Matching | Feature-based ML | Graph Neural Networks |
| Cold Start | Requires intake form | Inferred from follow patterns |
| Discovery | Search-based | "People You May Know" predictions |

### 1. The Engine Upgrade: Graph Neural Networks (GNN)

**Technology:** GraphSAGE or Node2Vec

**The Paradigm Shift:**
- V1/V2: Match Profile Text vs. Profile Text
- V3: Match Node vs. Node in a relationship graph

**Data Model:**
```
Nodes: Users (profiles)
Edges:
  - Previous matches (weighted by outcome)
  - Event co-attendance
  - Explicit connections
  - Email interactions
```

### 2. The Magic: Link Prediction

**Triadic Closure:**
```
If A matches well with B
And B matches well with C
Then A should meet C
```

This is the same tech LinkedIn uses for "People You May Know."

**Implementation:**
```python
import networkx as nx
from node2vec import Node2Vec

# Build graph
G = nx.Graph()
G.add_edges_from(previous_matches)
G.add_edges_from(co_attendance)

# Generate embeddings
node2vec = Node2Vec(G, dimensions=64, walk_length=30, num_walks=200)
model = node2vec.fit(window=10, min_count=1)

# Predict links
def predict_link(user_a, user_b):
    embedding_a = model.wv[user_a]
    embedding_b = model.wv[user_b]
    return cosine_similarity(embedding_a, embedding_b)
```

### 3. New Feature: "Cold Start" Elimination

**V1 Problem:** New user needs to fill out forms to get matches

**V3 Solution:**
- New user joins and immediately follows "User X"
- Graph Engine infers their niche/interests based on User X's cluster
- Generate matches instantly without zero data entry

**Algorithm:**
```python
def cold_start_embedding(new_user, followed_users):
    # Average the embeddings of followed users
    followed_embeddings = [model.wv[u] for u in followed_users]
    new_user_embedding = np.mean(followed_embeddings, axis=0)
    return new_user_embedding
```

### 4. New Feature: "Ecosystem Mapping"

**Visualization:**
- "Here is the cluster of Health Coaches"
- "Here is the cluster of SaaS Founders"
- "Here are the Marketing Agencies"

**Bridge Detection:**
- Identify "Super-Connectors" who link two different clusters
- Give them special VIP status or tools
- These are the most valuable community members

**Metrics:**
```python
def identify_bridges(G):
    betweenness = nx.betweenness_centrality(G)
    bridges = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)
    return bridges[:10]  # Top 10 super-connectors
```

---

## Code Architecture Notes

### V1 Design Principles (For Future Compatibility)

1. **Modular Scoring Functions**
   - Each component (Intent, Synergy, Momentum, Context) is a separate function
   - Easy to swap rule-based logic for ML predictions

2. **Feature Extraction Layer**
   - All features computed independently
   - Can be fed to XGBoost in V2 without refactoring

3. **Outcome Tracking Ready**
   - `match_suggestions` table has status tracking
   - Adding `match_outcomes` table is additive, not breaking

4. **Graph-Ready Data Model**
   - `connections` table stores explicit relationships
   - `match_suggestions` stores implicit relationships
   - Easy to build NetworkX graph from existing tables

### Migration Path

```
V1 (Now)           V2 (Months 4-8)        V3 (Month 9+)
─────────────────────────────────────────────────────────
Rule-based         XGBoost ranking        GraphSAGE
Harmonic Mean      Personalized weights   Link prediction
Static weights     Dynamic learning       Emergent clusters
Manual pods        K-Means pods           Community detection
```

---

## Analyst Note

**Stick to V1 for now.**

V1 solves the user's problem today:
- Trust through verification
- Fairness through popularity caps
- Explainability through reason strings

V2/V3 solves your scaling problems tomorrow:
- When you have 1000+ users
- When you have outcome data to learn from
- When the network effect becomes valuable

But keeping this roadmap file ensures your codebase doesn't become a mess of spaghetti code that prevents you from upgrading later.
