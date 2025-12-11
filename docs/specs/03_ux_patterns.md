# UX & "World Class" Patterns

## 1. The "Confidence" Intake (Per-Event)

### Pattern
Pre-fill the form using AI extraction from transcripts. User confirms to create Platinum trust data.

### Trigger
Called automatically after transcript processing completes (per-event, not monthly).

### UI Flow

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  🎯 Post-Event Check-in: December JV Mastermind               │
│  ─────────────────────────────────────────────────────────────│
│                                                                │
│  Confirm what you're offering and seeking to get better matches│
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ What are you offering right now? (Max 2)                 │ │
│  │                                                          │ │
│  │ We detected these from your conversations. Confirm/edit: │ │
│  │                                                          │ │
│  │ Offer 1: [Podcast guest spots________________]          │ │
│  │ Offer 2: [Email list promotion_______________]          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ What are you seeking right now? (Max 2)                  │ │
│  │                                                          │ │
│  │ Need 1: [Video editor_______________________]           │ │
│  │ Need 2: [JV partners with 10k+ lists________]           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ─────────────────────────────────────────────────────────────│
│                                                                │
│  What type of partner are you looking for?                    │
│                                                                │
│  ○ 🤝 Peer/Bundle - Same niche, let's collaborate            │
│  ● ⬆️ Referral Partner - Serves clients BEFORE they need me  │
│  ○ ⬇️ Referral Partner - Serves clients AFTER they work with │
│  ○ 🔧 Service Provider - A vendor/service I need              │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │           ✅ Confirm & Update My Matches                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Constraints
- **Max 2 Offers, Max 2 Needs** - Force prioritization
- **Match Preference Required** - Drives Synergy Score logic
- **60 seconds max** - Quick confirmation, not a survey

### Success State
```
✅ Preferences saved! Regenerating your matches with verified data...
```

## 2. The Match Card

### Mandatory Elements
Every match card MUST display:
- Partner name and company
- Match score (0-100)
- **Match Reason String** (The "Why")
- **Verified Active Badge** (if active in last 30 days)
- Trust level indicator

### UI Layout

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  Sarah Johnson                                    Score: 87    │
│  Wellness Media Co.                              ───────────── │
│                                                                │
│  ─────────────────────────────────────────────────────────────│
│                                                                │
│  💡 Matched because:                                          │
│  You need [Video Editor] and they offer [Video Production].   │
│  You share the [Health & Wellness] audience.                  │
│  ✅ Verified Active (last seen 3 days ago)                    │
│                                                                │
│  ─────────────────────────────────────────────────────────────│
│                                                                │
│  ▶ Score Breakdown                                            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Intent:   ████████████████████ 95%                       │ │
│  │ Synergy:  ████████████████░░░░ 80%                       │ │
│  │ Momentum: ██████████████████░░ 90%                       │ │
│  │ Context:  ██████████░░░░░░░░░░ 50%                       │ │
│  │                                                          │ │
│  │ A→B Score: 85.2                                         │ │
│  │ B→A Score: 89.1                                         │ │
│  │ Harmonic Mean: 87.1/100                                 │ │
│  │                                                          │ │
│  │ ✅ Based on verified preferences                         │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ─────────────────────────────────────────────────────────────│
│                                                                │
│  📧 Outreach Message (AI-Generated)                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ Hi Sarah,                                                │ │
│  │                                                          │ │
│  │ JV MatchMaker connected us because we both focus on      │ │
│  │ Health & Wellness. I noticed you offer video production  │ │
│  │ services - I'm looking for exactly that for my upcoming  │ │
│  │ course launch.                                           │ │
│  │                                                          │ │
│  │ Would you be open to a 15-min chat this week?           │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  [📧 Send Email]  [📋 Copy Message]                           │
│                                                                │
│  ─────────────────────────────────────────────────────────────│
│                                                                │
│  [Mark Viewed]  [Connect]  [Dismiss]                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Trust Level Indicators

| Trust Level | Badge | Color |
|-------------|-------|-------|
| Platinum | ✅ Based on verified preferences | Green |
| Gold | ℹ️ Based on profile data | Blue |
| Legacy | ⚠️ Complete intake for better matches | Yellow |

### Activity Badges

| Status | Badge | Threshold |
|--------|-------|-----------|
| Very Active | ✅ Verified Active | < 7 days |
| Active | 🟢 Active | 7-30 days |
| Less Active | 🟡 Less active | 30-60 days |
| Inactive | 🔴 Last seen 60+ days ago | > 60 days |

## 3. The "No-Ghost" Connector

### Pattern
Clicking "Accept" or "Send Email" generates a personalized draft message.

### Default Template
```
Hi [Name],

MatchMaker connected us because we both focus on [Niche].
[Specific reason from match context]

Would you be open to a 15-min chat?

Best,
[Your Name]
```

### Template Variables
- `[Name]` - Match partner's name
- `[Niche]` - Shared audience/niche
- `[Your Name]` - Current user's name
- `[Specific reason]` - From match_reason field

### Email Integration
```python
def generate_mailto_link(suggested, user_profile, outreach_message):
    subject = f"Partnership Opportunity - {user_profile['name']}"
    body = outreach_message
    email = suggested.get('email', '')

    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"
```

## 4. Admin Match Overview

### Post-Processing Display
After transcript processing, show admin the top discovered connections:

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│  🤝 Top Connections Discovered                                │
│  Here are some of the best matches from this transcript:      │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ John Smith ↔ Sarah Johnson — Score: 92/100             │   │
│  │                                                        │   │
│  │ John Smith             Sarah Johnson                   │   │
│  │ TechCo Inc.            Wellness Media                  │   │
│  │                                                        │   │
│  │ Why they match:                                        │   │
│  │ John seeks video editing, Sarah offers video production│   │
│  │                                                        │   │
│  │ When topics were mentioned:                            │   │
│  │ • John mentioned seeking at December Mastermind        │   │
│  │ • Sarah mentioned offering at November Workshop        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## 5. Onboarding Flow (The "Magic" Experience)

### Ideal First-Time Experience

1. **User Login**
   ```
   Welcome back, Sarah!
   ```

2. **System Recognition** (from CSV/Database)
   ```
   We see you run Wellness Media Co. and focus on Health & Fitness content.
   ```

3. **Context Injection** (from Transcripts - Bronze)
   ```
   In the last call, you mentioned you were looking for Podcast Guests.
   Is that still a priority?
   ```

4. **Scale Awareness** (from CSV)
   ```
   We also see you have a reach of ~50k.
   We have queued 3 matches with similar audience sizes.
   ```

5. **Confirmation Prompt**
   ```
   Click "Confirm" to see your personalized matches.
   [Confirm Preferences]
   ```

This feels like magic because we did the heavy lifting of data fusion in the background.
