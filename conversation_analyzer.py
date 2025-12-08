"""
Conversation Analyzer - Extracts signals from networking transcripts
Handles both single-person intros and multi-person group conversations
"""
import os
import re
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


class ConversationAnalyzer:
    """
    Analyzes networking event transcripts to extract:
    1. Speaker identification and segmentation
    2. Topics/themes discussed
    3. Expressed interests and needs
    4. Connection signals (who showed interest in whom)
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the conversation analyzer"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)
        self.directory_service = DirectoryService(use_admin=True)
        self.supabase = get_admin_client()

    def analyze_transcript(
        self,
        transcript_text: str,
        event_name: str = None
    ) -> Dict[str, Any]:
        """
        Main entry point - analyzes a transcript and returns structured data

        Args:
            transcript_text: The raw transcript text
            event_name: Optional name of the event (e.g., "JV Mastermind Dec 2025")

        Returns:
            Dict with analysis results including speakers, topics, and signals
        """
        try:
            logger.info(f"Analyzing transcript (event: {event_name or 'unnamed'})")

            # Step 1: Detect transcript type
            transcript_type = self._detect_transcript_type(transcript_text)
            logger.info(f"Detected transcript type: {transcript_type}")

            # Step 2: Extract conversation signals using GPT
            analysis = self._extract_conversation_signals(transcript_text, transcript_type)

            if not analysis.get("success"):
                return analysis

            # Step 3: Match speakers to existing profiles
            analysis["data"] = self._match_speakers_to_profiles(analysis["data"])

            # Step 4: Store in database
            stored = self._store_conversation_data(
                transcript_text,
                event_name,
                transcript_type,
                analysis["data"]
            )

            return {
                "success": True,
                "transcript_type": transcript_type,
                "transcript_id": stored.get("transcript_id"),
                "speakers_count": len(analysis["data"].get("speakers", [])),
                "topics_count": len(analysis["data"].get("topics", [])),
                "signals_count": len(analysis["data"].get("signals", [])),
                "data": analysis["data"]
            }

        except Exception as e:
            logger.error(f"Error analyzing transcript: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _detect_transcript_type(self, text: str) -> str:
        """
        Detect if this is a solo intro or group conversation

        Args:
            text: Transcript text

        Returns:
            'solo_intro' or 'group'
        """
        # Look for speaker patterns like "Name:" at start of lines
        speaker_pattern = r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):'
        speakers = set(re.findall(speaker_pattern, text, re.MULTILINE))

        word_count = len(text.split())

        # Multiple speakers or long content suggests group conversation
        if len(speakers) > 1:
            return "group"
        elif word_count > 1000 and len(speakers) <= 1:
            # Long transcript with unclear speakers - treat as group
            return "group"
        else:
            return "solo_intro"

    def _extract_conversation_signals(
        self,
        transcript: str,
        transcript_type: str
    ) -> Dict[str, Any]:
        """
        Use GPT to extract structured conversation data

        Args:
            transcript: The transcript text
            transcript_type: 'solo_intro' or 'group'

        Returns:
            Dict with success status and extracted data
        """
        prompt = self._build_extraction_prompt(transcript, transcript_type)

        try:
            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing networking conversations to identify business opportunities, partnership potential, and connection signals."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )

            data = json.loads(response.choices[0].message.content)
            logger.info(f"Extracted {len(data.get('speakers', []))} speakers, "
                       f"{len(data.get('topics', []))} topics, "
                       f"{len(data.get('signals', []))} signals")

            return {"success": True, "data": data}

        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return {"success": False, "error": str(e), "data": {}}

    def _build_extraction_prompt(self, transcript: str, transcript_type: str) -> str:
        """Build the GPT extraction prompt based on transcript type"""

        if transcript_type == "solo_intro":
            return f"""
Analyze this individual introduction transcript and extract structured data.

TRANSCRIPT:
{transcript[:15000]}

Return a JSON object with:
{{
    "speakers": [
        {{
            "name": "Speaker's full name (extract from context)",
            "speaker_text": "Brief summary of what they said",
            "profile_data": {{
                "what_you_do": "Their business/service description",
                "who_you_serve": "Target audience",
                "seeking": "What they're looking for in partnerships",
                "offering": "What they can offer to partners",
                "current_projects": "Active initiatives mentioned"
            }}
        }}
    ],
    "topics": [
        {{
            "topic_name": "specific topic discussed (e.g., 'email marketing', 'course launches')",
            "topic_category": "business|health|finance|personal_dev|content|tech|relationships|spirituality",
            "relevance_score": 0-100
        }}
    ],
    "signals": [
        {{
            "speaker_name": "who said it",
            "signal_type": "need|interest|offer",
            "signal_text": "exact quote or close paraphrase of what indicates this signal",
            "confidence": 0-100
        }}
    ]
}}

Focus on extracting actionable partnership signals like:
- "I need someone who..." or "I'm looking for..." (need)
- "I'm interested in..." (interest)
- "I can help with..." or "I offer..." (offer)

Extract specific, concrete signals - not general business descriptions.
"""
        else:
            return f"""
Analyze this GROUP networking conversation transcript and extract structured data.

TRANSCRIPT:
{transcript[:15000]}

Return a JSON object with:
{{
    "speakers": [
        {{
            "name": "Speaker's full name",
            "speaker_text": "Summary of their main contributions (2-3 sentences)",
            "profile_data": {{
                "what_you_do": "Their business/service if mentioned",
                "who_you_serve": "Target audience if mentioned",
                "seeking": "What they're looking for if mentioned",
                "offering": "What they can offer if mentioned"
            }}
        }}
    ],
    "topics": [
        {{
            "topic_name": "specific topic discussed",
            "topic_category": "business|health|finance|personal_dev|content|tech|relationships|spirituality",
            "relevance_score": 0-100,
            "mentioned_by": ["Speaker Name 1", "Speaker Name 2"]
        }}
    ],
    "signals": [
        {{
            "speaker_name": "who expressed this",
            "signal_type": "need|interest|offer|connection",
            "signal_text": "exact quote or close paraphrase",
            "target_speaker": "name of person they showed interest in (for connection type, null otherwise)",
            "confidence": 0-100
        }}
    ],
    "connections": [
        {{
            "from_speaker": "Person A",
            "to_speaker": "Person B",
            "connection_reason": "Why they should connect based on conversation",
            "strength": 0-100
        }}
    ]
}}

Pay special attention to:
- Who showed interest in whom's offerings
- Complementary needs and offers between speakers
- Explicit "we should talk" or "I'd love to connect" moments
- Implicit connection opportunities based on aligned interests

Signal types:
- need: "I'm looking for...", "I need help with..."
- interest: "That sounds interesting", "Tell me more about..."
- offer: "I can help with...", "I offer...", "I have..."
- connection: "We should talk", direct interest in another person
"""

    def _match_speakers_to_profiles(self, data: Dict) -> Dict:
        """
        Match extracted speakers to existing profiles in the database

        Args:
            data: Extracted conversation data

        Returns:
            Data with matched_profile_id added to speakers
        """
        try:
            # Get all profiles for matching
            profiles_result = self.directory_service.get_profiles(limit=500)
            if not profiles_result.get("success"):
                logger.warning("Could not retrieve profiles for matching")
                return data

            all_profiles = profiles_result.get("data", [])

            for speaker in data.get("speakers", []):
                speaker_name = speaker.get("name", "").strip()
                if not speaker_name:
                    continue

                best_match = None
                best_score = 0.0

                for profile in all_profiles:
                    profile_name = profile.get("name", "").strip()
                    if not profile_name:
                        continue

                    # Calculate name similarity
                    similarity = self._name_similarity(speaker_name, profile_name)

                    if similarity > best_score and similarity >= 0.7:
                        best_score = similarity
                        best_match = profile

                if best_match:
                    speaker["matched_profile_id"] = best_match["id"]
                    speaker["match_confidence"] = round(best_score * 100, 2)
                    speaker["matched_profile_name"] = best_match.get("name")
                    logger.info(f"Matched speaker '{speaker_name}' to profile '{best_match.get('name')}' ({speaker['match_confidence']}%)")
                else:
                    speaker["matched_profile_id"] = None
                    speaker["match_confidence"] = 0
                    logger.info(f"No profile match found for speaker '{speaker_name}'")

            return data

        except Exception as e:
            logger.error(f"Error matching speakers to profiles: {e}")
            return data

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names"""
        # Normalize names
        n1 = " ".join(name1.lower().strip().split())
        n2 = " ".join(name2.lower().strip().split())

        # Exact match
        if n1 == n2:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, n1, n2).ratio()

    def _store_conversation_data(
        self,
        transcript_text: str,
        event_name: str,
        transcript_type: str,
        data: Dict
    ) -> Dict[str, Any]:
        """
        Store extracted conversation data in database

        Args:
            transcript_text: Original transcript
            event_name: Event name
            transcript_type: 'solo_intro' or 'group'
            data: Extracted data

        Returns:
            Dict with transcript_id and success status
        """
        try:
            # 1. Store transcript
            transcript_response = self.supabase.table("conversation_transcripts").insert({
                "event_name": event_name,
                "transcript_text": transcript_text[:50000],  # Limit size
                "transcript_type": transcript_type,
                "participant_count": len(data.get("speakers", [])),
                "analyzed_at": "now()"
            }).execute()

            transcript_id = transcript_response.data[0]["id"]
            logger.info(f"Stored transcript: {transcript_id}")

            # 2. Store speakers and build ID map
            speaker_id_map = {}
            for speaker in data.get("speakers", []):
                speaker_response = self.supabase.table("conversation_speakers").insert({
                    "transcript_id": transcript_id,
                    "speaker_name": speaker.get("name"),
                    "matched_profile_id": speaker.get("matched_profile_id"),
                    "match_confidence": speaker.get("match_confidence"),
                    "speaker_text": speaker.get("speaker_text", "")[:10000]
                }).execute()
                speaker_id_map[speaker.get("name")] = speaker_response.data[0]["id"]

            logger.info(f"Stored {len(speaker_id_map)} speakers")

            # 3. Store topics
            topics_stored = 0
            for topic in data.get("topics", []):
                # Map speaker names to IDs for mentioned_by
                mentioned_by_ids = []
                for name in topic.get("mentioned_by", []):
                    if speaker_id_map.get(name):
                        mentioned_by_ids.append(speaker_id_map[name])

                self.supabase.table("conversation_topics").insert({
                    "transcript_id": transcript_id,
                    "topic_name": topic.get("topic_name"),
                    "topic_category": topic.get("topic_category"),
                    "relevance_score": topic.get("relevance_score"),
                    "mentioned_by": mentioned_by_ids if mentioned_by_ids else None
                }).execute()
                topics_stored += 1

            logger.info(f"Stored {topics_stored} topics")

            # 4. Store signals
            signals_stored = 0
            for signal in data.get("signals", []):
                speaker_id = speaker_id_map.get(signal.get("speaker_name"))
                target_speaker_id = speaker_id_map.get(signal.get("target_speaker"))

                # Resolve profile IDs
                profile_id = None
                target_profile_id = None
                for speaker in data.get("speakers", []):
                    if speaker.get("name") == signal.get("speaker_name"):
                        profile_id = speaker.get("matched_profile_id")
                    if speaker.get("name") == signal.get("target_speaker"):
                        target_profile_id = speaker.get("matched_profile_id")

                self.supabase.table("conversation_signals").insert({
                    "transcript_id": transcript_id,
                    "speaker_id": speaker_id,
                    "profile_id": profile_id,
                    "signal_type": signal.get("signal_type"),
                    "signal_text": signal.get("signal_text"),
                    "target_speaker_id": target_speaker_id,
                    "target_profile_id": target_profile_id,
                    "confidence": signal.get("confidence")
                }).execute()
                signals_stored += 1

            logger.info(f"Stored {signals_stored} signals")

            return {"success": True, "transcript_id": transcript_id}

        except Exception as e:
            logger.error(f"Error storing conversation data: {e}")
            return {"success": False, "error": str(e)}

    def get_signals_for_profile(self, profile_id: str) -> List[Dict]:
        """
        Get all conversation signals for a profile

        Args:
            profile_id: The profile UUID

        Returns:
            List of signals
        """
        try:
            response = self.supabase.table("conversation_signals") \
                .select("*, transcript:transcript_id(event_name, created_at)") \
                .eq("profile_id", profile_id) \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting signals for profile: {e}")
            return []

    def get_connection_opportunities(self, profile_id: str) -> List[Dict]:
        """
        Find profiles that expressed interest in this profile's offerings

        Args:
            profile_id: The profile UUID

        Returns:
            List of connection opportunities
        """
        try:
            response = self.supabase.table("conversation_signals") \
                .select("*, speaker:speaker_id(speaker_name, matched_profile_id)") \
                .eq("target_profile_id", profile_id) \
                .eq("signal_type", "connection") \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error getting connection opportunities: {e}")
            return []

    def get_profiles_with_need(self, keyword: str) -> List[Dict]:
        """
        Find profiles that expressed a need matching a keyword

        Args:
            keyword: Keyword to search for in needs

        Returns:
            List of profiles with matching needs
        """
        try:
            response = self.supabase.table("conversation_signals") \
                .select("profile_id, signal_text, confidence") \
                .eq("signal_type", "need") \
                .ilike("signal_text", f"%{keyword}%") \
                .execute()
            return response.data
        except Exception as e:
            logger.error(f"Error finding profiles with need: {e}")
            return []

    def get_shared_topics(self, profile_id_1: str, profile_id_2: str) -> List[str]:
        """
        Find topics that both profiles discussed

        Args:
            profile_id_1: First profile UUID
            profile_id_2: Second profile UUID

        Returns:
            List of shared topic names
        """
        try:
            # Get speaker IDs for each profile
            speakers_1 = self.supabase.table("conversation_speakers") \
                .select("id") \
                .eq("matched_profile_id", profile_id_1) \
                .execute()

            speakers_2 = self.supabase.table("conversation_speakers") \
                .select("id") \
                .eq("matched_profile_id", profile_id_2) \
                .execute()

            if not speakers_1.data or not speakers_2.data:
                return []

            speaker_ids_1 = {s["id"] for s in speakers_1.data}
            speaker_ids_2 = {s["id"] for s in speakers_2.data}

            # Get topics for each speaker set
            topics_1 = self.supabase.table("conversation_topics") \
                .select("topic_name, mentioned_by") \
                .execute()

            shared_topics = []
            for topic in topics_1.data:
                mentioned_by = topic.get("mentioned_by") or []
                # Check if any speaker from profile 1 AND any speaker from profile 2 mentioned this topic
                mentioned_by_1 = any(sid in speaker_ids_1 for sid in mentioned_by)
                mentioned_by_2 = any(sid in speaker_ids_2 for sid in mentioned_by)
                if mentioned_by_1 and mentioned_by_2:
                    shared_topics.append(topic["topic_name"])

            return shared_topics

        except Exception as e:
            logger.error(f"Error finding shared topics: {e}")
            return []

    def were_in_same_conversation(self, profile_id_1: str, profile_id_2: str) -> bool:
        """
        Check if two profiles were in the same conversation

        Args:
            profile_id_1: First profile UUID
            profile_id_2: Second profile UUID

        Returns:
            True if they were in the same conversation
        """
        try:
            speakers_1 = self.supabase.table("conversation_speakers") \
                .select("transcript_id") \
                .eq("matched_profile_id", profile_id_1) \
                .execute()

            speakers_2 = self.supabase.table("conversation_speakers") \
                .select("transcript_id") \
                .eq("matched_profile_id", profile_id_2) \
                .execute()

            if not speakers_1.data or not speakers_2.data:
                return False

            transcript_ids_1 = {s["transcript_id"] for s in speakers_1.data}
            transcript_ids_2 = {s["transcript_id"] for s in speakers_2.data}

            return bool(transcript_ids_1 & transcript_ids_2)

        except Exception as e:
            logger.error(f"Error checking same conversation: {e}")
            return False
