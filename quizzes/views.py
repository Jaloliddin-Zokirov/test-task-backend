from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Quiz, QuizStatus, Student
from .serializers import (
    QuizCreateSerializer,
    QuizSerializer,
    QuizStartSerializer,
    QuizStatusSerializer,
    QuizResultsSerializer,
    StudentJoinSerializer,
    StudentResultSerializer,
    StudentSerializer,
    SubmitAnswersSerializer,
    serialize_scoreboard,
)
from .services import finalize_quiz, start_quiz, submit_answers
from .selectors import build_scoreboard
from .utils import calculate_percentage


def _broadcast(room_code: str, event: str, payload: dict):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"quiz_{room_code}",
        {
            "type": "quiz.event",
            "event": event,
            "payload": payload,
        },
    )


def _time_remaining(quiz: Quiz) -> int:
    if not quiz.started_at:
        return quiz.duration_seconds
    elapsed = timezone.now() - quiz.started_at
    remaining = quiz.duration_seconds - int(elapsed.total_seconds())
    return max(0, remaining)


class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quiz = serializer.save()
        output = QuizSerializer(quiz, context={"request": request})
        headers = self.get_success_headers(output.data)
        _broadcast(quiz.room_code, "quiz_created", output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Quiz.objects.none()
        return Quiz.objects.filter(created_by=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return QuizCreateSerializer
        return super().get_serializer_class()

    @action(detail=True, methods=["post"], url_path="start")
    def start(self, request, pk=None):
        quiz = self.get_object()
        if quiz.status == QuizStatus.RUNNING:
            return Response({"detail": "Quiz already running"}, status=status.HTTP_400_BAD_REQUEST)
        if not quiz.questions.exists():
            return Response({"detail": "Quiz has no questions yet"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = QuizStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update_quiz(quiz)
        start_quiz(quiz)

        payload = {
            "quiz": QuizStatusSerializer(quiz, context={"request": request}).data,
            "time_remaining": _time_remaining(quiz),
        }
        _broadcast(quiz.room_code, "quiz_started", payload)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="finish")
    def finish(self, request, pk=None):
        quiz = self.get_object()
        finalize_quiz(quiz)
        payload = {
            "quiz": QuizStatusSerializer(quiz, context={"request": request}).data,
            "scoreboard": serialize_scoreboard(quiz),
        }
        _broadcast(quiz.room_code, "quiz_finished", payload)
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="status")
    def status_view(self, request, pk=None):
        quiz = self.get_object()
        payload = {
            "quiz": QuizStatusSerializer(quiz, context={"request": request}).data,
            "time_remaining": _time_remaining(quiz),
            "scoreboard": serialize_scoreboard(quiz),
        }
        return Response(payload)

    @action(detail=True, methods=["get"], url_path="results")
    def results(self, request, pk=None):
        quiz = self.get_object()
        scoreboard = serialize_scoreboard(quiz)
        serializer = QuizResultsSerializer(
            {
                "quiz": QuizStatusSerializer(quiz, context={"request": request}).data,
                "scoreboard": scoreboard,
            }
        )
        return Response(serializer.data)


class QuizByCodeView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, room_code: str):
        quiz = get_object_or_404(Quiz.objects.prefetch_related("questions__choices"), room_code=room_code.upper())
        data = QuizStatusSerializer(quiz, context={"request": request}).data
        data.update(
            {
                "time_remaining": _time_remaining(quiz),
            }
        )
        return Response(data)


class StudentJoinView(APIView):
    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_description="Join a quiz by providing room code and name",
        request_body=StudentJoinSerializer,
        responses={
            201: "Student joined successfully",
            400: "Bad request - invalid data",
        },
    )
    def post(self, request):
        serializer = StudentJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.save()
        quiz = student.quiz
        payload = {
            "student": {
                "id": student.id,
                "name": student.name,
                "joined_at": student.joined_at.isoformat(),
            },
            "students": StudentSerializer(quiz.students.all(), many=True).data,
            "time_remaining": _time_remaining(quiz),
        }
        _broadcast(quiz.room_code, "student_joined", payload)
        return Response(payload, status=status.HTTP_201_CREATED)


class SubmitAnswersView(APIView):
    permission_classes = (permissions.AllowAny,)

    @swagger_auto_schema(
        operation_description="Submit answers for a student in a quiz",
        request_body=SubmitAnswersSerializer,
        responses={
            200: "Answers submitted successfully",
            400: "Bad request - invalid data or quiz not accepting answers",
        },
    )
    def post(self, request, room_code: str, student_id: int):
        quiz = get_object_or_404(Quiz, room_code=room_code.upper())
        if quiz.status != QuizStatus.RUNNING:
            return Response({"detail": "Quiz is not accepting answers"}, status=status.HTTP_400_BAD_REQUEST)
        student = get_object_or_404(Student, pk=student_id, quiz=quiz)

        serializer = SubmitAnswersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = submit_answers(student, serializer.validated_data["answers"])

        scoreboard = serialize_scoreboard(quiz)
        _broadcast(
            quiz.room_code,
            "scoreboard_updated",
            {
                "scoreboard": scoreboard,
                "student_id": student.id,
            },
        )

        rank = next((index + 1 for index, entry in enumerate(scoreboard) if entry["student_id"] == student.id), None)
        result_payload = {
            "name": student.name,
            "score": result["score"],
            "total_questions": result["total_questions"],
            "percentage": result["percentage"],
            "rank": rank,
            "time_remaining": _time_remaining(quiz),
        }

        if quiz.status == QuizStatus.FINISHED:
            _broadcast(
                quiz.room_code,
                "quiz_finished",
                {
                    "quiz": QuizStatusSerializer(quiz, context={"request": request}).data,
                    "scoreboard": scoreboard,
                },
            )

        return Response(result_payload, status=status.HTTP_200_OK)


class StudentResultsView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request, room_code: str, student_id: int):
        quiz = get_object_or_404(Quiz, room_code=room_code.upper())
        if quiz.status != QuizStatus.FINISHED:
            return Response({"detail": "Quiz is not finished yet"}, status=status.HTTP_400_BAD_REQUEST)
        student = get_object_or_404(Student, pk=student_id, quiz=quiz)

        scoreboard = build_scoreboard(quiz)
        student_entry = next((entry for entry in scoreboard if entry["student_id"] == student.id), None)
        if not student_entry:
            return Response({"detail": "Student not found in scoreboard"}, status=status.HTTP_404_NOT_FOUND)

        winner_entry = scoreboard[0] if scoreboard else None

        data = {
            "student": {
                "name": student_entry["name"],
                "score": student_entry["score"],
                "total_questions": student_entry["total_questions"],
                "percentage": calculate_percentage(student_entry["score"], student_entry["total_questions"]),
                "rank": next((index + 1 for index, entry in enumerate(scoreboard) if entry["student_id"] == student.id), None),
            },
            "winner": {
                "name": winner_entry["name"],
                "score": winner_entry["score"],
                "total_questions": winner_entry["total_questions"],
                "percentage": calculate_percentage(winner_entry["score"], winner_entry["total_questions"]),
            } if winner_entry else None,
        }
        return Response(data)


class LeaderboardView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, pk: int):
        quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
        scoreboard = build_scoreboard(quiz)
        data = []
        for index, entry in enumerate(scoreboard, start=1):
            percentage = calculate_percentage(entry["score"], entry["total_questions"])
            data.append(
                {
                    "rank": index,
                    "name": entry["name"],
                    "score": entry["score"],
                    "total_questions": entry["total_questions"],
                    "percentage": percentage,
                }
            )
        serializer = StudentResultSerializer(data, many=True)
        return Response(serializer.data)
