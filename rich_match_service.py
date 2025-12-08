"""
Rich Match Service for JV Matching System
Generates AI-powered rich match analysis with revenue estimates, opportunities, and outreach messages
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from supabase_client import get_admin_client
from directory_service import DirectoryService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RichMatchService:
    """
    Generates rich, actionable match analysis for JV partnerships
    Uses OpenAI to create detailed partnership opportunities with revenue estimates
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the rich match service

        Args:
            api_key: OpenAI API key (defaults to environment variable)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key)
        self.directory_service = DirectoryService(use_admin=True)
        self.supabase = get_admin_client()

    def generate_rich_analysis(
        self,
        user_profile: Dict[str, Any],
        match_profile: Dict[str, Any],
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate comprehensive match analysis with actionable insights

        Args:
            user_profile: The user's profile data
            match_profile: The potential match's profile data
            temperature: OpenAI temperature for creativity (0.0-1.0)

        Returns:
            Dict containing rich analysis with all match details
        """
        try:
            logger.info(f"Generating rich analysis for {user_profile.get('name')} <-> {match_profile.get('name')}")

            # Build the analysis prompt
            prompt = self._build_analysis_prompt(user_profile, match_profile)

            # Call OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert joint venture matchmaker who identifies high-value partnership opportunities. You provide specific, actionable insights with realistic revenue estimates."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=temperature
            )

            # Parse the response
            analysis = json.loads(response.choices[0].message.content)

            # Validate and structure the response
            structured_analysis = self._validate_and_structure_analysis(analysis, user_profile, match_profile)

            logger.info(f"Successfully generated rich analysis: {structured_analysis.get('match_type')}")

            return {
                "success": True,
                "analysis": structured_analysis
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in rich analysis: {str(e)}")
            return self._create_fallback_analysis(user_profile, match_profile, "JSON parsing error")

        except Exception as e:
            logger.error(f"Error generating rich analysis: {str(e)}")
            return self._create_fallback_analysis(user_profile, match_profile, str(e))

    def _build_analysis_prompt(self, user_profile: Dict[str, Any], match_profile: Dict[str, Any]) -> str:
        """Build the prompt for OpenAI analysis"""

        user_name = user_profile.get("name", "User")
        match_name = match_profile.get("name", "Match")

        prompt = f"""
Analyze this potential joint venture partnership and provide a detailed match analysis.

**Profile 1: {user_name}**
- Company: {user_profile.get('company', 'N/A')}
- Business Focus: {user_profile.get('business_focus', 'N/A')}
- What They Do: {user_profile.get('what_you_do', user_profile.get('service_provided', 'N/A'))}
- Who They Serve: {user_profile.get('who_you_serve', 'N/A')}
- Seeking: {user_profile.get('seeking', 'N/A')}
- Offering: {user_profile.get('offering', 'N/A')}
- List Size: {user_profile.get('list_size', 0):,}
- Social Reach: {user_profile.get('social_reach', 0):,}
- Current Projects: {user_profile.get('current_projects', 'N/A')}

**Profile 2: {match_name}**
- Company: {match_profile.get('company', 'N/A')}
- Business Focus: {match_profile.get('business_focus', 'N/A')}
- What They Do: {match_profile.get('what_you_do', match_profile.get('service_provided', 'N/A'))}
- Who They Serve: {match_profile.get('who_you_serve', 'N/A')}
- Seeking: {match_profile.get('seeking', 'N/A')}
- Offering: {match_profile.get('offering', 'N/A')}
- List Size: {match_profile.get('list_size', 0):,}
- Social Reach: {match_profile.get('social_reach', 0):,}
- Current Projects: {match_profile.get('current_projects', 'N/A')}

Provide a JSON response with these exact fields:

{{
    "fit": "2-3 sentences explaining why this is a strategic match and what makes it compelling",
    "opportunity": "Specific, actionable collaboration idea (be creative and concrete)",
    "benefits": "Clear mutual benefits for both parties, highlighting value exchange",
    "revenue_estimate": "Realistic revenue range in format $X,000-$Y,000 based on list sizes and opportunity type",
    "timing": "One of: Immediate, This Quarter, Ongoing, or Long-term",
    "outreach_message": "Ready-to-send personalized introduction message (50-100 words) from {user_name} to {match_name}. Make it warm, specific, and compelling.",
    "match_type": "One of: Joint Venture, Cross-Referral, Speaking Opportunity, Content Collaboration, Affiliate Partnership, Co-Marketing, Strategic Alliance, or Other",
    "confidence_score": 75-95 (number only, based on how well these profiles align)
}}

Guidelines:
- Be specific and actionable, not generic
- Revenue estimates should be realistic based on list sizes and opportunity type
- Outreach message should be warm, professional, and reference specific mutual interests
- Focus on concrete, implementable opportunities
- Highlight complementary strengths and audiences
"""

        return prompt

    def _validate_and_structure_analysis(
        self,
        analysis: Dict[str, Any],
        user_profile: Dict[str, Any],
        match_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate and structure the AI analysis with fallbacks for missing fields

        Args:
            analysis: Raw analysis from OpenAI
            user_profile: User profile data
            match_profile: Match profile data

        Returns:
            Fully structured and validated analysis
        """
        # Ensure all required fields exist with defaults
        structured = {
            "fit": analysis.get("fit", "These profiles show complementary business models and target audiences."),
            "opportunity": analysis.get(
                "opportunity",
                f"Explore a collaborative partnership leveraging {user_profile.get('name')}'s expertise with {match_profile.get('name')}'s audience."
            ),
            "benefits": analysis.get(
                "benefits",
                f"Mutual benefit through audience cross-pollination and expertise sharing."
            ),
            "revenue_estimate": self._validate_revenue_estimate(analysis.get("revenue_estimate", "$5,000-$15,000")),
            "timing": self._validate_timing(analysis.get("timing", "This Quarter")),
            "outreach_message": analysis.get(
                "outreach_message",
                f"Hi {match_profile.get('name', 'there')}, I came across your profile and think there could be a great synergy between what we're both doing. Would love to explore a potential collaboration. Are you open to a quick call?"
            ),
            "match_type": self._validate_match_type(analysis.get("match_type", "Strategic Alliance")),
            "confidence_score": self._validate_confidence_score(analysis.get("confidence_score", 80))
        }

        # Add metadata
        structured["user_profile_id"] = user_profile.get("id")
        structured["match_profile_id"] = match_profile.get("id")
        structured["generated_at"] = "now()"

        return structured

    def _validate_revenue_estimate(self, estimate: str) -> str:
        """
        Validate and format revenue estimate

        Args:
            estimate: Revenue estimate string

        Returns:
            Formatted estimate or default
        """
        if not estimate or not isinstance(estimate, str):
            return "$5,000-$25,000"

        # Ensure proper format
        estimate = estimate.strip()
        if not estimate.startswith("$"):
            estimate = "$" + estimate

        # Basic validation - should contain dash and numbers
        if "-" in estimate and any(c.isdigit() for c in estimate):
            return estimate

        return "$5,000-$25,000"

    def _validate_timing(self, timing: str) -> str:
        """Validate timing is one of the expected values"""
        valid_timings = ["Immediate", "This Quarter", "Ongoing", "Long-term"]

        if not timing or not isinstance(timing, str):
            return "This Quarter"

        # Case-insensitive match
        timing_lower = timing.strip().lower()
        for valid in valid_timings:
            if valid.lower() == timing_lower:
                return valid

        # If contains key words, map to closest match
        if "immediate" in timing_lower or "urgent" in timing_lower or "now" in timing_lower:
            return "Immediate"
        elif "quarter" in timing_lower or "month" in timing_lower:
            return "This Quarter"
        elif "ongoing" in timing_lower or "continuous" in timing_lower:
            return "Ongoing"
        elif "long" in timing_lower or "future" in timing_lower:
            return "Long-term"

        return "This Quarter"

    def _validate_match_type(self, match_type: str) -> str:
        """Validate match type is one of the expected values"""
        valid_types = [
            "Joint Venture",
            "Cross-Referral",
            "Speaking Opportunity",
            "Content Collaboration",
            "Affiliate Partnership",
            "Co-Marketing",
            "Strategic Alliance",
            "Other"
        ]

        if not match_type or not isinstance(match_type, str):
            return "Strategic Alliance"

        # Case-insensitive match
        match_type_lower = match_type.strip().lower()
        for valid in valid_types:
            if valid.lower() == match_type_lower:
                return valid

        # Fuzzy matching for common variations
        if "referral" in match_type_lower or "refer" in match_type_lower:
            return "Cross-Referral"
        elif "speak" in match_type_lower or "presentation" in match_type_lower:
            return "Speaking Opportunity"
        elif "content" in match_type_lower or "collaboration" in match_type_lower:
            return "Content Collaboration"
        elif "affiliate" in match_type_lower or "commission" in match_type_lower:
            return "Affiliate Partnership"
        elif "marketing" in match_type_lower or "promo" in match_type_lower:
            return "Co-Marketing"
        elif "jv" in match_type_lower or "joint" in match_type_lower:
            return "Joint Venture"

        return "Strategic Alliance"

    def _validate_confidence_score(self, score: Any) -> int:
        """
        Validate and normalize confidence score

        Args:
            score: Confidence score (should be 75-95)

        Returns:
            Valid integer score between 75-95
        """
        try:
            score_int = int(float(score))
            # Clamp to valid range
            return max(75, min(95, score_int))
        except (ValueError, TypeError):
            return 80  # Default confidence

    def _create_fallback_analysis(
        self,
        user_profile: Dict[str, Any],
        match_profile: Dict[str, Any],
        error: str
    ) -> Dict[str, Any]:
        """
        Create a basic fallback analysis when AI generation fails

        Args:
            user_profile: User profile data
            match_profile: Match profile data
            error: Error message

        Returns:
            Basic analysis structure with default values
        """
        logger.warning(f"Creating fallback analysis due to: {error}")

        user_name = user_profile.get("name", "User")
        match_name = match_profile.get("name", "Match")
        user_focus = user_profile.get("business_focus", "their business")
        match_focus = match_profile.get("business_focus", "their business")

        fallback_analysis = {
            "fit": f"{user_name} and {match_name} operate in complementary spaces that could benefit from collaboration.",
            "opportunity": f"Explore a strategic partnership leveraging both parties' expertise in {user_focus} and {match_focus}.",
            "benefits": f"{user_name} gains access to {match_name}'s network and expertise, while {match_name} benefits from {user_name}'s audience and offerings.",
            "revenue_estimate": "$10,000-$25,000",
            "timing": "This Quarter",
            "outreach_message": f"Hi {match_name}, I came across your profile and was impressed by your work in {match_focus}. I think there could be excellent synergy with what I'm doing in {user_focus}. Would you be open to a brief conversation about potential collaboration opportunities?",
            "match_type": "Strategic Alliance",
            "confidence_score": 75,
            "user_profile_id": user_profile.get("id"),
            "match_profile_id": match_profile.get("id"),
            "generated_at": "now()",
            "fallback": True,
            "error": error
        }

        return {
            "success": True,
            "analysis": fallback_analysis,
            "fallback": True
        }

    def save_rich_match(
        self,
        profile_id: str,
        suggested_profile_id: str,
        analysis: Dict[str, Any],
        match_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Save rich match analysis to match_suggestions table

        Args:
            profile_id: The user's profile ID
            suggested_profile_id: The matched profile ID
            analysis: The rich analysis dictionary
            match_score: Optional override for match score

        Returns:
            Dict with success status and match suggestion ID
        """
        try:
            logger.info(f"Saving rich match: {profile_id} -> {suggested_profile_id}")

            # Use confidence score as match score if not provided
            if match_score is None:
                match_score = analysis.get("confidence_score", 80)

            # Build match reason from analysis
            match_reason = f"{analysis.get('match_type', 'Partnership')}: {analysis.get('fit', 'Strategic alignment identified.')}"

            # Store full analysis in notes as JSON
            notes = json.dumps({
                "rich_analysis": analysis,
                "generated_by": "rich_match_service"
            })

            # Create match suggestion
            match_data = {
                "profile_id": profile_id,
                "suggested_profile_id": suggested_profile_id,
                "match_score": match_score,
                "match_reason": match_reason[:500],  # Limit length
                "source": "ai_rich_matcher",
                "status": "pending",
                "notes": notes
            }

            response = self.supabase.table("match_suggestions").insert(match_data).execute()

            logger.info(f"Successfully saved rich match: {response.data[0]['id']}")

            return {
                "success": True,
                "match_id": response.data[0]["id"],
                "message": "Rich match analysis saved successfully"
            }

        except Exception as e:
            logger.error(f"Error saving rich match: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to save rich match: {str(e)}"
            }

    def generate_and_save_match(
        self,
        user_profile_id: str,
        match_profile_id: str
    ) -> Dict[str, Any]:
        """
        Complete pipeline: Generate rich analysis and save to database

        Args:
            user_profile_id: The user's profile ID
            match_profile_id: The matched profile ID

        Returns:
            Dict with full results including match_id and analysis
        """
        try:
            # Fetch both profiles
            user_result = self.directory_service.get_profile_by_id(user_profile_id)
            match_result = self.directory_service.get_profile_by_id(match_profile_id)

            if not user_result["success"] or not match_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to fetch profiles",
                    "message": "Could not retrieve one or both profiles"
                }

            user_profile = user_result["data"]
            match_profile = match_result["data"]

            # Generate analysis
            analysis_result = self.generate_rich_analysis(user_profile, match_profile)

            if not analysis_result["success"]:
                return analysis_result

            analysis = analysis_result["analysis"]

            # Save to database
            save_result = self.save_rich_match(
                user_profile_id,
                match_profile_id,
                analysis,
                match_score=analysis.get("confidence_score")
            )

            if not save_result["success"]:
                return save_result

            return {
                "success": True,
                "match_id": save_result["match_id"],
                "analysis": analysis,
                "message": "Rich match generated and saved successfully"
            }

        except Exception as e:
            logger.error(f"Error in generate_and_save_match: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Pipeline error: {str(e)}"
            }
