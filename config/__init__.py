"""Config loader for V1.5 tactical settings"""
import json
import os
from functools import lru_cache
from typing import Dict, Any, List, Optional

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'tactics.json')


@lru_cache(maxsize=1)
def load_tactics_config() -> Dict[str, Any]:
    """Load and cache tactics config from JSON file"""
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def get_anti_personas() -> List[Dict[str, str]]:
    """Get anti-persona options for intake form"""
    return load_tactics_config()['intake_questions']['anti_personas']


def get_confidence_tiers() -> Dict[str, Dict[str, Any]]:
    """Get confidence tier thresholds and display info"""
    return load_tactics_config()['confidence_tiers']


def get_intro_template(match_preference: str) -> Dict[str, str]:
    """
    Get intro template for a match preference type.

    Args:
        match_preference: One of 'Peer_Bundle', 'Referral_Upstream',
                         'Referral_Downstream', 'Service_Provider'

    Returns:
        Dict with 'subject' and 'body' keys
    """
    templates = load_tactics_config()['intro_templates']
    return templates.get(match_preference, templates['Peer_Bundle'])


def get_feedback_options() -> Dict[str, List[str]]:
    """Get feedback configuration (tags for categorization)"""
    return load_tactics_config()['feedback_options']


def get_match_expiry_days() -> int:
    """Get match expiration period in days"""
    return load_tactics_config().get('match_expiry_days', 7)
