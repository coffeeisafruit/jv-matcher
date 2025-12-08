"""
AI Profile Extractor for Rich JV Matching System
Extracts structured profile data from transcripts and matches to existing profiles
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher
from openai import OpenAI
from supabase_client import get_admin_client
from directory_service import DirectoryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIProfileExtractor:
    """
    Extracts rich profile information from transcript text using OpenAI
    and intelligently matches to existing profiles with confidence scoring
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the profile extractor

        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.directory_service = DirectoryService(use_admin=True)
        self.supabase = get_admin_client()

    def extract_profile_from_transcript(self, transcript_text: str) -> Dict[str, Any]:
        """
        Extract structured profile data from a transcript using GPT-4o-mini

        Args:
            transcript_text: The raw transcript text

        Returns:
            Dict containing extracted profile fields with confidence scores
        """
        try:
            logger.info("Extracting profile data from transcript")

            prompt = """
            Extract profile information from this transcript. Return a JSON object with these fields:

            {
                "name": "Person's full name",
                "email": "Email address if mentioned",
                "company": "Company or brand name",
                "what_you_do": "Clear description of their business/service (2-3 sentences)",
                "who_you_serve": "Target audience/ideal client description",
                "seeking": "What they're looking for in partnerships",
                "offering": "What they can offer to partners",
                "current_projects": "Active projects or initiatives",
                "contact": "Contact information (phone, website, social media)",
                "business_focus": "Primary business category/niche",
                "list_size": "Email list size (number only, 0 if not mentioned)",
                "social_reach": "Social media following (number only, 0 if not mentioned)"
            }

            Guidelines:
            - Extract only information explicitly stated in the transcript
            - Use null for fields not mentioned
            - Be specific and concise
            - Focus on actionable partnership details
            - For list_size and social_reach, extract numbers only

            Transcript:
            """

            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting structured business profile data from conversations."},
                    {"role": "user", "content": f"{prompt}\n\n{transcript_text}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            extracted_data = json.loads(response.choices[0].message.content)
            logger.info(f"Successfully extracted profile for: {extracted_data.get('name', 'Unknown')}")

            return {
                "success": True,
                "data": extracted_data,
                "confidence": self._calculate_extraction_confidence(extracted_data)
            }

        except Exception as e:
            logger.error(f"Error extracting profile from transcript: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "data": {}
            }

    def _calculate_extraction_confidence(self, profile_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on completeness of extracted data

        Args:
            profile_data: Extracted profile dictionary

        Returns:
            Confidence score (0-100)
        """
        required_fields = ["name", "what_you_do", "who_you_serve"]
        important_fields = ["email", "company", "seeking", "offering"]
        optional_fields = ["current_projects", "contact", "business_focus"]

        score = 0.0

        # Required fields: 50% of score
        for field in required_fields:
            if profile_data.get(field):
                score += 50.0 / len(required_fields)

        # Important fields: 30% of score
        for field in important_fields:
            if profile_data.get(field):
                score += 30.0 / len(important_fields)

        # Optional fields: 20% of score
        for field in optional_fields:
            if profile_data.get(field):
                score += 20.0 / len(optional_fields)

        return round(score, 2)

    def find_matching_profile(
        self,
        extracted_data: Dict[str, Any],
        confidence_threshold: float = 50.0
    ) -> Dict[str, Any]:
        """
        Find matching existing profile with confidence-based matching

        Matching strategy (by priority):
        1. Email match: 100% confidence
        2. Name + Company: 90% confidence
        3. Name only: 70% confidence
        4. Fuzzy name match: 50% confidence

        Args:
            extracted_data: Profile data extracted from transcript
            confidence_threshold: Minimum confidence to auto-update (default 50%)

        Returns:
            Dict with: {action: 'update'|'create'|'review', profile_id: str|None, confidence: float, match_details: dict}
        """
        try:
            name = extracted_data.get("name", "").strip()
            email = extracted_data.get("email", "").strip()
            company = extracted_data.get("company", "").strip()

            if not name:
                logger.warning("No name found in extracted data")
                return {
                    "action": "review",
                    "profile_id": None,
                    "confidence": 0.0,
                    "match_details": {"reason": "Missing name"},
                    "message": "Cannot match profile without a name"
                }

            # Strategy 1: Email match (100% confidence)
            if email:
                result = self.directory_service.get_profiles(limit=1)
                if result["success"] and result["data"]:
                    for profile in result["data"]:
                        if profile.get("email", "").lower() == email.lower():
                            logger.info(f"Found exact email match: {profile['id']}")
                            return {
                                "action": "update",
                                "profile_id": profile["id"],
                                "confidence": 100.0,
                                "match_details": {
                                    "strategy": "email_match",
                                    "matched_field": "email",
                                    "profile_name": profile.get("name")
                                },
                                "message": f"Exact email match found: {profile.get('name')}"
                            }

            # Get all profiles for fuzzy matching
            all_profiles_result = self.directory_service.get_profiles(limit=1000)
            if not all_profiles_result["success"]:
                logger.error("Failed to retrieve profiles for matching")
                return {
                    "action": "review",
                    "profile_id": None,
                    "confidence": 0.0,
                    "match_details": {"reason": "Database error"},
                    "message": "Unable to retrieve profiles for matching"
                }

            profiles = all_profiles_result["data"]

            # Strategy 2: Name + Company match (90% confidence)
            if company:
                for profile in profiles:
                    profile_name = profile.get("name", "").strip().lower()
                    profile_company = profile.get("company", "").strip().lower()

                    if (self._normalize_name(profile_name) == self._normalize_name(name.lower()) and
                        profile_company and company.lower() in profile_company):
                        logger.info(f"Found name+company match: {profile['id']}")
                        return {
                            "action": "update",
                            "profile_id": profile["id"],
                            "confidence": 90.0,
                            "match_details": {
                                "strategy": "name_company_match",
                                "profile_name": profile.get("name"),
                                "profile_company": profile.get("company")
                            },
                            "message": f"Strong match found: {profile.get('name')} at {profile.get('company')}"
                        }

            # Strategy 3: Exact name match (70% confidence)
            for profile in profiles:
                profile_name = profile.get("name", "").strip().lower()
                if self._normalize_name(profile_name) == self._normalize_name(name.lower()):
                    logger.info(f"Found exact name match: {profile['id']}")
                    return {
                        "action": "review" if confidence_threshold > 70 else "update",
                        "profile_id": profile["id"],
                        "confidence": 70.0,
                        "match_details": {
                            "strategy": "exact_name_match",
                            "profile_name": profile.get("name"),
                            "profile_company": profile.get("company")
                        },
                        "message": f"Name match found: {profile.get('name')} - recommend manual review"
                    }

            # Strategy 4: Fuzzy name match (50% confidence)
            best_match = None
            best_similarity = 0.0

            for profile in profiles:
                profile_name = profile.get("name", "").strip().lower()
                similarity = self._fuzzy_match(self._normalize_name(name.lower()), self._normalize_name(profile_name))

                if similarity > best_similarity and similarity >= 0.80:  # 80% string similarity
                    best_similarity = similarity
                    best_match = profile

            if best_match:
                confidence = 50.0 + (best_similarity - 0.80) * 100  # Scale 80-100% similarity to 50-70% confidence
                logger.info(f"Found fuzzy match: {best_match['id']} (similarity: {best_similarity:.2f})")
                return {
                    "action": "review",
                    "profile_id": best_match["id"],
                    "confidence": round(confidence, 2),
                    "match_details": {
                        "strategy": "fuzzy_name_match",
                        "similarity": round(best_similarity * 100, 2),
                        "profile_name": best_match.get("name"),
                        "profile_company": best_match.get("company")
                    },
                    "message": f"Possible match found: {best_match.get('name')} ({round(best_similarity * 100, 1)}% similar) - requires review"
                }

            # No match found - create new profile
            logger.info(f"No match found for {name}, suggesting creation")
            return {
                "action": "create",
                "profile_id": None,
                "confidence": 0.0,
                "match_details": {"reason": "No matching profile found"},
                "message": f"No existing profile found for {name}. Create new profile."
            }

        except Exception as e:
            logger.error(f"Error finding matching profile: {str(e)}")
            return {
                "action": "review",
                "profile_id": None,
                "confidence": 0.0,
                "match_details": {"error": str(e)},
                "message": f"Error during matching: {str(e)}"
            }

    def _normalize_name(self, name: str) -> str:
        """Normalize name for comparison (remove extra spaces, lowercase)"""
        return " ".join(name.lower().strip().split())

    def _fuzzy_match(self, str1: str, str2: str) -> float:
        """
        Calculate fuzzy string similarity using SequenceMatcher

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity ratio (0.0 to 1.0)
        """
        return SequenceMatcher(None, str1, str2).ratio()

    def queue_for_review(
        self,
        extracted_data: Dict[str, Any],
        match_result: Dict[str, Any],
        transcript_text: str = "",
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Add uncertain profile matches to review queue

        Args:
            extracted_data: Profile data extracted from transcript
            match_result: Result from find_matching_profile()
            transcript_text: Original transcript (optional)
            notes: Additional notes (optional)

        Returns:
            Dict with success status
        """
        try:
            logger.info(f"Adding to review queue: {extracted_data.get('name')}")

            # Match columns to the profile_review_queue table schema
            review_data = {
                "extracted_name": extracted_data.get("name", "Unknown"),
                "extracted_data": extracted_data,  # JSONB column
                "candidate_profile_id": match_result.get("profile_id"),
                "confidence_score": match_result.get("confidence", 0.0),
                "status": "pending",
                "source_transcript": transcript_text[:5000] if transcript_text else None,
            }

            response = self.supabase.table("profile_review_queue").insert(review_data).execute()

            logger.info(f"Successfully queued for review: {response.data[0]['id']}")
            return {
                "success": True,
                "review_id": response.data[0]["id"],
                "message": "Profile queued for manual review"
            }

        except Exception as e:
            logger.error(f"Error queueing for review: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to queue for review: {str(e)}"
            }

    def process_transcript(
        self,
        transcript_text: str,
        auto_update_threshold: float = 90.0,
        auto_create: bool = False
    ) -> Dict[str, Any]:
        """
        Complete pipeline: extract, match, and take action on transcript

        Args:
            transcript_text: The transcript to process
            auto_update_threshold: Minimum confidence to auto-update (default 90%)
            auto_create: Whether to automatically create new profiles (default False)

        Returns:
            Dict with full processing results
        """
        try:
            # Step 1: Extract profile data
            extraction_result = self.extract_profile_from_transcript(transcript_text)
            if not extraction_result["success"]:
                return extraction_result

            extracted_data = extraction_result["data"]

            # Step 2: Find matching profile
            match_result = self.find_matching_profile(extracted_data, auto_update_threshold)

            # Step 3: Take action based on match confidence
            action = match_result["action"]
            confidence = match_result["confidence"]

            if action == "update" and confidence >= auto_update_threshold:
                # High confidence - auto update
                profile_id = match_result["profile_id"]
                update_result = self.directory_service.update_profile(profile_id, {
                    "what_you_do": extracted_data.get("what_you_do"),
                    "who_you_serve": extracted_data.get("who_you_serve"),
                    "seeking": extracted_data.get("seeking"),
                    "offering": extracted_data.get("offering"),
                    "current_projects": extracted_data.get("current_projects"),
                    "business_focus": extracted_data.get("business_focus"),
                    "list_size": extracted_data.get("list_size", 0),
                    "social_reach": extracted_data.get("social_reach", 0)
                })

                return {
                    "success": True,
                    "action": "updated",
                    "profile_id": profile_id,
                    "confidence": confidence,
                    "message": f"Profile auto-updated with {confidence}% confidence"
                }

            elif action == "create" and auto_create:
                # Create new profile
                create_result = self.directory_service.create_profile(extracted_data)
                if create_result["success"]:
                    return {
                        "success": True,
                        "action": "created",
                        "profile_id": create_result["data"]["id"],
                        "message": "New profile created"
                    }
                else:
                    return create_result

            else:
                # Queue for review
                review_result = self.queue_for_review(
                    extracted_data,
                    match_result,
                    transcript_text,
                    notes=f"Action: {action}, Confidence: {confidence}%"
                )

                return {
                    "success": True,
                    "action": "queued_for_review",
                    "review_id": review_result.get("review_id"),
                    "confidence": confidence,
                    "match_details": match_result,
                    "message": match_result["message"]
                }

        except Exception as e:
            logger.error(f"Error processing transcript: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to process transcript: {str(e)}"
            }
