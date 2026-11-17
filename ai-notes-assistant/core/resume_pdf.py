from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


NAVY = colors.HexColor("#183153")
BLUE = colors.HexColor("#315D9B")
GRAY = colors.HexColor("#536273")


def _add_text_section(story, title, text, heading_style, body_style):
    text = (text or "").strip()

    if not text:
        return

    story.append(Paragraph(escape(title.upper()), heading_style))
    story.append(Spacer(1, 5))

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if len(lines) <= 1:
        story.append(
            Paragraph(escape(text).replace("\n", "<br/>"), body_style)
        )
    else:
        items = []

        for line in lines:
            cleaned_line = line.lstrip("•*- ").strip()
            if cleaned_line:
                items.append(
                    ListItem(
                        Paragraph(escape(cleaned_line), body_style),
                        leftIndent=12,
                    )
                )

        if items:
            story.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    leftIndent=18,
                    bulletFontName="Helvetica",
                    bulletFontSize=7,
                )
            )

    story.append(Spacer(1, 12))


def create_resume_pdf(profile, combined_skills, practiced_topics):
    buffer = BytesIO()
    styles = getSampleStyleSheet()

    name_style = ParagraphStyle(
        "ResumeName",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=5,
    )

    role_style = ParagraphStyle(
        "ResumeRole",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=BLUE,
        alignment=TA_CENTER,
        spaceAfter=8,
    )

    contact_style = ParagraphStyle(
        "ResumeContact",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=GRAY,
        alignment=TA_CENTER,
        spaceAfter=14,
    )

    heading_style = ParagraphStyle(
        "ResumeSectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=BLUE,
        spaceBefore=8,
        spaceAfter=2,
    )

    body_style = ParagraphStyle(
        "ResumeBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#273444"),
    )

    story = [
        Paragraph(escape(profile.full_name), name_style),
        Paragraph(escape(profile.target_role), role_style),
    ]

    contact_parts = [
        profile.email,
        profile.phone,
        profile.location,
        profile.linkedin_url,
        profile.portfolio_url,
    ]
    contact_line = "  |  ".join(
        escape(value.strip())
        for value in contact_parts
        if value and value.strip()
    )

    if contact_line:
        story.append(Paragraph(contact_line, contact_style))

    story.append(
        Paragraph("PROFESSIONAL SUMMARY", heading_style)
    )
    if profile.professional_summary.strip():
        story.append(
            Paragraph(
                escape(profile.professional_summary).replace("\n", "<br/>"),
                body_style,
            )
        )
    else:
        story.append(
            Paragraph(
                "Motivated candidate seeking a role as "
                + escape(profile.target_role)
                + ".",
                body_style,
            )
        )
    story.append(Spacer(1, 12))

    if combined_skills:
        story.append(Paragraph("SKILLS", heading_style))
        story.append(
            Paragraph(
                escape(", ".join(combined_skills)),
                body_style,
            )
        )
        story.append(Spacer(1, 5))

        if practiced_topics:
            story.append(
                Paragraph(
                    "<b>Topics practiced:</b> "
                    + escape(", ".join(practiced_topics)),
                    body_style,
                )
            )
        story.append(Spacer(1, 12))

    _add_text_section(
        story,
        "Education",
        profile.education,
        heading_style,
        body_style,
    )

    _add_text_section(
        story,
        "Grades and academic results",
        profile.grades,
        heading_style,
        body_style,
    )

    _add_text_section(
        story,
        "Experience",
        profile.experience,
        heading_style,
        body_style,
    )

    _add_text_section(
        story,
        "Projects",
        profile.projects,
        heading_style,
        body_style,
    )

    _add_text_section(
        story,
        "Certifications",
        profile.certifications,
        heading_style,
        body_style,
    )

    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
        title=f"{profile.full_name} - Resume",
        author=profile.full_name,
    )

    document.build(story)
    return buffer.getvalue()