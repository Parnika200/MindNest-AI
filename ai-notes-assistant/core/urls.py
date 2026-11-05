from django.urls import path
from . import quiz_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),

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
]