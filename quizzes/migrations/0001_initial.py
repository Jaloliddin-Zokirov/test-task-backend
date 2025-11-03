# Generated manually for quiz models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import quizzes.utils


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Quiz",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("room_code", models.CharField(default=quizzes.utils.generate_room_code, max_length=8, unique=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("waiting", "Waiting"), ("running", "Running"), ("finished", "Finished")], default="draft", max_length=32)),
                ("duration_seconds", models.PositiveIntegerField(default=60)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(blank=True, null=True)),
                (
                    "created_by",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quizzes", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.TextField()),
                ("order", models.PositiveIntegerField(default=0)),
                ("time_limit", models.PositiveIntegerField(blank=True, help_text="Optional per-question time limit in seconds", null=True)),
                (
                    "quiz",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="questions", to="quizzes.quiz"),
                ),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="Student",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "quiz",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="students", to="quizzes.quiz"),
                ),
            ],
            options={"ordering": ["joined_at"], "unique_together": {("quiz", "name")}},
        ),
        migrations.CreateModel(
            name="Choice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text", models.CharField(max_length=255)),
                ("is_correct", models.BooleanField(default=False)),
                (
                    "question",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="choices", to="quizzes.question"),
                ),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.CreateModel(
            name="StudentAnswer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_correct", models.BooleanField(default=False)),
                ("answered_at", models.DateTimeField(auto_now_add=True)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                (
                    "choice",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chosen_answers", to="quizzes.choice"),
                ),
                (
                    "question",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="quizzes.question"),
                ),
                (
                    "student",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="answers", to="quizzes.student"),
                ),
            ],
            options={"ordering": ["answered_at"], "unique_together": {("student", "question")}},
        ),
    ]
