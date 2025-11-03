from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Question, Quiz, QuizStatus


@receiver(post_save, sender=Question)
def ensure_waiting_status(sender, instance: Question, created: bool, **kwargs):
    quiz: Quiz = instance.quiz
    if quiz.status == QuizStatus.DRAFT and quiz.questions.exists():
        Quiz.objects.filter(pk=quiz.pk).update(status=QuizStatus.WAITING)


@receiver(post_delete, sender=Question)
def revert_to_draft_when_empty(sender, instance: Question, **kwargs):
    quiz: Quiz = instance.quiz
    if not quiz.questions.exists():
        Quiz.objects.filter(pk=quiz.pk).update(status=QuizStatus.DRAFT)
