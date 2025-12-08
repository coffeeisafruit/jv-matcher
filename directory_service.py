"""
Directory service for JV Directory
Handles all profile/directory database operations
Schema v2: contacts = profiles (unified)
"""
import pandas as pd
from typing import List, Dict, Any, Optional, Set
from supabase_client import get_client, get_admin_client

class DirectoryService:
    def __init__(self, use_admin: bool = False):
        self.client = get_admin_client() if use_admin else get_client()

    # ==========================================
    # PROFILE CRUD OPERATIONS
    # ==========================================

    def get_profiles(
        self,
        search: str = "",
        status: str = "",
        business_focus: str = "",
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get profiles with optional filtering"""
        try:
            query = self.client.table("profiles").select("*", count="exact")

            # Apply filters
            if search:
                query = query.or_(
                    f"name.ilike.%{search}%,"
                    f"company.ilike.%{search}%,"
                    f"business_focus.ilike.%{search}%,"
                    f"service_provided.ilike.%{search}%"
                )
            if status:
                query = query.eq("status", status)
            if business_focus:
                query = query.ilike("business_focus", f"%{business_focus}%")

            # Pagination and ordering
            query = query.order("name").range(offset, offset + limit - 1)

            response = query.execute()
            return {
                "success": True,
                "data": response.data,
                "count": response.count
            }
        except Exception as e:
            return {"success": False, "error": str(e), "data": [], "count": 0}

    # Alias for backward compatibility
    def get_contacts(self, **kwargs):
        return self.get_profiles(**kwargs)

    def get_profile_by_id(self, profile_id: str) -> Dict[str, Any]:
        """Get a single profile by ID"""
        try:
            response = self.client.table("profiles").select("*").eq("id", profile_id).single().execute()
            return {"success": True, "data": response.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new profile"""
        try:
            response = self.client.table("profiles").insert(data).execute()
            return {"success": True, "data": response.data[0] if response.data else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_profile(self, profile_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing profile"""
        try:
            response = self.client.table("profiles").update(data).eq("id", profile_id).execute()
            return {"success": True, "data": response.data[0] if response.data else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_profile(self, profile_id: str) -> Dict[str, Any]:
        """Delete a profile"""
        try:
            self.client.table("profiles").delete().eq("id", profile_id).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==========================================
    # BULK OPERATIONS
    # ==========================================

    def import_from_csv(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Import profiles from a pandas DataFrame"""
        try:
            records_imported = 0
            records_skipped = 0
            errors = []

            column_mapping = {
                "Name": "name",
                "Company": "company",
                "Business Focus": "business_focus",
                "Status": "status",
                "Service Provided": "service_provided",
                "List Size": "list_size",
                "Business Size": "business_size",
                "Social Reach": "social_reach"
            }

            for idx, row in df.iterrows():
                try:
                    profile_data = {}

                    for csv_col, db_col in column_mapping.items():
                        if csv_col in row and pd.notna(row[csv_col]):
                            value = row[csv_col]

                            if db_col in ["list_size", "social_reach"]:
                                if isinstance(value, str):
                                    value = value.replace(",", "")
                                try:
                                    value = int(float(value)) if value else 0
                                except (ValueError, TypeError):
                                    value = 0

                            profile_data[db_col] = value

                    if not profile_data.get("name"):
                        records_skipped += 1
                        continue

                    self.client.table("profiles").insert(profile_data).execute()
                    records_imported += 1

                except Exception as e:
                    records_skipped += 1
                    errors.append(f"Row {idx}: {str(e)}")

            return {
                "success": True,
                "records_imported": records_imported,
                "records_skipped": records_skipped,
                "errors": errors[:10]
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_to_dataframe(self) -> pd.DataFrame:
        """Export all profiles to a pandas DataFrame"""
        try:
            response = self.client.table("profiles").select("*").order("name").execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            return pd.DataFrame()

    # ==========================================
    # CONNECTIONS (formerly favorites)
    # ==========================================

    def get_connections(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get profiles this user is following/connected to"""
        try:
            response = self.client.table("connections") \
                .select("*, following:following_id(*)") \
                .eq("follower_id", profile_id) \
                .execute()
            return response.data
        except Exception:
            return []

    def add_connection(self, follower_id: str, following_id: str, notes: str = "") -> Dict[str, Any]:
        """Add a connection (follow/save a profile)"""
        try:
            self.client.table("connections").insert({
                "follower_id": follower_id,
                "following_id": following_id,
                "notes": notes
            }).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def remove_connection(self, follower_id: str, following_id: str) -> Dict[str, Any]:
        """Remove a connection"""
        try:
            self.client.table("connections") \
                .delete() \
                .eq("follower_id", follower_id) \
                .eq("following_id", following_id) \
                .execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_connected(self, follower_id: str, following_id: str) -> bool:
        """Check if user is connected to a profile"""
        try:
            response = self.client.table("connections") \
                .select("*") \
                .eq("follower_id", follower_id) \
                .eq("following_id", following_id) \
                .execute()
            return len(response.data) > 0
        except Exception:
            return False

    # ==========================================
    # INTERACTIONS
    # ==========================================

    def add_interaction(
        self,
        from_profile_id: str,
        to_profile_id: str,
        interaction_type: str,
        description: str
    ) -> Dict[str, Any]:
        """Log an interaction between profiles"""
        try:
            self.client.table("interactions").insert({
                "from_profile_id": from_profile_id,
                "to_profile_id": to_profile_id,
                "interaction_type": interaction_type,
                "description": description
            }).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_interactions(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get all interactions for a profile"""
        try:
            response = self.client.table("interactions") \
                .select("*, to_profile:to_profile_id(name, company)") \
                .eq("from_profile_id", profile_id) \
                .order("interaction_date", desc=True) \
                .execute()
            return response.data
        except Exception:
            return []

    # ==========================================
    # MATCH SUGGESTIONS
    # ==========================================

    def get_match_suggestions(self, profile_id: str, status: str = None) -> List[Dict[str, Any]]:
        """Get match suggestions for a profile"""
        try:
            query = self.client.table("match_suggestions") \
                .select("*, suggested:suggested_profile_id(*)") \
                .eq("profile_id", profile_id)

            if status:
                query = query.eq("status", status)

            response = query.order("match_score", desc=True).execute()
            return response.data
        except Exception:
            return []

    def create_match_suggestion(
        self,
        profile_id: str,
        suggested_profile_id: str,
        match_score: float,
        match_reason: str,
        source: str = "ai_matcher"
    ) -> Dict[str, Any]:
        """Create a new match suggestion"""
        try:
            self.client.table("match_suggestions").insert({
                "profile_id": profile_id,
                "suggested_profile_id": suggested_profile_id,
                "match_score": match_score,
                "match_reason": match_reason,
                "source": source
            }).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_match_status(self, match_id: str, status: str) -> Dict[str, Any]:
        """Update match suggestion status"""
        try:
            update_data = {"status": status}
            if status == "viewed":
                update_data["viewed_at"] = "now()"
            elif status == "contacted":
                update_data["contacted_at"] = "now()"

            self.client.table("match_suggestions").update(update_data).eq("id", match_id).execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_dismissed_profile_ids(self, profile_id: str) -> Set[str]:
        """Get IDs of profiles this user has dismissed"""
        try:
            response = self.client.table("match_suggestions") \
                .select("suggested_profile_id") \
                .eq("profile_id", profile_id) \
                .eq("status", "dismissed") \
                .execute()
            return {r['suggested_profile_id'] for r in response.data}
        except Exception:
            return set()

    def dismiss_match(self, profile_id: str, suggested_profile_id: str) -> Dict[str, Any]:
        """Mark a match as dismissed (won't appear again)"""
        try:
            # Check if match suggestion exists
            existing = self.client.table("match_suggestions") \
                .select("id") \
                .eq("profile_id", profile_id) \
                .eq("suggested_profile_id", suggested_profile_id) \
                .execute()

            if existing.data:
                # Update existing record to dismissed
                self.client.table("match_suggestions") \
                    .update({"status": "dismissed"}) \
                    .eq("id", existing.data[0]["id"]) \
                    .execute()
            else:
                # Create new dismissed record
                self.client.table("match_suggestions").insert({
                    "profile_id": profile_id,
                    "suggested_profile_id": suggested_profile_id,
                    "status": "dismissed",
                    "match_score": 0,
                    "match_reason": "Dismissed by user",
                    "source": "user_action"
                }).execute()

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_profile_preferences(
        self,
        profile_id: str,
        categories_interested: List[str],
        partnership_types: List[str]
    ) -> Dict[str, Any]:
        """Save user preferences for matching - stores in profile notes as JSON"""
        import json
        try:
            # Store preferences as JSON in the notes field
            preferences_json = json.dumps({
                "categories_interested": categories_interested,
                "partnership_types": partnership_types
            })

            self.client.table("profiles") \
                .update({"notes": preferences_json}) \
                .eq("id", profile_id) \
                .execute()

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_profile_preferences(self, profile_id: str) -> Dict[str, Any]:
        """Get user's saved preferences from profile notes"""
        import json
        try:
            response = self.client.table("profiles") \
                .select("notes") \
                .eq("id", profile_id) \
                .single() \
                .execute()

            if response.data and response.data.get("notes"):
                try:
                    prefs = json.loads(response.data["notes"])
                    return {"success": True, "data": prefs}
                except json.JSONDecodeError:
                    pass

            # Return default preferences if none exist
            return {
                "success": True,
                "data": {
                    "categories_interested": [],
                    "partnership_types": []
                }
            }
        except Exception:
            return {
                "success": True,
                "data": {
                    "categories_interested": [],
                    "partnership_types": []
                }
            }

    # ==========================================
    # STATISTICS
    # ==========================================

    def get_stats(self) -> Dict[str, Any]:
        """Get directory statistics"""
        try:
            # Total profiles
            total_response = self.client.table("profiles").select("*", count="exact").execute()
            total = total_response.count or 0

            # Registered users (have auth_user_id)
            registered_response = self.client.table("profiles") \
                .select("*", count="exact") \
                .not_.is_("auth_user_id", "null") \
                .execute()
            registered = registered_response.count or 0

            # Count by status
            members_response = self.client.table("profiles") \
                .select("*", count="exact") \
                .eq("status", "Member") \
                .execute()
            members = members_response.count or 0

            non_members_response = self.client.table("profiles") \
                .select("*", count="exact") \
                .eq("status", "Non Member Resource") \
                .execute()
            non_members = non_members_response.count or 0

            return {
                "total_profiles": total,
                "registered_users": registered,
                "members": members,
                "non_members": non_members
            }
        except Exception:
            return {"total_profiles": 0, "registered_users": 0, "members": 0, "non_members": 0}

    def get_profile_by_auth_user(self, auth_user_id: str) -> Optional[Dict[str, Any]]:
        """Get profile by auth user ID"""
        try:
            response = self.client.table("profiles") \
                .select("*") \
                .eq("auth_user_id", auth_user_id) \
                .single() \
                .execute()
            return response.data
        except Exception:
            return None

    # ==========================================
    # EMBEDDING OPERATIONS
    # ==========================================

    def update_profile_embedding(self, profile_id: str, embedding: List[float]) -> Dict[str, Any]:
        """Store embedding vector for a profile"""
        try:
            import json
            self.client.table("profiles") \
                .update({"embedding": json.dumps(embedding)}) \
                .eq("id", profile_id) \
                .execute()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_profiles_with_embeddings(self, limit: int = 10000) -> List[Dict[str, Any]]:
        """Get all profiles that have embeddings stored"""
        try:
            response = self.client.table("profiles") \
                .select("*") \
                .not_.is_("embedding", "null") \
                .order("name") \
                .limit(limit) \
                .execute()
            return response.data
        except Exception:
            return []

    def get_profiles_without_embeddings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get profiles that need embeddings generated"""
        try:
            response = self.client.table("profiles") \
                .select("*") \
                .is_("embedding", "null") \
                .order("name") \
                .limit(limit) \
                .execute()
            return response.data
        except Exception:
            return []

    def get_all_profiles_for_matching(self, limit: int = 10000) -> List[Dict[str, Any]]:
        """Get all profiles with their embeddings for matching"""
        try:
            response = self.client.table("profiles") \
                .select("*") \
                .order("name") \
                .limit(limit) \
                .execute()

            # Parse embeddings from JSON
            import json
            for profile in response.data:
                if profile.get("embedding"):
                    try:
                        profile["embedding_vector"] = json.loads(profile["embedding"])
                    except (json.JSONDecodeError, TypeError):
                        profile["embedding_vector"] = None
                else:
                    profile["embedding_vector"] = None

            return response.data
        except Exception:
            return []

    # ==========================================
    # RICH JV MATCHING SYSTEM
    # ==========================================

    def update_match_rich_analysis(self, match_id: str, rich_analysis: dict) -> Dict[str, Any]:
        """Updates match_suggestions table with rich_analysis JSON and analysis_generated_at timestamp"""
        try:
            import json
            from datetime import datetime

            update_data = {
                "rich_analysis": json.dumps(rich_analysis),
                "analysis_generated_at": datetime.utcnow().isoformat()
            }

            response = self.client.table("match_suggestions") \
                .update(update_data) \
                .eq("id", match_id) \
                .execute()

            return {"success": True, "data": response.data[0] if response.data else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_matches_with_rich_analysis(self, profile_id: str, status: str = None) -> List[Dict[str, Any]]:
        """Gets matches including the rich_analysis field (parsed from JSON), joined with suggested profile data"""
        try:
            import json

            query = self.client.table("match_suggestions") \
                .select("*, suggested:suggested_profile_id(*)") \
                .eq("profile_id", profile_id)

            if status:
                query = query.eq("status", status)

            response = query.order("match_score", desc=True).execute()

            # Parse rich_analysis from JSON
            for match in response.data:
                if match.get("rich_analysis"):
                    try:
                        match["rich_analysis_parsed"] = json.loads(match["rich_analysis"])
                    except (json.JSONDecodeError, TypeError):
                        match["rich_analysis_parsed"] = None
                else:
                    match["rich_analysis_parsed"] = None

            return response.data
        except Exception as e:
            return []

    def track_email_sent(self, match_id: str) -> Dict[str, Any]:
        """Updates email_sent_at timestamp on match_suggestions and logs to analytics_events"""
        try:
            from datetime import datetime

            # Update match_suggestions table
            update_data = {"email_sent_at": datetime.utcnow().isoformat()}

            self.client.table("match_suggestions") \
                .update(update_data) \
                .eq("id", match_id) \
                .execute()

            # Log to analytics_events
            self.client.table("analytics_events").insert({
                "match_id": match_id,
                "event_type": "email_click",
                "event_timestamp": datetime.utcnow().isoformat()
            }).execute()

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def record_feedback(self, match_id: str, feedback: str) -> Dict[str, Any]:
        """Updates user_feedback and feedback_at on match_suggestions, logs to analytics_events"""
        try:
            from datetime import datetime

            if feedback not in ['positive', 'negative']:
                return {"success": False, "error": "Feedback must be 'positive' or 'negative'"}

            # Update match_suggestions table
            update_data = {
                "user_feedback": feedback,
                "feedback_at": datetime.utcnow().isoformat()
            }

            self.client.table("match_suggestions") \
                .update(update_data) \
                .eq("id", match_id) \
                .execute()

            # Log to analytics_events
            self.client.table("analytics_events").insert({
                "match_id": match_id,
                "event_type": f"feedback_{feedback}",
                "event_timestamp": datetime.utcnow().isoformat()
            }).execute()

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_analytics_summary(self) -> Dict[str, Any]:
        """Returns summary stats: total_matches, emails_sent, contacted_count, connected_count, positive/negative feedback"""
        try:
            # Total matches
            total_matches_response = self.client.table("match_suggestions") \
                .select("*", count="exact") \
                .execute()
            total_matches = total_matches_response.count or 0

            # Emails sent
            emails_sent_response = self.client.table("match_suggestions") \
                .select("*", count="exact") \
                .not_.is_("email_sent_at", "null") \
                .execute()
            emails_sent = emails_sent_response.count or 0

            # Contacted count
            contacted_response = self.client.table("match_suggestions") \
                .select("*", count="exact") \
                .eq("status", "contacted") \
                .execute()
            contacted_count = contacted_response.count or 0

            # Connected count
            connected_response = self.client.table("match_suggestions") \
                .select("*", count="exact") \
                .eq("status", "connected") \
                .execute()
            connected_count = connected_response.count or 0

            # Positive feedback
            positive_feedback_response = self.client.table("match_suggestions") \
                .select("*", count="exact") \
                .eq("user_feedback", "positive") \
                .execute()
            positive_feedback = positive_feedback_response.count or 0

            # Negative feedback
            negative_feedback_response = self.client.table("match_suggestions") \
                .select("*", count="exact") \
                .eq("user_feedback", "negative") \
                .execute()
            negative_feedback = negative_feedback_response.count or 0

            return {
                "success": True,
                "data": {
                    "total_matches": total_matches,
                    "emails_sent": emails_sent,
                    "contacted_count": contacted_count,
                    "connected_count": connected_count,
                    "positive_feedback": positive_feedback,
                    "negative_feedback": negative_feedback
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def regenerate_match_analysis(self, match_id: str) -> Dict[str, Any]:
        """Regenerate rich analysis for a specific match using RichMatchService"""
        try:
            # Get the match with both profiles
            response = self.client.table("match_suggestions") \
                .select("*, profile:profile_id(*), suggested:suggested_profile_id(*)") \
                .eq("id", match_id) \
                .single() \
                .execute()

            match = response.data
            if not match:
                return {"success": False, "error": "Match not found"}

            user_profile = match.get('profile', {})
            match_profile = match.get('suggested', {})

            if not user_profile or not match_profile:
                return {"success": False, "error": "Could not load profiles for match"}

            # Import and use RichMatchService
            try:
                from rich_match_service import RichMatchService
                import os

                rich_service = RichMatchService(os.getenv('OPENAI_API_KEY'))
                result = rich_service.generate_rich_analysis(user_profile, match_profile)

                if result.get('success') and result.get('analysis'):
                    # Store the analysis
                    update_result = self.update_match_rich_analysis(match_id, result['analysis'])
                    return update_result
                else:
                    return {"success": False, "error": result.get('error', 'Failed to generate analysis')}

            except ImportError:
                return {"success": False, "error": "RichMatchService not available"}
            except Exception as e:
                return {"success": False, "error": f"Analysis generation failed: {str(e)}"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==========================================
    # PROFILE REVIEW QUEUE
    # ==========================================

    def add_to_review_queue(
        self,
        extracted_name: str,
        extracted_data: dict,
        candidate_profile_id: str,
        confidence_score: float,
        source_transcript: str
    ) -> Dict[str, Any]:
        """Inserts into profile_review_queue table"""
        try:
            import json

            insert_data = {
                "extracted_name": extracted_name,
                "extracted_data": json.dumps(extracted_data),
                "candidate_profile_id": candidate_profile_id,
                "confidence_score": confidence_score,
                "source_transcript": source_transcript,
                "status": "pending"
            }

            response = self.client.table("profile_review_queue").insert(insert_data).execute()
            return {"success": True, "data": response.data[0] if response.data else None}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Gets all pending profile reviews with candidate profile data"""
        try:
            import json

            response = self.client.table("profile_review_queue") \
                .select("*, candidate:candidate_profile_id(*)") \
                .eq("status", "pending") \
                .order("created_at", desc=True) \
                .execute()

            # Parse extracted_data from JSON
            for review in response.data:
                if review.get("extracted_data"):
                    try:
                        review["extracted_data_parsed"] = json.loads(review["extracted_data"])
                    except (json.JSONDecodeError, TypeError):
                        review["extracted_data_parsed"] = None
                else:
                    review["extracted_data_parsed"] = None

            return response.data
        except Exception as e:
            return []

    def resolve_review(self, review_id: str, action: str, reviewed_by: str) -> Dict[str, Any]:
        """Updates review status to 'approved', 'rejected', or 'merged'"""
        try:
            import json
            from datetime import datetime

            if action not in ['approved', 'rejected', 'merged']:
                return {"success": False, "error": "Action must be 'approved', 'rejected', or 'merged'"}

            # Get review details
            review_response = self.client.table("profile_review_queue") \
                .select("*") \
                .eq("id", review_id) \
                .single() \
                .execute()

            review = review_response.data

            # Update review status
            update_data = {
                "status": action,
                "reviewed_by": reviewed_by,
                "reviewed_at": datetime.utcnow().isoformat()
            }

            self.client.table("profile_review_queue") \
                .update(update_data) \
                .eq("id", review_id) \
                .execute()

            # Handle different actions
            if action == "approved":
                # Parse extracted data
                extracted_data = json.loads(review["extracted_data"]) if review.get("extracted_data") else {}

                if review.get("candidate_profile_id"):
                    # Update existing profile
                    self.update_profile(review["candidate_profile_id"], extracted_data)
                else:
                    # Create new profile
                    extracted_data["name"] = review["extracted_name"]
                    self.create_profile(extracted_data)

            elif action == "merged" and review.get("candidate_profile_id"):
                # Merge data into existing profile
                extracted_data = json.loads(review["extracted_data"]) if review.get("extracted_data") else {}
                self.update_profile(review["candidate_profile_id"], extracted_data)

            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==========================================
    # PROFILE SEARCH & FUZZY MATCHING
    # ==========================================

    def find_profile_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Exact email match lookup"""
        try:
            response = self.client.table("profiles") \
                .select("*") \
                .eq("email", email) \
                .single() \
                .execute()
            return response.data
        except Exception:
            return None

    def search_profiles_fuzzy(self, name: str, company: str = None) -> List[Dict[str, Any]]:
        """Returns profiles with similarity scores for fuzzy matching"""
        try:
            # Use PostgreSQL similarity search (pg_trgm extension)
            # This requires the pg_trgm extension to be enabled in Supabase
            query = self.client.table("profiles").select("*")

            # Search by name with ilike for fuzzy matching
            query = query.ilike("name", f"%{name}%")

            # Optionally filter by company
            if company:
                query = query.ilike("company", f"%{company}%")

            response = query.order("name").limit(10).execute()

            # Add simple similarity scores based on string matching
            results = []
            for profile in response.data:
                # Calculate a simple similarity score (0-100)
                name_lower = name.lower()
                profile_name_lower = profile.get("name", "").lower()

                # Simple scoring: exact match = 100, contains = 50, partial = 25
                if profile_name_lower == name_lower:
                    similarity = 100
                elif name_lower in profile_name_lower:
                    similarity = 75
                elif any(word in profile_name_lower for word in name_lower.split()):
                    similarity = 50
                else:
                    similarity = 25

                # Boost score if company matches
                if company and profile.get("company"):
                    company_lower = company.lower()
                    profile_company_lower = profile.get("company", "").lower()
                    if company_lower in profile_company_lower or profile_company_lower in company_lower:
                        similarity = min(100, similarity + 20)

                profile["similarity_score"] = similarity
                results.append(profile)

            # Sort by similarity score
            results.sort(key=lambda x: x["similarity_score"], reverse=True)

            return results
        except Exception as e:
            return []
