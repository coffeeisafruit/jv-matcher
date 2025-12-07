"""
Supabase client configuration for JV Directory
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

def get_supabase_client() -> Client:
    """Get Supabase client with anon key (for client-side operations)"""
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Missing Supabase configuration. Check your .env file.")
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def get_supabase_admin_client() -> Client:
    """Get Supabase client with service key (for admin operations)"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing Supabase admin configuration. Check your .env file.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Singleton client instance
_client: Client = None
_admin_client: Client = None

def get_client() -> Client:
    """Get or create singleton Supabase client"""
    global _client
    if _client is None:
        _client = get_supabase_client()
    return _client

def get_admin_client() -> Client:
    """Get or create singleton Supabase admin client"""
    global _admin_client
    if _admin_client is None:
        _admin_client = get_supabase_admin_client()
    return _admin_client
