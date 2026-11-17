from django.urls import path
from . import quiz_views
from . import views
from . import flashcard_views
from . import dashboard_views
from . import resume_views

urlpatterns = [
    path("", views.home, name="home"),
    path(
    "dashboard/",
    dashboard_views.dashboard,
    name="dashboard",
),

    #upload PDF
    path("materials/", views.material_list, name="material_list"),
    path("materials/upload/", views.material_upload, name="material_upload"),
    path(
        "materials/<int:material_id>/open/",
        views.material_open,
        name="material_open",
    ),
    path(
        "materials/<int:material_id>/delete/",
        views.material_delete,
        name="material_delete",
    ),

    #SUMMARY
    path("summaries/", views.summary_list, name="summary_list"),
path(
    "materials/<int:material_id>/summaries/generate/",
    views.summary_generate,
    name="summary_generate",
),
path(
    "summaries/<int:summary_id>/download/",
    views.summary_download,
    name="summary_download",
),

#chatbot
path("chat/", views.chat_page, name="chat_page"),

#quize
path("quizzes/", quiz_views.quiz_list, name="quiz_list"),
path("quizzes/create/", quiz_views.quiz_create, name="quiz_create"),
path(
    "quizzes/<int:quiz_id>/start/",
    quiz_views.quiz_start,
    name="quiz_start",
),
path(
    "quiz-attempts/<int:attempt_id>/",
    quiz_views.quiz_attempt,
    name="quiz_attempt",
),
path(
    "quiz-attempts/<int:attempt_id>/submit/",
    quiz_views.quiz_submit,
    name="quiz_submit",
),
path(
    "quiz-attempts/<int:attempt_id>/result/",
    quiz_views.quiz_result,
    name="quiz_result",
),
path(
    "quizzes/<int:quiz_id>/delete/",
    quiz_views.quiz_delete,
    name="quiz_delete",
),

#flashcards
path(
    "flashcards/",
    flashcard_views.flashcard_list,
    name="flashcard_list",
),
path(
    "flashcards/generate/",
    flashcard_views.flashcard_generate,
    name="flashcard_generate",
),
path(
    "flashcards/<int:card_id>/review/",
    flashcard_views.flashcard_mark_reviewed,
    name="flashcard_mark_reviewed",
),
path(
    "flashcards/material/<int:material_id>/finish/",
    flashcard_views.revision_finish,
    name="revision_finish",
),

#resume
path(
    "resume/",
    resume_views.resume_builder,
    name="resume_builder",
),
path(
    "resume/download/",
    resume_views.resume_download,
    name="resume_download",
),
path(
    "resume/analyze/",
    resume_views.resume_analyze,
    name="resume_analyze",
),
]