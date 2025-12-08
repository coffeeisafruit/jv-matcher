"""
Match Generator - Creates JV partner suggestions based on profile data
Supports two modes:
1. Keyword matching (fast, no API needed)
2. AI matching via OpenRouter (higher quality, requires API key)
"""
import os
import json
import re
from typing import List, Dict, Set, Tuple, Optional
from directory_service import DirectoryService

# Optional OpenAI import for AI matching
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def clean_json_string(text):
    """Clean common JSON formatting issues from AI responses"""
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = re.sub(r',\s*]', ']', text)
    text = re.sub(r',\s*}', '}', text)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    lines = text.split('\n')
    text = ' '.join(lines)
    text = re.sub(r'  +', ' ', text)
    return text


def extract_json_array(text):
    """Extract JSON array from AI response text"""
    start = text.find('[')
    end = text.rfind(']')

    if start != -1 and end != -1 and end > start:
        json_str = text[start:end + 1]
        json_str = clean_json_string(json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Try more aggressive cleaning
    if start != -1 and end != -1:
        json_str = text[start:end + 1]
        json_str = re.sub(r'\s+', ' ', json_str)
        json_str = clean_json_string(json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    return None


class MatchGenerator:
    """Generate JV partner matches from database profiles"""

    # Business-related stop words to filter out
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
        'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
        'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you',
        'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'service', 'provider', 'services', 'member', 'non', 'resource'
    }

    # High-value matching categories
    CATEGORY_KEYWORDS = {
        'health': ['health', 'wellness', 'medical', 'fitness', 'natural', 'traditional', 'mental'],
        'business': ['business', 'entrepreneur', 'startup', 'consulting', 'coaching', 'marketing'],
        'finance': ['finance', 'financial', 'money', 'investment', 'wealth', 'accounting'],
        'personal_dev': ['improvement', 'success', 'mindset', 'motivation', 'leadership', 'growth'],
        'spirituality': ['spiritual', 'spirituality', 'meditation', 'mindfulness'],
        'relationships': ['relationship', 'relationships', 'dating', 'marriage', 'family'],
        'content': ['podcast', 'speaking', 'author', 'book', 'content', 'media', 'video'],
        'tech': ['technology', 'software', 'digital', 'online', 'internet', 'website', 'app']
    }

    # Collaboration templates based on category combinations
    COLLABORATION_TEMPLATES = {
        ('health', 'content'): "Health expert interviews and wellness content series",
        ('health', 'business'): "Wellness programs for entrepreneurs and business teams",
        ('finance', 'business'): "Joint webinar on business financial strategies",
        ('personal_dev', 'business'): "Mindset workshop for entrepreneurs",
        ('content', 'content'): "Guest appearances on each other's podcasts/shows",
        ('tech', 'business'): "Technology solutions workshop for business clients",
        ('relationships', 'personal_dev'): "Personal growth coaching partnership",
        ('spirituality', 'health'): "Holistic wellness retreat collaboration",
    }

    def __init__(self):
        self.directory_service = DirectoryService(use_admin=True)

    def extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return set()

        # Normalize and extract words
        text = text.lower()
        words = re.findall(r'\b[a-z]{3,}\b', text)

        # Filter stop words and return unique keywords
        keywords = {w for w in words if w not in self.STOP_WORDS}
        return keywords

    def get_categories(self, keywords: Set[str]) -> Set[str]:
        """Identify which business categories a profile belongs to"""
        categories = set()
        for category, cat_keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in keywords for kw in cat_keywords):
                categories.add(category)
        return categories

    def generate_collaboration_idea(self, target_categories: Set[str], match_categories: Set[str]) -> str:
        """Generate specific collaboration suggestion based on categories"""
        for t_cat in target_categories:
            for m_cat in match_categories:
                if (t_cat, m_cat) in self.COLLABORATION_TEMPLATES:
                    return self.COLLABORATION_TEMPLATES[(t_cat, m_cat)]
                if (m_cat, t_cat) in self.COLLABORATION_TEMPLATES:
                    return self.COLLABORATION_TEMPLATES[(m_cat, t_cat)]
        return "Cross-promotion to complementary audiences"

    def calculate_match_score(
        self,
        profile1_keywords: Set[str],
        profile2_keywords: Set[str],
        profile1_categories: Set[str],
        profile2_categories: Set[str]
    ) -> Tuple[float, List[str]]:
        """
        Calculate match score between two profiles
        Returns (score 0-100, list of common keywords)
        """
        # Keyword overlap
        common_keywords = profile1_keywords.intersection(profile2_keywords)
        keyword_score = len(common_keywords) / max(len(profile1_keywords | profile2_keywords), 1)

        # Category overlap (weighted higher)
        common_categories = profile1_categories.intersection(profile2_categories)
        category_score = len(common_categories) / max(len(profile1_categories | profile2_categories), 1)

        # Combined score (categories weighted 60%, keywords 40%)
        combined_score = (category_score * 0.6 + keyword_score * 0.4) * 100

        return round(combined_score, 1), list(common_keywords)[:5]

    def calculate_mutual_score(self, profile1: Dict, profile2: Dict) -> Tuple[float, List[str], str]:
        """Calculate mutual match score (both directions) and collaboration idea"""
        # Get text and keywords for both profiles
        text1 = ' '.join(filter(None, [
            profile1.get('business_focus', ''),
            profile1.get('service_provided', ''),
            profile1.get('company', '')
        ]))
        keywords1 = self.extract_keywords(text1)
        categories1 = self.get_categories(keywords1)

        text2 = ' '.join(filter(None, [
            profile2.get('business_focus', ''),
            profile2.get('service_provided', ''),
            profile2.get('company', '')
        ]))
        keywords2 = self.extract_keywords(text2)
        categories2 = self.get_categories(keywords2)

        # Calculate score A->B
        score_ab, common_keywords_ab = self.calculate_match_score(
            keywords1, keywords2, categories1, categories2
        )

        # Calculate score B->A
        score_ba, common_keywords_ba = self.calculate_match_score(
            keywords2, keywords1, categories2, categories1
        )

        # Use average score and combined keywords
        mutual_score = round((score_ab + score_ba) / 2, 1)
        common_keywords = list(set(common_keywords_ab + common_keywords_ba))[:5]

        # Generate collaboration idea
        collaboration_idea = self.generate_collaboration_idea(categories1, categories2)

        return mutual_score, common_keywords, collaboration_idea

    def generate_match_reason(
        self,
        target_name: str,
        match_name: str,
        common_keywords: List[str],
        score: float,
        collaboration_idea: str = None
    ) -> str:
        """Generate human-readable match reason"""
        if not common_keywords:
            base_reason = f"{match_name} has complementary skills that could create valuable partnership opportunities."
        elif len(common_keywords) >= 3:
            kw_text = f"{', '.join(common_keywords[:2])}, and {common_keywords[2]}"
            if score >= 70:
                base_reason = f"Strong alignment in {kw_text}. Highly compatible for joint ventures."
            elif score >= 50:
                base_reason = f"Shared focus on {kw_text}. Good potential for collaboration."
            else:
                base_reason = f"Common interests in {kw_text}. Worth exploring partnership opportunities."
        elif len(common_keywords) == 2:
            kw_text = f"{common_keywords[0]} and {common_keywords[1]}"
            if score >= 70:
                base_reason = f"Strong alignment in {kw_text}. Highly compatible for joint ventures."
            elif score >= 50:
                base_reason = f"Shared focus on {kw_text}. Good potential for collaboration."
            else:
                base_reason = f"Common interests in {kw_text}. Worth exploring partnership opportunities."
        else:
            kw_text = common_keywords[0]
            if score >= 70:
                base_reason = f"Strong alignment in {kw_text}. Highly compatible for joint ventures."
            elif score >= 50:
                base_reason = f"Shared focus on {kw_text}. Good potential for collaboration."
            else:
                base_reason = f"Common interests in {kw_text}. Worth exploring partnership opportunities."

        # Add collaboration idea if provided
        if collaboration_idea:
            return f"{base_reason} Suggested collaboration: {collaboration_idea}"
        return base_reason

    def generate_matches_for_profile(
        self,
        target_profile: Dict,
        all_profiles: List[Dict],
        top_n: int = 10,
        min_score: float = 10.0,
        dismissed_ids: Set[str] = None
    ) -> List[Dict]:
        """Generate top matches for a single profile"""
        if dismissed_ids is None:
            dismissed_ids = set()

        matches = []

        for profile in all_profiles:
            # Skip self
            if profile['id'] == target_profile['id']:
                continue

            # Skip dismissed profiles
            if profile['id'] in dismissed_ids:
                continue

            # Extract profile data
            profile_text = ' '.join(filter(None, [
                profile.get('business_focus', ''),
                profile.get('service_provided', ''),
                profile.get('company', '')
            ]))
            profile_keywords = self.extract_keywords(profile_text)
            profile_categories = self.get_categories(profile_keywords)

            # Skip if no keywords to match
            if not profile_keywords and not profile_categories:
                continue

            # Calculate mutual match score and collaboration idea
            score, common_keywords, collaboration_idea = self.calculate_mutual_score(
                target_profile, profile
            )

            # Only include if above minimum score
            if score >= min_score:
                matches.append({
                    'profile': profile,
                    'score': score,
                    'common_keywords': common_keywords,
                    'collaboration_idea': collaboration_idea,
                    'reason': self.generate_match_reason(
                        target_profile.get('name', ''),
                        profile.get('name', ''),
                        common_keywords,
                        score,
                        collaboration_idea
                    )
                })

        # Sort by score and return top N
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:top_n]

    def generate_all_matches(
        self,
        top_n: int = 10,
        min_score: float = 10.0,
        only_registered: bool = False
    ) -> Dict:
        """
        Generate matches for all profiles (or just registered users)
        Stores results in match_suggestions table
        """
        # Get all profiles
        result = self.directory_service.get_profiles(limit=10000)
        if not result['success']:
            return {'success': False, 'error': 'Failed to fetch profiles'}

        all_profiles = result['data']
        print(f"Loaded {len(all_profiles)} profiles")

        # Filter to only registered users if requested
        if only_registered:
            target_profiles = [p for p in all_profiles if p.get('auth_user_id')]
            print(f"Generating matches for {len(target_profiles)} registered users")
        else:
            target_profiles = all_profiles

        total_matches = 0
        profiles_processed = 0

        for target in target_profiles:
            # Generate matches for this profile
            matches = self.generate_matches_for_profile(
                target, all_profiles, top_n=top_n, min_score=min_score
            )

            # Store each match in database
            for match in matches:
                result = self.directory_service.create_match_suggestion(
                    profile_id=target['id'],
                    suggested_profile_id=match['profile']['id'],
                    match_score=match['score'],
                    match_reason=match['reason'],
                    source='ai_matcher'
                )
                if result['success']:
                    total_matches += 1

            profiles_processed += 1
            if profiles_processed % 100 == 0:
                print(f"  Processed {profiles_processed} / {len(target_profiles)}...")

        return {
            'success': True,
            'profiles_processed': profiles_processed,
            'matches_created': total_matches
        }

    def generate_matches_for_user(self, profile_id: str, top_n: int = 10) -> Dict:
        """Generate matches for a specific user"""
        # Get target profile
        result = self.directory_service.get_profile_by_id(profile_id)
        if not result['success']:
            return {'success': False, 'error': 'Profile not found'}

        target_profile = result['data']

        # Get all profiles for matching
        all_result = self.directory_service.get_profiles(limit=10000)
        if not all_result['success']:
            return {'success': False, 'error': 'Failed to fetch profiles'}

        all_profiles = all_result['data']

        # Generate matches
        matches = self.generate_matches_for_profile(
            target_profile, all_profiles, top_n=top_n
        )

        # Store matches
        matches_created = 0
        for match in matches:
            result = self.directory_service.create_match_suggestion(
                profile_id=profile_id,
                suggested_profile_id=match['profile']['id'],
                match_score=match['score'],
                match_reason=match['reason'],
                source='ai_matcher'
            )
            if result['success']:
                matches_created += 1

        return {
            'success': True,
            'matches_created': matches_created,
            'matches': matches
        }


class AIMatchGenerator:
    """
    AI-powered JV partner matching using OpenRouter API.
    Provides higher quality matches with outreach messages.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenRouter API key"""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package required. Install with: pip install openai")

        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )
        self.model = "amazon/nova-2-lite-v1:free"
        self.directory_service = DirectoryService(use_admin=True)

    def profile_to_text(self, profile: Dict) -> str:
        """Convert database profile to text for AI"""
        parts = [
            f"Name: {profile.get('name', 'Unknown')}",
            f"Company: {profile.get('company', 'N/A')}",
            f"Business Focus: {profile.get('business_focus', 'N/A')}",
            f"Services: {profile.get('service_provided', 'N/A')}",
            f"Status: {profile.get('status', 'N/A')}",
            f"List Size: {profile.get('list_size', 0)}",
            f"Social Reach: {profile.get('social_reach', 0)}"
        ]
        return "\n".join(parts)

    def generate_ai_matches(
        self,
        target_profile: Dict,
        candidate_profiles: List[Dict],
        num_matches: int = 10
    ) -> List[Dict]:
        """Generate AI-powered matches for a profile"""
        target_text = self.profile_to_text(target_profile)

        # Limit candidates to avoid token limits
        candidates = candidate_profiles[:50]
        candidates_text = "\n\n".join([
            f"--- Profile {i+1} ---\n{self.profile_to_text(p)}"
            for i, p in enumerate(candidates)
        ])

        prompt = f"""You are an expert at identifying strategic JV partnerships. Find the TOP {num_matches} best partnership matches.

TARGET PERSON:
{target_text}

POTENTIAL PARTNERS:
{candidates_text}

For each match, provide:
1. partner_name - Their full name (must match exactly from the list)
2. score - Match quality 0-100
3. match_type - Type (Affiliate, Speaking, Referral, Content, Service)
4. why_good_fit - 1-2 sentences on why they match
5. collaboration_opportunity - Specific actionable idea
6. first_outreach_message - Ready-to-send message (50-100 words)

MATCHING CRITERIA:
- Prioritize COMPLEMENTARY services (not competitors)
- Consider TARGET MARKET alignment
- Look for synergies in services and audiences
- Only include matches with score >= 60

Return ONLY a JSON array, no preamble:
[{{"partner_name": "...", "score": 85, "match_type": "...", "why_good_fit": "...", "collaboration_opportunity": "...", "first_outreach_message": "..."}}]"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.choices[0].message.content
            matches = extract_json_array(content)

            if not matches:
                return []

            # Filter and validate matches
            valid_matches = []
            candidate_names = {p.get('name', '').lower(): p for p in candidates}

            for match in matches:
                if match.get('score', 0) < 60:
                    continue
                partner_name = match.get('partner_name', '').lower()
                if partner_name in candidate_names:
                    match['profile'] = candidate_names[partner_name]
                    valid_matches.append(match)

            return valid_matches[:num_matches]

        except Exception as e:
            print(f"AI matching error: {e}")
            return []

    def generate_matches_for_user(
        self,
        profile_id: str,
        top_n: int = 10,
        store_results: bool = True
    ) -> Dict:
        """Generate AI matches for a specific user"""
        # Get target profile
        result = self.directory_service.get_profile_by_id(profile_id)
        if not result['success']:
            return {'success': False, 'error': 'Profile not found'}

        target_profile = result['data']

        # Get candidate profiles
        all_result = self.directory_service.get_profiles(limit=500)
        if not all_result['success']:
            return {'success': False, 'error': 'Failed to fetch profiles'}

        candidates = [p for p in all_result['data'] if p['id'] != profile_id]

        # Generate AI matches
        matches = self.generate_ai_matches(target_profile, candidates, top_n)

        # Store in database
        matches_created = 0
        if store_results:
            for match in matches:
                profile = match.get('profile', {})
                reason = f"{match.get('why_good_fit', '')} {match.get('collaboration_opportunity', '')}"

                result = self.directory_service.create_match_suggestion(
                    profile_id=profile_id,
                    suggested_profile_id=profile['id'],
                    match_score=match.get('score', 0),
                    match_reason=reason[:500],
                    source='ai_matcher'
                )
                if result['success']:
                    matches_created += 1

        return {
            'success': True,
            'matches_created': matches_created,
            'matches': matches
        }

    def generate_all_matches(
        self,
        top_n: int = 10,
        only_registered: bool = True
    ) -> Dict:
        """Generate AI matches for all registered users"""
        result = self.directory_service.get_profiles(limit=10000)
        if not result['success']:
            return {'success': False, 'error': 'Failed to fetch profiles'}

        all_profiles = result['data']

        if only_registered:
            target_profiles = [p for p in all_profiles if p.get('auth_user_id')]
        else:
            target_profiles = all_profiles[:100]  # Limit for non-registered

        total_matches = 0
        profiles_processed = 0

        for target in target_profiles:
            candidates = [p for p in all_profiles if p['id'] != target['id']]
            matches = self.generate_ai_matches(target, candidates, top_n)

            for match in matches:
                profile = match.get('profile', {})
                reason = f"{match.get('why_good_fit', '')} {match.get('collaboration_opportunity', '')}"

                result = self.directory_service.create_match_suggestion(
                    profile_id=target['id'],
                    suggested_profile_id=profile['id'],
                    match_score=match.get('score', 0),
                    match_reason=reason[:500],
                    source='ai_matcher'
                )
                if result['success']:
                    total_matches += 1

            profiles_processed += 1
            print(f"AI Matched {profiles_processed}/{len(target_profiles)}: {target.get('name')}")

        return {
            'success': True,
            'profiles_processed': profiles_processed,
            'matches_created': total_matches
        }


def get_matcher(use_ai: bool = False, api_key: Optional[str] = None):
    """Factory function to get appropriate matcher"""
    if use_ai:
        return AIMatchGenerator(api_key)
    return MatchGenerator()


# CLI for testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == '--all':
            print("Generating keyword-based matches for all profiles...")
            generator = MatchGenerator()
            result = generator.generate_all_matches(top_n=10, min_score=15.0)
            print(f"\nResult: {result}")
        elif sys.argv[1] == '--ai':
            print("Generating AI-powered matches for registered users...")
            generator = AIMatchGenerator()
            result = generator.generate_all_matches(top_n=10, only_registered=True)
            print(f"\nResult: {result}")
    else:
        print("Usage:")
        print("  python match_generator.py --all    # Keyword matching for all")
        print("  python match_generator.py --ai     # AI matching (needs OPENROUTER_API_KEY)")
