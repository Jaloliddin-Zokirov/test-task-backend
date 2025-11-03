from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    LeaderboardView,
    QuizByCodeView,
    QuizViewSet,
    StudentJoinView,
    SubmitAnswersView,
)

router = DefaultRouter()
router.register(r"", QuizViewSet, basename="quiz")

urlpatterns = [
    path("join/", StudentJoinView.as_view(), name="student-join"),
    path("leaderboard/<int:pk>/", LeaderboardView.as_view(), name="quiz-leaderboard"),
    path("room/<str:room_code>/", QuizByCodeView.as_view(), name="quiz-by-code"),
    path(
        "room/<str:room_code>/students/<int:student_id>/answers/",
        SubmitAnswersView.as_view(),
        name="submit-answers",
    ),
    path("", include(router.urls)),
]
