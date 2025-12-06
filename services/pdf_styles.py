"""
PDF styling and layout configuration
"""

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.colors import HexColor, white


def create_pdf_styles():
    """Create all PDF styles"""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name='Hero',
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=HexColor('#2C3E50'),
        alignment=TA_CENTER,
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        name='HeroSubtitle',
        fontName='Helvetica',
        fontSize=14,
        textColor=HexColor('#7F8C8D'),
        alignment=TA_CENTER,
        spaceAfter=20
    ))

    styles.add(ParagraphStyle(
        name='SectionHead',
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=HexColor('#2C3E50'),
        spaceAfter=12,
        spaceBefore=16
    ))

    styles.add(ParagraphStyle(
        name='Subhead',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=HexColor('#2980B9'),
        spaceAfter=6
    ))

    styles.add(ParagraphStyle(
        name='Body',
        fontName='Helvetica',
        fontSize=10,
        textColor=HexColor('#2C3E50'),
        leading=14
    ))

    styles.add(ParagraphStyle(
        name='BodySmall',
        fontName='Helvetica',
        fontSize=9,
        textColor=HexColor('#2C3E50'),
        leading=12
    ))

    styles.add(ParagraphStyle(
        name='Small',
        fontName='Helvetica',
        fontSize=8,
        textColor=HexColor('#555555'),
        leading=11
    ))

    styles.add(ParagraphStyle(
        name='SmallBold',
        fontName='Helvetica-Bold',
        fontSize=8,
        textColor=HexColor('#2C3E50'),
        leading=11
    ))

    styles.add(ParagraphStyle(
        name='MatchTitle',
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=white,
        leading=14
    ))

    styles.add(ParagraphStyle(
        name='BigScore',
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=white,
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name='ProfileLabel',
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=HexColor('#2980B9'),
        spaceAfter=2
    ))

    styles.add(ParagraphStyle(
        name='ProfileValue',
        fontName='Helvetica',
        fontSize=10,
        textColor=HexColor('#2C3E50'),
        leading=13,
        spaceAfter=8
    ))

    styles.add(ParagraphStyle(
        name='TableHeader',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=white,
        alignment=TA_CENTER
    ))

    styles.add(ParagraphStyle(
        name='TableCell',
        fontName='Helvetica',
        fontSize=8,
        textColor=HexColor('#2C3E50'),
        leading=10
    ))

    styles.add(ParagraphStyle(
        name='MessageBox',
        fontName='Helvetica',
        fontSize=9,
        textColor=HexColor('#2C3E50'),
        leading=12,
        leftIndent=10,
        rightIndent=10
    ))

    return styles


# Color scheme
COLORS = {
    'primary': HexColor('#2980B9'),
    'secondary': HexColor('#27AE60'),
    'dark': HexColor('#2C3E50'),
    'light_bg': HexColor('#F8F9FA'),
    'border': HexColor('#E0E0E0'),
    'white': white,
    'urgency_high': HexColor('#E74C3C'),
    'urgency_medium': HexColor('#F39C12'),
    'urgency_low': HexColor('#95A5A6'),
    'tier_top': HexColor('#27AE60'),
    'tier_high': HexColor('#2980B9'),
    'tier_good': HexColor('#95A5A6'),
    'score_excellent': HexColor('#27AE60'),
    'score_good': HexColor('#2980B9'),
    'score_fair': HexColor('#F39C12'),
}
