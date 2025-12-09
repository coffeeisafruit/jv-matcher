"""
AI Profile Extractor for Rich JV Matching System
Extracts structured profile data from transcripts and matches to existing profiles
Supports chunked processing for large transcripts

Features:
- Chunk tracking and persistence for debugging/reprocessing
- Error tracking (no silent fails)
- Time-stamped profile field history
"""
import os
import re
import json
import logging
import hashlib
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Callable
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI
from supabase_client import get_admin_client
from directory_service import DirectoryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Token/character limits for chunking
MAX_CHUNK_CHARS = 24000  # ~6000 tokens - larger chunks = fewer API calls
MAX_PARALLEL_CHUNKS = 4  # Process up to 4 chunks concurrently


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

    # ============================================
    # ERROR TRACKING METHODS
    # ============================================

    def _log_error(
        self,
        error_type: str,
        error_message: str,
        error_details: Dict = None,
        transcript_id: str = None,
        chunk_id: str = None,
        profile_id: str = None
    ) -> None:
        """
        Log an error to the processing_errors table - NO MORE SILENT FAILS
        """
        try:
            error_data = {
                "error_type": error_type,
                "error_message": str(error_message)[:1000],  # Limit message length
                "error_details": error_details or {},
                "transcript_id": transcript_id,
                "chunk_id": chunk_id,
                "profile_id": profile_id,
                "status": "new"
            }
            self.supabase.table("processing_errors").insert(error_data).execute()
            logger.error(f"[TRACKED] {error_type}: {error_message}")
        except Exception as e:
            # If we can't even log the error, at least print it
            logger.critical(f"Failed to log error to database: {e}")
            logger.critical(f"Original error - {error_type}: {error_message}")

    def get_unresolved_errors(self) -> List[Dict]:
        """Get all unresolved processing errors"""
        try:
            result = self.supabase.table("processing_errors")\
                .select("*")\
                .eq("status", "new")\
                .order("created_at", desc=True)\
                .execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to fetch errors: {e}")
            return []

    # ============================================
    # CHUNK PERSISTENCE METHODS
    # ============================================

    def _save_chunk(
        self,
        transcript_id: str,
        chunk_index: int,
        chunk_text: str,
        char_start: int = None,
        char_end: int = None
    ) -> Optional[str]:
        """Save a chunk to the database and return its ID"""
        try:
            chunk_data = {
                "transcript_id": transcript_id,
                "chunk_index": chunk_index,
                "chunk_text": chunk_text,
                "char_start": char_start,
                "char_end": char_end,
                "status": "pending"
            }
            result = self.supabase.table("transcript_chunks").insert(chunk_data).execute()
            return result.data[0]["id"] if result.data else None
        except Exception as e:
            self._log_error(
                "chunk_save_failed",
                f"Failed to save chunk {chunk_index}: {e}",
                {"chunk_index": chunk_index, "transcript_id": transcript_id}
            )
            return None

    def _update_chunk_status(
        self,
        chunk_id: str,
        status: str,
        profiles_extracted: int = 0,
        error_message: str = None
    ) -> None:
        """Update chunk processing status"""
        try:
            update_data = {
                "status": status,
                "profiles_extracted": profiles_extracted,
                "processed_at": datetime.utcnow().isoformat()
            }
            if error_message:
                update_data["error_message"] = error_message
            if status == "failed":
                # Increment retry count
                self.supabase.table("transcript_chunks")\
                    .update({**update_data, "retry_count": self.supabase.rpc("increment_retry", {"chunk_id": chunk_id})})\
                    .eq("id", chunk_id)\
                    .execute()
            else:
                self.supabase.table("transcript_chunks")\
                    .update(update_data)\
                    .eq("id", chunk_id)\
                    .execute()
        except Exception as e:
            logger.error(f"Failed to update chunk status: {e}")

    # ============================================
    # PROFILE FIELD HISTORY METHODS
    # ============================================

    def _save_field_history(
        self,
        profile_id: str,
        field_name: str,
        field_value: str,
        event_date: date = None,
        event_name: str = None,
        transcript_id: str = None,
        chunk_id: str = None,
        timestamp_in_transcript: str = None,
        confidence: float = None
    ) -> None:
        """Save a profile field update to history for time-based matching"""
        try:
            history_data = {
                "profile_id": profile_id,
                "field_name": field_name,
                "field_value": field_value,
                "event_date": event_date.isoformat() if event_date else None,
                "event_name": event_name,
                "transcript_id": transcript_id,
                "chunk_id": chunk_id,
                "timestamp_in_transcript": timestamp_in_transcript,
                "confidence": confidence
            }
            self.supabase.table("profile_field_history").insert(history_data).execute()
            logger.debug(f"Saved field history: {field_name} for profile {profile_id}")
        except Exception as e:
            self._log_error(
                "field_history_save_failed",
                f"Failed to save field history: {e}",
                {"profile_id": profile_id, "field_name": field_name},
                profile_id=profile_id
            )

    def get_profile_field_history(self, profile_id: str, field_name: str = None) -> List[Dict]:
        """Get the history of a profile's field changes with dates"""
        try:
            query = self.supabase.table("profile_field_history")\
                .select("*")\
                .eq("profile_id", profile_id)

            if field_name:
                query = query.eq("field_name", field_name)

            result = query.order("event_date", desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to fetch field history: {e}")
            return []

    # ============================================
    # TRANSCRIPT PERSISTENCE METHODS
    # ============================================

    def save_transcript(
        self,
        filename: str,
        content: str,
        event_name: str = None,
        event_date = None
    ) -> Optional[str]:
        """
        Save a transcript to the database and return its ID.
        This must be called BEFORE processing to enable chunk tracking.
        """
        try:
            transcript_data = {
                "file_name": filename,
                "content": content,
                "event_name": event_name,
                "event_date": str(event_date) if event_date else None,
                "status": "processing"
            }
            result = self.supabase.table("conversation_transcripts").insert(transcript_data).execute()

            if result.data:
                transcript_id = result.data[0]["id"]
                logger.info(f"Saved transcript {filename} with ID: {transcript_id}")
                return transcript_id
            return None
        except Exception as e:
            self._log_error(
                "transcript_save",
                f"Failed to save transcript {filename}: {str(e)}",
                {"filename": filename, "error": str(e)}
            )
            return None

    def update_transcript_status(self, transcript_id: str, status: str, profiles_extracted: int = None) -> None:
        """Update the status of a transcript after processing"""
        try:
            update_data = {"status": status}
            if profiles_extracted is not None:
                update_data["profiles_extracted"] = profiles_extracted

            self.supabase.table("conversation_transcripts")\
                .update(update_data)\
                .eq("id", transcript_id)\
                .execute()
        except Exception as e:
            logger.error(f"Failed to update transcript status: {e}")

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
                response_format={"type": "json_object"}
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

    def extract_all_profiles_from_transcript(
        self,
        transcript_text: str,
        progress_callback: Optional[Callable] = None,
        transcript_id: str = None,
        event_date: date = None,
        event_name: str = None
    ) -> Dict[str, Any]:
        """
        Extract ALL profiles from a transcript (handles large multi-speaker transcripts)

        This method:
        1. Splits large transcripts into chunks
        2. SAVES each chunk to database for tracking
        3. Extracts profiles from each chunk IN PARALLEL
        4. TRACKS errors (no silent fails)
        5. Merges and deduplicates results
        6. Records timestamps for time-based matching

        Args:
            transcript_text: The raw transcript text (any size)
            progress_callback: Optional callback(current, total, message) for progress updates
            transcript_id: ID of the transcript in conversation_transcripts table
            event_date: Date of the networking event (for time-based matching)
            event_name: Name of the event (e.g., "JV Mastermind December 2025")

        Returns:
            Dict containing list of all extracted profiles
        """
        failed_chunks = []
        successful_chunks = []

        try:
            logger.info(f"Extracting all profiles from transcript ({len(transcript_text)} chars)")

            # Check if transcript is small enough to process directly
            if len(transcript_text) <= MAX_CHUNK_CHARS:
                # Small transcript - extract multiple profiles in one call
                if progress_callback:
                    progress_callback(1, 1, "Processing transcript...")

                # Save as single chunk if we have a transcript_id
                chunk_id = None
                if transcript_id:
                    chunk_id = self._save_chunk(transcript_id, 0, transcript_text, 0, len(transcript_text))

                result = self._extract_multiple_profiles(transcript_text)

                # Update chunk status
                if chunk_id:
                    if result.get("success"):
                        self._update_chunk_status(chunk_id, "success", len(result.get("profiles", [])))
                        successful_chunks.append({"chunk_id": chunk_id, "index": 0})
                    else:
                        self._update_chunk_status(chunk_id, "failed", 0, result.get("error"))
                        failed_chunks.append({"chunk_id": chunk_id, "index": 0, "error": result.get("error")})

                # Add event metadata to profiles
                if result.get("success") and result.get("profiles"):
                    for profile in result["profiles"]:
                        profile["_event_date"] = event_date
                        profile["_event_name"] = event_name
                        profile["_transcript_id"] = transcript_id
                        profile["_chunk_id"] = chunk_id

                return result

            # Large transcript - chunk and process in parallel
            chunks = self._chunk_transcript(transcript_text)
            total_chunks = len(chunks)
            logger.info(f"Split transcript into {total_chunks} chunks (processing {MAX_PARALLEL_CHUNKS} in parallel)")

            if progress_callback:
                progress_callback(0, total_chunks, f"Split into {total_chunks} chunks, processing {MAX_PARALLEL_CHUNKS} in parallel...")

            # Save all chunks to database BEFORE processing
            chunk_records = []
            char_position = 0
            for i, chunk in enumerate(chunks):
                chunk_id = None
                if transcript_id:
                    chunk_id = self._save_chunk(
                        transcript_id, i, chunk,
                        char_position, char_position + len(chunk)
                    )
                chunk_records.append({
                    "index": i,
                    "chunk_id": chunk_id,
                    "text": chunk
                })
                char_position += len(chunk)

            all_profiles = []
            completed = 0

            # Process chunks in parallel using ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=MAX_PARALLEL_CHUNKS) as executor:
                # Submit all chunks for processing
                future_to_chunk = {
                    executor.submit(self._extract_multiple_profiles, rec["text"]): rec
                    for rec in chunk_records
                }

                # Collect results as they complete
                for future in as_completed(future_to_chunk):
                    chunk_rec = future_to_chunk[future]
                    chunk_idx = chunk_rec["index"]
                    chunk_id = chunk_rec["chunk_id"]
                    completed += 1

                    try:
                        result = future.result()
                        if result.get("success") and result.get("profiles"):
                            # Add event metadata to each profile
                            for profile in result["profiles"]:
                                profile["_event_date"] = event_date
                                profile["_event_name"] = event_name
                                profile["_transcript_id"] = transcript_id
                                profile["_chunk_id"] = chunk_id

                            all_profiles.extend(result["profiles"])
                            logger.info(f"Chunk {chunk_idx+1}: Found {len(result['profiles'])} profiles")

                            # Update chunk status to success
                            if chunk_id:
                                self._update_chunk_status(chunk_id, "success", len(result["profiles"]))
                                successful_chunks.append({"chunk_id": chunk_id, "index": chunk_idx})
                        else:
                            # Chunk returned no profiles or failed
                            error_msg = result.get("error", "No profiles found")
                            if chunk_id:
                                self._update_chunk_status(chunk_id, "failed", 0, error_msg)
                            failed_chunks.append({"chunk_id": chunk_id, "index": chunk_idx, "error": error_msg})

                            # LOG THE ERROR - no silent fails!
                            self._log_error(
                                "chunk_extraction_failed",
                                f"Chunk {chunk_idx+1} failed: {error_msg}",
                                {"chunk_index": chunk_idx, "profiles_found": 0},
                                transcript_id=transcript_id,
                                chunk_id=chunk_id
                            )

                        if progress_callback:
                            progress_callback(completed, total_chunks,
                                f"Completed {completed}/{total_chunks} chunks (Found {len(all_profiles)} profiles)")

                    except Exception as e:
                        # TRACK THE ERROR - no silent fails!
                        error_msg = str(e)
                        logger.error(f"Chunk {chunk_idx+1} failed: {error_msg}")

                        if chunk_id:
                            self._update_chunk_status(chunk_id, "failed", 0, error_msg)

                        failed_chunks.append({"chunk_id": chunk_id, "index": chunk_idx, "error": error_msg})

                        self._log_error(
                            "chunk_extraction_exception",
                            f"Chunk {chunk_idx+1} threw exception: {error_msg}",
                            {"chunk_index": chunk_idx, "exception_type": type(e).__name__},
                            transcript_id=transcript_id,
                            chunk_id=chunk_id
                        )

            # Deduplicate profiles by name similarity
            if progress_callback:
                progress_callback(total_chunks, total_chunks, f"Deduplicating {len(all_profiles)} profiles...")

            unique_profiles = self._deduplicate_profiles(all_profiles)
            logger.info(f"Extracted {len(unique_profiles)} unique profiles from {len(all_profiles)} total")

            # Report on failed chunks
            if failed_chunks:
                logger.warning(f"WARNING: {len(failed_chunks)} chunks failed processing. Check processing_errors table.")

            return {
                "success": True,
                "profiles": unique_profiles,
                "total_extracted": len(all_profiles),
                "unique_count": len(unique_profiles),
                "chunks_processed": total_chunks,
                "chunks_successful": len(successful_chunks),
                "chunks_failed": len(failed_chunks),
                "failed_chunk_details": failed_chunks if failed_chunks else None
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error extracting all profiles: {error_msg}")

            # LOG THE ERROR
            self._log_error(
                "extraction_pipeline_failed",
                f"Full extraction pipeline failed: {error_msg}",
                {"transcript_length": len(transcript_text)},
                transcript_id=transcript_id
            )

            return {
                "success": False,
                "error": error_msg,
                "profiles": [],
                "failed_chunk_details": failed_chunks if failed_chunks else None
            }

    def _chunk_transcript(self, text: str) -> List[str]:
        """
        Split a large transcript into processable chunks

        Tries to split on speaker boundaries to maintain context

        Args:
            text: Full transcript text

        Returns:
            List of transcript chunks
        """
        # Pattern to match speaker lines like "[Name] 10:35:12" or "Name:"
        speaker_pattern = r'(?=\[[^\]]+\]\s*\d{1,2}:\d{2}:\d{2}|\n[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:)'

        # Split on speaker boundaries
        segments = re.split(speaker_pattern, text)

        chunks = []
        current_chunk = ""

        for segment in segments:
            # If adding this segment would exceed limit, save current chunk
            if len(current_chunk) + len(segment) > MAX_CHUNK_CHARS and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = segment
            else:
                current_chunk += segment

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        # If we couldn't split by speakers, fall back to simple character splits
        if len(chunks) <= 1 and len(text) > MAX_CHUNK_CHARS:
            chunks = []
            for i in range(0, len(text), MAX_CHUNK_CHARS):
                chunk = text[i:i + MAX_CHUNK_CHARS]
                # Try to end at a sentence or line break
                last_break = max(chunk.rfind('\n'), chunk.rfind('. '), chunk.rfind('? '), chunk.rfind('! '))
                if last_break > MAX_CHUNK_CHARS * 0.7:  # Only if we find a break in last 30%
                    chunk = chunk[:last_break + 1]
                chunks.append(chunk)

        return chunks

    def _extract_multiple_profiles(self, text: str) -> Dict[str, Any]:
        """
        Extract multiple profiles from a single chunk of text

        Args:
            text: Transcript text chunk

        Returns:
            Dict with list of extracted profiles
        """
        try:
            prompt = """
            Extract ALL speaker profiles from this networking transcript.
            This is a multi-person conversation - identify EVERY person who speaks and their business information.

            Return a JSON object with:
            {
                "profiles": [
                    {
                        "name": "Person's full name (extract from speaker labels like [Name] or 'Name:')",
                        "email": "Email if mentioned, null otherwise",
                        "company": "Company or brand name if mentioned",
                        "what_you_do": "What they do/offer (2-3 sentences based on what they said)",
                        "who_you_serve": "Target audience mentioned",
                        "seeking": "What they're looking for in partnerships",
                        "offering": "What they can offer to partners",
                        "current_projects": "Active projects mentioned",
                        "contact": "Contact info if shared (website, social, etc)",
                        "business_focus": "Primary business category",
                        "list_size": 0,
                        "social_reach": 0
                    }
                ]
            }

            IMPORTANT:
            - Extract EVERY unique speaker, not just the main one
            - Look for speaker labels like "[Name - Company]" or "Name:"
            - Include people even if they only say a few things
            - Use null for fields not mentioned
            - For list_size/social_reach, extract numbers if mentioned (e.g., "30,000 VIPs" = 30000)

            Transcript:
            """

            response = self.client.chat.completions.create(
                model="gpt-5-nano",
                messages=[
                    {"role": "system", "content": "You are an expert at identifying all speakers in networking conversations and extracting their business profile data."},
                    {"role": "user", "content": f"{prompt}\n\n{text}"}
                ],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            profiles = result.get("profiles", [])

            # Add confidence scores to each profile
            for profile in profiles:
                profile["confidence"] = self._calculate_extraction_confidence(profile)

            # Filter out invalid profiles (no name or generic names)
            valid_profiles = [
                p for p in profiles
                if p.get("name") and p["name"].lower() not in [
                    "unknown", "participant", "speaker", "mobile", "email", "introducing", "none"
                ]
            ]

            logger.info(f"Extracted {len(valid_profiles)} valid profiles from chunk")

            return {
                "success": True,
                "profiles": valid_profiles
            }

        except Exception as e:
            logger.error(f"Error extracting multiple profiles: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "profiles": []
            }

    def _deduplicate_profiles(self, profiles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate profiles based on name similarity
        Merges data from duplicates into the most complete profile

        Args:
            profiles: List of extracted profiles (may contain duplicates)

        Returns:
            List of unique profiles with merged data
        """
        if not profiles:
            return []

        unique = []

        for profile in profiles:
            name = (profile.get("name") or "").strip()
            if not name:
                continue

            # Check if this profile matches any existing unique profile
            found_match = False
            for existing in unique:
                existing_name = (existing.get("name") or "").strip()
                similarity = self._fuzzy_match(
                    self._normalize_name(name),
                    self._normalize_name(existing_name)
                )

                if similarity >= 0.85:  # 85% name similarity = same person
                    # Merge data into existing profile (prefer non-null values)
                    self._merge_profile_data(existing, profile)
                    found_match = True
                    break

            if not found_match:
                unique.append(profile.copy())

        # Sort by confidence
        unique.sort(key=lambda p: p.get("confidence", 0), reverse=True)

        return unique

    def _merge_profile_data(self, target: Dict, source: Dict):
        """
        Merge data from source profile into target profile
        Prefers existing non-null values but fills in gaps
        Also preserves event metadata for time-based matching

        Args:
            target: Profile to merge into (modified in place)
            source: Profile to merge from
        """
        mergeable_fields = [
            "email", "company", "what_you_do", "who_you_serve",
            "seeking", "offering", "current_projects", "contact", "business_focus"
        ]

        for field in mergeable_fields:
            # If target doesn't have this field, use source's value
            if not target.get(field) and source.get(field):
                target[field] = source[field]
            # If both have values, concatenate if they're different
            elif target.get(field) and source.get(field):
                if field in ["what_you_do", "seeking", "offering"] and \
                   target[field] != source[field] and \
                   source[field] not in target[field]:
                    target[field] = f"{target[field]} {source[field]}"

        # For numeric fields, take the maximum
        for field in ["list_size", "social_reach"]:
            target[field] = max(target.get(field, 0) or 0, source.get(field, 0) or 0)

        # Update confidence to max
        target["confidence"] = max(target.get("confidence", 0), source.get("confidence", 0))

        # Preserve event metadata - collect all events this profile appeared in
        if "_events" not in target:
            target["_events"] = []

        # Add target's original event if it has one
        if target.get("_event_date") or target.get("_event_name"):
            existing_event = {
                "event_date": target.get("_event_date"),
                "event_name": target.get("_event_name"),
                "transcript_id": target.get("_transcript_id"),
                "chunk_id": target.get("_chunk_id")
            }
            if existing_event not in target["_events"]:
                target["_events"].append(existing_event)

        # Add source's event
        if source.get("_event_date") or source.get("_event_name"):
            source_event = {
                "event_date": source.get("_event_date"),
                "event_name": source.get("_event_name"),
                "transcript_id": source.get("_transcript_id"),
                "chunk_id": source.get("_chunk_id")
            }
            if source_event not in target["_events"]:
                target["_events"].append(source_event)

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
            name = (extracted_data.get("name") or "").strip()
            email = (extracted_data.get("email") or "").strip()
            company = (extracted_data.get("company") or "").strip()

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
                        if (profile.get("email") or "").lower() == email.lower():
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
                    profile_name = (profile.get("name") or "").strip().lower()
                    profile_company = (profile.get("company") or "").strip().lower()

                    if (self._normalize_name(profile_name) == self._normalize_name((name or "").lower()) and
                        profile_company and (company or "").lower() in profile_company):
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
                profile_name = (profile.get("name") or "").strip().lower()
                if self._normalize_name(profile_name) == self._normalize_name((name or "").lower()):
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
                profile_name = (profile.get("name") or "").strip().lower()
                similarity = self._fuzzy_match(self._normalize_name((name or "").lower()), self._normalize_name(profile_name))

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
        if not name:
            return ""
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

