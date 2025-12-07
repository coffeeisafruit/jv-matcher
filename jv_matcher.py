"""
JV Matcher - Complete AI-Powered Matching Engine
This file contains all the logic for profile extraction and matching
"""

import os
import json
import re
from openai import OpenAI
from datetime import datetime


def clean_json_string(text):
    """Clean common JSON formatting issues from AI responses"""
    # Remove any markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)

    # Fix trailing commas before ] or }
    text = re.sub(r',\s*]', ']', text)
    text = re.sub(r',\s*}', '}', text)

    # Remove control characters except \n \r \t
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

    # Fix common issues with newlines in strings
    # Replace actual newlines inside strings with \n escape
    lines = text.split('\n')
    text = ' '.join(lines)

    # Fix multiple spaces
    text = re.sub(r'  +', ' ', text)

    return text


def extract_json_array(text):
    """Try multiple methods to extract JSON array from text"""
    print(f"🔍 Attempting to extract JSON from {len(text)} chars of text")
    print(f"📄 First 200 chars of response: {text[:200]}")

    # Method 1: Find [ and ] directly
    start = text.find('[')
    end = text.rfind(']')

    print(f"📍 Found '[' at position {start}, ']' at position {end}")

    if start != -1 and end != -1 and end > start:
        json_str = text[start:end + 1]
        json_str = clean_json_string(json_str)
        print(f"📋 Extracted JSON string length: {len(json_str)}")

        try:
            result = json.loads(json_str)
            print(f"✅ Method 1 success: parsed {len(result)} items")
            return result
        except json.JSONDecodeError as e:
            print(f"⚠️ Method 1 failed: {e}")

    # Method 2: Try to find JSON in code blocks
    code_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', text)
    if code_match:
        json_str = clean_json_string(code_match.group(1))
        try:
            result = json.loads(json_str)
            print(f"✅ Method 2 success: parsed {len(result)} items")
            return result
        except json.JSONDecodeError as e:
            print(f"⚠️ Method 2 failed: {e}")

    # Method 3: More aggressive - extract anything between first [ and last ]
    if start != -1 and end != -1:
        json_str = text[start:end + 1]
        # Remove all newlines and extra spaces
        json_str = re.sub(r'\s+', ' ', json_str)
        json_str = clean_json_string(json_str)

        try:
            result = json.loads(json_str)
            print(f"✅ Method 3 success: parsed {len(result)} items")
            return result
        except json.JSONDecodeError as e:
            print(f"❌ Method 3 failed: {e}")
            print(f"📄 First 500 chars of JSON: {json_str[:500]}")
            print(f"📄 Last 500 chars of JSON: {json_str[-500:]}")

    # Method 4: Try parsing individual objects if array fails
    print("🔄 Attempting Method 4: individual object extraction")
    objects = []
    obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    for match in re.finditer(obj_pattern, text):
        try:
            obj = json.loads(match.group())
            if 'name' in obj:  # Looks like a profile
                objects.append(obj)
        except json.JSONDecodeError:
            continue

    if objects:
        print(f"✅ Method 4 success: extracted {len(objects)} individual objects")
        return objects

    print("❌ All JSON extraction methods failed")
    return None

class JVMatcher:
    """AI-powered JV partner matching system"""

    def __init__(self, api_key=None):
        """Initialize with OpenRouter API key"""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set. Add it in Streamlit Secrets.")

        # Use OpenRouter with OpenAI-compatible API
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )
        # Use Qwen 2.5 7B (free) via OpenRouter
        self.model = "qwen/qwen-2.5-7b-instruct:free"
    
    def extract_profiles(self, transcript_content, chat_content):
        """Extract participant profiles from transcript and chat using Claude"""
        
        print(f"📄 Extracting profiles from {len(transcript_content)} chars transcript, {len(chat_content)} chars chat...")
        
        prompt = f"""Analyze this JV Directory networking meeting and extract detailed profiles for ALL participants who shared meaningful information.

TRANSCRIPT (what people said):
{transcript_content[:50000]}

CHAT LOG (contact info and offerings):
{chat_content[:20000]}

For each person who actively participated (introduced themselves, asked questions, shared their business), create a profile with these fields:

1. name - Full name (required)
2. business - Business/company name
3. what_they_do - What service/product they offer (2-3 sentences)
4. who_they_serve - Target market/ideal client
5. offerings - List of specific things they're offering (affiliates, speaking, partnerships, services)
6. seeking - List of what they need or are looking for
7. contact_info - Email, phone, LinkedIn, website, Calendly (from chat)
8. current_projects - Any launches, programs, or current initiatives mentioned
9. pain_points - Challenges or problems they mentioned
10. keywords - 5-10 relevant keywords for matching

Return ONLY a JSON array of profile objects. No preamble, no explanation - just the JSON array.

Example format:
[
  {{
    "name": "Jane Smith",
    "business": "Smith Coaching",
    "what_they_do": "Executive coach helping C-suite leaders...",
    "who_they_serve": "Fortune 500 executives and founders",
    "offerings": ["Executive coaching packages", "Speaking at corporate events", "Leadership workshops"],
    "seeking": ["Corporate partnership opportunities", "Speaking engagements", "Referral partners"],
    "contact_info": "jane@smithcoaching.com, LinkedIn: jane-smith-coach",
    "current_projects": "Launching new executive retreat program in Q1",
    "pain_points": "Looking for better lead generation strategies",
    "keywords": ["executive coaching", "leadership", "C-suite", "corporate training", "workshops"]
  }}
]

Extract at least 20-30 profiles if that many people participated. Focus on people who shared substantial information."""

        try:
            print(f"🤖 Calling model: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.choices[0].message.content
            print(f"📝 Got response ({len(content)} chars)")

            # Log the full response for debugging (first 1000 chars)
            print(f"📄 Response preview: {content[:1000]}...")

            # Extract JSON using robust parser
            profiles = extract_json_array(content)

            if profiles is None:
                print("❌ No JSON array found in response")
                print(f"📄 Full response was: {content[:2000]}")
                return []

            if len(profiles) == 0:
                print("⚠️ JSON parsed but array was empty")
                return []

            print(f"✅ Extracted {len(profiles)} profiles")
            # Log first profile as sample
            if profiles:
                print(f"📋 Sample profile: {json.dumps(profiles[0], indent=2)[:500]}")
            return profiles

        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {str(e)}")
            print("The AI returned malformed JSON. Try again or use a different model.")
            return []
        except Exception as e:
            print(f"❌ Error extracting profiles: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def generate_matches(self, person_profile, all_profiles, num_matches=10):
        """Generate top matches for one person using Claude"""
        
        person_name = person_profile.get('name', 'Unknown')
        print(f"  🔍 Generating matches for {person_name}...")
        
        # Filter out the person themselves and get sample of others
        others = [p for p in all_profiles if p.get('name') != person_name]
        
        if len(others) < 5:
            print(f"    ⚠️  Only {len(others)} other participants - skipping")
            return []
        
        # Limit to 50 profiles to stay within token limits
        others_sample = others[:50]
        
        prompt = f"""You are an expert at identifying strategic JV partnerships. Find the TOP {num_matches} best partnership matches for this person.

TARGET PERSON:
{json.dumps(person_profile, indent=2)}

POTENTIAL PARTNERS (find the best {num_matches} from these):
{json.dumps(others_sample, indent=2)}

For each of the top {num_matches} matches, provide:
1. partner_name - Their full name
2. score - Match quality score 0-100 (be realistic, use full range)
3. match_type - Type of partnership (e.g., "Affiliate Partnership", "Speaking Opportunity", "Referral Exchange")
4. why_good_fit - 2-3 specific sentences explaining why they're a good match
5. collaboration_opportunity - Specific, actionable collaboration idea
6. mutual_benefits - What each person gets from the partnership
7. revenue_potential - Realistic revenue estimate or opportunity description
8. urgency - Why they should connect soon (timing, current projects, etc.)
9. first_outreach_message - Ready-to-send personalized message (100-150 words) that the target person can send
10. contact_method - Their contact information

IMPORTANT MATCHING CRITERIA:
- Prioritize COMPLEMENTARY services (not competitors)
- Match stated NEEDS with available OFFERINGS
- Consider TARGET MARKET alignment
- Look for CURRENT PROJECT synergies
- Estimate realistic REVENUE potential
- Only include matches with score >= 60

Return ONLY a JSON array of the top {num_matches} matches, sorted by score (highest first). No preamble.

[
  {{
    "partner_name": "...",
    "score": 85,
    "match_type": "...",
    ...
  }}
]"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=8000,
                messages=[{"role": "user", "content": prompt}]
            )

            content = response.choices[0].message.content
            print(f"    📝 Got response ({len(content)} chars)")

            # Extract JSON using robust parser
            matches = extract_json_array(content)

            if matches is None:
                print(f"    ❌ No matches found for {person_name}")
                return []

            # Filter to only matches with score >= 60
            matches = [m for m in matches if m.get('score', 0) >= 60]

            print(f"    ✅ Found {len(matches)} quality matches")
            return matches

        except json.JSONDecodeError as e:
            print(f"    ❌ JSON parsing failed for {person_name}: {str(e)}")
            return []
        except Exception as e:
            print(f"    ❌ Error generating matches for {person_name}: {str(e)}")
            return []
    
    def process_files(self, transcript_files, chat_files, num_matches=10):
        """
        Process uploaded files and generate matches
        
        Args:
            transcript_files: List of transcript file objects
            chat_files: List of chat file objects
            num_matches: Number of matches to generate per person
            
        Returns:
            dict with profiles and matches
        """
        
        print("\n" + "="*70)
        print("🚀 STARTING JV MATCHING PROCESS")
        print("="*70)
        
        # Combine all transcripts
        all_transcript_content = ""
        for f in transcript_files:
            content = f.read().decode('utf-8')
            all_transcript_content += content + "\n\n"
            print(f"📄 Read transcript: {f.name} ({len(content):,} chars)")
        
        # Combine all chats
        all_chat_content = ""
        for f in chat_files:
            content = f.read().decode('utf-8')
            all_chat_content += content + "\n\n"
            print(f"💬 Read chat: {f.name} ({len(content):,} chars)")
        
        # Step 1: Extract profiles
        print("\n" + "-"*70)
        print("STEP 1: Extracting participant profiles...")
        print("-"*70)
        
        profiles = self.extract_profiles(all_transcript_content, all_chat_content)
        
        if not profiles:
            raise ValueError("No profiles extracted. Check your files contain participant information.")
        
        print(f"\n✅ Extracted {len(profiles)} profiles")
        
        # Step 2: Generate matches for each person
        print("\n" + "-"*70)
        print(f"STEP 2: Generating top {num_matches} matches for each person...")
        print("-"*70)
        
        results = {}
        
        for i, person in enumerate(profiles, 1):
            person_name = person.get('name', f'Person_{i}')
            print(f"\n[{i}/{len(profiles)}] Processing {person_name}...")
            
            matches = self.generate_matches(person, profiles, num_matches)
            
            results[person_name] = {
                'profile': person,
                'matches': matches,
                'match_count': len(matches)
            }
        
        print("\n" + "="*70)
        print("✅ MATCHING COMPLETE!")
        print(f"   Profiles: {len(profiles)}")
        print(f"   Total matches generated: {sum(r['match_count'] for r in results.values())}")
        print("="*70 + "\n")
        
        return results
    
    def generate_report(self, person_name, person_data):
        """Generate a formatted report for one person"""
        
        profile = person_data['profile']
        matches = person_data['matches']
        
        report = f"""# JV PARTNER MATCHING REPORT

**Participant:** {person_name}
**Generated:** {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

---

## YOUR PROFILE SUMMARY

**What you do:** {profile.get('what_they_do', 'N/A')}

**Who you serve:** {profile.get('who_they_serve', 'N/A')}

**What you're offering:**
"""
        
        for offering in (profile.get('offerings') or []):
            report += f"- {offering}\n"

        report += "\n**What you're seeking:**\n"
        for seeking in (profile.get('seeking') or []):
            report += f"- {seeking}\n"
        
        if profile.get('current_projects'):
            report += f"\n**Current projects:** {profile.get('current_projects')}\n"
        
        report += f"\n---\n\n## YOUR TOP {len(matches)} JV PARTNER MATCHES\n\n"
        
        for i, match in enumerate(matches, 1):
            report += f"""
### MATCH #{i}: {match.get('partner_name', 'Unknown')} 
**Score:** {match.get('score', 0)}/100 | **Type:** {match.get('match_type', 'Partnership')}

**WHY THIS IS A GOOD FIT:**
{match.get('why_good_fit', 'N/A')}

**COLLABORATION OPPORTUNITY:**
{match.get('collaboration_opportunity', 'N/A')}

**MUTUAL BENEFITS:**
{match.get('mutual_benefits', 'N/A')}

**REVENUE POTENTIAL:**
{match.get('revenue_potential', 'N/A')}

**WHY CONNECT NOW:**
{match.get('urgency', 'N/A')}

**READY-TO-SEND OUTREACH MESSAGE:**
```
{match.get('first_outreach_message', 'N/A')}
```

**CONTACT:** {match.get('contact_method', 'N/A')}

---
"""
        
        report += """
## NEXT STEPS

1. Review each recommended partner above
2. Reach out to those with highest match scores first
3. Use the ready-to-send messages (personalize as needed)
4. Mention specific collaboration opportunities when connecting
5. Follow up within 48 hours for best results

---

*Generated by JV Matcher - AI-Powered Partnership Matching*
"""
        
        return report
