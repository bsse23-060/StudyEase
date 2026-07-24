from django.contrib import admin
from .models import Concept, Course, Lesson, Module, QuizQuestion
admin.site.register((Course, Module, Lesson, Concept, QuizQuestion))
