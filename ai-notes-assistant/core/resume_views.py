from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify

from .models import ResumeProfile
from .resume_forms import ResumeProfileForm
from .resume_utils import (
    calculate_resume_score,
    get_combined_skills,
    get_practiced_topics,
)


@login_required
def resume_builder(request):
    profile, created = ResumeProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "full_name": (
                request.user.get_full_name() or request.user.username
            ),
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

    if not all(value.strip() for value in required_values):
        messages.error(
            request,
            "Complete and save your name, email, target role, and education before downloading.",
        )
        return redirect("resume_builder")

    practiced_topics = get_practiced_topics(request.user)
    combined_skills = get_combined_skills(profile, practiced_topics)

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