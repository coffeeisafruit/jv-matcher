"""
Reusable PDF components for JV Matcher Reports
"""

from reportlab.platypus import (
    Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.units import inch
from reportlab.lib.colors import white, HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pdf_styles import COLORS


def detect_urgency(timing_text):
    """Detect urgency level from timing text"""
    if not timing_text:
        return 'Medium'

    timing_lower = str(timing_text).lower()

    high_keywords = ['immediate', 'urgent', 'asap', 'time-sensitive', 'this week', 'tomorrow', 'now']
    if any(k in timing_lower for k in high_keywords):
        return 'High'

    low_keywords = ['ongoing', 'no rush', 'long-term', 'whenever', 'flexible']
    if any(k in timing_lower for k in low_keywords):
        return 'Low'

    return 'Medium'


def detect_collaboration_type(opportunity_text):
    """Detect collaboration type from opportunity text"""
    if not opportunity_text:
        return 'Partnership'

    opp_lower = str(opportunity_text).lower()

    if 'joint venture' in opp_lower or 'jv' in opp_lower:
        return 'Joint Venture'
    elif 'cross-referral' in opp_lower or 'referral' in opp_lower:
        return 'Cross-Referral'
    elif 'publishing' in opp_lower or 'book' in opp_lower:
        return 'Publishing'
    elif 'speaking' in opp_lower or 'event' in opp_lower:
        return 'Speaking'
    elif 'coaching' in opp_lower or 'mentoring' in opp_lower:
        return 'Coaching'
    else:
        return 'Partnership'


def get_score_color(score):
    """Get color based on score value"""
    if score >= 90:
        return COLORS['score_excellent']
    elif score >= 75:
        return COLORS['score_good']
    else:
        return COLORS['score_fair']


def parse_score(score_str):
    """Parse score from string like '95/100' or '95'"""
    try:
        score_text = str(score_str)
        if '/' in score_text:
            return int(score_text.split('/')[0])
        return int(score_text)
    except (ValueError, TypeError):
        return 0


def safe_get(obj, key, default="[Not provided]"):
    """Safely get value with user-friendly default"""
    value = obj.get(key, default) if obj else default
    return value if value and str(value).strip() else default


def create_cover_page(data, styles):
    """Create cover page with participant profile"""
    elements = []

    # Title
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("JV MATCHER REPORT", styles['Hero']))
    elements.append(Paragraph("Your Personalized Partnership Opportunities", styles['HeroSubtitle']))
    elements.append(Spacer(1, 0.3 * inch))

    # Participant name
    participant = safe_get(data, 'participant', 'JV Member')
    elements.append(Paragraph(f"Prepared for: <b>{participant}</b>", styles['SectionHead']))

    # Date
    date_str = safe_get(data, 'date', '')
    if date_str:
        elements.append(Paragraph(f"Generated: {date_str}", styles['Body']))

    elements.append(Spacer(1, 0.3 * inch))

    # Profile section
    profile = data.get('profile', {})

    elements.append(Paragraph("YOUR PROFILE", styles['SectionHead']))
    elements.append(Spacer(1, 0.1 * inch))

    # Profile fields
    profile_fields = [
        ('What You Do', 'what_you_do'),
        ('Who You Serve', 'who_you_serve'),
        ('What You\'re Seeking', 'seeking'),
        ('What You\'re Offering', 'offering'),
        ('Current Projects', 'current_projects'),
    ]

    for label, key in profile_fields:
        value = safe_get(profile, key, '')
        if value and value != "[Not provided]":
            elements.append(Paragraph(f"<b>{label}:</b>", styles['ProfileLabel']))
            elements.append(Paragraph(value, styles['ProfileValue']))

    # Match summary
    matches = data.get('matches', [])
    if matches:
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("MATCH SUMMARY", styles['SectionHead']))

        # Calculate stats
        scores = [parse_score(m.get('score', 0)) for m in matches]
        avg_score = sum(scores) / len(scores) if scores else 0
        top_score = max(scores) if scores else 0

        summary_text = f"Total Matches: <b>{len(matches)}</b> | Average Score: <b>{avg_score:.0f}/100</b> | Top Score: <b>{top_score}/100</b>"
        elements.append(Paragraph(summary_text, styles['Body']))

    elements.append(PageBreak())

    return elements


def create_dashboard(matches, styles):
    """Create executive dashboard with all matches overview"""
    elements = []

    elements.append(Paragraph("EXECUTIVE DASHBOARD", styles['Hero']))
    elements.append(Paragraph("Quick Overview of All Your Matches", styles['HeroSubtitle']))
    elements.append(Spacer(1, 0.2 * inch))

    if not matches:
        elements.append(Paragraph("No matches available.", styles['Body']))
        elements.append(PageBreak())
        return elements

    # Create table data
    table_data = [
        ['#', 'Partner Name', 'Score', 'Type', 'Urgency', 'Revenue Potential']
    ]

    for i, match in enumerate(matches, 1):
        score = parse_score(match.get('score', 0))
        urgency = detect_urgency(match.get('timing', ''))

        # Parse revenue - get short version
        revenue = safe_get(match, 'revenue', 'TBD')
        if 'annually' in revenue.lower():
            revenue_short = revenue.split('annually')[0].strip()
        elif 'per year' in revenue.lower():
            revenue_short = revenue.split('per year')[0].strip()
        else:
            revenue_short = revenue[:30] + '...' if len(revenue) > 30 else revenue

        table_data.append([
            str(i),
            safe_get(match, 'name', 'Unknown')[:25],
            f"{score}/100",
            safe_get(match, 'type', 'Partnership')[:20],
            urgency,
            revenue_short[:25]
        ])

    # Create table
    col_widths = [0.4 * inch, 1.5 * inch, 0.7 * inch, 1.3 * inch, 0.7 * inch, 1.4 * inch]
    table = Table(table_data, colWidths=col_widths)

    # Style the table
    table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['primary']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),

        # Body styling
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # # column
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Score column
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Urgency column

        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, COLORS['light_bg']]),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ])

    # Add urgency color highlighting
    for i, match in enumerate(matches, 1):
        urgency = detect_urgency(match.get('timing', ''))
        if urgency == 'High':
            table_style.add('TEXTCOLOR', (4, i), (4, i), COLORS['urgency_high'])
            table_style.add('FONTNAME', (4, i), (4, i), 'Helvetica-Bold')
        elif urgency == 'Medium':
            table_style.add('TEXTCOLOR', (4, i), (4, i), COLORS['urgency_medium'])

        # Score color
        score = parse_score(match.get('score', 0))
        if score >= 90:
            table_style.add('TEXTCOLOR', (2, i), (2, i), COLORS['score_excellent'])
            table_style.add('FONTNAME', (2, i), (2, i), 'Helvetica-Bold')
        elif score >= 75:
            table_style.add('TEXTCOLOR', (2, i), (2, i), COLORS['score_good'])

    table.setStyle(table_style)
    elements.append(table)

    elements.append(Spacer(1, 0.3 * inch))

    # Legend
    legend_text = "<b>Urgency Legend:</b> <font color='#E74C3C'>High</font> = Act Now | <font color='#F39C12'>Medium</font> = This Quarter | <font color='#95A5A6'>Low</font> = Ongoing"
    elements.append(Paragraph(legend_text, styles['Small']))

    elements.append(PageBreak())

    return elements


def _create_single_match(match, styles, match_num):
    """Create a single match detail card"""
    elements = []

    score = parse_score(match.get('score', 0))
    score_color = get_score_color(score)
    urgency = detect_urgency(match.get('timing', ''))
    collab_type = detect_collaboration_type(match.get('opportunity', ''))

    # Header with name and score
    header_data = [[
        Paragraph(f"<b>MATCH #{match_num}: {safe_get(match, 'name', 'Unknown')}</b>", styles['MatchTitle']),
        Paragraph(f"<b>{score}/100</b>", styles['BigScore'])
    ]]

    header_table = Table(header_data, colWidths=[4.5 * inch, 1.5 * inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), score_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (0, 0), 12),
        ('RIGHTPADDING', (1, 0), (1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(header_table)

    # Match type and urgency badges
    badge_text = f"<b>Type:</b> {safe_get(match, 'type', collab_type)} | <b>Urgency:</b> {urgency}"
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph(badge_text, styles['Subhead']))
    elements.append(Spacer(1, 0.15 * inch))

    # Detail sections in a clean layout
    sections = [
        ('Why They\'re a Great Fit', 'fit'),
        ('Collaboration Opportunity', 'opportunity'),
        ('Mutual Benefits', 'benefits'),
        ('Revenue Potential', 'revenue'),
        ('Timing & Next Steps', 'timing'),
    ]

    for label, key in sections:
        value = safe_get(match, key, '')
        if value and value != "[Not provided]":
            elements.append(Paragraph(f"<b>{label}</b>", styles['ProfileLabel']))
            elements.append(Paragraph(value, styles['BodySmall']))
            elements.append(Spacer(1, 0.08 * inch))

    # Outreach message in a box
    message = safe_get(match, 'message', '')
    if message and message != "[Not provided]":
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("<b>Ready-to-Send Outreach Message:</b>", styles['ProfileLabel']))

        # Message in a styled box
        msg_table = Table([[Paragraph(message, styles['MessageBox'])]], colWidths=[6 * inch])
        msg_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLORS['light_bg']),
            ('BOX', (0, 0), (-1, -1), 1, COLORS['border']),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(msg_table)

    # Contact info
    contact = safe_get(match, 'contact', '')
    if contact and contact != "[Not provided]":
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph(f"<b>Contact:</b> {contact}", styles['Small']))

    return elements


def create_match_pages(matches, styles):
    """Create all match detail pages"""
    elements = []

    elements.append(Paragraph("DETAILED MATCH PROFILES", styles['Hero']))
    elements.append(Paragraph("In-Depth Analysis of Your Top Opportunities", styles['HeroSubtitle']))
    elements.append(Spacer(1, 0.2 * inch))

    for i, match in enumerate(matches, 1):
        match_elements = _create_single_match(match, styles, i)
        elements.extend([KeepTogether(match_elements)])

        if i < len(matches):
            elements.append(Spacer(1, 0.3 * inch))

            # Add page break every 2 matches for readability
            if i % 2 == 0:
                elements.append(PageBreak())

    elements.append(PageBreak())

    return elements


def create_action_tracker(matches, styles):
    """Create action tracker page for follow-up"""
    elements = []

    elements.append(Paragraph("ACTION TRACKER", styles['Hero']))
    elements.append(Paragraph("Your Follow-Up Checklist", styles['HeroSubtitle']))
    elements.append(Spacer(1, 0.2 * inch))

    if not matches:
        elements.append(Paragraph("No matches to track.", styles['Body']))
        return elements

    # Create checklist table
    table_data = [
        ['', 'Partner', 'Action Item', 'Urgency', 'Status']
    ]

    for i, match in enumerate(matches, 1):
        urgency = detect_urgency(match.get('timing', ''))
        name = safe_get(match, 'name', 'Unknown')[:20]

        # Default action based on urgency
        if urgency == 'High':
            action = "Send outreach message TODAY"
        elif urgency == 'Medium':
            action = "Schedule outreach this week"
        else:
            action = "Add to follow-up list"

        table_data.append([
            str(i),
            name,
            action,
            urgency,
            '[ ]'  # Empty checkbox
        ])

    # Create table
    col_widths = [0.4 * inch, 1.3 * inch, 2.2 * inch, 0.8 * inch, 0.6 * inch]
    table = Table(table_data, colWidths=col_widths)

    table_style = TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), COLORS['dark']),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),

        # Body
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('ALIGN', (4, 1), (4, -1), 'CENTER'),

        # Alternating rows
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, COLORS['light_bg']]),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, COLORS['border']),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
    ])

    # Urgency highlighting
    for i, match in enumerate(matches, 1):
        urgency = detect_urgency(match.get('timing', ''))
        if urgency == 'High':
            table_style.add('TEXTCOLOR', (3, i), (3, i), COLORS['urgency_high'])
            table_style.add('FONTNAME', (3, i), (3, i), 'Helvetica-Bold')
        elif urgency == 'Medium':
            table_style.add('TEXTCOLOR', (3, i), (3, i), COLORS['urgency_medium'])

    table.setStyle(table_style)
    elements.append(table)

    # Tips section
    elements.append(Spacer(1, 0.3 * inch))
    elements.append(Paragraph("<b>Follow-Up Tips:</b>", styles['Subhead']))

    tips = [
        "Personalize each message - reference specific points from their profile",
        "High urgency contacts should be reached within 24-48 hours",
        "Follow up if no response within 5-7 business days",
        "Track all communications in your CRM or spreadsheet",
    ]

    for tip in tips:
        elements.append(Paragraph(f"  {tip}", styles['BodySmall']))

    return elements


class FooterCanvas(canvas.Canvas):
    """Custom canvas with page numbers and footer"""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor('#95A5A6'))

        # Page number on right
        page_num = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(7.5 * inch, 0.5 * inch, page_num)

        # Footer text on left
        self.drawString(0.75 * inch, 0.5 * inch, "JV Matcher Report | Confidential")
