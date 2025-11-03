from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

from .utils import generate_room_code


class QuizStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    WAITING = "waiting", "Waiting"
    RUNNING = "running", "Running"
    FINISHED = "finished", "Finished"


class Quiz(models.Model):
    title = models.CharField(max_length=255)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quizzes")
    room_code = models.CharField(max_length=8, unique=True, default=generate_room_code)
    status = models.CharField(max_length=32, choices=QuizStatus.choices, default=QuizStatus.DRAFT)
    duration_seconds = models.PositiveIntegerField(default=60)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.room_code})"

    @property
    def is_running(self) -> bool:
        return self.status == QuizStatus.RUNNING

    def start(self):
        self.status = QuizStatus.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def finish(self):
        self.status = QuizStatus.FINISHED
        self.ended_at = timezone.now()
        self.save(update_fields=["status", "ended_at", "updated_at"])


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    time_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Optional per-question time limit in seconds")

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.text


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.text


class Student(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="students")
    name = models.CharField(max_length=255)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["joined_at"]
        unique_together = ("quiz", "name")

    def __str__(self) -> str:
        return f"{self.name} - {self.quiz.room_code}"

    @property
    def score(self) -> int:
        return self.answers.filter(is_correct=True).count()


class StudentAnswer(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE, related_name="chosen_answers")
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)
    latency_ms = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("student", "question")
        ordering = ["answered_at"]

    def save(self, *args, **kwargs):
        self.is_correct = self.choice.is_correct
        super().save(*args, **kwargs)
