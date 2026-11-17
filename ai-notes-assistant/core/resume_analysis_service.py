import logging
from typing import Literal

from django.conf import settings
from google import genai
from google.genai import types
from google.genai.errors import ServerError
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class RoleFitAssessment(BaseModel):
    label: Literal["Strong match", "Developing match", "Weak match"]
    score: int = Field(ge=0, le=100)
    summary: str
    strengths: list[str]
    skill_gaps: list[str]
    recommendations: list[str]


def analyze_resume_for_role(profile, practiced_topics):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    # Personal contact details are intentionally left out.
    resume_data = {
        "target_role": profile.target_role,
        "job_description": profile.job_description,
        "professional_summary": profile.professional_summary,
        "education": profile.education,
        "grades": profile.grades,
        "student_skills": profile.skills,
        "topics_practised_in_app": practiced_topics,
        "experience": profile.experience,
        "projects": profile.projects,
        "certifications": profile.certifications,
    }

    prompt = f"""
Review this resume for the student's target role.

Return an honest assessment with:
- A fit label: Strong match, Developing match, or Weak match.
- A score from 0 to 100 estimating alignment with the role.
- A short explanation of the assessment.
- Evidence-based strengths from the supplied details.
- Important skills or experience gaps.
- Specific skills, projects, or learning steps that could improve the match.

Rules:
- Base the assessment only on the information supplied.
- Do not invent experience, qualifications, or skills.
- If no job description was supplied, assess against common expectations
  for an entry-level version of the target role and say that the review
  is general.
- Be constructive and specific.
- A score is guidance, not a hiring decision.

Resume information:
{resume_data}
"""

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    # Try the configured model first, then free-tier Flash-Lite alternatives.
    model_names = list(dict.fromkeys([
        settings.GEMINI_MODEL,
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash-lite",
    ]))

    last_server_error = None

    for model_name in model_names:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RoleFitAssessment,
                ),
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty assessment.")

            return RoleFitAssessment.model_validate_json(response.text)

        except ServerError as error:
            status_code = (
                getattr(error, "code", None)
                or getattr(error, "status_code", None)
            )

            # Try another model only for temporary server overload.
            if status_code not in (None, 503):
                raise

            logger.warning(
                "Gemini model %s returned a server error; trying the next model.",
                model_name,
            )
            last_server_error = error

    if last_server_error:
        raise last_server_error

    raise RuntimeError("No Gemini model was available.")