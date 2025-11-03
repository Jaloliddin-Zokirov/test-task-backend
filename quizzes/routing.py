from django.urls import path

from .consumers import QuizConsumer

websocket_urlpatterns = [
    path("ws/quizzes/<str:room_code>/", QuizConsumer.as_asgi()),
]
