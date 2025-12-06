#!/usr/bin/env python3
"""
JV Matcher - Core processing logic
Extracts profiles from meeting transcripts and matches people for joint ventures
"""
import os
import json
import re
from typing import List, Dict, Tuple
from datetime import datetime
import zipfile
from pathlib import Path


class JVMatcher:
    """Core JV matching engine"""
    
    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def extract_profiles_from_transcript(self, transcript_path: str) -> List[Dict]:
        """
        Extract individual profiles from a meeting transcript
        Returns list of profiles with name, content, and metadata
        """
        profiles = []
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple extraction: look for speaker patterns
            # In real implementation, this would use NLP/AI to identify speakers
            lines = content.split('\n')
            current_speaker = None
            current_text = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Detect speaker changes (simple heuristic)
                # Look for patterns like "Speaker 1:", "John:", etc.
                speaker_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*):\s*(.+)$', line)
                if speaker_match:
                    # Save previous speaker's content
                    if current_speaker and current_text:
                        profiles.append({
                            'name': current_speaker,
                            'content': ' '.join(current_text),
                            'word_count': len(' '.join(current_text).split())
                        })
                    
                    current_speaker = speaker_match.group(1)
                    current_text = [speaker_match.group(2)]
                else:
                    if current_speaker:
                        current_text.append(line)
            
            # Save last speaker
            if current_speaker and current_text:
                profiles.append({
                    'name': current_speaker,
                    'content': ' '.join(current_text),
                    'word_count': len(' '.join(current_text).split())
                })
            
            # If no speakers detected, treat entire transcript as one profile
            if not profiles:
                profiles.append({
                    'name': 'Participant',
                    'content': content,
                    'word_count': len(content.split())
                })
            
        except Exception as e:
            raise Exception(f"Error extracting profiles: {str(e)}")
        
        return profiles
    
    def chunk_content(self, content: str, max_chunk_size: int = 8000) -> List[str]:
        """
        Split large content into manageable chunks
        Tries to split at sentence boundaries
        """
        sentences = re.split(r'(?<=[.!?])\s+', content)
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence.split())
            if current_size + sentence_size > max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def generate_profile_summary(self, profile: Dict) -> Dict:
        """
        Generate a summary/profile for a person
        In production, this would use AI/LLM
        """
        content = profile['content']
        word_count = profile['word_count']
        
        # Extract key topics (simple keyword extraction)
        # In production, use NLP/AI for better extraction
        keywords = self._extract_keywords(content)
        
        return {
            'name': profile['name'],
            'word_count': word_count,
            'keywords': keywords[:10],  # Top 10 keywords
            'summary': content[:500] + '...' if len(content) > 500 else content
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Simple keyword extraction - in production, use proper NLP"""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        words = re.findall(r'\b[a-z]{4,}\b', text.lower())
        word_freq = {}
        for word in words:
            if word not in stop_words:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top keywords by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words]
    
    def find_matches(self, target_profile: Dict, all_profiles: List[Dict], top_n: int = 10) -> List[Dict]:
        """
        Find best JV partner matches for a target profile
        Returns list of matched profiles with match scores and reasons
        """
        matches = []
        target_keywords = set(target_profile.get('keywords', []))
        
        for profile in all_profiles:
            if profile['name'] == target_profile['name']:
                continue  # Skip self
            
            profile_keywords = set(profile.get('keywords', []))
            
            # Calculate similarity score (simple keyword overlap)
            # In production, use semantic similarity (embeddings, etc.)
            common_keywords = target_keywords.intersection(profile_keywords)
            similarity_score = len(common_keywords) / max(len(target_keywords), 1)
            
            matches.append({
                'profile': profile,
                'score': similarity_score,
                'common_keywords': list(common_keywords)[:5],
                'match_reason': self._generate_match_reason(target_profile, profile, common_keywords)
            })
        
        # Sort by score and return top N
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:top_n]
    
    def _generate_match_reason(self, target: Dict, match: Dict, common_keywords: set) -> str:
        """Generate a human-readable reason for the match"""
        if not common_keywords:
            return f"{match['name']} shares complementary interests that could create valuable synergies."
        
        keyword_list = ', '.join(list(common_keywords)[:3])
        return f"{match['name']} shares interests in {keyword_list}, making them an ideal JV partner for collaborative opportunities."
    
    def generate_report(self, profile: Dict, matches: List[Dict], output_path: str):
        """
        Generate a personalized report for a profile
        """
        report_lines = [
            f"# JV Partner Matching Report for {profile['name']}",
            f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"\n## Your Profile Summary",
            f"\n**Name:** {profile['name']}",
            f"**Content Length:** {profile['word_count']:,} words",
            f"**Key Interests:** {', '.join(profile.get('keywords', [])[:10])}",
            f"\n## Top {len(matches)} Recommended JV Partners\n",
        ]
        
        for i, match in enumerate(matches, 1):
            match_profile = match['profile']
            report_lines.extend([
                f"### {i}. {match_profile['name']}",
                f"\n**Match Score:** {match['score']:.1%}",
                f"\n**Why This Match:** {match['match_reason']}",
                f"\n**Shared Interests:** {', '.join(match.get('common_keywords', [])) if match.get('common_keywords') else 'Complementary skills'}",
                f"\n**Profile Summary:** {match_profile.get('summary', match_profile['content'][:300])}...",
                "\n---\n"
            ])
        
        report_lines.append("\n## Next Steps\n")
        report_lines.append("1. Review each recommended partner above")
        report_lines.append("2. Reach out to those with highest match scores")
        report_lines.append("3. Mention shared interests when connecting")
        report_lines.append("4. Explore collaborative opportunities together\n")
        
        report_content = '\n'.join(report_lines)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        return output_path
    
    def process_files(self, transcript_files: List[str], matches_per_person: int = 10) -> Dict:
        """
        Process multiple transcript files and generate matching reports
        Returns statistics and output file paths
        """
        all_profiles = []
        file_profiles_map = {}
        
        # Extract profiles from all files
        for transcript_file in transcript_files:
            profiles = self.extract_profiles_from_transcript(transcript_file)
            all_profiles.extend(profiles)
            file_profiles_map[transcript_file] = profiles
        
        # Generate summaries for all profiles
        profile_summaries = []
        for profile in all_profiles:
            summary = self.generate_profile_summary(profile)
            profile_summaries.append(summary)
        
        # Generate reports for each profile
        reports_generated = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        reports_dir = self.output_dir / f"reports_{timestamp}"
        reports_dir.mkdir(exist_ok=True)
        
        for profile_summary in profile_summaries:
            matches = self.find_matches(profile_summary, profile_summaries, top_n=matches_per_person)
            
            # Generate report
            safe_name = re.sub(r'[^\w\s-]', '', profile_summary['name']).strip().replace(' ', '_')
            report_path = reports_dir / f"{safe_name}_JV_Report.md"
            
            self.generate_report(profile_summary, matches, str(report_path))
            reports_generated.append(str(report_path))
        
        # Create ZIP file
        zip_path = self.output_dir / f"JV_Reports_{timestamp}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for report_path in reports_generated:
                zipf.write(report_path, os.path.basename(report_path))
        
        return {
            'total_profiles': len(profile_summaries),
            'total_reports': len(reports_generated),
            'reports_dir': str(reports_dir),
            'zip_path': str(zip_path),
            'reports': reports_generated
        }

