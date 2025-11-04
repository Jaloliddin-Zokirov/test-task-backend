from __future__ import annotations

from typing import Any

from django.db import transaction
from rest_framework import serializers

from accounts.serializers import UserSerializer
from .models import Choice, Question, Quiz, QuizStatus, Student
from .selectors import build_scoreboard
from .utils import calculate_percentage


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("id", "text", "is_correct")
        read_only_fields = ("id",)


class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ("id", "text", "order", "time_limit", "choices")
        read_only_fields = ("id",)


class QuestionCreateSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True)

    class Meta:
        model = Question
        fields = ("text", "order", "time_limit", "choices")

    def validate_choices(self, value):
        if not (2 <= len(value) <= 4):
            raise serializers.ValidationError("Each question must have between 2 and 4 choices")
        if sum(1 for choice in value if choice.get("is_correct")) == 0:
            raise serializers.ValidationError("At least one choice must be marked as correct")
        return value


class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = Quiz
        fields = (
            "id",
            "title",
            "room_code",
            "status",
            "duration_seconds",
            "created_by",
            "created_at",
            "updated_at",
            "started_at",
            "ended_at",
            "questions",
        )
        read_only_fields = ("room_code", "status", "created_at", "updated_at", "started_at", "ended_at")


class QuizCreateSerializer(serializers.ModelSerializer):
    questions = QuestionCreateSerializer(many=True)

    class Meta:
        model = Quiz
        fields = ("id", "title", "duration_seconds", "questions")
        read_only_fields = ("id",)

    def validate_questions(self, value):
        if not value:
            raise serializers.ValidationError("Provide at least one question")
        return value

    def create(self, validated_data):
        questions_data = validated_data.pop("questions", [])
        user = self.context["request"].user
        with transaction.atomic():
            quiz = Quiz.objects.create(created_by=user, **validated_data)
            for index, question_data in enumerate(questions_data):
                choices = question_data.pop("choices", [])
                question = Question.objects.create(quiz=quiz, **question_data)
                choices_to_create = [Choice(question=question, **choice_data) for choice_data in choices]
                Choice.objects.bulk_create(choices_to_create)
        quiz.refresh_from_db()
        return quiz


class QuizStartSerializer(serializers.Serializer):
    duration_seconds = serializers.IntegerField(required=False, min_value=10)

    def update_quiz(self, quiz: Quiz) -> Quiz:
        duration = self.validated_data.get("duration_seconds")
        if duration:
            quiz.duration_seconds = duration
            quiz.save(update_fields=["duration_seconds", "updated_at"])
        return quiz


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ("id", "name", "joined_at")
        read_only_fields = ("id", "joined_at")


class StudentJoinSerializer(serializers.Serializer):
    room_code = serializers.CharField(max_length=8)
    name = serializers.CharField(max_length=255)

    def validate(self, attrs):
        room_code = attrs["room_code"].upper()
        attrs["room_code"] = room_code
        try:
            quiz = Quiz.objects.get(room_code=room_code)
        except Quiz.DoesNotExist as exc:  # pragma: no cover - runtime validation
            raise serializers.ValidationError({"room_code": "Invalid room code"}) from exc

        if quiz.status == QuizStatus.FINISHED:
            raise serializers.ValidationError({"room_code": "Quiz already finished"})

        attrs["quiz"] = quiz
        return attrs

    def create(self, validated_data):
        quiz: Quiz = validated_data["quiz"]
        name: str = validated_data["name"].strip()
        student, _ = Student.objects.get_or_create(quiz=quiz, name=name)
        return student


class AnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    choice_id = serializers.IntegerField()
    latency_ms = serializers.IntegerField(required=False, min_value=0)


class SubmitAnswersSerializer(serializers.Serializer):
    answers = AnswerSerializer(many=True)


class QuizStatusSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)
    students = StudentSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = (
            "id",
            "title",
            "room_code",
            "status",
            "duration_seconds",
            "started_at",
            "ended_at",
            "questions",
            "students",
        )


class ScoreboardEntrySerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    rank = serializers.IntegerField()
    name = serializers.CharField()
    score = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    percentage = serializers.SerializerMethodField()

    def get_percentage(self, obj):
        return calculate_percentage(obj["score"], obj["total_questions"])


class QuizResultsSerializer(serializers.Serializer):
    quiz = QuizStatusSerializer()
    scoreboard = ScoreboardEntrySerializer(many=True)


class StudentResultSerializer(serializers.Serializer):
    name = serializers.CharField()
    score = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    percentage = serializers.FloatField()
    rank = serializers.IntegerField()


def serialize_scoreboard(quiz: Quiz) -> list[dict[str, Any]]:
    scoreboard = build_scoreboard(quiz)
    for index, entry in enumerate(scoreboard, start=1):
        entry["rank"] = index
        entry["percentage"] = calculate_percentage(entry["score"], entry["total_questions"])
    return scoreboard
