"""
Embedding Service - Semantic matching using OpenAI embeddings
Converts profile text to vectors for similarity matching
"""
import os
import json
from typing import List, Dict, Optional, Tuple
from functools import lru_cache

# Optional OpenAI import
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class EmbeddingService:
    """
    Generate and compare embeddings using OpenAI's text-embedding-3-small model.
    Provides semantic similarity for profile matching.
    """

    MODEL = "text-embedding-3-small"  # 1536 dimensions, cheap and fast
    DIMENSIONS = 1536

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key"""
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package required. Install with: pip install openai")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not set")

        self.client = OpenAI(api_key=self.api_key)

    def profile_to_text(self, profile: Dict) -> str:
        """Convert profile data to text for embedding"""
        parts = []

        # Name and company
        if profile.get('name'):
            parts.append(f"Name: {profile['name']}")
        if profile.get('company'):
            parts.append(f"Company: {profile['company']}")

        # Business details (most important for matching)
        if profile.get('business_focus'):
            parts.append(f"Business Focus: {profile['business_focus']}")
        if profile.get('service_provided'):
            parts.append(f"Services: {profile['service_provided']}")

        # Additional context
        if profile.get('status'):
            parts.append(f"Status: {profile['status']}")

        return "\n".join(parts) if parts else "No profile information available"

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector for a single text"""
        if not text or not text.strip():
            return [0.0] * self.DIMENSIONS

        try:
            response = self.client.embeddings.create(
                model=self.MODEL,
                input=text.strip()
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return [0.0] * self.DIMENSIONS

    def get_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """Get embeddings for multiple texts in batches"""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            # Filter empty strings
            batch = [t.strip() if t else "" for t in batch]

            try:
                response = self.client.embeddings.create(
                    model=self.MODEL,
                    input=batch
                )
                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                print(f"Batch embedding error: {e}")
                # Return zero vectors for failed batch
                all_embeddings.extend([[0.0] * self.DIMENSIONS] * len(batch))

        return all_embeddings

    def get_profile_embedding(self, profile: Dict) -> List[float]:
        """Get embedding for a profile"""
        text = self.profile_to_text(profile)
        return self.get_embedding(text)

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if not vec1 or not vec2:
            return 0.0

        # Manual calculation to avoid numpy dependency
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    def calculate_semantic_similarity(
        self,
        profile1: Dict,
        profile2: Dict,
        profile1_embedding: Optional[List[float]] = None,
        profile2_embedding: Optional[List[float]] = None
    ) -> float:
        """
        Calculate semantic similarity between two profiles.
        Returns value between 0 and 1.
        """
        # Use provided embeddings or generate new ones
        emb1 = profile1_embedding or self.get_profile_embedding(profile1)
        emb2 = profile2_embedding or self.get_profile_embedding(profile2)

        similarity = self.cosine_similarity(emb1, emb2)

        # Normalize to 0-1 range (cosine similarity can be -1 to 1)
        return max(0.0, min(1.0, (similarity + 1) / 2))

    def find_similar_profiles(
        self,
        target_profile: Dict,
        candidate_profiles: List[Dict],
        target_embedding: Optional[List[float]] = None,
        candidate_embeddings: Optional[List[List[float]]] = None,
        top_n: int = 10
    ) -> List[Tuple[Dict, float]]:
        """
        Find most similar profiles to target.
        Returns list of (profile, similarity_score) tuples.
        """
        # Get target embedding
        if target_embedding is None:
            target_embedding = self.get_profile_embedding(target_profile)

        # Get candidate embeddings if not provided
        if candidate_embeddings is None:
            texts = [self.profile_to_text(p) for p in candidate_profiles]
            candidate_embeddings = self.get_embeddings_batch(texts)

        # Calculate similarities
        similarities = []
        for i, candidate in enumerate(candidate_profiles):
            if candidate.get('id') == target_profile.get('id'):
                continue  # Skip self

            similarity = self.cosine_similarity(target_embedding, candidate_embeddings[i])
            # Convert to 0-100 scale
            score = max(0.0, min(100.0, similarity * 100))
            similarities.append((candidate, score))

        # Sort by similarity (highest first)
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_n]


def embedding_to_json(embedding: List[float]) -> str:
    """Convert embedding list to JSON string for database storage"""
    return json.dumps(embedding)


def json_to_embedding(json_str: str) -> List[float]:
    """Convert JSON string back to embedding list"""
    if not json_str:
        return []
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return []


# Factory function
def get_embedding_service(api_key: Optional[str] = None) -> Optional[EmbeddingService]:
    """Get embedding service if available"""
    try:
        return EmbeddingService(api_key)
    except (ImportError, ValueError) as e:
        print(f"Embedding service unavailable: {e}")
        return None


# CLI for testing
if __name__ == '__main__':
    import sys

    service = get_embedding_service()
    if not service:
        print("Could not initialize embedding service")
        sys.exit(1)

    # Test with sample profiles
    profile1 = {
        "name": "John Smith",
        "company": "Health Coaching Pro",
        "business_focus": "Health and wellness coaching for entrepreneurs",
        "service_provided": "1-on-1 coaching, group workshops, online courses"
    }

    profile2 = {
        "name": "Jane Doe",
        "company": "Wellness Warriors",
        "business_focus": "Corporate wellness programs and fitness training",
        "service_provided": "Corporate workshops, fitness bootcamps, nutrition consulting"
    }

    profile3 = {
        "name": "Bob Johnson",
        "company": "Digital Marketing Agency",
        "business_focus": "Social media marketing and content creation",
        "service_provided": "Social media management, content strategy, paid ads"
    }

    print("Getting embeddings...")
    emb1 = service.get_profile_embedding(profile1)
    emb2 = service.get_profile_embedding(profile2)
    emb3 = service.get_profile_embedding(profile3)

    print(f"\nSimilarity scores:")
    print(f"  Health Coach vs Wellness Warrior: {service.cosine_similarity(emb1, emb2) * 100:.1f}%")
    print(f"  Health Coach vs Marketing Agency: {service.cosine_similarity(emb1, emb3) * 100:.1f}%")
    print(f"  Wellness Warrior vs Marketing: {service.cosine_similarity(emb2, emb3) * 100:.1f}%")
