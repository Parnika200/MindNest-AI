import logging
from datetime import timedelta
from math import ceil

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    AttemptAnswer,
    Quiz,
    QuizAttempt,
    QuizQuestion,
    StudyMaterial,
)
from .quiz_service import generate_questions

#quiz_create → quiz_list → quiz_start → quiz_attempt → quiz_submit → quiz_result

logger = logging.getLogger(__name__)

ALLOWED_QUESTION_COUNTS = {5, 10}
TIMER_GRACE_SECONDS = 5

"""Shows all quizzes created by the logged-in user. For each quiz it also loads the user’s attempts, counts them, and finds the best-scoring one,
   then renders quiz_list.html."""
@login_required
def quiz_list(request):
    quizzes = (
        Quiz.objects
        .filter(user=request.user)
        .select_related("material")
        .order_by("-created_at")
    )

    quiz_cards = []

    for quiz in quizzes:
        attempts = list(
            QuizAttempt.objects
            .filter(user=request.user, quiz=quiz)
            .order_by("-started_at")
        )

        best_attempt = max(
            attempts,
            key=lambda attempt: attempt.score,
            default=None,
        )

        quiz_cards.append({
            "quiz": quiz,
            "attempts": attempts,
            "attempt_count": len(attempts),
            "best_attempt": best_attempt,
        })

    return render(
        request,
        "core/quiz_list.html",
        {"quiz_cards": quiz_cards},
    )


@login_required
def quiz_create(request):
    materials = (
        StudyMaterial.objects
        .filter(user=request.user, status="processed")
        .exclude(extracted_text="")
        .order_by("title")
    )

    if request.method == "POST":
        material_id = request.POST.get("material_id", "")
        difficulty = request.POST.get("difficulty", "")
        question_count_value = request.POST.get("question_count", "5")

        material = get_object_or_404(
            StudyMaterial,
            id=material_id,
            user=request.user,
            status="processed",
        )

        valid_difficulties = {
            value for value, label in Quiz.Difficulty.choices
        }

        try:
            question_count = int(question_count_value)
        except (TypeError, ValueError):
            question_count = 0

        if difficulty not in valid_difficulties:
            messages.error(request, "Choose easy, medium, or hard.")
        elif question_count not in ALLOWED_QUESTION_COUNTS:
            messages.error(request, "Choose 5 or 10 questions.")
        elif not material.extracted_text.strip():
            messages.error(
                request,
                "This material does not have extracted text.",
            )
        else:
            
            source_text = material.extracted_text[:60000]

            try:
                generated_questions = generate_questions(
                    material_text=source_text,
                    topic=material.title,
                    difficulty=difficulty,
                    question_count=question_count,
                )

                with transaction.atomic():
                    quiz = Quiz.objects.create(
                        user=request.user,
                        material=material,
                        title=f"{material.title} - {difficulty.title()} quiz",
                        difficulty=difficulty,
                        duration_minutes=10,
                    )

                    QuizQuestion.objects.bulk_create([
                        QuizQuestion(
                            quiz=quiz,
                            question_text=item.question_text[:2000],
                            option_a=item.option_a[:500],
                            option_b=item.option_b[:500],
                            option_c=item.option_c[:500],
                            option_d=item.option_d[:500],
                            correct_option=item.correct_option,
                            explanation=item.explanation,
                        )
                        for item in generated_questions
                    ])

                messages.success(
                    request,
                    "Quiz generated and saved. It has a 10-minute timer.",
                )
                return redirect("quiz_list")

            except Exception:
                logger.exception(
                    "Quiz generation failed for material ID %s",
                    material.id,
                )
                messages.error(
                    request,
                    "Quiz generation failed. Check your Gemini settings and try again.",
                )

    return render(
        request,
        "core/quiz_create.html",
        {
            "materials": materials,
            "difficulty_choices": Quiz.Difficulty.choices,
            "question_counts": sorted(ALLOWED_QUESTION_COUNTS),
        },
    )


"""Starts a quiz. It checks the quiz belongs to the user and has questions, creates a new QuizAttempt (score 0), and redirects to the attempt page. 
started_at is set automatically, which begins the timer."""
@login_required
@require_POST
def quiz_start(request, quiz_id):
    quiz = get_object_or_404(
        Quiz,
        id=quiz_id,
        user=request.user,
    )

    total_questions = QuizQuestion.objects.filter(quiz=quiz).count()

    if total_questions == 0:
        messages.error(request, "This quiz has no questions.")
        return redirect("quiz_list")

    attempt = QuizAttempt.objects.create(
        user=request.user,
        quiz=quiz,
        score=0,
        total_questions=total_questions,
    )

    return redirect("quiz_attempt", attempt_id=attempt.id)

#user takes quize
@login_required
def quiz_attempt(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz", "quiz__material"),
        id=attempt_id,
        user=request.user,
    )

    if attempt.completed_at:
        return redirect("quiz_result", attempt_id=attempt.id)

    questions = QuizQuestion.objects.filter(
        quiz=attempt.quiz
    ).order_by("id")

    deadline = attempt.started_at + timedelta(
        minutes=attempt.quiz.duration_minutes
    )
    remaining_seconds = max(
        0,
        ceil((deadline - timezone.now()).total_seconds()),
    )

    return render(
        request,
        "core/quiz_attempt.html",
        {
            "attempt": attempt,
            "questions": questions,
            "remaining_seconds": remaining_seconds,
        },
    )


@login_required
@require_POST
def quiz_submit(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz"),
        id=attempt_id,
        user=request.user,
    )

    if attempt.completed_at:
        return redirect("quiz_result", attempt_id=attempt.id)

    questions = list(
        QuizQuestion.objects.filter(quiz=attempt.quiz).order_by("id")
    )

    deadline = attempt.started_at + timedelta(
        minutes=attempt.quiz.duration_minutes
    )
    too_late = timezone.now() > deadline + timedelta(
        seconds=TIMER_GRACE_SECONDS
    )

    score = 0
    answers_to_save = []

    if not too_late:
        for question in questions:
            selected_option = request.POST.get(
                f"question_{question.id}",
                "",
            ).upper()

            if selected_option not in {"A", "B", "C", "D"}:
                continue

            is_correct = selected_option == question.correct_option

            if is_correct:
                score += 1

            answers_to_save.append(
                AttemptAnswer(
                    attempt=attempt,
                    question=question,
                    selected_option=selected_option,
                    is_correct=is_correct,
                )
            )

    with transaction.atomic():
        AttemptAnswer.objects.bulk_create(answers_to_save)

        attempt.score = score
        attempt.total_questions = len(questions)
        attempt.completed_at = timezone.now()
        attempt.save(
            update_fields=[
                "score",
                "total_questions",
                "completed_at",
            ]
        )

    if too_late:
        messages.warning(
            request,
            "Time expired before the answers were submitted. This attempt was scored as zero.",
        )

    return redirect("quiz_result", attempt_id=attempt.id)


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("quiz", "quiz__material"),
        id=attempt_id,
        user=request.user,
    )

    saved_answers = {
        answer.question_id: answer
        for answer in AttemptAnswer.objects.filter(
            attempt=attempt
        ).select_related("question")
    }

    review = []

    for question in QuizQuestion.objects.filter(
        quiz=attempt.quiz
    ).order_by("id"):
        answer = saved_answers.get(question.id)

        option_names = {
            "A": question.option_a,
            "B": question.option_b,
            "C": question.option_c,
            "D": question.option_d,
        }

        review.append({
            "question": question,
            "selected_option": answer.selected_option if answer else "",
            "selected_text": (
                option_names.get(answer.selected_option, "Not answered")
                if answer
                else "Not answered"
            ),
            "correct_option": question.correct_option,
            "correct_text": option_names.get(
                question.correct_option,
                "",
            ),
            "is_correct": answer.is_correct if answer else False,
            "explanation": question.explanation,
        })

    return render(
        request,
        "core/quiz_result.html",
        {
            "attempt": attempt,
            "review": review,
        },
    )



@login_required
@require_POST
def quiz_delete(request, quiz_id):
    quiz = get_object_or_404(
        Quiz,
        id=quiz_id,
        user=request.user,
    )

    quiz.delete()
    messages.success(
        request,
        "Quiz and its saved attempts and scores were deleted.",
    )

    return redirect("quiz_list")