from __future__ import annotations

from typing import Iterable

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Choice, Question, Quiz, QuizStatus, Student, StudentAnswer
from .selectors import build_scoreboard
from .utils import calculate_percentage


class AnswerPayload(dict):
    question_id: int
    choice_id: int
    latency_ms: int | None


@transaction.atomic
def submit_answers(student: Student, answers: Iterable[AnswerPayload]) -> dict:
    created_answers = []
    for payload in answers:
        question = Question.objects.select_for_update().get(id=payload["question_id"], quiz=student.quiz)
        choice = Choice.objects.get(id=payload["choice_id"], question=question)
        answer, created = StudentAnswer.objects.get_or_create(
            student=student,
            question=question,
            defaults={
                "choice": choice,
                "latency_ms": payload.get("latency_ms") or 0,
                "is_correct": choice.is_correct,
            },
        )
        if not created:
            answer.choice = choice
            answer.latency_ms = payload.get("latency_ms") or 0
            answer.is_correct = choice.is_correct
            answer.save(update_fields=["choice", "latency_ms", "is_correct"])
        created_answers.append(answer)

    score = student.answers.filter(is_correct=True).count()
    total_questions = student.quiz.questions.count()
    percentage = calculate_percentage(score, total_questions)

    # Auto-finish quiz when all students answered
    quiz = student.quiz
    total_answers = StudentAnswer.objects.filter(question__quiz=quiz).count()
    expected_answers = quiz.students.count() * quiz.questions.count()
    if quiz.status == QuizStatus.RUNNING and expected_answers and total_answers >= expected_answers:
        finalize_quiz(quiz)

    return {
        "score": score,
        "total_questions": total_questions,
        "percentage": percentage,
        "answers": [answer.id for answer in created_answers],
    }


def finalize_quiz(quiz: Quiz) -> None:
    if quiz.status == QuizStatus.FINISHED:
        return
    quiz.finish()
    scoreboard = build_scoreboard(quiz)
    send_telegram_summary(quiz, scoreboard)


def send_telegram_summary(quiz: Quiz, scoreboard: list[dict]) -> None:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return

    top_three = scoreboard[:3]
    lines = [f"Quiz '{quiz.title}' finished!", f"Participants: {len(scoreboard)}"]
    if top_three:
        lines.append("Top 3:")
        for index, entry in enumerate(top_three, start=1):
            percentage = calculate_percentage(entry["score"], entry["total_questions"])
            lines.append(f"{index}. {entry['name']} - {entry['score']} correct ({percentage}%)")

    message = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)
    except requests.RequestException:
        # Swallow exceptions to avoid breaking request flow
        pass


def start_quiz(quiz: Quiz) -> Quiz:
    quiz.status = QuizStatus.RUNNING
    quiz.started_at = timezone.now()
    quiz.save(update_fields=["status", "started_at", "updated_at"])
    return quiz
