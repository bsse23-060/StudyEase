from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from courses.models import Concept, Course, Module, Quiz, QuizQuestion

class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        DROPPED = "dropped", "Dropped"
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=("learner", "course"), name="unique_enrollment")]

class LearningProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="learning_profile")
    modality = models.FloatField(default=.5, validators=[MinValueValidator(0), MaxValueValidator(1)])
    depth = models.FloatField(default=.5, validators=[MinValueValidator(0), MaxValueValidator(1)])
    pace = models.FloatField(default=.5, validators=[MinValueValidator(0), MaxValueValidator(1)])
    abstraction = models.FloatField(default=.5, validators=[MinValueValidator(0), MaxValueValidator(1)])
    preferred_time = models.FloatField(default=.5, validators=[MinValueValidator(0), MaxValueValidator(1)])
    updated_at = models.DateTimeField(auto_now=True)

class Mastery(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="masteries")
    concept = models.ForeignKey(Concept, on_delete=models.CASCADE, related_name="masteries")
    probability = models.FloatField(default=.3, validators=[MinValueValidator(0), MaxValueValidator(1)])
    stability_days = models.FloatField(default=1, validators=[MinValueValidator(0)])
    last_seen_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=("learner", "concept"), name="unique_learner_mastery")]

class QuizAttempt(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    question = models.ForeignKey(QuizQuestion, on_delete=models.PROTECT, related_name="attempts")
    answer = models.JSONField()
    is_correct = models.BooleanField(editable=False)
    points_earned = models.PositiveSmallIntegerField(default=0, editable=False)
    seconds_spent = models.PositiveIntegerField(default=0)
    feedback = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class QuizSubmission(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUBMITTED = "submitted", "Submitted"
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_submissions")
    quiz = models.ForeignKey(Quiz, on_delete=models.PROTECT, related_name="submissions")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.STARTED)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    total_score = models.PositiveIntegerField(default=0)
    maximum_score = models.PositiveIntegerField(default=0)
    percentage_score = models.FloatField(null=True, blank=True)
    passed = models.BooleanField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=64, blank=True)
    class Meta:
        ordering = ("-started_at",)
        constraints = [models.UniqueConstraint(fields=("learner", "quiz", "idempotency_key"), condition=~models.Q(idempotency_key=""), name="unique_quiz_submission_idempotency")]

class QuizSubmissionAnswer(models.Model):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(QuizQuestion, on_delete=models.PROTECT, related_name="submission_answers")
    answer = models.JSONField()
    is_correct = models.BooleanField()
    points_earned = models.PositiveIntegerField(default=0)
    feedback = models.TextField(blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=("submission", "question"), name="unique_submission_question")]

class RoadmapStep(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="roadmap_steps")
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="roadmap_steps")
    position = models.PositiveIntegerField()
    target_date = models.DateField(null=True, blank=True)
    rationale = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ("position",)
        constraints = [models.UniqueConstraint(fields=("enrollment", "position"), name="unique_roadmap_position")]

class EngagementEvent(models.Model):
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="engagement_events")
    kind = models.CharField(max_length=32, db_index=True)
    module = models.ForeignKey(Module, null=True, blank=True, on_delete=models.SET_NULL, related_name="events")
    payload = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
