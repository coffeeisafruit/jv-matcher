"""
Utility functions for JV Matcher
"""

import re
from typing import Optional


def detect_urgency(timing_text: Optional[str]) -> str:
    """
    Detect urgency level from timing text

    Args:
        timing_text: Text describing timing/urgency

    Returns:
        'High', 'Medium', or 'Low'
    """
    if not timing_text:
        return 'Medium'

    timing_lower = str(timing_text).lower()

    # High urgency indicators
    high_keywords = [
        'immediate', 'urgent', 'asap', 'time-sensitive',
        'this week', 'tomorrow', 'now', 'today',
        'right away', 'critical'
    ]
    if any(k in timing_lower for k in high_keywords):
        return 'High'

    # Low urgency indicators
    low_keywords = [
        'ongoing', 'no rush', 'long-term', 'whenever',
        'flexible', 'when ready', 'eventually'
    ]
    if any(k in timing_lower for k in low_keywords):
        return 'Low'

    return 'Medium'


def detect_collaboration_type(opportunity_text: Optional[str]) -> str:
    """
    Detect collaboration type from opportunity text

    Args:
        opportunity_text: Description of the opportunity

    Returns:
        Type of collaboration
    """
    if not opportunity_text:
        return 'Partnership'

    opp_lower = str(opportunity_text).lower()

    type_mapping = {
        'Joint Venture': ['joint venture', 'jv '],
        'Cross-Referral': ['cross-referral', 'referral', 'refer'],
        'Publishing': ['publishing', 'book', 'author', 'write'],
        'Speaking': ['speaking', 'event', 'conference', 'summit'],
        'Coaching': ['coaching', 'mentoring', 'training'],
        'Affiliate': ['affiliate', 'commission', 'promote'],
        'Strategic': ['strategic', 'alliance', 'partner'],
    }

    for collab_type, keywords in type_mapping.items():
        if any(k in opp_lower for k in keywords):
            return collab_type

    return 'Partnership'


def parse_score(score_str) -> int:
    """
    Parse score from various formats

    Args:
        score_str: Score string like '95/100', '95', 95

    Returns:
        Integer score (0-100)
    """
    try:
        score_text = str(score_str)
        if '/' in score_text:
            return int(score_text.split('/')[0])
        return int(float(score_text))
    except (ValueError, TypeError):
        return 0


def parse_revenue(revenue_text: Optional[str]) -> str:
    """
    Parse and format revenue string

    Args:
        revenue_text: Revenue description

    Returns:
        Formatted short revenue string
    """
    if not revenue_text:
        return "TBD"

    revenue = str(revenue_text)

    # Try to extract dollar amounts
    amounts = re.findall(r'\$?[\d,]+[kK]?', revenue)

    if len(amounts) >= 2:
        return f"{amounts[0]}-{amounts[1]}"
    elif len(amounts) == 1:
        return f"Up to {amounts[0]}"

    # Fallback: shorten if too long
    if 'annually' in revenue.lower():
        short = revenue.split('annually')[0].strip()
        return short[:40] + '...' if len(short) > 40 else short

    return revenue[:40] + '...' if len(revenue) > 40 else revenue


def safe_get(obj: dict, key: str, default: str = "[Not provided]") -> str:
    """
    Safely get value from dict with user-friendly default

    Args:
        obj: Dictionary to get value from
        key: Key to look up
        default: Default value if not found or empty

    Returns:
        Value or default
    """
    if not obj:
        return default

    value = obj.get(key, default)
    return value if value and str(value).strip() else default


def sanitize_filename(name: str) -> str:
    """
    Create safe filename from string

    Args:
        name: Original name

    Returns:
        Safe filename string
    """
    # Remove or replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', name)
    safe = safe.replace(' ', '_')
    return safe[:100]  # Limit length


def format_contact_info(contact: str) -> dict:
    """
    Parse contact string into structured data

    Args:
        contact: Contact info string (email, phone, url)

    Returns:
        Dict with email, phone, website keys
    """
    result = {'email': None, 'phone': None, 'website': None}

    if not contact:
        return result

    parts = str(contact).split(',')

    for part in parts:
        part = part.strip()

        # Email detection
        if '@' in part and '.' in part:
            result['email'] = part
        # URL detection
        elif 'http' in part or 'www.' in part or '.com' in part:
            result['website'] = part
        # Phone detection (simple pattern)
        elif re.search(r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}', part):
            result['phone'] = part

    return result
