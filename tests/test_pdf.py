"""
Tests for PDF generation
"""

import pytest
import json
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pdf_generator import PDFGenerator, PDFGenerationError
from services.data_validator import DataValidator, ValidationError
from utils.helpers import detect_urgency, detect_collaboration_type, parse_score


def load_fixture(filename):
    """Load test fixture"""
    fixture_path = Path(__file__).parent / 'fixtures' / filename
    with open(fixture_path, 'r') as f:
        return json.load(f)


class TestDataValidator:
    """Test data validation"""

    def test_valid_data(self):
        """Test with valid data"""
        data = load_fixture('sample_data.json')
        assert DataValidator.validate_member_data(data) == True

    def test_missing_participant(self):
        """Test missing participant name"""
        data = load_fixture('sample_data.json')
        del data['participant']

        with pytest.raises(ValidationError, match="Missing participant"):
            DataValidator.validate_member_data(data)

    def test_missing_profile_field(self):
        """Test missing required profile field"""
        data = load_fixture('sample_data.json')
        del data['profile']['seeking']

        with pytest.raises(ValidationError, match="Missing profile field"):
            DataValidator.validate_member_data(data)

    def test_empty_matches(self):
        """Test with no matches"""
        data = load_fixture('sample_data.json')
        data['matches'] = []

        with pytest.raises(ValidationError, match="No matches"):
            DataValidator.validate_member_data(data)

    def test_invalid_score(self):
        """Test invalid score format"""
        data = load_fixture('sample_data.json')
        data['matches'][0]['score'] = 'invalid'

        with pytest.raises(ValidationError, match="invalid score"):
            DataValidator.validate_member_data(data)

    def test_score_out_of_range(self):
        """Test score outside 0-100 range"""
        data = load_fixture('sample_data.json')
        data['matches'][0]['score'] = '150/100'

        with pytest.raises(ValidationError, match="invalid score"):
            DataValidator.validate_member_data(data)

    def test_missing_match_field(self):
        """Test missing required match field"""
        data = load_fixture('sample_data.json')
        del data['matches'][0]['name']

        with pytest.raises(ValidationError, match="missing field: name"):
            DataValidator.validate_member_data(data)


class TestPDFGenerator:
    """Test PDF generation"""

    def test_generate_pdf(self, tmp_path):
        """Test successful PDF generation"""
        data = load_fixture('sample_data.json')

        generator = PDFGenerator(output_dir=str(tmp_path))
        pdf_path = generator.generate(data, member_id='test123')

        assert Path(pdf_path).exists()
        assert Path(pdf_path).suffix == '.pdf'
        assert 'test123' in pdf_path

    def test_generate_pdf_without_member_id(self, tmp_path):
        """Test PDF generation without member_id"""
        data = load_fixture('sample_data.json')

        generator = PDFGenerator(output_dir=str(tmp_path))
        pdf_path = generator.generate(data)

        assert Path(pdf_path).exists()
        assert Path(pdf_path).suffix == '.pdf'
        assert 'Test_User' in pdf_path

    def test_invalid_data_fails(self, tmp_path):
        """Test that invalid data raises error"""
        data = {"invalid": "data"}

        generator = PDFGenerator(output_dir=str(tmp_path))

        with pytest.raises(PDFGenerationError):
            generator.generate(data)

    def test_generate_to_bytes(self, tmp_path):
        """Test generating PDF as bytes"""
        data = load_fixture('sample_data.json')

        generator = PDFGenerator(output_dir=str(tmp_path))
        pdf_bytes = generator.generate_to_bytes(data, member_id='test')

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        # PDF files start with %PDF
        assert pdf_bytes[:4] == b'%PDF'


class TestHelperFunctions:
    """Test utility helper functions"""

    def test_detect_urgency_high(self):
        """Test high urgency detection"""
        assert detect_urgency("Immediate action needed") == 'High'
        assert detect_urgency("urgent - this week") == 'High'
        assert detect_urgency("ASAP") == 'High'
        assert detect_urgency("time-sensitive opportunity") == 'High'

    def test_detect_urgency_low(self):
        """Test low urgency detection"""
        assert detect_urgency("ongoing opportunity") == 'Low'
        assert detect_urgency("no rush, whenever works") == 'Low'
        assert detect_urgency("long-term project") == 'Low'

    def test_detect_urgency_medium(self):
        """Test medium urgency detection"""
        assert detect_urgency("sometime next month") == 'Medium'
        assert detect_urgency("Q2 2025") == 'Medium'
        assert detect_urgency(None) == 'Medium'
        assert detect_urgency("") == 'Medium'

    def test_detect_collaboration_type(self):
        """Test collaboration type detection"""
        assert detect_collaboration_type("joint venture opportunity") == 'Joint Venture'
        assert detect_collaboration_type("cross-referral partnership") == 'Cross-Referral'
        assert detect_collaboration_type("book publishing deal") == 'Publishing'
        assert detect_collaboration_type("speaking at their event") == 'Speaking'
        assert detect_collaboration_type("general business") == 'Partnership'
        assert detect_collaboration_type(None) == 'Partnership'

    def test_parse_score(self):
        """Test score parsing"""
        assert parse_score("95/100") == 95
        assert parse_score("88") == 88
        assert parse_score(82) == 82
        assert parse_score("invalid") == 0
        assert parse_score(None) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
