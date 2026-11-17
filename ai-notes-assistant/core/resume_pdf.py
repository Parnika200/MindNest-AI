from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from .resume_utils import get_combined_skills


NAVY = colors.HexColor("#17324D")
TEAL = colors.HexColor("#197C80")
TEXT = colors.HexColor("#263746")
MUTED = colors.HexColor("#536878")
RULE = colors.HexColor("#D8E2E8")


def add_section(story, title, styles):
    story.append(Spacer(1, 8))
    story.append(Paragraph(escape(title.upper()), styles["ResumeSection"]))
    story.append(
        HRFlowable(
            width="100%",
            thickness=0.8,
            color=RULE,
            spaceBefore=1,
            spaceAfter=6,
        )
    )


def add_multiline_bullets(story, text, styles):
    lines = []

    for raw_line in (text or "").splitlines():
        line = raw_line.strip().lstrip("-*• ").strip()
        if line:
            lines.append(line)

    if not lines:
        return

    items = [
        ListItem(
            Paragraph(escape(line), styles["ResumeBody"]),
            leftIndent=8,
        )
        for line in lines
    ]

    story.append(
        ListFlowable(
            items,
            bulletType="bullet",
            leftIndent=16,
            bulletFontName="Helvetica",
            bulletFontSize=6,
            bulletColor=TEAL,
            spaceAfter=3,
        )
    )


def add_text_block(story, text, styles):
    text = (text or "").strip()

    if not text:
        return

    escaped_text = escape(text).replace("\n", "<br/>")
    story.append(Paragraph(escaped_text, styles["ResumeBody"]))


def create_resume_pdf(profile, combined_skills, practiced_topics):
    buffer = BytesIO()
    sample_styles = getSampleStyleSheet()

    styles = {
        "Name": ParagraphStyle(
            "ResumeName",
            parent=sample_styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=3,
        ),
        "Role": ParagraphStyle(
            "ResumeRole",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=TEAL,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "Contact": ParagraphStyle(
            "ResumeContact",
            parent=sample_styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "ResumeSection": ParagraphStyle(
            "ResumeSection",
            parent=sample_styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=NAVY,
            spaceBefore=6,
            spaceAfter=3,
        ),
        "ResumeBody": ParagraphStyle(
            "ResumeBody",
            parent=sample_styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=TEXT,
            spaceAfter=3,
        ),
    }

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.78 * inch,
        leftMargin=0.78 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.62 * inch,
        title=f"{profile.full_name} - Resume",
        author=profile.full_name,
    )

    contact_items = [
        profile.email,
        profile.phone,
        profile.location,
        profile.linkedin_url,
        profile.portfolio_url,
    ]
    contact_line = "  |  ".join(
        escape(item.strip())
        for item in contact_items
        if item and item.strip()
    )

    story = [
        Paragraph(escape(profile.full_name), styles["Name"]),
        Paragraph(escape(profile.target_role), styles["Role"]),
    ]

    if contact_line:
        story.append(Paragraph(contact_line, styles["Contact"]))

    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=TEAL,
            spaceBefore=2,
            spaceAfter=8,
        )
    )

    if profile.professional_summary.strip():
        add_section(story, "Professional Summary", styles)
        add_text_block(
            story,
            profile.professional_summary,
            styles,
        )

    skills = combined_skills
    if skills:
        add_section(story, "Skills & Practiced Topics", styles)
        add_text_block(story, ", ".join(skills), styles)

    if profile.education.strip() or profile.grades.strip():
        add_section(story, "Education", styles)
        add_multiline_bullets(story, profile.education, styles)

        if profile.grades.strip():
            story.append(Spacer(1, 3))
            story.append(
                Paragraph(
                    f"<b>Grades:</b> {escape(profile.grades).replace(chr(10), '<br/>')}",
                    styles["ResumeBody"],
                )
            )

    for heading, value in [
        ("Experience", profile.experience),
        ("Projects", profile.projects),
        ("Certifications", profile.certifications),
    ]:
        if value.strip():
            add_section(story, heading, styles)
            add_multiline_bullets(story, value, styles)

    def draw_footer(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(
            doc.leftMargin,
            0.43 * inch,
            letter[0] - doc.rightMargin,
            0.43 * inch,
        )
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(
            letter[0] - doc.rightMargin,
            0.25 * inch,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    document.build(
        story,
        onFirstPage=draw_footer,
        onLaterPages=draw_footer,
    )

    return buffer.getvalue()