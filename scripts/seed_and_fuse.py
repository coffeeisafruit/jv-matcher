#!/usr/bin/env python3
"""
Seed & Fuse Pipeline
====================
Merges Directory CSV with AI-extracted transcript data into the database.

Flow:
1. Step A: Load data/members.csv → Upsert into profiles table
2. Step B: Load data/processed_transcripts.json
3. Step C: Fuzzy match speakers to profiles (threshold 0.8)
4. Step D: Fuse matched data, log unmatched speakers

Usage:
    python scripts/seed_and_fuse.py
    python scripts/seed_and_fuse.py --csv data/members.csv --json data/processed_transcripts.json
    python scripts/seed_and_fuse.py --seed-only  # Only import CSV, skip fusion
    python scripts/seed_and_fuse.py --fuse-only  # Only fuse transcripts (CSV already imported)

Requirements:
    - SUPABASE_URL and SUPABASE_KEY environment variables
    - pip install supabase pandas python-dotenv
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

try:
    import pandas as pd
except ImportError:
    print("Error: pandas not installed. Run: pip install pandas")
    sys.exit(1)

try:
    from supabase import create_client, Client
except ImportError:
    print("Error: supabase not installed. Run: pip install supabase")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()


@dataclass
class FusionResult:
    """Result of the fusion operation"""
    csv_imported: int = 0
    csv_skipped: int = 0
    speakers_matched: int = 0
    speakers_unmatched: int = 0
    profiles_updated: int = 0
    errors: List[Dict] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class NumericParser:
    """Parse various numeric formats from CSV data"""

    @staticmethod
    def parse_list_size(value: Any) -> Optional[int]:
        """
        Parse list_size from various formats:
        - "1,000" → 1000
        - "10k" → 10000
        - "1.5M" → 1500000
        - "1,000,000" → 1000000
        - Empty/None → None
        """
        if value is None or pd.isna(value):
            return None

        value_str = str(value).strip().lower()
        if not value_str:
            return None

        # Remove commas
        value_str = value_str.replace(',', '')

        # Handle k/K suffix (thousands)
        if value_str.endswith('k'):
            try:
                return int(float(value_str[:-1]) * 1000)
            except ValueError:
                return None

        # Handle m/M suffix (millions)
        if value_str.endswith('m'):
            try:
                return int(float(value_str[:-1]) * 1000000)
            except ValueError:
                return None

        # Handle plain numbers
        try:
            # Try as float first to handle "1.5" etc
            return int(float(value_str))
        except ValueError:
            return None

    @staticmethod
    def parse_social_reach(value: Any) -> Optional[int]:
        """Parse social_reach (same logic as list_size)"""
        return NumericParser.parse_list_size(value)


class FuzzyMatcher:
    """Fuzzy name matching using SequenceMatcher"""

    DEFAULT_THRESHOLD = 0.80

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize name for matching"""
        if not name:
            return ""

        # Lowercase
        name = name.lower()

        # Remove common suffixes
        name = re.sub(r'\s*\([^)]+\)\s*', '', name)  # Remove (Host), etc
        name = re.sub(r'\s*-\s*zoom.*$', '', name, flags=re.IGNORECASE)

        # Normalize whitespace
        name = ' '.join(name.strip().split())

        return name

    @staticmethod
    def similarity(name1: str, name2: str) -> float:
        """Calculate similarity ratio between two names"""
        n1 = FuzzyMatcher.normalize_name(name1)
        n2 = FuzzyMatcher.normalize_name(name2)

        if not n1 or not n2:
            return 0.0

        return SequenceMatcher(None, n1, n2).ratio()

    @staticmethod
    def find_best_match(
        speaker_name: str,
        profiles: List[Dict],
        threshold: float = DEFAULT_THRESHOLD
    ) -> Optional[Tuple[Dict, float]]:
        """
        Find the best matching profile for a speaker name.

        Returns:
            Tuple of (profile_dict, confidence_score) or None if no match above threshold
        """
        best_match = None
        best_score = 0.0

        for profile in profiles:
            profile_name = profile.get('name', '')
            score = FuzzyMatcher.similarity(speaker_name, profile_name)

            if score > best_score and score >= threshold:
                best_score = score
                best_match = profile

        if best_match:
            return (best_match, best_score)
        return None


class SeedAndFuseService:
    """Main service for seeding from CSV and fusing with transcript data"""

    CSV_COLUMN_MAPPING = {
        "Name": "name",
        "Company": "company",
        "Business Focus": "business_focus",
        "Status": "status",
        "Service Provided": "service_provided",
        "List Size": "list_size",
        "Business Size": "business_size",
        "Social Reach": "social_reach"
    }

    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        url = supabase_url or os.getenv("SUPABASE_URL")
        key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables required")

        self.supabase: Client = create_client(url, key)

    def seed_from_csv(self, csv_path: str = "data/members.csv") -> Dict[str, int]:
        """
        Import profiles from CSV file.

        Returns:
            Dict with 'imported' and 'skipped' counts
        """
        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"Error: CSV file not found: {csv_file}")
            return {'imported': 0, 'skipped': 0, 'error': 'File not found'}

        print(f"\n{'='*50}")
        print(f"Step A: Seeding from CSV")
        print(f"{'='*50}")
        print(f"Loading: {csv_file}")

        df = pd.read_csv(csv_file)
        print(f"Found {len(df)} rows")

        imported = 0
        skipped = 0
        errors = []

        for idx, row in df.iterrows():
            try:
                profile_data = self._map_csv_row(row)

                if not profile_data.get('name'):
                    skipped += 1
                    continue

                # Upsert by name (use name as the unique identifier for now)
                # Note: This is a simple approach - production might use email or composite key
                existing = self.supabase.table("profiles") \
                    .select("id") \
                    .eq("name", profile_data['name']) \
                    .limit(1) \
                    .execute()

                if existing.data:
                    # Update existing profile
                    self.supabase.table("profiles") \
                        .update(profile_data) \
                        .eq("id", existing.data[0]['id']) \
                        .execute()
                else:
                    # Insert new profile
                    self.supabase.table("profiles") \
                        .insert(profile_data) \
                        .execute()

                imported += 1

                if imported % 50 == 0:
                    print(f"  Progress: {imported} imported...")

            except Exception as e:
                errors.append({'row': idx, 'name': row.get('Name', 'Unknown'), 'error': str(e)})
                skipped += 1

        print(f"\nCSV Import Complete:")
        print(f"  Imported: {imported}")
        print(f"  Skipped: {skipped}")
        print(f"  Errors: {len(errors)}")

        return {'imported': imported, 'skipped': skipped, 'errors': errors}

    def _map_csv_row(self, row: pd.Series) -> Dict[str, Any]:
        """Map CSV row to profile data dict"""
        profile_data = {}

        for csv_col, db_col in self.CSV_COLUMN_MAPPING.items():
            if csv_col in row.index and pd.notna(row[csv_col]):
                value = row[csv_col]

                # Special handling for numeric fields
                if db_col == 'list_size':
                    value = NumericParser.parse_list_size(value)
                elif db_col == 'social_reach':
                    value = NumericParser.parse_social_reach(value)
                else:
                    value = str(value).strip() if value else None

                if value is not None:
                    profile_data[db_col] = value

        return profile_data

    def fuse_transcripts(
        self,
        json_path: str = "data/processed_transcripts.json",
        unmatched_path: str = "data/unmatched_speakers.json",
        match_threshold: float = 0.80
    ) -> Dict[str, Any]:
        """
        Fuse AI-extracted transcript data with existing profiles.

        Returns:
            Dict with fusion statistics
        """
        json_file = Path(json_path)
        if not json_file.exists():
            print(f"Error: JSON file not found: {json_file}")
            return {'error': 'File not found'}

        print(f"\n{'='*50}")
        print(f"Step B & C: Loading and Fusing Transcripts")
        print(f"{'='*50}")
        print(f"Loading: {json_file}")

        with open(json_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)

        speakers = transcript_data.get('speakers', [])
        print(f"Found {len(speakers)} speakers to process")

        # Get all existing profiles
        print(f"\nFetching existing profiles from database...")
        profiles_result = self.supabase.table("profiles").select("*").execute()
        all_profiles = profiles_result.data or []
        print(f"Found {len(all_profiles)} profiles in database")

        # Process each speaker
        matched = 0
        unmatched_speakers = []
        updated = 0
        errors = []

        print(f"\nMatching speakers to profiles (threshold: {match_threshold})...")

        for speaker in speakers:
            speaker_name = speaker.get('name', '')
            if not speaker_name:
                continue

            # Try to find matching profile
            match_result = FuzzyMatcher.find_best_match(
                speaker_name,
                all_profiles,
                threshold=match_threshold
            )

            if match_result:
                profile, confidence = match_result
                matched += 1

                print(f"  ✓ Matched: '{speaker_name}' → '{profile['name']}' ({confidence:.0%})")

                # Update profile with transcript data
                try:
                    update_data = self._build_update_data(speaker)
                    if update_data:
                        self.supabase.table("profiles") \
                            .update(update_data) \
                            .eq("id", profile['id']) \
                            .execute()
                        updated += 1

                except Exception as e:
                    errors.append({
                        'speaker': speaker_name,
                        'profile': profile['name'],
                        'error': str(e)
                    })

            else:
                # No match found - log for manual review
                unmatched_speakers.append({
                    'speaker_name': speaker_name,
                    'company': speaker.get('company'),
                    'inferred_niche': speaker.get('inferred_niche'),
                    'potential_offers': speaker.get('potential_offers', []),
                    'potential_needs': speaker.get('potential_needs', []),
                    'source_file': speaker.get('source_file'),
                    'event_name': speaker.get('event_name'),
                    'reason': 'No matching profile found above threshold'
                })
                print(f"  ✗ Unmatched: '{speaker_name}' (no profile match >= {match_threshold:.0%})")

        # Save unmatched speakers for manual review
        if unmatched_speakers:
            unmatched_file = Path(unmatched_path)
            unmatched_file.parent.mkdir(parents=True, exist_ok=True)

            with open(unmatched_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'generated_at': datetime.now().isoformat(),
                    'match_threshold': match_threshold,
                    'total_unmatched': len(unmatched_speakers),
                    'speakers': unmatched_speakers
                }, f, indent=2)

            print(f"\nUnmatched speakers saved to: {unmatched_file}")

        print(f"\n{'='*50}")
        print(f"Fusion Complete!")
        print(f"{'='*50}")
        print(f"  Speakers matched: {matched}")
        print(f"  Speakers unmatched: {len(unmatched_speakers)}")
        print(f"  Profiles updated: {updated}")
        print(f"  Errors: {len(errors)}")

        return {
            'matched': matched,
            'unmatched': len(unmatched_speakers),
            'updated': updated,
            'errors': errors
        }

    def _build_update_data(self, speaker: Dict) -> Dict[str, Any]:
        """Build profile update dict from speaker extraction"""
        update_data = {}

        # Update seeking field from potential_needs (Bronze trust)
        needs = speaker.get('potential_needs', [])
        if needs:
            update_data['seeking'] = ', '.join(needs[:2])  # Max 2

        # Update offering field from potential_offers (Bronze trust)
        offers = speaker.get('potential_offers', [])
        if offers:
            update_data['offering'] = ', '.join(offers[:2])  # Max 2

        # Update niche if we have it
        niche = speaker.get('inferred_niche')
        if niche:
            update_data['niche'] = niche

        # Update company if we have it and profile doesn't
        company = speaker.get('company')
        if company:
            update_data['company'] = company

        # Always update last_active_at for momentum scoring
        update_data['last_active_at'] = datetime.now().isoformat()

        return update_data

    def run_full_pipeline(
        self,
        csv_path: str = "data/members.csv",
        json_path: str = "data/processed_transcripts.json",
        unmatched_path: str = "data/unmatched_speakers.json",
        match_threshold: float = 0.80
    ) -> FusionResult:
        """Run the full seed and fuse pipeline"""

        result = FusionResult()

        # Step A: Seed from CSV
        csv_result = self.seed_from_csv(csv_path)
        result.csv_imported = csv_result.get('imported', 0)
        result.csv_skipped = csv_result.get('skipped', 0)
        result.errors.extend(csv_result.get('errors', []))

        # Step B & C: Fuse transcripts
        fuse_result = self.fuse_transcripts(
            json_path=json_path,
            unmatched_path=unmatched_path,
            match_threshold=match_threshold
        )
        result.speakers_matched = fuse_result.get('matched', 0)
        result.speakers_unmatched = fuse_result.get('unmatched', 0)
        result.profiles_updated = fuse_result.get('updated', 0)
        result.errors.extend(fuse_result.get('errors', []))

        return result


def main():
    parser = argparse.ArgumentParser(
        description="Seed profiles from CSV and fuse with AI-extracted transcript data"
    )
    parser.add_argument(
        '--csv', '-c',
        default='data/members.csv',
        help='Path to CSV file'
    )
    parser.add_argument(
        '--json', '-j',
        default='data/processed_transcripts.json',
        help='Path to processed transcripts JSON'
    )
    parser.add_argument(
        '--unmatched', '-u',
        default='data/unmatched_speakers.json',
        help='Path to save unmatched speakers'
    )
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=0.80,
        help='Fuzzy match threshold (0-1)'
    )
    parser.add_argument(
        '--seed-only',
        action='store_true',
        help='Only run CSV import, skip transcript fusion'
    )
    parser.add_argument(
        '--fuse-only',
        action='store_true',
        help='Only run transcript fusion, skip CSV import'
    )

    args = parser.parse_args()

    try:
        service = SeedAndFuseService()

        if args.seed_only:
            # Only seed from CSV
            result = service.seed_from_csv(args.csv)
            print(f"\nSeed-only complete: {result}")

        elif args.fuse_only:
            # Only fuse transcripts
            result = service.fuse_transcripts(
                json_path=args.json,
                unmatched_path=args.unmatched,
                match_threshold=args.threshold
            )
            print(f"\nFuse-only complete: {result}")

        else:
            # Full pipeline
            result = service.run_full_pipeline(
                csv_path=args.csv,
                json_path=args.json,
                unmatched_path=args.unmatched,
                match_threshold=args.threshold
            )
            print(f"\n{'='*50}")
            print(f"Full Pipeline Summary")
            print(f"{'='*50}")
            print(f"CSV Imported: {result.csv_imported}")
            print(f"CSV Skipped: {result.csv_skipped}")
            print(f"Speakers Matched: {result.speakers_matched}")
            print(f"Speakers Unmatched: {result.speakers_unmatched}")
            print(f"Profiles Updated: {result.profiles_updated}")
            print(f"Total Errors: {len(result.errors)}")

    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
