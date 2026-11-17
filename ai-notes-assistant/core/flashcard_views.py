import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .flashcard_service import generate_flashcards
from .models import Flashcard, RevisionProgress, StudyMaterial


logger = logging.getLogger(__name__)

ALLOWED_CARD_COUNTS = {5, 10}


@login_required
def flashcard_list(request):
    materials = (
        StudyMaterial.objects
        .filter(user=request.user, status="processed")
        .exclude(extracted_text="")
        .order_by("title")
    )

    material_id = request.GET.get("material_id", "")
    selected_material = None
    cards = []
    progress = None
    all_reviewed = False
    reviewed_count = 0

    if material_id:
        selected_material = get_object_or_404(
            StudyMaterial,
            id=material_id,
            user=request.user,
            status="processed",
        )

        cards = list(
            Flashcard.objects
            .filter(
                user=request.user,
                material=selected_material,
            )
            .order_by("created_at", "id")
        )

        progress = RevisionProgress.objects.filter(
            user=request.user,
            material=selected_material,
        ).first()

        reviewed_count = sum(card.is_reviewed for card in cards)
        all_reviewed = bool(cards) and reviewed_count == len(cards)

    return render(
        request,
        "core/flashcard_list.html",
        {
            "materials": materials,
            "selected_material": selected_material,
            "cards": cards,
            "progress": progress,
            "all_reviewed": all_reviewed,
            "reviewed_count": reviewed_count,
            "card_counts": sorted(ALLOWED_CARD_COUNTS),
        },
    )


@login_required
@require_POST
def flashcard_generate(request):
    material_id = request.POST.get("material_id", "")
    number_value = request.POST.get("number_of_cards", "5")

    material = get_object_or_404(
        StudyMaterial,
        id=material_id,
        user=request.user,
        status="processed",
    )

    try:
        number_of_cards = int(number_value)
    except (TypeError, ValueError):
        number_of_cards = 0

    if number_of_cards not in ALLOWED_CARD_COUNTS:
        messages.error(request, "Choose either 5 or 10 flashcards.")
        return redirect(f"/flashcards/?material_id={material.id}")

    if not material.extracted_text.strip():
        messages.error(
            request,
            "This material does not have extracted text.",
        )
        return redirect(f"/flashcards/?material_id={material.id}")

    source_text = material.extracted_text[:60000]

    try:
        generated_cards = generate_flashcards(
            material_text=source_text,
            topic=material.title,
            number_of_cards=number_of_cards,
        )

        with transaction.atomic():
            Flashcard.objects.bulk_create([
                Flashcard(
                    user=request.user,
                    material=material,
                    question=card.question,
                    answer=card.answer,
                )
                for card in generated_cards
            ])

            progress, _ = RevisionProgress.objects.get_or_create(
                user=request.user,
                material=material,
                defaults={
                    "revision_count": 0,
                    "status": RevisionProgress.Status.NOT_STARTED,
                },
            )

            # New cards begin a new review cycle.
            progress.status = RevisionProgress.Status.NOT_STARTED
            progress.save(update_fields=["status"])

        messages.success(
            request,
            f"{number_of_cards} flashcards were generated and saved.",
        )

    except Exception:
        logger.exception(
            "Flashcard generation failed for material ID %s",
            material.id,
        )
        messages.error(
            request,
            "Flashcard generation failed. Check your Gemini settings and try again.",
        )

    return redirect(f"/flashcards/?material_id={material.id}")


@login_required
@require_POST
def flashcard_mark_reviewed(request, card_id):
    card = get_object_or_404(
        Flashcard.objects.select_related("material"),
        id=card_id,
        user=request.user,
    )

    if not card.is_reviewed:
        card.is_reviewed = True
        card.save(update_fields=["is_reviewed"])

    progress, _ = RevisionProgress.objects.get_or_create(
        user=request.user,
        material=card.material,
        defaults={
            "revision_count": 0,
            "status": RevisionProgress.Status.IN_PROGRESS,
        },
    )

    if progress.status != RevisionProgress.Status.COMPLETED:
        progress.status = RevisionProgress.Status.IN_PROGRESS
        progress.save(update_fields=["status"])

    messages.success(request, "Card marked as reviewed.")
    return redirect(f"/flashcards/?material_id={card.material_id}")


@login_required
@require_POST
def revision_finish(request, material_id):
    material = get_object_or_404(
        StudyMaterial,
        id=material_id,
        user=request.user,
    )

    cards = Flashcard.objects.filter(
        user=request.user,
        material=material,
    )

    if not cards.exists():
        messages.error(request, "Generate flashcards before finishing a review.")
        return redirect(f"/flashcards/?material_id={material.id}")

    if cards.filter(is_reviewed=False).exists():
        messages.error(
            request,
            "Mark every flashcard as reviewed before finishing this session.",
        )
        return redirect(f"/flashcards/?material_id={material.id}")

    with transaction.atomic():
        progress, _ = RevisionProgress.objects.get_or_create(
            user=request.user,
            material=material,
            defaults={
                "revision_count": 0,
                "status": RevisionProgress.Status.NOT_STARTED,
            },
        )

        progress.revision_count = F("revision_count") + 1
        progress.last_revised_at = timezone.now()
        progress.status = RevisionProgress.Status.COMPLETED
        progress.save(
            update_fields=[
                "revision_count",
                "last_revised_at",
                "status",
            ]
        )
        progress.refresh_from_db()

        # Clear the card flags so the student can review this material again.
        cards.update(is_reviewed=False)

    messages.success(
        request,
        f"Review complete. You have revised this material "
        f"{progress.revision_count} time(s).",
    )
    return redirect(f"/flashcards/?material_id={material.id}")