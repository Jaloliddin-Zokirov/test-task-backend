from collections.abc import Iterable
from typing import TypedDict

from .models import Quiz, Student


class ScoreEntry(TypedDict):
    student_id: int
    name: str
    score: int
    total_questions: int


def build_scoreboard(quiz: Quiz) -> list[ScoreEntry]:
    total_questions = quiz.questions.count()
    scoreboard: list[ScoreEntry] = []
    students: Iterable[Student] = quiz.students.prefetch_related("answers")
    for student in students:
        scoreboard.append(
            {
                "student_id": student.id,
                "name": student.name,
                "score": student.score,
                "total_questions": total_questions,
            }
        )
    scoreboard.sort(key=lambda entry: (-entry["score"], entry["name"]))
    return scoreboard
