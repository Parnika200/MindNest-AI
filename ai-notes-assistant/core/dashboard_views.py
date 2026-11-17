import calendar
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from .models import (
    Quiz,
    QuizAttempt,
    RevisionProgress,
    StudyMaterial,
    Summary,
)


@login_required
def dashboard(request):
    user = request.user

    materials = StudyMaterial.objects.filter(user=user)
    summaries = Summary.objects.filter(material__user=user)
    quizzes = Quiz.objects.filter(user=user)

    completed_attempts = QuizAttempt.objects.filter(
        user=user,
        completed_at__isnull=False,
    )

    overall_scores = completed_attempts.aggregate(
        correct=Sum("score"),
        total=Sum("total_questions"),
    )

    correct_answers = overall_scores["correct"] or 0
    total_answers = overall_scores["total"] or 0
    incorrect_answers = max(total_answers - correct_answers, 0)

    if total_answers:
        average_score = round(correct_answers * 100 / total_answers)
    else:
        average_score = 0

    revision_sessions = (
        RevisionProgress.objects
        .filter(user=user)
        .aggregate(total=Sum("revision_count"))["total"]
        or 0
    )

    # Build the current and previous five calendar months.
    today = timezone.localdate()
    current_month_index = today.year * 12 + today.month - 1
    first_month_index = current_month_index - 5

    month_labels = []
    month_keys = []

    for offset in range(6):
        month_index = first_month_index + offset
        year = month_index // 12
        month = month_index % 12 + 1

        month_labels.append(f"{calendar.month_abbr[month]} {year}")
        month_keys.append((year, month))

    first_year, first_month = month_keys[0]
    first_month_datetime = datetime(first_year, first_month, 1)
    first_month_datetime = timezone.make_aware(
        first_month_datetime,
        timezone.get_current_timezone(),
    )

    monthly_rows = (
        completed_attempts
        .filter(started_at__gte=first_month_datetime)
        .annotate(
            month=TruncMonth(
                "started_at",
                tzinfo=timezone.get_current_timezone(),
            )
        )
        .values("month")
        .annotate(
            attempt_count=Count("id"),
            correct=Sum("score"),
            total=Sum("total_questions"),
        )
        .order_by("month")
    )

    monthly_scores_by_key = {}

    for row in monthly_rows:
        month_value = row["month"]
        total = row["total"] or 0
        correct = row["correct"] or 0

        if total:
            score_percent = round(correct * 100 / total)
        else:
            score_percent = 0

        monthly_scores_by_key[
            (month_value.year, month_value.month)
        ] = score_percent

    monthly_score_data = [
        monthly_scores_by_key.get(key, 0)
        for key in month_keys
    ]

    revision_rows = (
        RevisionProgress.objects
        .filter(user=user, revision_count__gt=0)
        .select_related("material")
        .order_by("-revision_count", "material__title")[:5]
    )

    revision_labels = [
        row.material.title[:24]
        for row in revision_rows
    ]
    revision_counts = [
        row.revision_count
        for row in revision_rows
    ]

    recent_attempts = (
        completed_attempts
        .select_related("quiz", "quiz__material")
        .order_by("-completed_at")[:5]
    )

    recent_materials = materials.order_by("-uploaded_at")[:5]

    display_name = user.first_name or user.username

    chart_data = {
        "months": month_labels,
        "monthlyScores": monthly_score_data,
        "correctAnswers": correct_answers,
        "incorrectAnswers": incorrect_answers,
        "revisionLabels": revision_labels,
        "revisionCounts": revision_counts,
    }

    context = {
        "display_name": display_name,
        "total_materials": materials.count(),
        "processed_materials": materials.filter(status="processed").count(),
        "summary_count": summaries.count(),
        "quiz_count": quizzes.count(),
        "completed_quiz_count": completed_attempts.count(),
        "average_score": average_score,
        "revision_sessions": revision_sessions,
        "total_answers": total_answers,
        "has_revision_data": bool(revision_labels),
        "recent_attempts": recent_attempts,
        "recent_materials": recent_materials,
        "chart_data": chart_data,
    }

    return render(request, "core/dashboard.html", context)