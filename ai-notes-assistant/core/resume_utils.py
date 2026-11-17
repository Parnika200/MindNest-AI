import re

from .models import ChatHistory, QuizAttempt, RevisionProgress


def get_practiced_topics(user):
    topics = set()

    # Topics with at least one completed flashcard revision session.
    revised_titles = (
        RevisionProgress.objects
        .filter(user=user, revision_count__gt=0)
        .values_list("material__title", flat=True)
    )
    topics.update(title.strip() for title in revised_titles if title.strip())

    # Topics with a completed quiz attempt.
    quiz_titles = (
        QuizAttempt.objects
        .filter(user=user, completed_at__isnull=False)
        .values_list("quiz__material__title", flat=True)
    )
    topics.update(title.strip() for title in quiz_titles if title.strip())

    # Topics the student has asked questions about in chat.
    chat_titles = (
        ChatHistory.objects
        .filter(user=user)
        .values_list("material__title", flat=True)
    )
    topics.update(title.strip() for title in chat_titles if title.strip())

    # Remove duplicates without regard to capitalization.
    unique_topics = {}
    for topic in topics:
        unique_topics.setdefault(topic.casefold(), topic)

    return sorted(unique_topics.values(), key=str.casefold)


def get_manual_skills(profile):
    raw_skills = re.split(r"[,;\n]+", profile.skills or "")
    return [skill.strip() for skill in raw_skills if skill.strip()]


def get_combined_skills(profile, practiced_topics):
    skills = get_manual_skills(profile)
    known_skills = {skill.casefold() for skill in skills}

    for topic in practiced_topics:
        if topic.casefold() not in known_skills:
            skills.append(topic)
            known_skills.add(topic.casefold())

    return skills


def calculate_resume_score(profile, practiced_topics):
    """
    Return a completeness score from 0 to 100 and suggestions.

    This measures whether useful resume sections are filled in.
    It is not a hiring prediction or a professional recruiter rating.
    """
    sections = [
        ("Full name", bool(profile.full_name.strip()), 8),
        ("Email address", bool(profile.email.strip()), 8),
        ("Phone number", bool(profile.phone.strip()), 5),
        ("Location", bool(profile.location.strip()), 4),
        ("Target role", bool(profile.target_role.strip()), 10),
        ("Professional summary", bool(profile.professional_summary.strip()), 15),
        ("Education", bool(profile.education.strip()), 10),
        ("Grades or GPA", bool(profile.grades.strip()), 8),
        (
            "Skills",
            bool(profile.skills.strip()) or bool(practiced_topics),
            10,
        ),
        ("Experience", bool(profile.experience.strip()), 8),
        ("Projects", bool(profile.projects.strip()), 8),
        ("Certifications", bool(profile.certifications.strip()), 3),
        (
            "LinkedIn or portfolio link",
            bool(profile.linkedin_url.strip())
            or bool(profile.portfolio_url.strip()),
            3,
        ),
    ]

    score = sum(weight for label, completed, weight in sections if completed)
    missing_sections = [
        label for label, completed, weight in sections if not completed
    ]

    feedback = []

    if missing_sections:
        feedback.append(
            "Consider adding: " + ", ".join(missing_sections) + "."
        )
    else:
        feedback.append(
            "All main resume sections contain information."
        )

    if not practiced_topics:
        feedback.append(
            "Complete a quiz, chat about a study material, or finish a "
            "flashcard review to add practiced topics to your skills section."
        )

    return score, feedback