#!/usr/bin/env python3
"""
Batch Extract Pipeline
======================
Converts raw Zoom VTT files into structured JSON with AI extraction.

Flow:
1. Iterate through data/raw_transcripts/*.vtt
2. Parse VTT format to extract speakers and text
3. Use GPT-4o-mini to extract: Speaker, Niche, Offers, Needs, Context
4. Save to data/processed_transcripts.json

Usage:
    python scripts/batch_extract.py
    python scripts/batch_extract.py --input data/raw_transcripts --output data/processed_transcripts.json

Requirements:
    - OPENAI_API_KEY environment variable
    - pip install openai
"""

import os
import sys
import json
import re
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
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
    from openai import OpenAI
except ImportError:
    print("Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


@dataclass
class ExtractedSpeaker:
    """Structured data extracted from a speaker's transcript"""
    name: str
    company: Optional[str] = None
    inferred_niche: Optional[str] = None
    potential_offers: List[str] = None
    potential_needs: List[str] = None
    context_quotes: List[str] = None
    word_count: int = 0
    line_count: int = 0
    source_file: str = ""
    event_name: str = ""
    extracted_at: str = ""

    def __post_init__(self):
        if self.potential_offers is None:
            self.potential_offers = []
        if self.potential_needs is None:
            self.potential_needs = []
        if self.context_quotes is None:
            self.context_quotes = []
        if not self.extracted_at:
            self.extracted_at = datetime.now().isoformat()


class VTTParser:
    """Parse Zoom VTT transcript files"""

    # Common VTT patterns
    TIMESTAMP_PATTERN = re.compile(
        r'(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})'
    )
    SPEAKER_PATTERN = re.compile(r'^([^:]+):\s*(.+)$')

    def parse_file(self, file_path: Path) -> Dict[str, List[str]]:
        """
        Parse VTT file and group text by speaker.

        Returns:
            Dict mapping speaker names to list of their utterances
        """
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        return self.parse_content(content)

    def parse_content(self, content: str) -> Dict[str, List[str]]:
        """Parse VTT content string"""
        speaker_texts: Dict[str, List[str]] = {}
        lines = content.split('\n')

        current_text = []
        for line in lines:
            line = line.strip()

            # Skip empty lines, WEBVTT header, and timestamps
            if not line or line == 'WEBVTT' or self.TIMESTAMP_PATTERN.match(line):
                continue

            # Skip numeric cue identifiers
            if line.isdigit():
                continue

            # Try to extract speaker from "Speaker: text" format
            speaker_match = self.SPEAKER_PATTERN.match(line)
            if speaker_match:
                speaker = self._normalize_speaker_name(speaker_match.group(1))
                text = speaker_match.group(2).strip()

                if speaker not in speaker_texts:
                    speaker_texts[speaker] = []
                if text:
                    speaker_texts[speaker].append(text)
            else:
                # Line without speaker attribution - append to "Unknown"
                if line and not line.startswith('NOTE'):
                    if 'Unknown' not in speaker_texts:
                        speaker_texts['Unknown'] = []
                    speaker_texts['Unknown'].append(line)

        return speaker_texts

    def _normalize_speaker_name(self, name: str) -> str:
        """Normalize speaker name for consistency"""
        # Remove common suffixes/prefixes
        name = name.strip()

        # Remove "(Host)", "(Co-host)", etc.
        name = re.sub(r'\s*\([^)]+\)\s*', '', name)

        # Remove "- Zoom" or similar
        name = re.sub(r'\s*-\s*Zoom.*$', '', name, flags=re.IGNORECASE)

        # Normalize whitespace
        name = ' '.join(name.split())

        return name


class BatchExtractor:
    """Extract structured data from VTT transcripts using AI"""

    MIN_LINES_THRESHOLD = 3  # Skip speakers with fewer lines (casual observers)
    MAX_CONTEXT_QUOTES = 3    # Max quotes to preserve per speaker

    def __init__(self, openai_api_key: Optional[str] = None):
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable required")

        self.openai = OpenAI(api_key=api_key)
        self.parser = VTTParser()

    def extract_from_file(self, vtt_path: Path) -> List[ExtractedSpeaker]:
        """Extract speaker data from a single VTT file"""
        print(f"  Parsing: {vtt_path.name}")

        speaker_texts = self.parser.parse_file(vtt_path)
        event_name = vtt_path.stem  # Use filename as event name

        extracted = []
        for speaker_name, texts in speaker_texts.items():
            # Skip speakers with too few lines (casual observers)
            if len(texts) < self.MIN_LINES_THRESHOLD:
                print(f"    Skipping '{speaker_name}' ({len(texts)} lines < {self.MIN_LINES_THRESHOLD} threshold)")
                continue

            # Skip "Unknown" speaker
            if speaker_name.lower() in ['unknown', 'narrator', 'system']:
                continue

            # Combine texts for AI analysis
            combined_text = ' '.join(texts)
            word_count = len(combined_text.split())

            print(f"    Extracting from '{speaker_name}' ({len(texts)} lines, {word_count} words)")

            try:
                speaker_data = self._extract_with_ai(
                    speaker_name=speaker_name,
                    speaker_text=combined_text,
                    texts=texts,
                    event_name=event_name
                )

                speaker_data.source_file = vtt_path.name
                speaker_data.event_name = event_name
                speaker_data.word_count = word_count
                speaker_data.line_count = len(texts)

                extracted.append(speaker_data)

            except Exception as e:
                print(f"    Error extracting from '{speaker_name}': {e}")
                # Create minimal entry on error
                extracted.append(ExtractedSpeaker(
                    name=speaker_name,
                    source_file=vtt_path.name,
                    event_name=event_name,
                    word_count=word_count,
                    line_count=len(texts)
                ))

        return extracted

    def _extract_with_ai(
        self,
        speaker_name: str,
        speaker_text: str,
        texts: List[str],
        event_name: str
    ) -> ExtractedSpeaker:
        """Use GPT-4o-mini to extract structured data from speaker's text"""

        # Truncate text if too long (context window management)
        max_chars = 8000
        if len(speaker_text) > max_chars:
            speaker_text = speaker_text[:max_chars] + "..."

        prompt = f"""Analyze this networking event transcript excerpt from "{event_name}" and extract structured business intelligence.

SPEAKER: {speaker_name}

WHAT THEY SAID:
{speaker_text}

Extract the following information (use null if not clearly mentioned):

1. **company**: Their company/business name if mentioned
2. **inferred_niche**: Their business category (e.g., "Health Coach", "SaaS Founder", "Marketing Agency", "Real Estate", "Financial Services")
3. **potential_offers**: What they can offer to partners (services, products, expertise, audience access). List up to 3.
4. **potential_needs**: What they're looking for (services, partners, resources). List up to 3.
5. **context_quotes**: 1-2 brief, relevant quotes that show their expertise or needs (for match explanation display)

Return ONLY valid JSON in this exact format:
{{
    "company": "string or null",
    "inferred_niche": "string or null",
    "potential_offers": ["string", "string"],
    "potential_needs": ["string", "string"],
    "context_quotes": ["quote 1", "quote 2"]
}}

Important:
- Only include offers/needs that are CLEARLY stated or strongly implied
- Keep context_quotes SHORT (under 100 chars each)
- Use lowercase for niche categories when possible
- If someone is just chatting without business content, return empty arrays"""

        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a business intelligence analyst extracting partnership signals from networking transcripts. Be conservative - only extract clearly stated business information."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
            temperature=0.3  # Lower temperature for more consistent extraction
        )

        try:
            result = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            result = {}

        return ExtractedSpeaker(
            name=speaker_name,
            company=result.get('company'),
            inferred_niche=result.get('inferred_niche'),
            potential_offers=result.get('potential_offers', []) or [],
            potential_needs=result.get('potential_needs', []) or [],
            context_quotes=result.get('context_quotes', [])[:self.MAX_CONTEXT_QUOTES]
        )

    def process_directory(
        self,
        input_dir: str = "data/raw_transcripts",
        output_file: str = "data/processed_transcripts.json"
    ) -> Dict:
        """Process all VTT files in a directory"""

        input_path = Path(input_dir)
        output_path = Path(output_file)

        if not input_path.exists():
            print(f"Error: Input directory not found: {input_path}")
            return {'success': False, 'error': 'Input directory not found'}

        # Find all VTT files
        vtt_files = list(input_path.glob("*.vtt")) + list(input_path.glob("*.txt"))
        if not vtt_files:
            print(f"Warning: No .vtt or .txt files found in {input_path}")
            return {'success': False, 'error': 'No VTT files found'}

        print(f"\nFound {len(vtt_files)} VTT files to process\n")

        all_speakers: List[ExtractedSpeaker] = []
        files_processed = 0
        errors: List[Dict] = []

        for vtt_file in sorted(vtt_files):
            print(f"\nProcessing [{files_processed + 1}/{len(vtt_files)}]: {vtt_file.name}")

            try:
                speakers = self.extract_from_file(vtt_file)
                all_speakers.extend(speakers)
                files_processed += 1
                print(f"  Extracted {len(speakers)} speakers")

            except Exception as e:
                error_entry = {'file': vtt_file.name, 'error': str(e)}
                errors.append(error_entry)
                print(f"  ERROR: {e}")

        # Deduplicate speakers across files (same name = merge)
        deduplicated = self._deduplicate_speakers(all_speakers)

        # Prepare output
        output = {
            'metadata': {
                'extracted_at': datetime.now().isoformat(),
                'files_processed': files_processed,
                'total_files': len(vtt_files),
                'total_speakers': len(deduplicated),
                'speakers_before_dedup': len(all_speakers),
                'errors': errors
            },
            'speakers': [asdict(s) for s in deduplicated]
        }

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write output
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*50}")
        print(f"Extraction Complete!")
        print(f"{'='*50}")
        print(f"Files processed: {files_processed}/{len(vtt_files)}")
        print(f"Speakers extracted: {len(deduplicated)} (from {len(all_speakers)} before dedup)")
        print(f"Errors: {len(errors)}")
        print(f"Output saved to: {output_path}")

        return output['metadata']

    def _deduplicate_speakers(
        self,
        speakers: List[ExtractedSpeaker]
    ) -> List[ExtractedSpeaker]:
        """Deduplicate speakers by name, merging data from multiple appearances"""

        from difflib import SequenceMatcher

        unique: Dict[str, ExtractedSpeaker] = {}

        for speaker in speakers:
            name_lower = speaker.name.lower().strip()

            # Check if similar name already exists
            matched_key = None
            for existing_key in unique.keys():
                ratio = SequenceMatcher(None, name_lower, existing_key).ratio()
                if ratio >= 0.85:
                    matched_key = existing_key
                    break

            if matched_key:
                # Merge with existing
                existing = unique[matched_key]

                # Merge offers (dedupe)
                existing.potential_offers = list(set(
                    existing.potential_offers + speaker.potential_offers
                ))[:5]  # Cap at 5

                # Merge needs (dedupe)
                existing.potential_needs = list(set(
                    existing.potential_needs + speaker.potential_needs
                ))[:5]

                # Keep best niche (prefer non-null)
                if not existing.inferred_niche and speaker.inferred_niche:
                    existing.inferred_niche = speaker.inferred_niche

                # Keep best company
                if not existing.company and speaker.company:
                    existing.company = speaker.company

                # Add more quotes
                existing.context_quotes = list(set(
                    existing.context_quotes + speaker.context_quotes
                ))[:self.MAX_CONTEXT_QUOTES]

                # Update stats
                existing.word_count += speaker.word_count
                existing.line_count += speaker.line_count

            else:
                unique[name_lower] = speaker

        return list(unique.values())


def main():
    parser = argparse.ArgumentParser(
        description="Extract structured data from Zoom VTT transcripts"
    )
    parser.add_argument(
        '--input', '-i',
        default='data/raw_transcripts',
        help='Input directory containing VTT files'
    )
    parser.add_argument(
        '--output', '-o',
        default='data/processed_transcripts.json',
        help='Output JSON file path'
    )
    parser.add_argument(
        '--api-key',
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )

    args = parser.parse_args()

    try:
        extractor = BatchExtractor(openai_api_key=args.api_key)
        result = extractor.process_directory(
            input_dir=args.input,
            output_file=args.output
        )

        if result.get('success') is False:
            sys.exit(1)

    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
