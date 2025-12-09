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
from typing import List, Dict, Set, Tuple, Optional
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

        self._conversation_data_loaded = True
        print(f"  Indexed: {len(self._signals_by_profile)} profiles with signals, "
              f"{len(self._transcripts_by_profile)} profiles in conversations")

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

            # Add to all_matches with rank
            for rank, match in enumerate(matches):
                all_matches.append({
                    'profile_id': target['id'],
                    'suggested_profile_id': match['profile']['id'],
                    'score': match['score'],
                    'reason': match.get('reason', ''),
                    'rank': rank + 1,
                    'rich_analysis': None
                })

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


def get_matcher(use_ai: bool = False, use_hybrid: bool = False, use_conversation: bool = False, api_key: Optional[str] = None):
    """Factory function to get appropriate matcher"""
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
