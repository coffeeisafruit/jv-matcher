"""
Authentication service for JV Directory
Handles user signup, login, logout, and session management
"""
import streamlit as st
from supabase_client import get_client
from typing import Optional, Dict, Any

class AuthService:
    def __init__(self):
        self.client = get_client()

    def sign_up(self, email: str, password: str, full_name: str = "") -> Dict[str, Any]:
        """Register a new user"""
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name
                    }
                }
            })
            return {"success": True, "user": response.user, "session": response.session}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in existing user"""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {"success": True, "user": response.user, "session": response.session}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sign_out(self) -> Dict[str, Any]:
        """Sign out current user"""
        try:
            self.client.auth.sign_out()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_session(self) -> Optional[Dict[str, Any]]:
        """Get current session"""
        try:
            session = self.client.auth.get_session()
            return session
        except Exception:
            return None

    def get_user(self) -> Optional[Dict[str, Any]]:
        """Get current user"""
        try:
            user = self.client.auth.get_user()
            return user.user if user else None
        except Exception:
            return None

    def reset_password(self, email: str) -> Dict[str, Any]:
        """Send password reset email"""
        try:
            self.client.auth.reset_password_email(email)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_password(self, new_password: str) -> Dict[str, Any]:
        """Update user password"""
        try:
            self.client.auth.update_user({"password": new_password})
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile from database"""
        try:
            response = self.client.table("profiles").select("*").eq("id", user_id).single().execute()
            return response.data
        except Exception:
            return None

    def update_user_profile(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile"""
        try:
            response = self.client.table("profiles").update(data).eq("id", user_id).execute()
            return {"success": True, "data": response.data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def is_admin(self, user_id: str) -> bool:
        """Check if user is admin"""
        profile = self.get_user_profile(user_id)
        return profile and profile.get("role") == "admin"


def init_session_state():
    """Initialize authentication session state"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = None


def require_auth(func):
    """Decorator to require authentication for a page"""
    def wrapper(*args, **kwargs):
        init_session_state()
        if not st.session_state.authenticated:
            st.warning("Please log in to access this page.")
            return
        return func(*args, **kwargs)
    return wrapper


def require_admin(func):
    """Decorator to require admin role"""
    def wrapper(*args, **kwargs):
        init_session_state()
        if not st.session_state.authenticated:
            st.warning("Please log in to access this page.")
            return
        if not st.session_state.user_profile or st.session_state.user_profile.get("role") != "admin":
            st.error("Admin access required.")
            return
        return func(*args, **kwargs)
    return wrapper
