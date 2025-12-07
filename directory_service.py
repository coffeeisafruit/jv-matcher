"""
Directory service for JV Directory
Handles all profile/directory database operations
Schema v2: contacts = profiles (unified)
"""
import pandas as pd
from typing import List, Dict, Any, Optional
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
