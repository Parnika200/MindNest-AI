from django.conf import settings
from google import genai


def generate_summary(source_text, topic, summary_type):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    instructions = {
        "short": (
            "Write a concise study summary of about 150 to 200 words. "
            "Keep the main ideas and important terms."
        ),
        "long": (
            "Write a detailed study summary with clear headings. "
            "Explain the main ideas, definitions, and relationships."
        ),
        "key_points": (
            "Create 8 to 12 useful revision key points as a bulleted list. "
            "Keep each point clear and based only on the supplied material."
        ),
    }

    if summary_type not in instructions:
        raise ValueError("Choose short, long, or key points.")

    prompt = f"""
You are a study assistant. Use only the supplied study material.
Do not invent facts. If something is unclear or missing, leave it out.

Topic: {topic}

Task:
{instructions[summary_type]}

Study material:
{source_text}
"""

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )

    generated_text = (response.text or "").strip()

    if not generated_text:
        raise RuntimeError("Gemini returned an empty response.")

    return generated_text