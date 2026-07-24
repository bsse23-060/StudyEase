from django.contrib import admin
from .models import EngagementEvent, Enrollment, LearningProfile, Mastery, QuizAttempt, RoadmapStep
admin.site.register((Enrollment, LearningProfile, Mastery, QuizAttempt, RoadmapStep, EngagementEvent))
