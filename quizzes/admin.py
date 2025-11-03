from django.contrib import admin

from .models import Choice, Question, Quiz, Student, StudentAnswer


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "room_code", "status", "created_by", "created_at")
    search_fields = ("title", "room_code", "created_by__full_name")
    list_filter = ("status", "created_at")
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("quiz", "order", "text")
    search_fields = ("text", "quiz__title")
    inlines = [ChoiceInline]


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("question", "text", "is_correct")
    list_filter = ("is_correct",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "quiz", "joined_at")
    search_fields = ("name", "quiz__room_code")


@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ("student", "question", "choice", "is_correct", "answered_at")
    list_filter = ("is_correct", "answered_at")
