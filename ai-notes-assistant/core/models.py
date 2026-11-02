from django.conf import settings
from django.db import models
from django.core.validators import FileExtensionValidator

class StudyMaterial(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="study_materials",
    )
    title = models.CharField(max_length=255)
    file_path = models.FileField(
        upload_to="study_materials/",
        validators=[FileExtensionValidator(["pdf", "docx", "txt"])],
    )
    file_type = models.CharField(max_length=20, default="PDF")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="pending")
    extracted_text = models.TextField(blank=True)

    def __str__(self):
        return self.title

class Summary(models.Model):
    class SummaryType(models.TextChoices):
        SHORT = "short", "Short summary"
        LONG = "long", "Long summary"

    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="summaries",
    )
    summary_type = models.CharField(
        max_length=20,
        choices=SummaryType.choices,
        default=SummaryType.SHORT,
    )
    summary_text = models.TextField()
    key_concepts = models.JSONField(default=list, blank=True)
    key_points = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["material", "summary_type"],
                name="one_summary_per_type_per_material",
            )
        ]

    def __str__(self):
        return f"{self.get_summary_type_display()} for {self.material.title}"

class Summary(models.Model):
    class SummaryType(models.TextChoices):
        SHORT = "short", "Short summary"
        LONG = "long", "Long summary"

    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="summaries",
    )
    summary_type = models.CharField(
        max_length=20,
        choices=SummaryType.choices,
        default=SummaryType.SHORT,
    )
    summary_text = models.TextField()
    key_concepts = models.JSONField(default=list, blank=True)
    key_points = models.JSONField(default=list, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["material", "summary_type"],
                name="one_summary_per_type_per_material",
            )
        ]

    def __str__(self):
        return f"{self.get_summary_type_display()} for {self.material.title}"
class ChatHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_history",
    )
    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="chat_history",
    )
    question = models.TextField()
    answer = models.TextField()
    asked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-asked_at"]
        verbose_name_plural = "chat history"

    def __str__(self):
        return f"Question about {self.material.title}"


class Quiz(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="quizzes",
    )
    title = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class QuizQuestion(models.Model):
    class Option(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"

    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="questions",
    )
    question_text = models.TextField()
    option_a = models.CharField(max_length=500)
    option_b = models.CharField(max_length=500)
    option_c = models.CharField(max_length=500)
    option_d = models.CharField(max_length=500)
    correct_option = models.CharField(
        max_length=1,
        choices=Option.choices,
    )
    explanation = models.TextField(blank=True)

    def __str__(self):
        return f"Question {self.pk} for {self.quiz.title}"


class QuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
    )
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name="attempts",
    )
    score = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    @property
    def percentage(self):
        if self.total_questions == 0:
            return 0
        return round(self.score * 100 / self.total_questions)

    def __str__(self):
        return f"Attempt for {self.quiz.title} by {self.user}"


class AttemptAnswer(models.Model):
    class Option(models.TextChoices):
        A = "A", "A"
        B = "B", "B"
        C = "C", "C"
        D = "D", "D"

    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
    )
    question = models.ForeignKey(
        QuizQuestion,
        on_delete=models.CASCADE,
        related_name="attempt_answers",
    )
    selected_option = models.CharField(
        max_length=1,
        choices=Option.choices,
    )
    is_correct = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "question"],
                name="unique_question_answer_per_attempt",
            )
        ]

    def __str__(self):
        return f"Answer to question {self.question_id}"


class Flashcard(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="flashcards",
    )
    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="flashcards",
    )
    question = models.TextField()
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Flashcard for {self.material.title}"


class RevisionProgress(models.Model):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="revision_progress",
    )
    material = models.ForeignKey(
        StudyMaterial,
        on_delete=models.CASCADE,
        related_name="revision_progress",
    )
    last_revised_at = models.DateTimeField(null=True, blank=True)
    revision_count = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NOT_STARTED,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "material"],
                name="one_revision_progress_per_user_material",
            )
        ]

    def __str__(self):
        return f"Revision progress: {self.user} / {self.material.title}"