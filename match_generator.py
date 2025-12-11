"""
Match Generator - Creates JV partner suggestions based on profile data
Supports three modes:
1. Keyword matching (fast, no API needed)
2. AI matching via OpenRouter (higher quality, requires API key)
3. Hybrid matching with rich analysis (semantic + AI analysis)
"""
import os
import json
import re
from typing import List, Dict, Set, Tuple, Optional, Any, Union
from directory_service import DirectoryService

# Import rich match service for AI-powered analysis
try:
    from rich_match_service import RichMatchService
    RICH_MATCH_AVAILABLE = True
except ImportError:
    RICH_MATCH_AVAILABLE = False

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


class HybridMatchGenerator:
    """
    Hybrid matcher combining multiple signals:
    - Semantic similarity (embeddings): 35%
    - Category overlap: 30%
    - Keyword overlap: 20%
    - Reach compatibility: 15%
    """

    WEIGHTS = {
        'semantic': 0.35,
        'category': 0.30,
        'keyword': 0.20,
        'reach': 0.15
    }

    def __init__(self, openai_api_key: Optional[str] = None):
        self.directory_service = DirectoryService(use_admin=True)
        self.keyword_matcher = MatchGenerator()

        # Initialize embedding service if available
        self.embedding_service = None
        try:
            from embedding_service import get_embedding_service
            self.embedding_service = get_embedding_service(openai_api_key)
        except Exception as e:
            print(f"Embedding service not available: {e}")

        # Initialize rich match service for AI analysis
        self.rich_match_service = None
        if RICH_MATCH_AVAILABLE:
            try:
                self.rich_match_service = RichMatchService(openai_api_key)
            except Exception as e:
                print(f"Rich match service not available: {e}")

    def calculate_reach_compatibility(self, reach1: int, reach2: int) -> float:
        """
        Calculate reach compatibility score (0-100).
        Higher score when reaches are complementary (big helps small).
        """
        if reach1 == 0 and reach2 == 0:
            return 50.0  # Neutral if both unknown

        # Both have reach - use ratio bonus
        if reach1 > 0 and reach2 > 0:
            larger = max(reach1, reach2)
            smaller = min(reach1, reach2)
            ratio = larger / smaller

            # Slight bonus for complementary reaches (up to 10x difference)
            if ratio <= 10:
                return 70 + (ratio * 3)  # 73-100 range
            else:
                return 70.0  # Cap at 70 for very large differences

        # One has reach, one doesn't - neutral
        return 50.0

    def calculate_hybrid_score(
        self,
        target_profile: Dict,
        candidate_profile: Dict,
        target_embedding: Optional[List[float]] = None,
        candidate_embedding: Optional[List[float]] = None
    ) -> Tuple[float, Dict[str, float], List[str], str]:
        """
        Calculate hybrid match score combining all signals.
        Returns: (total_score, component_scores, common_keywords, collaboration_idea)
        """
        component_scores = {}

        # 1. Keyword-based scores (from existing matcher)
        target_text = ' '.join(filter(None, [
            target_profile.get('business_focus', ''),
            target_profile.get('service_provided', ''),
            target_profile.get('company', '')
        ]))
        target_keywords = self.keyword_matcher.extract_keywords(target_text)
        target_categories = self.keyword_matcher.get_categories(target_keywords)

        candidate_text = ' '.join(filter(None, [
            candidate_profile.get('business_focus', ''),
            candidate_profile.get('service_provided', ''),
            candidate_profile.get('company', '')
        ]))
        candidate_keywords = self.keyword_matcher.extract_keywords(candidate_text)
        candidate_categories = self.keyword_matcher.get_categories(candidate_keywords)

        # Keyword overlap score
        common_keywords = target_keywords.intersection(candidate_keywords)
        if target_keywords or candidate_keywords:
            keyword_score = len(common_keywords) / max(len(target_keywords | candidate_keywords), 1) * 100
        else:
            keyword_score = 0.0
        component_scores['keyword'] = keyword_score

        # Category overlap score
        common_categories = target_categories.intersection(candidate_categories)
        if target_categories or candidate_categories:
            category_score = len(common_categories) / max(len(target_categories | candidate_categories), 1) * 100
        else:
            category_score = 0.0
        component_scores['category'] = category_score

        # 2. Semantic similarity (if embeddings available)
        if self.embedding_service and target_embedding and candidate_embedding:
            semantic_sim = self.embedding_service.cosine_similarity(target_embedding, candidate_embedding)
            semantic_score = max(0.0, semantic_sim * 100)
        else:
            # Fall back to keyword/category average if no embeddings
            semantic_score = (keyword_score + category_score) / 2
        component_scores['semantic'] = semantic_score

        # 3. Reach compatibility
        target_reach = target_profile.get('social_reach', 0) or 0
        candidate_reach = candidate_profile.get('social_reach', 0) or 0
        reach_score = self.calculate_reach_compatibility(target_reach, candidate_reach)
        component_scores['reach'] = reach_score

        # Calculate weighted total
        total_score = (
            component_scores['semantic'] * self.WEIGHTS['semantic'] +
            component_scores['category'] * self.WEIGHTS['category'] +
            component_scores['keyword'] * self.WEIGHTS['keyword'] +
            component_scores['reach'] * self.WEIGHTS['reach']
        )

        # Generate collaboration idea
        collaboration_idea = self.keyword_matcher.generate_collaboration_idea(
            target_categories, candidate_categories
        )

        return round(total_score, 1), component_scores, list(common_keywords)[:5], collaboration_idea

    def generate_matches_for_profile(
        self,
        target_profile: Dict,
        all_profiles: List[Dict],
        top_n: int = 10,
        min_score: float = 15.0,
        dismissed_ids: Optional[Set[str]] = None
    ) -> List[Dict]:
        """Generate top matches using hybrid scoring"""
        if dismissed_ids is None:
            dismissed_ids = set()

        matches = []

        # Get target embedding
        target_embedding = target_profile.get('embedding_vector')
        if not target_embedding and self.embedding_service:
            target_embedding = self.embedding_service.get_profile_embedding(target_profile)

        for candidate in all_profiles:
            # Skip self and dismissed
            if candidate['id'] == target_profile['id']:
                continue
            if candidate['id'] in dismissed_ids:
                continue

            # Get candidate embedding
            candidate_embedding = candidate.get('embedding_vector')

            # Calculate hybrid score
            score, components, common_keywords, collaboration_idea = self.calculate_hybrid_score(
                target_profile, candidate, target_embedding, candidate_embedding
            )

            if score >= min_score:
                matches.append({
                    'profile': candidate,
                    'score': score,
                    'component_scores': components,
                    'common_keywords': common_keywords,
                    'collaboration_idea': collaboration_idea,
                    'reason': self.keyword_matcher.generate_match_reason(
                        target_profile.get('name', ''),
                        candidate.get('name', ''),
                        common_keywords,
                        score,
                        collaboration_idea
                    )
                })

        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:top_n]

    def generate_all_embeddings(self, batch_size: int = 50) -> Dict:
        """Generate and store embeddings for all profiles without them"""
        if not self.embedding_service:
            return {'success': False, 'error': 'Embedding service not available'}

        profiles = self.directory_service.get_profiles_without_embeddings(limit=1000)
        if not profiles:
            return {'success': True, 'profiles_updated': 0, 'message': 'All profiles have embeddings'}

        updated = 0
        errors = 0

        for i in range(0, len(profiles), batch_size):
            batch = profiles[i:i + batch_size]
            texts = [self.embedding_service.profile_to_text(p) for p in batch]

            try:
                embeddings = self.embedding_service.get_embeddings_batch(texts)

                for j, profile in enumerate(batch):
                    result = self.directory_service.update_profile_embedding(
                        profile['id'], embeddings[j]
                    )
                    if result['success']:
                        updated += 1
                    else:
                        errors += 1
            except Exception as e:
                print(f"Batch embedding error: {e}")
                errors += len(batch)

            print(f"Progress: {i + len(batch)}/{len(profiles)} profiles processed")

        return {
            'success': True,
            'profiles_updated': updated,
            'errors': errors
        }

    def generate_all_matches(
        self,
        top_n: int = 10,
        min_score: float = 15.0,
        only_registered: bool = False,
        generate_rich_analysis: bool = True
    ) -> Dict:
        """Generate hybrid matches for all profiles with optional rich AI analysis"""
        # Auto-generate embeddings for profiles that don't have them
        if self.embedding_service:
            print("Checking for profiles needing embeddings...")
            embed_result = self.generate_all_embeddings(batch_size=50)
            if embed_result.get('profiles_updated', 0) > 0:
                print(f"Generated embeddings for {embed_result['profiles_updated']} profiles")

        # Get all profiles with embeddings
        all_profiles = self.directory_service.get_all_profiles_for_matching()
        if not all_profiles:
            return {'success': False, 'error': 'Failed to fetch profiles'}

        print(f"Loaded {len(all_profiles)} profiles for hybrid matching")

        # Filter targets if needed
        if only_registered:
            target_profiles = [p for p in all_profiles if p.get('auth_user_id')]
            print(f"Generating matches for {len(target_profiles)} registered users")
        else:
            target_profiles = all_profiles

        total_matches = 0
        total_rich_analyses = 0
        profiles_processed = 0

        for target in target_profiles:
            # Get dismissed profiles for this user
            dismissed_ids = self.directory_service.get_dismissed_profile_ids(target['id'])

            # Generate matches
            matches = self.generate_matches_for_profile(
                target, all_profiles, top_n=top_n, min_score=min_score,
                dismissed_ids=dismissed_ids
            )

            # Store matches with optional rich analysis
            for match in matches:
                result = self.directory_service.create_match_suggestion(
                    profile_id=target['id'],
                    suggested_profile_id=match['profile']['id'],
                    match_score=match['score'],
                    match_reason=match['reason'],
                    source='hybrid_matcher'
                )
                if result['success']:
                    total_matches += 1
                    match_id = result.get('data', {}).get('id')

                    # Generate rich AI analysis if enabled
                    if generate_rich_analysis and self.rich_match_service and match_id:
                        try:
                            rich_result = self.rich_match_service.generate_rich_analysis(
                                target, match['profile']
                            )
                            if rich_result.get('success') and rich_result.get('analysis'):
                                analysis_result = self.directory_service.update_match_rich_analysis(
                                    match_id, rich_result['analysis']
                                )
                                if analysis_result.get('success'):
                                    total_rich_analyses += 1
                        except Exception as e:
                            print(f"Error generating rich analysis: {e}")

            profiles_processed += 1
            if profiles_processed % 50 == 0:
                print(f"  Processed {profiles_processed}/{len(target_profiles)}... ({total_rich_analyses} rich analyses)")

        return {
            'success': True,
            'profiles_processed': profiles_processed,
            'matches_created': total_matches,
            'rich_analyses_generated': total_rich_analyses
        }

    def generate_matches_for_user(self, profile_id: str, top_n: int = 10, generate_rich_analysis: bool = True) -> Dict:
        """Generate hybrid matches for a single user with optional rich AI analysis"""
        # Get user profile
        profile_result = self.directory_service.get_profile_by_id(profile_id)
        if not profile_result.get('success') or not profile_result.get('data'):
            return {'success': False, 'error': 'Profile not found'}

        target_profile = profile_result['data']

        # Get all profiles for matching
        all_profiles = self.directory_service.get_all_profiles_for_matching()
        if not all_profiles:
            return {'success': False, 'error': 'Failed to fetch profiles'}

        # Get dismissed profiles
        dismissed_ids = self.directory_service.get_dismissed_profile_ids(profile_id)

        # Generate embedding for target if needed
        if self.embedding_service and not target_profile.get('embedding'):
            embedding = self.embedding_service.get_profile_embedding(target_profile)
            target_profile['embedding_vector'] = embedding

        # Generate matches
        matches = self.generate_matches_for_profile(
            target_profile, all_profiles, top_n=top_n, min_score=10.0,
            dismissed_ids=dismissed_ids
        )

        # Store matches in database
        matches_created = 0
        rich_analyses_generated = 0

        for match in matches:
            # Create the match suggestion first
            result = self.directory_service.create_match_suggestion(
                profile_id=profile_id,
                suggested_profile_id=match['profile']['id'],
                match_score=match['score'],
                match_reason=match['reason'],
                source='hybrid_matcher'
            )

            if result['success']:
                matches_created += 1
                match_id = result.get('data', {}).get('id')

                # Generate rich AI analysis if service available and enabled
                if generate_rich_analysis and self.rich_match_service and match_id:
                    try:
                        rich_result = self.rich_match_service.generate_rich_analysis(
                            target_profile, match['profile']
                        )

                        if rich_result.get('success') and rich_result.get('analysis'):
                            # Store rich analysis in database
                            analysis_result = self.directory_service.update_match_rich_analysis(
                                match_id, rich_result['analysis']
                            )
                            if analysis_result.get('success'):
                                rich_analyses_generated += 1
                                # Add rich analysis to match object for return
                                match['rich_analysis'] = rich_result['analysis']
                    except Exception as e:
                        print(f"Error generating rich analysis for match: {e}")

        return {
            'success': True,
            'matches_created': matches_created,
            'rich_analyses_generated': rich_analyses_generated,
            'matches': matches
        }


class ConversationAwareMatchGenerator(HybridMatchGenerator):
    """
    Enhanced matcher that incorporates conversation signals from networking events.

    New weights:
    - Semantic similarity: 30% (was 35%)
    - Category overlap: 25% (was 30%)
    - Keyword overlap: 15% (was 20%)
    - Reach compatibility: 10% (was 15%)
    - Conversation signals: 20% (NEW)

    Optimized with pre-fetching to eliminate per-pair database queries.
    """

    WEIGHTS = {
        'semantic': 0.30,
        'category': 0.25,
        'keyword': 0.15,
        'reach': 0.10,
        'conversation': 0.20
    }

    def __init__(self, openai_api_key: Optional[str] = None):
        super().__init__(openai_api_key)
        self.conversation_analyzer = None
        try:
            from conversation_analyzer import ConversationAnalyzer
            self.conversation_analyzer = ConversationAnalyzer(openai_api_key)
            print("ConversationAwareMatchGenerator initialized with conversation analysis")
        except Exception as e:
            print(f"Conversation analyzer not available: {e}")

        # Pre-fetched conversation data (populated by _prefetch_conversation_data)
        self._signals_by_profile = {}  # profile_id -> [signals]
        self._signals_by_target = {}   # target_profile_id -> [signals from others targeting this profile]
        self._transcripts_by_profile = {}  # profile_id -> {transcript_ids}
        self._field_history_by_profile = {}  # profile_id -> {field_name -> [history records]}
        self._conversation_data_loaded = False

    def _prefetch_conversation_data(self, profile_ids: List[str] = None) -> None:
        """
        Pre-fetch all conversation data in 2 queries, index in memory.
        This eliminates ~70 million queries when matching 3,734 profiles.
        """
        if not self.conversation_analyzer:
            print("No conversation analyzer available, skipping prefetch")
            return

        supabase = self.conversation_analyzer.supabase

        print("Pre-fetching conversation data...")

        # Query 1: All signals (needs, offers, connections)
        try:
            if profile_ids:
                # Fetch in batches to avoid query limits
                all_signals = []
                batch_size = 500
                for i in range(0, len(profile_ids), batch_size):
                    batch = profile_ids[i:i + batch_size]
                    signals_response = supabase.table("conversation_signals") \
                        .select("*") \
                        .in_("profile_id", batch) \
                        .execute()
                    all_signals.extend(signals_response.data or [])
            else:
                signals_response = supabase.table("conversation_signals") \
                    .select("*") \
                    .execute()
                all_signals = signals_response.data or []

            print(f"  Loaded {len(all_signals)} conversation signals")
        except Exception as e:
            print(f"  Error loading conversation signals: {e}")
            all_signals = []

        # Query 2: All speaker-transcript mappings
        try:
            if profile_ids:
                all_speakers = []
                for i in range(0, len(profile_ids), batch_size):
                    batch = profile_ids[i:i + batch_size]
                    speakers_response = supabase.table("conversation_speakers") \
                        .select("matched_profile_id, transcript_id") \
                        .in_("matched_profile_id", batch) \
                        .execute()
                    all_speakers.extend(speakers_response.data or [])
            else:
                speakers_response = supabase.table("conversation_speakers") \
                    .select("matched_profile_id, transcript_id") \
                    .not_.is_("matched_profile_id", "null") \
                    .execute()
                all_speakers = speakers_response.data or []

            print(f"  Loaded {len(all_speakers)} speaker-transcript mappings")
        except Exception as e:
            print(f"  Error loading speaker mappings: {e}")
            all_speakers = []

        # Index signals by profile_id
        self._signals_by_profile = {}
        self._signals_by_target = {}

        for signal in all_signals:
            pid = signal.get('profile_id')
            tid = signal.get('target_profile_id')

            if pid:
                if pid not in self._signals_by_profile:
                    self._signals_by_profile[pid] = []
                self._signals_by_profile[pid].append(signal)

            if tid:
                if tid not in self._signals_by_target:
                    self._signals_by_target[tid] = []
                self._signals_by_target[tid].append(signal)

        # Index transcripts by profile
        self._transcripts_by_profile = {}
        for speaker in all_speakers:
            pid = speaker.get('matched_profile_id')
            if pid:
                if pid not in self._transcripts_by_profile:
                    self._transcripts_by_profile[pid] = set()
                self._transcripts_by_profile[pid].add(speaker.get('transcript_id'))

        # Query 3: Profile field history (for time-based matching context)
        try:
            if profile_ids:
                all_field_history = []
                for i in range(0, len(profile_ids), batch_size):
                    batch = profile_ids[i:i + batch_size]
                    history_response = supabase.table("profile_field_history") \
                        .select("profile_id, field_name, field_value, event_date, event_name") \
                        .in_("profile_id", batch) \
                        .execute()
                    all_field_history.extend(history_response.data or [])
            else:
                history_response = supabase.table("profile_field_history") \
                    .select("profile_id, field_name, field_value, event_date, event_name") \
                    .execute()
                all_field_history = history_response.data or []

            print(f"  Loaded {len(all_field_history)} field history records")
        except Exception as e:
            print(f"  Note: Field history not available yet: {e}")
            all_field_history = []

        # Index field history by profile
        self._field_history_by_profile = {}
        for record in all_field_history:
            pid = record.get('profile_id')
            field_name = record.get('field_name')
            if pid and field_name:
                if pid not in self._field_history_by_profile:
                    self._field_history_by_profile[pid] = {}
                if field_name not in self._field_history_by_profile[pid]:
                    self._field_history_by_profile[pid][field_name] = []
                self._field_history_by_profile[pid][field_name].append(record)

        self._conversation_data_loaded = True
        print(f"  Indexed: {len(self._signals_by_profile)} profiles with signals, "
              f"{len(self._transcripts_by_profile)} profiles in conversations, "
              f"{len(self._field_history_by_profile)} profiles with field history")

    def get_affected_profiles_bidirectional(self, new_profile_ids: List[str]) -> Set[str]:
        """
        Get all profiles that need match regeneration when new profiles are added.

        This is bidirectional - when Person A is new, we regenerate:
        1. Matches FOR Person A (who should A connect with?)
        2. Matches WHERE Person A is a candidate (who else benefits from meeting A?)

        Args:
            new_profile_ids: List of newly added/updated profile IDs

        Returns:
            Set of all profile IDs that need match regeneration
        """
        if not new_profile_ids:
            return set()

        affected = set(new_profile_ids)  # Start with new profiles themselves
        supabase = self.directory_service.supabase

        try:
            # Pre-fetch the new profiles' needs and offers from profiles table
            new_profiles = supabase.table("profiles") \
                .select("id, business_focus, service_provided") \
                .in_("id", list(new_profile_ids)) \
                .execute()

            # Collect keywords from new profiles
            new_keywords = set()
            for p in (new_profiles.data or []):
                text = ' '.join(filter(None, [
                    p.get('business_focus', ''),
                    p.get('service_provided', '')
                ])).lower()
                words = text.split()
                new_keywords.update(w for w in words if len(w) > 3)

            if new_keywords:
                # Find profiles with overlapping business focus (potential matches)
                # Use text search on business_focus and service_provided
                all_profiles = supabase.table("profiles") \
                    .select("id, business_focus, service_provided") \
                    .not_.in_("id", list(new_profile_ids)) \
                    .execute()

                for p in (all_profiles.data or []):
                    text = ' '.join(filter(None, [
                        p.get('business_focus', ''),
                        p.get('service_provided', '')
                    ])).lower()
                    profile_words = set(w for w in text.split() if len(w) > 3)

                    # If there's keyword overlap, this profile might have new matches
                    if profile_words & new_keywords:
                        affected.add(p['id'])

            # Add profiles from the same conversation transcript
            new_transcripts = supabase.table("conversation_speakers") \
                .select("transcript_id") \
                .in_("matched_profile_id", list(new_profile_ids)) \
                .execute()

            transcript_ids = [t['transcript_id'] for t in (new_transcripts.data or []) if t.get('transcript_id')]

            if transcript_ids:
                same_conversation_profiles = supabase.table("conversation_speakers") \
                    .select("matched_profile_id") \
                    .in_("transcript_id", transcript_ids) \
                    .not_.is_("matched_profile_id", "null") \
                    .execute()

                for p in (same_conversation_profiles.data or []):
                    if p.get('matched_profile_id'):
                        affected.add(p['matched_profile_id'])

            print(f"Bidirectional update: {len(new_profile_ids)} new profiles -> {len(affected)} affected profiles")

        except Exception as e:
            print(f"Error calculating affected profiles: {e}")
            # On error, just return the new profiles
            return set(new_profile_ids)

        return affected

    def calculate_conversation_score(
        self,
        target_profile_id: str,
        candidate_profile_id: str
    ) -> float:
        """
        Calculate conversation-based matching score using pre-fetched cached data.

        Score components:
        1. +40 pts: Candidate expressed connection interest in target
        2. +30 pts: Target's needs match candidate's offers
        3. +10 pts: Were in the same conversation (already met)
        """
        if not self._conversation_data_loaded:
            return 50.0  # Neutral if no conversation data loaded

        score = 0.0

        # 1. Check if candidate expressed connection interest in target (+40 pts)
        target_signals = self._signals_by_target.get(target_profile_id, [])
        for signal in target_signals:
            if (signal.get('profile_id') == candidate_profile_id and
                signal.get('signal_type') == 'connection'):
                score += 40.0
                break

        # 2. Check if target's needs match candidate's offers (+30 pts)
        target_signals_all = self._signals_by_profile.get(target_profile_id, [])
        candidate_signals_all = self._signals_by_profile.get(candidate_profile_id, [])

        # Extract target's needs
        need_keywords = set()
        for signal in target_signals_all:
            if signal.get('signal_type') == 'need':
                words = signal.get('signal_text', '').lower().split()
                need_keywords.update(w for w in words if len(w) > 3)

        # Extract candidate's offers
        offer_keywords = set()
        for signal in candidate_signals_all:
            if signal.get('signal_type') == 'offer':
                words = signal.get('signal_text', '').lower().split()
                offer_keywords.update(w for w in words if len(w) > 3)

        # Check keyword overlap
        if need_keywords and offer_keywords:
            overlap = len(need_keywords & offer_keywords)
            if overlap > 0:
                score += min(30.0, overlap * 10)

        # 3. Check if they were in the same conversation (+10 pts)
        target_transcripts = self._transcripts_by_profile.get(target_profile_id, set())
        candidate_transcripts = self._transcripts_by_profile.get(candidate_profile_id, set())

        if target_transcripts & candidate_transcripts:
            score += 10.0

        return min(100.0, score)

    def calculate_hybrid_score(
        self,
        target_profile: Dict,
        candidate_profile: Dict,
        target_embedding: Optional[List[float]] = None,
        candidate_embedding: Optional[List[float]] = None
    ) -> Tuple[float, Dict[str, float], List[str], str]:
        """
        Extended hybrid score including conversation signals.
        Returns: (total_score, component_scores, common_keywords, collaboration_idea)
        """
        component_scores = {}

        # 1. Get base component scores from parent logic
        # Keyword-based scores
        target_text = ' '.join(filter(None, [
            target_profile.get('business_focus', ''),
            target_profile.get('service_provided', ''),
            target_profile.get('company', '')
        ]))
        target_keywords = self.keyword_matcher.extract_keywords(target_text)
        target_categories = self.keyword_matcher.get_categories(target_keywords)

        candidate_text = ' '.join(filter(None, [
            candidate_profile.get('business_focus', ''),
            candidate_profile.get('service_provided', ''),
            candidate_profile.get('company', '')
        ]))
        candidate_keywords = self.keyword_matcher.extract_keywords(candidate_text)
        candidate_categories = self.keyword_matcher.get_categories(candidate_keywords)

        # Keyword overlap score
        common_keywords = target_keywords.intersection(candidate_keywords)
        if target_keywords or candidate_keywords:
            keyword_score = len(common_keywords) / max(len(target_keywords | candidate_keywords), 1) * 100
        else:
            keyword_score = 0.0
        component_scores['keyword'] = keyword_score

        # Category overlap score
        common_categories = target_categories.intersection(candidate_categories)
        if target_categories or candidate_categories:
            category_score = len(common_categories) / max(len(target_categories | candidate_categories), 1) * 100
        else:
            category_score = 0.0
        component_scores['category'] = category_score

        # Semantic similarity
        if self.embedding_service and target_embedding and candidate_embedding:
            semantic_sim = self.embedding_service.cosine_similarity(target_embedding, candidate_embedding)
            semantic_score = max(0.0, semantic_sim * 100)
        else:
            semantic_score = (keyword_score + category_score) / 2
        component_scores['semantic'] = semantic_score

        # Reach compatibility
        target_reach = target_profile.get('social_reach', 0) or 0
        candidate_reach = candidate_profile.get('social_reach', 0) or 0
        reach_score = self.calculate_reach_compatibility(target_reach, candidate_reach)
        component_scores['reach'] = reach_score

        # 2. NEW: Conversation score
        conversation_score = self.calculate_conversation_score(
            target_profile.get('id'),
            candidate_profile.get('id')
        )
        component_scores['conversation'] = conversation_score

        # 3. Calculate weighted total with new weights
        total_score = (
            component_scores['semantic'] * self.WEIGHTS['semantic'] +
            component_scores['category'] * self.WEIGHTS['category'] +
            component_scores['keyword'] * self.WEIGHTS['keyword'] +
            component_scores['reach'] * self.WEIGHTS['reach'] +
            component_scores['conversation'] * self.WEIGHTS['conversation']
        )

        # Generate collaboration idea
        collaboration_idea = self.keyword_matcher.generate_collaboration_idea(
            target_categories, candidate_categories
        )

        # Enhance collaboration idea if high conversation score
        if conversation_score > 60:
            collaboration_idea = f"[Strong conversation signal] {collaboration_idea}"

        return round(total_score, 1), component_scores, list(common_keywords)[:5], collaboration_idea

    def _build_match_context(self, seeker_profile_id: str, match_profile_id: str) -> Optional[Dict]:
        """
        Build time-based match context showing when each person mentioned relevant topics.

        This enables displays like:
        "Ken mentioned publishing work at the January event"
        "Sarah mentioned seeking a publisher at the March event"

        Returns:
            Dict with seeker and match context, or None if no history available
        """
        seeker_history = self._field_history_by_profile.get(seeker_profile_id, {})
        match_history = self._field_history_by_profile.get(match_profile_id, {})

        if not seeker_history and not match_history:
            return None

        context = {}

        # Get what the seeker is looking for (seeking field) with dates
        if 'seeking' in seeker_history:
            # Get the most recent entry
            seeking_records = sorted(
                seeker_history['seeking'],
                key=lambda x: x.get('event_date') or '',
                reverse=True
            )
            if seeking_records:
                latest = seeking_records[0]
                context['seeker_mentioned'] = {
                    'field': 'seeking',
                    'value': latest.get('field_value', '')[:200],
                    'event_date': latest.get('event_date'),
                    'event_name': latest.get('event_name')
                }

        # Get what the match is offering (offering field) with dates
        if 'offering' in match_history:
            offering_records = sorted(
                match_history['offering'],
                key=lambda x: x.get('event_date') or '',
                reverse=True
            )
            if offering_records:
                latest = offering_records[0]
                context['match_offering'] = {
                    'field': 'offering',
                    'value': latest.get('field_value', '')[:200],
                    'event_date': latest.get('event_date'),
                    'event_name': latest.get('event_name')
                }

        # Also include what_you_do for the match
        if 'what_you_do' in match_history:
            what_records = sorted(
                match_history['what_you_do'],
                key=lambda x: x.get('event_date') or '',
                reverse=True
            )
            if what_records:
                latest = what_records[0]
                context['match_described'] = {
                    'field': 'what_you_do',
                    'value': latest.get('field_value', '')[:200],
                    'event_date': latest.get('event_date'),
                    'event_name': latest.get('event_name')
                }

        return context if context else None

    def _generate_with_retry(self, target_profile: Dict, candidate_profile: Dict, max_retries: int = 3) -> Optional[Dict]:
        """Generate rich analysis with exponential backoff for rate limits"""
        import time
        import random

        if not self.rich_match_service:
            return None

        for attempt in range(max_retries):
            try:
                return self.rich_match_service.generate_rich_analysis(target_profile, candidate_profile)
            except Exception as e:
                error_str = str(e).lower()
                if ("rate_limit" in error_str or "429" in error_str) and attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"Rate limit hit, waiting {wait_time:.1f}s before retry {attempt + 2}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    if attempt == max_retries - 1:
                        print(f"Rich analysis failed after {max_retries} attempts: {e}")
                    raise
        return None

    def _generate_rich_analyses_parallel(self, matches_to_generate: List[Dict], all_profiles_dict: Dict[str, Dict]) -> Dict[Tuple[str, str], Dict]:
        """
        Generate rich analyses for multiple matches in parallel with rate limiting.

        Args:
            matches_to_generate: List of dicts with 'profile_id' and 'suggested_profile_id'
            all_profiles_dict: Dict mapping profile_id to full profile data

        Returns:
            Dict mapping (profile_id, suggested_profile_id) to rich analysis result
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if not self.rich_match_service:
            print("Rich match service not available, skipping rich analysis generation")
            return {}

        # Tier 2: 2,500 requests/minute max (token-limited)
        # 100 concurrent workers with ~2.5s latency = ~2,400/minute (safe)
        MAX_WORKERS = 100

        results = {}
        total = len(matches_to_generate)
        completed = 0

        print(f"Generating rich analyses for {total} matches with {MAX_WORKERS} parallel workers...")

        def generate_single(match_info):
            profile_id = match_info['profile_id']
            suggested_id = match_info['suggested_profile_id']

            target_profile = all_profiles_dict.get(profile_id)
            candidate_profile = all_profiles_dict.get(suggested_id)

            if not target_profile or not candidate_profile:
                return (profile_id, suggested_id), None

            result = self._generate_with_retry(target_profile, candidate_profile)
            return (profile_id, suggested_id), result

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_match = {
                executor.submit(generate_single, match): match
                for match in matches_to_generate
            }

            for future in as_completed(future_to_match):
                try:
                    pair_key, result = future.result()
                    results[pair_key] = result
                    completed += 1

                    if completed % 100 == 0:
                        print(f"  Rich analysis progress: {completed}/{total} ({completed*100//total}%)")
                except Exception as e:
                    match = future_to_match[future]
                    pair_key = (match['profile_id'], match['suggested_profile_id'])
                    results[pair_key] = None
                    completed += 1
                    print(f"  Error generating rich analysis for {pair_key}: {e}")

        successful = sum(1 for v in results.values() if v and v.get('success'))
        print(f"Rich analysis complete: {successful}/{total} successful")

        return results

    def _get_cached_rich_analyses(self, pairs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], str]:
        """
        Fetch existing rich analyses from database for the given profile pairs.

        Args:
            pairs: List of (profile_id, suggested_profile_id) tuples

        Returns:
            Dict mapping (profile_id, suggested_profile_id) to cached rich_analysis text
        """
        if not pairs:
            return {}

        cache = {}
        supabase = self.directory_service.supabase

        # Batch fetch in groups to avoid query limits
        BATCH_SIZE = 100

        for i in range(0, len(pairs), BATCH_SIZE):
            batch = pairs[i:i + BATCH_SIZE]

            # Build OR conditions for this batch
            for profile_id, suggested_id in batch:
                try:
                    existing = supabase.table("match_suggestions") \
                        .select("profile_id, suggested_profile_id, rich_analysis") \
                        .eq("profile_id", profile_id) \
                        .eq("suggested_profile_id", suggested_id) \
                        .not_.is_("rich_analysis", "null") \
                        .limit(1) \
                        .execute()

                    if existing.data and existing.data[0].get('rich_analysis'):
                        cache[(profile_id, suggested_id)] = existing.data[0]['rich_analysis']
                except Exception as e:
                    # Skip this pair on error
                    pass

        print(f"Rich analysis cache: found {len(cache)}/{len(pairs)} cached analyses")
        return cache

    def _generate_rich_analyses_with_cache(self, matches: List[Dict], all_profiles_dict: Dict[str, Dict]) -> Dict[Tuple[str, str], Dict]:
        """
        Generate rich analyses, using cache for existing pairs to avoid regeneration.

        Args:
            matches: List of match dicts with 'profile_id' and 'suggested_profile_id'
            all_profiles_dict: Dict mapping profile_id to full profile data

        Returns:
            Dict mapping (profile_id, suggested_profile_id) to rich analysis result
        """
        if not matches:
            return {}

        # Build list of pairs we need
        pairs_needed = [(m['profile_id'], m['suggested_profile_id']) for m in matches]

        # Check cache first
        cached = self._get_cached_rich_analyses(pairs_needed)

        # Separate into cached vs needs-generation
        to_generate = []
        results = {}

        for match in matches:
            pair_key = (match['profile_id'], match['suggested_profile_id'])
            if pair_key in cached:
                # Use cached analysis - wrap in expected format
                results[pair_key] = {
                    'success': True,
                    'analysis': cached[pair_key]
                }
            else:
                to_generate.append(match)

        print(f"Rich analysis: {len(cached)} cached, {len(to_generate)} to generate")

        # Generate only what's needed (parallel with rate limiting)
        if to_generate:
            new_results = self._generate_rich_analyses_parallel(to_generate, all_profiles_dict)
            results.update(new_results)

        return results

    def _batch_save_all_matches(self, all_matches: List[Dict]) -> int:
        """
        Save all matches in large batches (500 rows per insert).
        Returns the number of matches saved successfully.
        """
        if not all_matches:
            return 0

        BATCH_SIZE = 500
        saved = 0

        # Get supabase client
        supabase = self.directory_service.supabase

        for i in range(0, len(all_matches), BATCH_SIZE):
            batch = all_matches[i:i + BATCH_SIZE]

            batch_data = []
            for match in batch:
                match_data = {
                    "profile_id": match['profile_id'],
                    "suggested_profile_id": match['suggested_profile_id'],
                    "match_score": match.get('score', 0),
                    "match_reason": match.get('reason', ''),
                    "source": "hybrid_matcher",
                    "status": "pending"
                }

                # Add rich analysis if available
                if match.get('rich_analysis'):
                    match_data['rich_analysis'] = match['rich_analysis']

                # Add time-based match context if available
                if match.get('match_context'):
                    match_data['match_context'] = match['match_context']

                batch_data.append(match_data)

            try:
                # Use upsert to handle duplicates
                result = supabase.table("match_suggestions").upsert(
                    batch_data,
                    on_conflict="profile_id,suggested_profile_id"
                ).execute()
                saved += len(batch_data)
                print(f"  Saved batch {i//BATCH_SIZE + 1}: {len(batch_data)} matches")
            except Exception as e:
                print(f"  Error saving batch: {e}")
                # Try individual inserts as fallback
                for match_data in batch_data:
                    try:
                        supabase.table("match_suggestions").upsert(
                            match_data,
                            on_conflict="profile_id,suggested_profile_id"
                        ).execute()
                        saved += 1
                    except:
                        pass

        return saved

    def generate_matches_two_stage(
        self,
        profile_ids: List[str] = None,
        top_n: int = 10,
        min_score: float = 15.0,
        generate_rich_for_top_n: int = 5
    ) -> Dict:
        """
        Two-stage match generation: instant scores, then background rich analysis.

        Stage 1: Calculate and save all matches without rich analysis (~30 seconds)
        Stage 2: Generate rich analysis for top N matches per profile (~8 minutes for top 5)

        Args:
            profile_ids: Optional list of profile IDs to generate matches for. If None, all profiles.
            top_n: Number of top matches to generate per profile
            min_score: Minimum score threshold
            generate_rich_for_top_n: Generate rich analysis for top N matches (default 5)

        Returns:
            Dict with success status and statistics
        """
        import time
        start_time = time.time()

        # Get all profiles
        all_profiles = self.directory_service.get_all_profiles_for_matching()
        if not all_profiles:
            return {'success': False, 'error': 'Failed to fetch profiles'}

        all_profiles_dict = {p['id']: p for p in all_profiles}

        # Determine which profiles to generate matches for
        if profile_ids:
            target_profiles = [all_profiles_dict[pid] for pid in profile_ids if pid in all_profiles_dict]
        else:
            target_profiles = all_profiles

        print(f"Stage 1: Scoring matches for {len(target_profiles)} profiles against {len(all_profiles)} candidates...")

        # Pre-fetch conversation data for optimized scoring
        profile_id_list = [p['id'] for p in all_profiles]
        self._prefetch_conversation_data(profile_id_list)

        # STAGE 1: Calculate all scores (no OpenAI)
        stage1_start = time.time()
        all_matches = []

        for idx, target in enumerate(target_profiles):
            dismissed_ids = self.directory_service.get_dismissed_profile_ids(target['id'])

            # Generate matches for this profile
            matches = self.generate_matches_for_profile(
                target, all_profiles, top_n=top_n, min_score=min_score,
                dismissed_ids=dismissed_ids
            )

            # Add to all_matches with rank and match context
            for rank, match in enumerate(matches):
                match_entry = {
                    'profile_id': target['id'],
                    'suggested_profile_id': match['profile']['id'],
                    'score': match['score'],
                    'reason': match.get('reason', ''),
                    'rank': rank + 1,
                    'rich_analysis': None
                }

                # Build time-based match context if field history is available
                match_context = self._build_match_context(target['id'], match['profile']['id'])
                if match_context:
                    match_entry['match_context'] = match_context

                all_matches.append(match_entry)

            if (idx + 1) % 100 == 0:
                print(f"  Scored {idx + 1}/{len(target_profiles)} profiles...")

        stage1_time = time.time() - stage1_start
        print(f"Stage 1 complete: {len(all_matches)} matches scored in {stage1_time:.1f}s")

        # Save all matches (without rich analysis)
        saved_count = self._batch_save_all_matches(all_matches)
        print(f"Saved {saved_count} matches to database")

        # STAGE 2: Generate rich analysis for top N matches only
        if generate_rich_for_top_n > 0 and self.rich_match_service:
            stage2_start = time.time()
            top_matches = [m for m in all_matches if m['rank'] <= generate_rich_for_top_n]
            print(f"Stage 2: Generating rich analysis for {len(top_matches)} top matches...")

            # Generate rich analyses in parallel
            rich_results = self._generate_rich_analyses_parallel(top_matches, all_profiles_dict)

            # Update matches with rich analysis
            rich_updates = []
            for match in top_matches:
                pair_key = (match['profile_id'], match['suggested_profile_id'])
                rich_result = rich_results.get(pair_key)
                if rich_result and rich_result.get('success'):
                    rich_updates.append({
                        'profile_id': match['profile_id'],
                        'suggested_profile_id': match['suggested_profile_id'],
                        'rich_analysis': rich_result.get('analysis')
                    })

            # Batch update rich analyses
            if rich_updates:
                supabase = self.directory_service.supabase
                for update in rich_updates:
                    try:
                        supabase.table("match_suggestions").update({
                            "rich_analysis": update['rich_analysis']
                        }).eq("profile_id", update['profile_id']).eq(
                            "suggested_profile_id", update['suggested_profile_id']
                        ).execute()
                    except Exception as e:
                        print(f"  Error updating rich analysis: {e}")

            stage2_time = time.time() - stage2_start
            print(f"Stage 2 complete: {len(rich_updates)} rich analyses in {stage2_time:.1f}s")
        else:
            rich_updates = []
            stage2_time = 0

        total_time = time.time() - start_time

        return {
            'success': True,
            'profiles_processed': len(target_profiles),
            'matches_created': saved_count,
            'rich_analyses_generated': len(rich_updates),
            'stage1_time_seconds': round(stage1_time, 1),
            'stage2_time_seconds': round(stage2_time, 1),
            'total_time_seconds': round(total_time, 1)
        }


class V1MatchGenerator:
    """
    V1 Match Generation Algorithm - Reciprocal Scoring with Harmonic Mean

    Formula: Score_AB = (0.45 * Intent) + (0.25 * Synergy) + (0.20 * Momentum) + (0.10 * Context)
    FinalScore = HarmonicMean = (2 * AB * BA) / (AB + BA)

    Features:
    - Verified Intent (Platinum) vs Profile Data (Legacy) trust weighting
    - Scale Symmetry penalty for 10x+ reach mismatches
    - Popularity cap to prevent over-representation
    - Semantic matching via GPT-4o-mini
    """

    WEIGHTS = {
        'intent': 0.45,
        'synergy': 0.25,
        'momentum': 0.20,
        'context': 0.10
    }

    # Niche adjacency map for synergy calculations
    NICHE_ADJACENCY = {
        'Health & Wellness': ['Personal Development', 'Fitness & Nutrition', 'Spirituality & Mindfulness'],
        'Personal Development': ['Health & Wellness', 'Business & Entrepreneurship', 'Spirituality & Mindfulness'],
        'Business & Entrepreneurship': ['Personal Development', 'Marketing & Sales', 'Finance & Investing'],
        'Marketing & Sales': ['Business & Entrepreneurship', 'E-commerce & Online Business', 'Content Creation'],
        'E-commerce & Online Business': ['Marketing & Sales', 'Technology & Software'],
        'Technology & Software': ['E-commerce & Online Business', 'Finance & Investing'],
        'Finance & Investing': ['Technology & Software', 'Business & Entrepreneurship'],
        'Fitness & Nutrition': ['Health & Wellness', 'Personal Development'],
        'Relationships & Dating': ['Personal Development', 'Lifestyle & Entertainment'],
        'Lifestyle & Entertainment': ['Relationships & Dating', 'Travel & Adventure', 'Content Creation'],
        'Travel & Adventure': ['Lifestyle & Entertainment', 'Personal Development'],
        'Education & Learning': ['Personal Development', 'Business & Entrepreneurship'],
        'Parenting & Family': ['Personal Development', 'Health & Wellness'],
        'Spirituality & Mindfulness': ['Personal Development', 'Health & Wellness'],
        'Creative Arts': ['Personal Development', 'Lifestyle & Entertainment', 'Content Creation'],
        'Content Creation': ['Marketing & Sales', 'Lifestyle & Entertainment', 'Creative Arts'],
    }

    POPULARITY_CAP = 5  # Max appearances in Top 3 per cycle
    SCALE_PENALTY_THRESHOLD = 0.1  # 10x difference triggers penalty

    def __init__(self, openai_api_key: Optional[str] = None):
        self.directory_service = DirectoryService(use_admin=True)
        self.supabase = self.directory_service.client
        self._semantic_cache = {}

        # Initialize OpenAI client for semantic matching
        try:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=openai_api_key or os.getenv('OPENAI_API_KEY'))
            self._openai_available = True
        except Exception as e:
            print(f"OpenAI not available for V1MatchGenerator: {e}")
            self._openai_available = False
            self.openai_client = None

    def _fetch_all_profiles_paginated(self, select_fields: str, filter_column: str = None, batch_size: int = 1000) -> List[Dict]:
        """
        Fetch ALL profiles with pagination to bypass Supabase's 1000 row limit.

        Args:
            select_fields: Comma-separated list of fields to select
            filter_column: Optional column to filter by not null (e.g., 'offering')
            batch_size: Number of rows per page (max 1000 for Supabase)

        Returns:
            List of all matching profiles
        """
        all_results = []
        offset = 0

        while True:
            query = self.supabase.table("profiles").select(select_fields)

            # Apply filter if specified
            if filter_column:
                query = query.not_.is_(filter_column, "null")

            # Paginate using range
            result = query.range(offset, offset + batch_size - 1).execute()
            batch = result.data or []

            if not batch:
                break

            all_results.extend(batch)

            # If we got fewer than batch_size, we've reached the end
            if len(batch) < batch_size:
                break

            offset += batch_size

        return all_results

    def _fetch_matchable_profiles_paginated(self, select_fields: str, batch_size: int = 1000) -> List[Dict]:
        """
        Fetch profiles that have EITHER offering OR niche data (matchable profiles).
        Uses OR filter to expand the matchable pool beyond just offering-only profiles.

        Args:
            select_fields: Comma-separated list of fields to select
            batch_size: Number of rows per page (max 1000 for Supabase)

        Returns:
            List of all matchable profiles (have offering OR niche)
        """
        all_results = []
        offset = 0

        while True:
            # Use or_ filter for offering OR niche
            result = self.supabase.table("profiles") \
                .select(select_fields) \
                .or_("offering.not.is.null,niche.not.is.null") \
                .range(offset, offset + batch_size - 1) \
                .execute()
            batch = result.data or []

            if not batch:
                break

            all_results.extend(batch)

            # If we got fewer than batch_size, we've reached the end
            if len(batch) < batch_size:
                break

            offset += batch_size

        return all_results

    def calculate_harmonic_mean(self, score_ab: float, score_ba: float) -> float:
        """
        Reciprocal scoring - penalizes lopsided matches.
        HM = (2 * AB * BA) / (AB + BA)
        """
        if score_ab + score_ba == 0:
            return 0.0
        return (2 * score_ab * score_ba) / (score_ab + score_ba)

    def _get_confidence_tier(self, score: float) -> Optional[Dict[str, Any]]:
        """
        Get confidence tier based on harmonic mean score (V1.5 Tactical).

        Thresholds (rewards Platinum verification):
        - Gold >= 60: Top Pick (exclusive to Platinum users typically)
        - Silver >= 40: Strong Match
        - Bronze >= 20: Discovery
        - Below 20: No badge

        Args:
            score: Harmonic mean score (0-100 scale after trust weighting)

        Returns:
            Dict with tier info: {tier, label, emoji, color} or None if below threshold
        """
        if score >= 60:
            return {
                'tier': 'gold',
                'label': 'Top Pick',
                'emoji': '🔥',
                'color': '#FFD700'
            }
        elif score >= 40:
            return {
                'tier': 'silver',
                'label': 'Strong Match',
                'emoji': '✅',
                'color': '#C0C0C0'
            }
        elif score >= 20:
            return {
                'tier': 'bronze',
                'label': 'Discovery',
                'emoji': '👀',
                'color': '#CD7F32'
            }
        return None

    def calculate_intent_score(self, needs: List[str], offers: List[str]) -> float:
        """
        Binary intent matching: 1.0 if ANY need matches ANY offer, else 0.0
        Uses semantic similarity via GPT-4o-mini
        """
        if not needs or not offers:
            return 0.0

        # Check cache first
        cache_key = (tuple(sorted(needs)), tuple(sorted(offers)))
        if cache_key in self._semantic_cache:
            return self._semantic_cache[cache_key]

        if self._openai_available and self.openai_client:
            try:
                prompt = f"""Compare these two lists and determine if ANY item from NEEDS semantically matches ANY item from OFFERS.

NEEDS: {needs}
OFFERS: {offers}

A semantic match means the need can be fulfilled by the offer, even if worded differently.
Examples:
- "podcast guest" matches "speaking opportunities"
- "email list growth" matches "list building strategies"
- "business coach" matches "coaching services"

Return ONLY "YES" if there's at least one semantic match, or "NO" if none."""

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a semantic matching expert. Answer only YES or NO."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=10
                )

                result = response.choices[0].message.content.strip().upper()
                score = 1.0 if result == "YES" else 0.0
                self._semantic_cache[cache_key] = score
                return score

            except Exception as e:
                print(f"Semantic matching error: {e}")

        # Fallback to simple keyword matching
        for need in needs:
            need_words = set(need.lower().split())
            for offer in offers:
                offer_words = set(offer.lower().split())
                if need_words & offer_words:  # Any word overlap
                    return 1.0
        return 0.0

    def calculate_synergy_score(
        self,
        niche_a: str,
        niche_b: str,
        match_preference: Union[str, List[str]],
        reach_a: int,
        reach_b: int
    ) -> Tuple[float, str]:
        """
        Synergy = Niche Logic + Scale Symmetry

        V1.5 Multi-Select: If match_preference is a list, calculate score for
        ALL preferences and return the BEST one along with the winning preference.

        Niche Logic:
        - Peer/Bundle + Identical Niche = 1.0
        - Peer/Bundle + Adjacent Niche = 0.6
        - Referral + Client-Adjacent = 0.9
        - Referral + Identical Niche = 0.1 (competitor penalty)

        Returns:
            Tuple of (score, winning_preference)
        """
        # Normalize to list for multi-select support
        if isinstance(match_preference, str):
            preferences = [match_preference]
        elif isinstance(match_preference, list):
            preferences = match_preference if match_preference else ['Peer_Bundle']
        else:
            preferences = ['Peer_Bundle']

        best_score = 0.0
        winning_preference = preferences[0] if preferences else 'Peer_Bundle'

        for pref in preferences:
            base_score = self._calculate_niche_score(niche_a, niche_b, pref)
            scale_modifier = self._calculate_scale_symmetry(reach_a, reach_b, pref)
            score = base_score * scale_modifier

            if score > best_score:
                best_score = score
                winning_preference = pref

        return best_score, winning_preference

    def _calculate_niche_score(self, niche_a: str, niche_b: str, match_preference: str) -> float:
        """Calculate niche-based synergy score"""
        identical = (niche_a or '').lower() == (niche_b or '').lower() and niche_a
        adjacent = (niche_b or '') in self.NICHE_ADJACENCY.get(niche_a or '', [])

        if match_preference == 'Peer_Bundle':
            if identical:
                return 1.0
            elif adjacent:
                return 0.6
            else:
                return 0.2

        elif match_preference in ['Referral_Upstream', 'Referral_Downstream']:
            if adjacent:
                return 0.9  # Ideal referral flow
            elif identical:
                return 0.1  # Competitor penalty!
            else:
                return 0.3

        elif match_preference == 'Service_Provider':
            return 0.7  # Neutral for service relationships

        return 0.5  # Default

    def _calculate_scale_symmetry(self, reach_a: int, reach_b: int, match_preference: str) -> float:
        """
        Scale Symmetry Check - penalize 10x+ reach mismatches

        Ratio = Min(A,B) / Max(A,B)
        - R > 0.5 (similar): No penalty (1.0)
        - R < 0.1 (10x diff): Penalty (0.5)
        - Exception: Service_Provider ignores scale
        """
        if match_preference == 'Service_Provider':
            return 1.0

        reach_a = reach_a or 0
        reach_b = reach_b or 0

        if reach_a == 0 and reach_b == 0:
            return 1.0  # Both unknown - no penalty

        if reach_a == 0 or reach_b == 0:
            return 0.8  # One unknown - slight penalty

        ratio = min(reach_a, reach_b) / max(reach_a, reach_b)

        if ratio > 0.5:
            return 1.0
        elif ratio < self.SCALE_PENALTY_THRESHOLD:
            return 0.5
        else:
            # Linear interpolation between 0.1 and 0.5
            return 0.5 + (ratio - 0.1) * (0.5 / 0.4)

    def calculate_momentum_score(self, last_active_at) -> float:
        """
        Time decay: e^(-0.02 * days_since_active)

        - Active today = 1.0
        - 30 days ago = ~0.55 (Gold Zone)
        - 45 days ago = ~0.41
        - 90 days ago = ~0.17
        """
        import math
        from datetime import datetime, timezone

        if not last_active_at:
            return 0.3  # Unknown = lower priority

        if isinstance(last_active_at, str):
            try:
                last_active_at = datetime.fromisoformat(last_active_at.replace('Z', '+00:00'))
            except:
                return 0.3

        if last_active_at.tzinfo is None:
            last_active_at = last_active_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        days = (now - last_active_at).days

        return math.exp(-0.02 * max(0, days))

    def calculate_context_score(self, events_a: List[str], events_b: List[str]) -> float:
        """
        Bonus for shared event attendance
        +0.25 per shared event, max 1.0
        """
        if not events_a or not events_b:
            return 0.0

        shared = set(events_a or []).intersection(set(events_b or []))
        return min(1.0, len(shared) * 0.25)

    def _get_verified_data(self, profile_id: str) -> Dict:
        """
        Get verified intent data with fallback chain:
        1. Verified intake (Platinum) - 1.0x weight
        2. Profile fields (Legacy) - 0.3x weight
        """
        # Try intake_submissions first (Platinum trust)
        try:
            intake_result = self.supabase.table("intake_submissions") \
                .select("*") \
                .eq("profile_id", profile_id) \
                .order("created_at", desc=True) \
                .limit(1) \
                .execute()

            if intake_result.data and intake_result.data[0].get('confirmed_at'):
                intake = intake_result.data[0]
                return {
                    'offers': intake.get('verified_offers', []) or [],
                    'needs': intake.get('verified_needs', []) or [],
                    'match_preference': intake.get('match_preference', 'Peer_Bundle'),
                    'events': [intake.get('event_id')] if intake.get('event_id') else [],
                    'trust_level': 'platinum',
                    'weight_multiplier': 1.0
                }
        except Exception as e:
            print(f"Error fetching intake for {profile_id}: {e}")

        # Fallback to profile fields (Legacy trust)
        try:
            profile_result = self.supabase.table("profiles") \
                .select("offering, seeking, business_focus") \
                .eq("id", profile_id) \
                .limit(1) \
                .execute()

            if profile_result.data:
                profile = profile_result.data[0]
                offers = []
                needs = []

                if profile.get('offering'):
                    offers = [o.strip() for o in profile['offering'].split(',') if o.strip()]
                if profile.get('seeking'):
                    needs = [n.strip() for n in profile['seeking'].split(',') if n.strip()]

                return {
                    'offers': offers,
                    'needs': needs,
                    'match_preference': 'Peer_Bundle',
                    'events': [],
                    'trust_level': 'legacy',
                    'weight_multiplier': 0.3
                }
        except Exception as e:
            print(f"Error fetching profile {profile_id}: {e}")

        return {
            'offers': [],
            'needs': [],
            'match_preference': 'Peer_Bundle',
            'events': [],
            'trust_level': 'none',
            'weight_multiplier': 0.1
        }

    def _calculate_directional_score(
        self,
        target_profile: Dict,
        candidate_profile: Dict,
        target_verified: Dict,
        candidate_verified: Dict
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate A → B score
        Returns: (total_score, component_scores)
        """
        # Intent: Does candidate offer what target needs?
        intent = self.calculate_intent_score(
            target_verified['needs'],
            candidate_verified['offers']
        )

        # Synergy (V1.5: returns tuple with winning_preference for multi-select)
        target_reach = (target_profile.get('list_size', 0) or 0) + (target_profile.get('social_reach', 0) or 0)
        candidate_reach = (candidate_profile.get('list_size', 0) or 0) + (candidate_profile.get('social_reach', 0) or 0)

        synergy, winning_preference = self.calculate_synergy_score(
            target_profile.get('niche') or target_profile.get('business_focus', ''),
            candidate_profile.get('niche') or candidate_profile.get('business_focus', ''),
            target_verified['match_preference'],
            target_reach,
            candidate_reach
        )

        # Momentum
        momentum = self.calculate_momentum_score(candidate_profile.get('last_active_at'))

        # Context
        context = self.calculate_context_score(
            target_verified.get('events', []),
            candidate_verified.get('events', [])
        )

        # Weighted total
        total = (
            self.WEIGHTS['intent'] * intent +
            self.WEIGHTS['synergy'] * synergy +
            self.WEIGHTS['momentum'] * momentum +
            self.WEIGHTS['context'] * context
        )

        components = {
            'intent': intent,
            'synergy': synergy,
            'momentum': momentum,
            'context': context,
            'winning_preference': winning_preference  # V1.5: For smart template selection
        }

        return total, components

    def _generate_reason(self, target: Dict, candidate: Dict, components: Dict, trust_level: str) -> str:
        """Generate explainable match reason string"""
        parts = []

        if components['intent'] > 0.5:
            parts.append(f"You need what {candidate.get('name', 'they')} offers")

        if components['synergy'] > 0.7:
            parts.append("Strong business alignment")
        elif components['synergy'] > 0.4:
            parts.append("Complementary niches")

        if components['momentum'] > 0.8:
            parts.append("Very active recently")
        elif components['momentum'] < 0.4:
            parts.append("Less active (30+ days)")

        if components['context'] > 0:
            parts.append("Attended same event(s)")

        if trust_level == 'platinum':
            parts.append("✅ Verified intent")
        elif trust_level == 'legacy':
            parts.append("⚠️ Based on profile data")

        return ". ".join(parts) if parts else "Potential partnership opportunity"

    def apply_popularity_cap(
        self,
        all_matches: List[Dict],
        match_cycle_id: str
    ) -> List[Dict]:
        """
        Post-processing: Limit how often any profile appears in Top 3

        Rule: A single profile cannot appear in Top 3 for more than
        POPULARITY_CAP (5) distinct users per cycle.
        """
        from collections import defaultdict

        appearance_count = defaultdict(int)
        filtered_matches = []

        # Group matches by target profile
        by_profile = defaultdict(list)
        for match in all_matches:
            by_profile[match['profile_id']].append(match)

        # Sort each profile's matches and count Top 3 appearances
        for profile_id, matches in by_profile.items():
            matches.sort(key=lambda x: x['harmonic_mean'], reverse=True)
            for rank, match in enumerate(matches):
                match['rank'] = rank + 1
                suggested_id = match['suggested_profile_id']

                if rank < 3:  # Top 3
                    if appearance_count[suggested_id] < self.POPULARITY_CAP:
                        appearance_count[suggested_id] += 1
                        filtered_matches.append(match)
                    # else: skip - over popular
                else:
                    filtered_matches.append(match)

        # Store popularity counts for analytics
        try:
            for profile_id, count in appearance_count.items():
                self.supabase.table("match_popularity").upsert({
                    'profile_id': profile_id,
                    'match_cycle_id': match_cycle_id,
                    'top_3_appearances': count
                }, on_conflict="profile_id,match_cycle_id").execute()
        except Exception as e:
            print(f"Error updating popularity: {e}")

        return filtered_matches

    def generate_all_matches_fast(
        self,
        match_cycle_id: str,
        top_n: int = 10,
        min_score: float = 5.0
    ) -> Dict:
        """
        OPTIMIZED V1 Match Generation - Much faster than generate_all_matches

        Optimizations:
        1. Pre-fetch ALL data in single batch queries (no per-profile DB calls)
        2. Only process profiles WITH offering data
        3. Use keyword matching before expensive semantic calls
        4. Skip obviously non-matching pairs early

        Args:
            match_cycle_id: Unique ID for this match cycle
            top_n: Number of top matches per profile
            min_score: Minimum harmonic mean score (0-100 scale)
        """
        import time
        from collections import defaultdict
        start_time = time.time()

        print(f"[V1-FAST] Starting optimized match generation for cycle: {match_cycle_id}")

        # Step 1: Batch fetch ALL matchable profiles (have offering OR niche)
        print("[V1-FAST] Fetching matchable profiles (offering OR niche)...")
        try:
            profiles_with_offers = self._fetch_matchable_profiles_paginated(
                select_fields="id, name, company, offering, seeking, niche, business_focus, list_size, social_reach, last_active_at"
            )
        except Exception as e:
            return {'success': False, 'error': f'Failed to fetch profiles: {e}'}

        print(f"[V1-FAST] Found {len(profiles_with_offers)} matchable profiles")

        if len(profiles_with_offers) < 2:
            return {'success': False, 'error': 'Not enough profiles with offering data'}

        # Step 2: Pre-process all profile data (no DB calls needed)
        profile_data = {}
        for p in profiles_with_offers:
            pid = p['id']
            # Parse offering into list (use business_focus as fallback)
            raw_offering = p.get('offering') or p.get('business_focus') or ''
            offers = [o.strip() for o in raw_offering.split(',') if o.strip()][:2]
            # Parse seeking (or use business_focus as fallback need indicator)
            needs = [n.strip() for n in (p.get('seeking') or p.get('business_focus') or '').split(',') if n.strip()][:2]

            profile_data[pid] = {
                'profile': p,
                'offers': offers,
                'needs': needs,
                'niche': p.get('niche') or p.get('business_focus') or '',
                'list_size': p.get('list_size') or 0,
                'social_reach': p.get('social_reach') or 0,
                'last_active_at': p.get('last_active_at'),
                # Default to legacy trust (no intake form)
                'trust_level': 'legacy',
                'weight_multiplier': 0.3
            }

        print(f"[V1-FAST] Pre-processed {len(profile_data)} profiles")

        # Step 3: Generate matches using keyword matching (no OpenAI calls)
        all_matches = []
        profiles_processed = 0
        pairs_evaluated = 0

        profile_ids = list(profile_data.keys())
        total_pairs = len(profile_ids) * (len(profile_ids) - 1) // 2
        print(f"[V1-FAST] Evaluating up to {total_pairs} pairs...")

        for i, target_id in enumerate(profile_ids):
            target = profile_data[target_id]
            target_profile = target['profile']

            for j in range(i + 1, len(profile_ids)):
                candidate_id = profile_ids[j]
                candidate = profile_data[candidate_id]
                candidate_profile = candidate['profile']
                pairs_evaluated += 1

                # Quick keyword match check (skip OpenAI)
                intent_ab = self._keyword_intent_score(target['needs'], candidate['offers'])
                intent_ba = self._keyword_intent_score(candidate['needs'], target['offers'])

                # Skip if no intent match in either direction
                if intent_ab == 0 and intent_ba == 0:
                    continue

                # Calculate synergy based on niche overlap
                synergy_ab = self._fast_synergy_score(target['niche'], candidate['niche'])
                synergy_ba = synergy_ab  # Symmetric

                # Calculate momentum (time decay)
                momentum_ab = self.calculate_momentum_score(target['last_active_at'])
                momentum_ba = self.calculate_momentum_score(candidate['last_active_at'])

                # Context score (placeholder - could add more factors)
                context_ab = 0.5
                context_ba = 0.5

                # Calculate directional scores
                score_ab = (
                    self.WEIGHTS['intent'] * intent_ab +
                    self.WEIGHTS['synergy'] * synergy_ab +
                    self.WEIGHTS['momentum'] * momentum_ab +
                    self.WEIGHTS['context'] * context_ab
                )
                score_ba = (
                    self.WEIGHTS['intent'] * intent_ba +
                    self.WEIGHTS['synergy'] * synergy_ba +
                    self.WEIGHTS['momentum'] * momentum_ba +
                    self.WEIGHTS['context'] * context_ba
                )

                # Harmonic mean (scale to 0-100)
                harmonic = self.calculate_harmonic_mean(score_ab, score_ba) * 100

                # Apply trust weighting
                trust_weight = min(target['weight_multiplier'], candidate['weight_multiplier'])
                weighted_score = harmonic * trust_weight

                if weighted_score < min_score:
                    continue

                # Add bidirectional matches
                match_reason = f"Keyword match: {target['offers'][:1]} ↔ {candidate['offers'][:1]}"

                all_matches.append({
                    'profile_id': target_id,
                    'suggested_profile_id': candidate_id,
                    'score_ab': round(score_ab * 100, 2),
                    'score_ba': round(score_ba * 100, 2),
                    'harmonic_mean': round(harmonic, 2),
                    'match_score': round(weighted_score, 2),
                    'trust_level': target['trust_level'],
                    'match_reason': match_reason
                })

                all_matches.append({
                    'profile_id': candidate_id,
                    'suggested_profile_id': target_id,
                    'score_ab': round(score_ba * 100, 2),
                    'score_ba': round(score_ab * 100, 2),
                    'harmonic_mean': round(harmonic, 2),
                    'match_score': round(weighted_score, 2),
                    'trust_level': candidate['trust_level'],
                    'match_reason': match_reason
                })

            profiles_processed += 1
            if profiles_processed % 100 == 0:
                elapsed = time.time() - start_time
                print(f"[V1-FAST] Processed {profiles_processed}/{len(profile_ids)} profiles ({pairs_evaluated} pairs, {len(all_matches)} matches) in {elapsed:.1f}s")

        print(f"[V1-FAST] Generated {len(all_matches)} total matches from {pairs_evaluated} pairs")

        # Step 4: Keep only top_n per profile
        by_profile = defaultdict(list)
        for match in all_matches:
            by_profile[match['profile_id']].append(match)

        # Sort and trim
        final_matches = []
        for profile_id, matches in by_profile.items():
            matches.sort(key=lambda x: x['harmonic_mean'], reverse=True)
            final_matches.extend(matches[:top_n])

        print(f"[V1-FAST] Trimmed to {len(final_matches)} matches (top {top_n} per profile)")

        # Step 5: Batch save to database
        saved = 0
        errors = 0
        for match in final_matches:
            try:
                self.supabase.table("match_suggestions").upsert(
                    match,
                    on_conflict="profile_id,suggested_profile_id"
                ).execute()
                saved += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"[V1-FAST] Save error: {e}")

        total_time = time.time() - start_time
        print(f"[V1-FAST] COMPLETE: Saved {saved} matches in {total_time:.1f}s ({errors} errors)")

        return {
            'success': True,
            'profiles_processed': profiles_processed,
            'pairs_evaluated': pairs_evaluated,
            'matches_created': saved,
            'total_time_seconds': round(total_time, 1)
        }

    def _keyword_intent_score(self, needs: List[str], offers: List[str]) -> float:
        """Fast keyword-based intent matching (no API calls)"""
        if not needs or not offers:
            return 0.0

        needs_lower = [n.lower() for n in needs]
        offers_lower = [o.lower() for o in offers]

        # Check for any word overlap
        for need in needs_lower:
            need_words = set(need.split())
            for offer in offers_lower:
                offer_words = set(offer.split())
                # If any significant word overlaps, count as match
                overlap = need_words & offer_words
                # Remove common stop words
                overlap -= {'and', 'the', 'a', 'an', 'or', 'for', 'to', 'in', 'of', 'with'}
                if overlap:
                    return 1.0

        return 0.0

    def _fast_synergy_score(self, niche_a: str, niche_b: str) -> float:
        """Fast niche overlap scoring (no API calls)"""
        if not niche_a or not niche_b:
            return 0.3  # Default for unknown niches

        niche_a_lower = niche_a.lower()
        niche_b_lower = niche_b.lower()

        # Exact match
        if niche_a_lower == niche_b_lower:
            return 0.8

        # Word overlap
        words_a = set(niche_a_lower.replace(',', ' ').split())
        words_b = set(niche_b_lower.replace(',', ' ').split())
        words_a -= {'and', 'the', 'a', 'an', 'or', 'for', 'to', 'in', 'of', 'with'}
        words_b -= {'and', 'the', 'a', 'an', 'or', 'for', 'to', 'in', 'of', 'with'}

        if not words_a or not words_b:
            return 0.3

        overlap = len(words_a & words_b)
        total = len(words_a | words_b)

        if overlap > 0:
            return 0.5 + (0.3 * overlap / total)

        return 0.3

    def generate_all_matches_hybrid(
        self,
        match_cycle_id: str,
        top_n: int = 10,
        min_score: float = 5.0
    ) -> Dict:
        """
        TWO-STAGE HYBRID Match Generation - Best quality with optimized speed

        Stage 1: Fast keyword pre-filter (eliminates ~60-70% of pairs)
        - Keyword overlap between needs/offers
        - Niche compatibility check
        - Scale symmetry pre-check

        Stage 2: Full V1 semantic scoring (on remaining ~30-40%)
        - OpenAI semantic intent matching
        - Full harmonic mean reciprocity
        - Trust level weighting

        This gives V1-quality results at ~3x speed improvement.
        """
        import time
        from collections import defaultdict
        start_time = time.time()

        print(f"[V1-HYBRID] Starting two-stage match generation for cycle: {match_cycle_id}")

        # ============================================
        # STAGE 0: Pre-fetch all matchable profiles (offering OR niche)
        # ============================================
        print("[V1-HYBRID] Stage 0: Fetching matchable profiles (offering OR niche)...")
        try:
            profiles_with_offers = self._fetch_matchable_profiles_paginated(
                select_fields="id, name, company, offering, seeking, niche, business_focus, list_size, social_reach, last_active_at"
            )
        except Exception as e:
            return {'success': False, 'error': f'Failed to fetch profiles: {e}'}

        print(f"[V1-HYBRID] Found {len(profiles_with_offers)} matchable profiles")

        if len(profiles_with_offers) < 2:
            return {'success': False, 'error': 'Not enough profiles with offering data'}

        # Pre-process profile data
        profile_data = {}
        for p in profiles_with_offers:
            pid = p['id']
            # Use business_focus as fallback for offering
            raw_offering = p.get('offering') or p.get('business_focus') or ''
            offers = [o.strip() for o in raw_offering.split(',') if o.strip()][:2]
            needs = [n.strip() for n in (p.get('seeking') or p.get('business_focus') or '').split(',') if n.strip()][:2]

            profile_data[pid] = {
                'profile': p,
                'offers': offers,
                'needs': needs,
                'niche': p.get('niche') or p.get('business_focus') or '',
                'list_size': p.get('list_size') or 0,
                'social_reach': p.get('social_reach') or 0,
                'last_active_at': p.get('last_active_at'),
                'trust_level': 'legacy',
                'weight_multiplier': 0.3
            }

        profile_ids = list(profile_data.keys())
        total_pairs = len(profile_ids) * (len(profile_ids) - 1) // 2
        print(f"[V1-HYBRID] Total possible pairs: {total_pairs}")

        # ============================================
        # STAGE 1: Fast keyword pre-filter
        # ============================================
        print("[V1-HYBRID] Stage 1: Running keyword pre-filter...")
        candidate_pairs = []
        pairs_checked = 0
        pairs_passed = 0

        for i, target_id in enumerate(profile_ids):
            target = profile_data[target_id]

            for j in range(i + 1, len(profile_ids)):
                candidate_id = profile_ids[j]
                candidate = profile_data[candidate_id]
                pairs_checked += 1

                # Pre-filter 1: Check keyword overlap in EITHER direction
                has_keyword_match = (
                    self._keyword_intent_score(target['needs'], candidate['offers']) > 0 or
                    self._keyword_intent_score(candidate['needs'], target['offers']) > 0
                )

                if not has_keyword_match:
                    # Pre-filter 2: Check niche overlap as fallback
                    niche_score = self._fast_synergy_score(target['niche'], candidate['niche'])
                    if niche_score < 0.5:  # No niche overlap either
                        continue

                # NOTE: Removed Scale Symmetry pre-filter (Pre-filter 3)
                # Reason: list_size and social_reach data is not reliably populated
                # Scale symmetry is still used as a SCORING FACTOR in Stage 2, not a hard filter

                # This pair passed pre-filtering
                candidate_pairs.append((target_id, candidate_id))
                pairs_passed += 1

        filter_rate = 100 * (1 - pairs_passed / max(pairs_checked, 1))
        stage1_time = time.time() - start_time
        print(f"[V1-HYBRID] Stage 1 complete: {pairs_passed}/{pairs_checked} pairs passed ({filter_rate:.1f}% filtered out) in {stage1_time:.1f}s")

        # ============================================
        # STAGE 2: Full V1 semantic scoring on candidates
        # ============================================
        print(f"[V1-HYBRID] Stage 2: Running V1 semantic scoring on {len(candidate_pairs)} candidate pairs...")
        stage2_start = time.time()

        all_matches = []
        pairs_scored = 0

        for target_id, candidate_id in candidate_pairs:
            target = profile_data[target_id]
            candidate = profile_data[candidate_id]
            target_profile = target['profile']
            candidate_profile = candidate['profile']

            # Full V1 semantic intent scoring (uses OpenAI)
            intent_ab = self.calculate_intent_score(target['needs'], candidate['offers'])
            intent_ba = self.calculate_intent_score(candidate['needs'], target['offers'])

            # Synergy scoring
            synergy = self._fast_synergy_score(target['niche'], candidate['niche'])

            # Momentum scoring
            momentum_ab = self.calculate_momentum_score(target['last_active_at'])
            momentum_ba = self.calculate_momentum_score(candidate['last_active_at'])

            # Context (placeholder)
            context = 0.5

            # Calculate directional scores
            score_ab = (
                self.WEIGHTS['intent'] * intent_ab +
                self.WEIGHTS['synergy'] * synergy +
                self.WEIGHTS['momentum'] * momentum_ab +
                self.WEIGHTS['context'] * context
            )
            score_ba = (
                self.WEIGHTS['intent'] * intent_ba +
                self.WEIGHTS['synergy'] * synergy +
                self.WEIGHTS['momentum'] * momentum_ba +
                self.WEIGHTS['context'] * context
            )

            # Harmonic mean (scale to 0-100)
            harmonic = self.calculate_harmonic_mean(score_ab, score_ba) * 100

            # Apply trust weighting
            trust_weight = min(target['weight_multiplier'], candidate['weight_multiplier'])
            weighted_score = harmonic * trust_weight

            pairs_scored += 1
            if pairs_scored % 500 == 0:
                elapsed = time.time() - stage2_start
                print(f"[V1-HYBRID] Stage 2 progress: {pairs_scored}/{len(candidate_pairs)} pairs scored in {elapsed:.1f}s")

            if weighted_score < min_score:
                continue

            # Generate match reason
            match_reason = self._generate_reason(target_profile, candidate_profile,
                {'intent': intent_ab, 'synergy': synergy, 'momentum': momentum_ab, 'context': context}, target['trust_level'])

            # Add bidirectional matches
            all_matches.append({
                'profile_id': target_id,
                'suggested_profile_id': candidate_id,
                'score_ab': round(score_ab * 100, 2),
                'score_ba': round(score_ba * 100, 2),
                'harmonic_mean': round(harmonic, 2),
                'match_score': round(weighted_score, 2),
                'trust_level': target['trust_level'],
                'match_reason': match_reason
            })

            all_matches.append({
                'profile_id': candidate_id,
                'suggested_profile_id': target_id,
                'score_ab': round(score_ba * 100, 2),
                'score_ba': round(score_ab * 100, 2),
                'harmonic_mean': round(harmonic, 2),
                'match_score': round(weighted_score, 2),
                'trust_level': candidate['trust_level'],
                'match_reason': match_reason
            })

        stage2_time = time.time() - stage2_start
        print(f"[V1-HYBRID] Stage 2 complete: {len(all_matches)} matches generated in {stage2_time:.1f}s")

        # ============================================
        # STAGE 3: Keep top_n per profile and save
        # ============================================
        print("[V1-HYBRID] Stage 3: Saving top matches to database...")

        by_profile = defaultdict(list)
        for match in all_matches:
            by_profile[match['profile_id']].append(match)

        final_matches = []
        for profile_id, matches in by_profile.items():
            matches.sort(key=lambda x: x['harmonic_mean'], reverse=True)
            final_matches.extend(matches[:top_n])

        print(f"[V1-HYBRID] Trimmed to {len(final_matches)} matches (top {top_n} per profile)")

        saved = 0
        errors = 0
        for match in final_matches:
            try:
                self.supabase.table("match_suggestions").upsert(
                    match,
                    on_conflict="profile_id,suggested_profile_id"
                ).execute()
                saved += 1
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"[V1-HYBRID] Save error: {e}")

        total_time = time.time() - start_time
        print(f"[V1-HYBRID] COMPLETE: Saved {saved} matches in {total_time:.1f}s total")
        print(f"[V1-HYBRID] Stats: {pairs_checked} pairs checked, {pairs_passed} passed filter ({filter_rate:.1f}% eliminated), {saved} saved")

        return {
            'success': True,
            'profiles_processed': len(profile_ids),
            'total_pairs': pairs_checked,
            'pairs_after_filter': pairs_passed,
            'filter_elimination_rate': round(filter_rate, 1),
            'matches_created': saved,
            'stage1_time_seconds': round(stage1_time, 1),
            'stage2_time_seconds': round(stage2_time, 1),
            'total_time_seconds': round(total_time, 1)
        }

    def generate_all_matches(
        self,
        match_cycle_id: str,
        top_n: int = 10,
        min_score: float = 15.0
    ) -> Dict:
        """
        Generate V1 matches for all profiles with verified intent or fallback data

        Args:
            match_cycle_id: Unique ID for this match cycle (e.g., "2025-01-cycle")
            top_n: Number of top matches per profile
            min_score: Minimum harmonic mean score (0-100 scale)

        Returns:
            Dict with success status and statistics
        """
        print(f"Starting V1 match generation for cycle: {match_cycle_id}")

        # Get all profiles (with pagination to bypass 1000 row limit)
        try:
            all_profiles = self._fetch_all_profiles_paginated(select_fields="*")
        except Exception as e:
            return {'success': False, 'error': f'Failed to fetch profiles: {e}'}

        print(f"Found {len(all_profiles)} profiles")

        # Pre-fetch verified data for all profiles
        profile_data = {}
        for profile in all_profiles:
            pid = profile['id']
            profile_data[pid] = {
                'profile': profile,
                'verified': self._get_verified_data(pid)
            }

        all_matches = []
        profiles_processed = 0

        for target_id, target_info in profile_data.items():
            target_profile = target_info['profile']
            target_verified = target_info['verified']

            for candidate_id, candidate_info in profile_data.items():
                if candidate_id == target_id:
                    continue

                candidate_profile = candidate_info['profile']
                candidate_verified = candidate_info['verified']

                # Calculate bidirectional scores
                score_ab, components_ab = self._calculate_directional_score(
                    target_profile, candidate_profile, target_verified, candidate_verified
                )
                score_ba, components_ba = self._calculate_directional_score(
                    candidate_profile, target_profile, candidate_verified, target_verified
                )

                # Harmonic mean (scale to 0-100)
                harmonic = self.calculate_harmonic_mean(score_ab, score_ba) * 100

                # Apply trust level weighting
                trust_weight = min(target_verified['weight_multiplier'], candidate_verified['weight_multiplier'])
                weighted_score = harmonic * trust_weight

                if weighted_score < min_score:
                    continue

                all_matches.append({
                    'profile_id': target_id,
                    'suggested_profile_id': candidate_id,
                    'score_ab': round(score_ab * 100, 2),
                    'score_ba': round(score_ba * 100, 2),
                    'harmonic_mean': round(harmonic, 2),
                    'match_score': round(weighted_score, 2),
                    'scale_symmetry_score': round(components_ab['synergy'], 2),
                    'trust_level': target_verified['trust_level'],
                    'match_reason': self._generate_reason(
                        target_profile, candidate_profile, components_ab, target_verified['trust_level']
                    )
                })

            profiles_processed += 1
            if profiles_processed % 100 == 0:
                print(f"Processed {profiles_processed}/{len(all_profiles)} profiles...")

        # Apply popularity cap
        filtered_matches = self.apply_popularity_cap(all_matches, match_cycle_id)

        # Save to database (keep only top_n per profile)
        from collections import defaultdict
        by_profile = defaultdict(list)
        for match in filtered_matches:
            by_profile[match['profile_id']].append(match)

        saved = 0
        for profile_id, matches in by_profile.items():
            matches.sort(key=lambda x: x['harmonic_mean'], reverse=True)
            for match in matches[:top_n]:
                try:
                    self.supabase.table("match_suggestions").upsert(
                        match,
                        on_conflict="profile_id,suggested_profile_id"
                    ).execute()
                    saved += 1
                except Exception as e:
                    print(f"Error saving match: {e}")

        print(f"V1 match generation complete: {saved} matches saved")

        return {
            'success': True,
            'profiles_processed': profiles_processed,
            'matches_created': saved,
            'match_cycle_id': match_cycle_id
        }

    def generate_matches_for_user(self, profile_id: str, top_n: int = 10, min_score: float = 5.0) -> Dict:
        """Generate V1 matches for a specific user"""
        print(f"[V1] Starting match generation for profile: {profile_id}")

        # Get target profile
        result = self.directory_service.get_profile_by_id(profile_id)
        if not result.get('success') or not result.get('data'):
            print(f"[V1] ERROR: Profile not found")
            return {'success': False, 'error': 'Profile not found'}

        target_profile = result['data']
        target_verified = self._get_verified_data(profile_id)
        print(f"[V1] Target: {target_profile.get('name')} | Trust: {target_verified['trust_level']} | Offers: {target_verified['offers'][:2] if target_verified['offers'] else 'None'} | Needs: {target_verified['needs'][:2] if target_verified['needs'] else 'None'}")

        # Get all profiles
        all_result = self.directory_service.get_all_profiles_for_matching()
        if not all_result:
            print(f"[V1] ERROR: Failed to fetch profiles")
            return {'success': False, 'error': 'Failed to fetch profiles'}

        print(f"[V1] Evaluating {len(all_result)} candidate profiles...")

        matches = []
        scores_above_zero = 0

        for candidate in all_result:
            if candidate['id'] == profile_id:
                continue

            candidate_verified = self._get_verified_data(candidate['id'])

            score_ab, components_ab = self._calculate_directional_score(
                target_profile, candidate, target_verified, candidate_verified
            )
            score_ba, components_ba = self._calculate_directional_score(
                candidate, target_profile, candidate_verified, target_verified
            )

            harmonic = self.calculate_harmonic_mean(score_ab, score_ba) * 100
            trust_weight = min(target_verified['weight_multiplier'], candidate_verified['weight_multiplier'])
            weighted_score = harmonic * trust_weight

            if harmonic > 0:
                scores_above_zero += 1

            # Lower threshold to allow more matches through (default 5.0 instead of 15.0)
            if weighted_score >= min_score:
                # V1.5: Include winning_preference for smart template selection
                winning_pref = components_ab.get('winning_preference', 'Peer_Bundle')

                matches.append({
                    'profile_id': profile_id,
                    'suggested_profile_id': candidate['id'],
                    'profile': candidate,
                    'score_ab': round(score_ab * 100, 2),
                    'score_ba': round(score_ba * 100, 2),
                    'harmonic_mean': round(harmonic, 2),
                    'match_score': round(weighted_score, 2),
                    'trust_level': target_verified['trust_level'],
                    'winning_preference': winning_pref,  # V1.5: For Draft Intro template
                    'match_reason': self._generate_reason(
                        target_profile, candidate, components_ab, target_verified['trust_level']
                    )
                })

        print(f"[V1] Scores > 0: {scores_above_zero} | Matches above threshold ({min_score}): {len(matches)}")

        # Sort and keep top N
        matches.sort(key=lambda x: x['harmonic_mean'], reverse=True)
        matches = matches[:top_n]

        if matches:
            print(f"[V1] Top match: {matches[0].get('profile', {}).get('name')} | Score: {matches[0].get('harmonic_mean')}")

        # Save to database
        saved = 0
        for match in matches:
            match_copy = {k: v for k, v in match.items() if k != 'profile'}
            try:
                self.supabase.table("match_suggestions").upsert(
                    match_copy,
                    on_conflict="profile_id,suggested_profile_id"
                ).execute()
                saved += 1
            except Exception as e:
                print(f"[V1] Error saving match: {e}")

        print(f"[V1] COMPLETE: Saved {saved} matches to database")

        return {
            'success': True,
            'matches_created': saved,
            'matches': matches
        }


def get_matcher(use_ai: bool = False, use_hybrid: bool = False, use_conversation: bool = False, use_v1: bool = False, api_key: Optional[str] = None):
    """Factory function to get appropriate matcher"""
    if use_v1:
        return V1MatchGenerator(api_key)
    if use_conversation:
        return ConversationAwareMatchGenerator(api_key)
    if use_hybrid:
        return HybridMatchGenerator(api_key)
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
        elif sys.argv[1] == '--hybrid':
            print("Generating hybrid matches for all profiles...")
            generator = HybridMatchGenerator()
            result = generator.generate_all_matches(top_n=10, min_score=15.0)
            print(f"\nResult: {result}")
        elif sys.argv[1] == '--embeddings':
            print("Generating embeddings for all profiles...")
            generator = HybridMatchGenerator()
            result = generator.generate_all_embeddings()
            print(f"\nResult: {result}")
    else:
        print("Usage:")
        print("  python match_generator.py --all        # Keyword matching for all")
        print("  python match_generator.py --ai         # AI matching (needs OPENROUTER_API_KEY)")
        print("  python match_generator.py --hybrid     # Hybrid matching (needs OPENAI_API_KEY)")
        print("  python match_generator.py --embeddings # Generate embeddings only")
