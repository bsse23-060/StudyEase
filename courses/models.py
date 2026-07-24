from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

class Course(models.Model):
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="taught_courses")
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="archived_courses")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self): return self.title

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    position = models.PositiveIntegerField()
    class Meta:
        ordering = ("position",)
        constraints = [models.UniqueConstraint(fields=("course", "position"), name="unique_module_position")]

class Lesson(models.Model):
    class Kind(models.TextChoices):
        TEXT = "text", "Text"
        VIDEO = "video", "Video"
        QUIZ = "quiz", "Quiz"
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=255)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.TEXT)
    content = models.TextField(blank=True)
    resource_url = models.URLField(blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=20)
    position = models.PositiveIntegerField()
    class Meta:
        ordering = ("position",)
        constraints = [models.UniqueConstraint(fields=("module", "position"), name="unique_lesson_position")]

class Concept(models.Model):
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.CASCADE, related_name="concepts")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="authored_concepts")
    lessons = models.ManyToManyField(Lesson, related_name="concepts", blank=True)
    prerequisites = models.ManyToManyField("self", symmetrical=False, related_name="unlocks", blank=True)
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

class Quiz(models.Model):
    lesson = models.OneToOneField(Lesson, on_delete=models.CASCADE, related_name="quiz")
    title = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    pass_mark = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    maximum_attempts = models.PositiveSmallIntegerField(null=True, blank=True)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    time_limit_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return self.title

class QuizQuestion(models.Model):
    quiz = models.ForeignKey(Quiz, null=True, blank=True, on_delete=models.CASCADE, related_name="questions")
    class Kind(models.TextChoices):
        MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
        TRUE_FALSE = "true_false", "True/false"
        SHORT_ANSWER = "short_answer", "Short answer"
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="questions")
    concept = models.ForeignKey(Concept, null=True, on_delete=models.SET_NULL, related_name="questions")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    prompt = models.TextField()
    options = models.JSONField(default=list, blank=True)
    correct_answer = models.JSONField()
    explanation = models.TextField(blank=True)
    difficulty = models.FloatField(default=.5, validators=[MinValueValidator(0), MaxValueValidator(1)])
    points = models.PositiveSmallIntegerField(default=1)
    position = models.PositiveIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    class Meta:
        ordering = ("position", "id")
        constraints = [models.UniqueConstraint(fields=("quiz", "position"), condition=models.Q(quiz__isnull=False), name="unique_quiz_question_position")]

class QuizAnswerOption(models.Model):
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE, related_name="answer_options")
    text = models.CharField(max_length=1000)
    position = models.PositiveIntegerField()
    is_correct = models.BooleanField(default=False)
    class Meta:
        ordering = ("position",)
        constraints = [models.UniqueConstraint(fields=("question", "position"), name="unique_question_option_position")]
