import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from .models import ResumeProfile
from .resume_analysis_service import analyze_resume_for_role
from .resume_forms import ResumeProfileForm
from .resume_utils import (
    calculate_resume_score,
    get_combined_skills,
    get_practiced_topics,
)

logger = logging.getLogger(__name__)


@login_required
def resume_builder(request):
    profile, created = ResumeProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "full_name": request.user.get_full_name() or request.user.username,
            "email": request.user.email or "",
        },
    )

    if request.method == "POST":
        form = ResumeProfileForm(request.POST, instance=profile)

        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user

            practiced_topics = get_practiced_topics(request.user)
            score, feedback = calculate_resume_score(
                profile,
                practiced_topics,
            )

            profile.resume_score = score
            profile.score_feedback = "\n".join(feedback)
            profile.rated_at = timezone.now()
            profile.save()

            messages.success(
                request,
                "Resume details saved and completeness score updated.",
            )
            return redirect("resume_builder")
    else:
        form = ResumeProfileForm(instance=profile)

    practiced_topics = get_practiced_topics(request.user)
    combined_skills = get_combined_skills(profile, practiced_topics)

    return render(
        request,
        "core/resume_builder.html",
        {
            "form": form,
            "profile": profile,
            "practiced_topics": practiced_topics,
            "combined_skills": combined_skills,
            "role_fit_strengths": (
                profile.role_fit_strengths.splitlines()
                if profile.role_fit_strengths
                else []
            ),
            "role_fit_gaps": (
                profile.role_fit_gaps.splitlines()
                if profile.role_fit_gaps
                else []
            ),
            "role_fit_recommendations": (
                profile.role_fit_recommendations.splitlines()
                if profile.role_fit_recommendations
                else []
            ),
        },
    )


@login_required
def resume_download(request):
    profile = get_object_or_404(
        ResumeProfile,
        user=request.user,
    )

    required_values = [
        profile.full_name,
        profile.email,
        profile.target_role,
        profile.education,
    ]

    if not all(value and value.strip() for value in required_values):
        messages.error(
            request,
            "Complete and save your name, email, target role, and education before downloading.",
        )
        return redirect("resume_builder")

    practiced_topics = get_practiced_topics(request.user)
    combined_skills = get_combined_skills(profile, practiced_topics)

    # This function must be defined in core/resume_pdf.py.
    from .resume_pdf import create_resume_pdf

    pdf_bytes = create_resume_pdf(
        profile=profile,
        combined_skills=combined_skills,
        practiced_topics=practiced_topics,
    )

    filename = slugify(profile.full_name) or "student"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{filename}-resume.pdf"'
    )
    return response


@login_required
@require_POST
def resume_analyze(request):
    if request.POST.get("ai_consent") != "yes":
        messages.error(
            request,
            "Agree to the role-fit review before requesting an analysis.",
        )
        return redirect("resume_builder")

    profile = get_object_or_404(
        ResumeProfile,
        user=request.user,
    )

    if not profile.target_role or not profile.target_role.strip():
        messages.error(request, "Enter your target role first.")
        return redirect("resume_builder")

    practiced_topics = get_practiced_topics(request.user)

    try:
        result = analyze_resume_for_role(profile, practiced_topics)

        profile.role_fit_score = result.score
        profile.role_fit_label = result.label
        profile.role_fit_summary = result.summary
        profile.role_fit_strengths = "\n".join(result.strengths)
        profile.role_fit_gaps = "\n".join(result.skill_gaps)
        profile.role_fit_recommendations = "\n".join(
            result.recommendations
        )
        profile.role_analysis_at = timezone.now()

        profile.save(
            update_fields=[
                "role_fit_score",
                "role_fit_label",
                "role_fit_summary",
                "role_fit_strengths",
                "role_fit_gaps",
                "role_fit_recommendations",
                "role_analysis_at",
            ]
        )

        messages.success(request, "Your role-fit analysis is ready.")

    except Exception:
        logger.exception(
            "Resume role-fit analysis failed for user ID %s",
            request.user.id,
        )
        messages.error(
            request,
            "The analysis could not be completed. Check the runserver terminal; if Gemini returned 503, wait briefly and retry.",
        )

    return redirect("resume_builder")