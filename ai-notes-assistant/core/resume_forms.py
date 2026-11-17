from django import forms

from .models import ResumeProfile


class ResumeProfileForm(forms.ModelForm):
    class Meta:
        model = ResumeProfile
        fields = [
        "full_name",
        "email",
        "phone",
        "location",
        "target_role",
        "job_description",
        "professional_summary",
        "education",
        "grades",
        "skills",
        "experience",
        "projects",
        "certifications",
        "linkedin_url",
        "portfolio_url",
         ]

        widgets = {
            "job_description": forms.Textarea(attrs={"rows": 5}),
            "professional_summary": forms.Textarea(attrs={"rows": 4}),
            "education": forms.Textarea(attrs={"rows": 4}),
            "grades": forms.Textarea(attrs={"rows": 3}),
            "skills": forms.Textarea(attrs={"rows": 3}),
            "experience": forms.Textarea(attrs={"rows": 5}),
            "projects": forms.Textarea(attrs={"rows": 5}),
            "certifications": forms.Textarea(attrs={"rows": 3}),
        }

        help_texts = {
            "education": (
                "Enter each qualification on a new line. Include institution "
                "and year, for example: BCA, Example College, 2027."
            ),
            "grades": (
                "Enter grades, GPA, or percentage. You can leave this blank "
                "if it does not apply."
            ),
            "skills": (
                "Enter skills separated by commas or new lines. App-practiced "
                "topics will be added automatically."
            ),
            "experience": (
                "Put each role on a new line. Include your position, "
                "organization, dates, and responsibilities."
            ),
            "projects": (
                "Put each project on a new line. Include its name and what "
                "you built or contributed."
            ),
            "job_description": (
    "Optional. Paste the job description to get a more specific role-fit review."
),
        }