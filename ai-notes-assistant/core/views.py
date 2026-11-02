from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404,HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import StudyMaterialForm
from .models import StudyMaterial,Summary,ChatHistory
import logging
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from django.utils.text import slugify #name downloaded file
from .summary_service import generate_summary
from .text_extraction import (
    NoTextExtractedError,
    extract_text_from_material,
)
from django.urls import reverse
from .chat_service import answer_question


logger = logging.getLogger(__name__)
# Content type for each supported file extension
CONTENT_TYPES = {
    "pdf": "application/pdf",
    "txt": "text/plain; charset=utf-8",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def home(request):
    return render(request, "core/home.html")


@login_required
def dashboard(request):
    return render(request, "core/dashboard.html")


# UPLOAD PDF 
@login_required
def material_list(request):
    materials = StudyMaterial.objects.filter(
        user=request.user
    ).order_by("-uploaded_at")

    return render(
        request,
        "core/material_list.html",
        {
            "materials": materials,
            "summary_types": Summary.SummaryType.choices,
        },
    )

@login_required
def material_upload(request):
    if request.method == "POST":
        form = StudyMaterialForm(request.POST, request.FILES)

        if form.is_valid():
            material = form.save(commit=False)
            material.user = request.user
            material.file_type = (
                material.file_path.name.rsplit(".", 1)[-1].upper()
            )
            material.status = "pending"
            material.save()

            try:
                material.extracted_text = extract_text_from_material(material)
                material.status = "processed"
                material.save(update_fields=["extracted_text", "status"])

                messages.success(request, "File uploaded and text extracted.")

            except NoTextExtractedError as error:
                material.status = "failed"
                material.save(update_fields=["status"])
                messages.warning(request, str(error))

            except Exception:
                logger.exception(
                    "Text extraction failed for study material ID %s",
                    material.id,
                )
                material.status = "failed"
                material.save(update_fields=["status"])
                messages.error(
                    request,
                    "The file was uploaded, but its text could not be extracted.",
                )

            return redirect("material_list")

    else:
        form = StudyMaterialForm()

    return render(
        request,
        "core/material_upload.html",
        {"form": form},
    )

@login_required
def material_open(request, material_id):
    material = get_object_or_404(StudyMaterial, id=material_id)

    if material.user_id != request.user.id: #if user not authenticated
        raise PermissionDenied

    try:
        file = material.file_path.open("rb")
    except (FileNotFoundError, ValueError):
        raise Http404("The file could not be found.")

    extension = material.file_path.name.rsplit(".", 1)[-1].lower()

    return FileResponse(
        file,
        content_type=CONTENT_TYPES.get(extension, "application/octet-stream"),
        as_attachment=(extension == "docx"),  # browsers can't display Word files, so download them
        filename=material.file_path.name.rsplit("/", 1)[-1],
    )


@login_required
@require_POST
def material_delete(request, material_id):
    material = get_object_or_404(
        StudyMaterial,
        id=material_id,
        user=request.user,
    )

    # Delete the stored PDF and database record.
    material.file_path.delete(save=False)
    material.delete()

    return redirect("material_list")


#SUMMARY
@login_required
def summary_list(request):
    summaries = (
        Summary.objects
        .filter(material__user=request.user)
        .select_related("material")
        .order_by("material__title", "-generated_at")
    )

    search_query = request.GET.get("q", "").strip()
    selected_type = request.GET.get("type", "").strip()

    if search_query:
        summaries = summaries.filter(
            Q(material__title__icontains=search_query)
            | Q(summary_text__icontains=search_query)
        )

    valid_types = {
        value for value, label in Summary.SummaryType.choices
    }

    if selected_type in valid_types:
        summaries = summaries.filter(summary_type=selected_type)
    else:
        selected_type = ""

    return render(
        request,
        "core/summary_list.html",
        {
            "summaries": summaries,
            "search_query": search_query,
            "selected_type": selected_type,
            "summary_types": Summary.SummaryType.choices,
        },
    )


@login_required
@require_POST
def summary_generate(request, material_id):
    material = get_object_or_404(
        StudyMaterial,
        id=material_id,
        user=request.user,
    )

    summary_type = request.POST.get("summary_type", "")
    valid_types = {
        value for value, label in Summary.SummaryType.choices
    }

    if summary_type not in valid_types:
        messages.error(request, "Choose a valid summary type.")
        return redirect("material_list")

    if not material.extracted_text.strip():
        messages.error(
            request,
            "This material has no extracted text. Upload or process it again first.",
        )
        return redirect("material_list")

    # Limit very large inputs for this first version.
    source_text = material.extracted_text[:60000]

    try:
        generated_text = generate_summary(
            source_text=source_text,
            topic=material.title,
            summary_type=summary_type,
        )

        Summary.objects.create(
            material=material,
            summary_type=summary_type,
            summary_text=generated_text,
            key_concepts="",
            key_points=(
                generated_text if summary_type == "key_points" else ""
            ),
        )

        messages.success(request, "Your summary has been generated and saved.")

    except Exception:
        logger.exception(
            "Summary generation failed for study material ID %s",
            material.id,
        )
        messages.error(
            request,
            "Summary generation failed. Check your Gemini API key and try again.",
        )

    return redirect("summary_list")


@login_required
def summary_download(request, summary_id):
    summary = get_object_or_404(
        Summary.objects.select_related("material"),
        id=summary_id,
        material__user=request.user,
    )

    from html import escape
    from io import BytesIO

    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    pdf_buffer = BytesIO()
    styles = getSampleStyleSheet()

    document = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"{summary.material.title} - {summary.get_summary_type_display()}",
    )

    content = [
        Paragraph(escape(summary.material.title), styles["Title"]),
        Spacer(1, 12),
        Paragraph(escape(summary.get_summary_type_display()), styles["Heading2"]),
        Spacer(1, 12),
    ]

    for line in summary.summary_text.splitlines():
        safe_line = escape(line.strip())
        if safe_line:
            content.append(Paragraph(safe_line, styles["BodyText"]))
            content.append(Spacer(1, 6))

    document.build(content)

    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )

    safe_topic = slugify(summary.material.title) or "study-summary"
    safe_type = slugify(summary.summary_type)
    response["Content-Disposition"] = (
        f'attachment; filename="{safe_topic}-{safe_type}.pdf"'
    )

    return response

#CHAT BOT
@login_required
def chat_page(request):
    materials = (
        StudyMaterial.objects
        .filter(user=request.user, status="processed")
        .exclude(extracted_text="")
        .order_by("title")
    )

    selected_material = None
    selected_material_id = request.POST.get(
        "material_id",
        request.GET.get("material_id", ""),
    )

    if selected_material_id:
        selected_material = get_object_or_404(
            StudyMaterial,
            id=selected_material_id,
            user=request.user,
            status="processed",
        )

    if request.method == "POST":
        question = request.POST.get("question", "").strip()

        if not selected_material:
            messages.error(request, "Select a study material first.")
        elif not question:
            messages.error(request, "Enter a question.")
        elif len(question) > 2000:
            messages.error(request, "Keep your question under 2,000 characters.")
        elif not selected_material.extracted_text.strip():
            messages.error(
                request,
                "This material does not have extracted text to chat about.",
            )
        else:
            # Include recent exchanges so follow-up questions have context.
            previous_messages = list(
                ChatHistory.objects
                .filter(
                    user=request.user,
                    material=selected_material,
                )
                .order_by("-asked_at")[:6]
            )
            previous_messages.reverse()

            try:
                answer = answer_question(
                    material_text=selected_material.extracted_text[:60000],
                    topic=selected_material.title,
                    question=question,
                    previous_messages=previous_messages,
                )

                ChatHistory.objects.create(
                    user=request.user,
                    material=selected_material,
                    question=question,
                    answer=answer,
                )

                messages.success(request, "Your answer is ready.")

            except Exception:
                logger.exception(
                    "Chat answer generation failed for material ID %s",
                    selected_material.id,
                )
                messages.error(
                    request,
                    "I couldn’t generate an answer. Check your Gemini settings and try again.",
                )

        if selected_material:
            chat_url = reverse("chat_page")
            return redirect(f"{chat_url}?material_id={selected_material.id}")

    chat_history = []

    if selected_material:
        chat_history = (
            ChatHistory.objects
            .filter(
                user=request.user,
                material=selected_material,
            )
            .order_by("asked_at")
        )

    return render(
        request,
        "core/chat.html",
        {
            "materials": materials,
            "selected_material": selected_material,
            "chat_history": chat_history,
        },
    )