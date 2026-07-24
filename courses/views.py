from django.db import models
from django.utils import timezone
from rest_framework import decorators, permissions, response, viewsets
from rest_framework.exceptions import PermissionDenied
from django.db.models import Avg, Count, Max, Min, Q
from statistics import median
from accounts.permissions import IsInstructorOwnerOrReadOnly
from accounts.models import AuditEvent
from .models import Concept, Course, Lesson, Module, Quiz, QuizAnswerOption, QuizQuestion
from .serializers import ConceptSerializer, CourseSerializer, LessonSerializer, ModuleSerializer, QuizAnswerOptionSerializer, QuizQuestionSerializer, QuizSerializer

class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsInstructorOwnerOrReadOnly]
    filterset_fields = ("instructor", "is_published", "is_archived")
    search_fields = ("title", "description")
    ordering_fields = ("created_at", "title")
    def get_queryset(self):
        qs = Course.objects.select_related("instructor").prefetch_related("modules__lessons__questions").order_by("id")
        if self.request.user.is_authenticated and self.request.user.role == "admin": return qs
        if self.request.user.is_authenticated and self.request.user.role == "instructor": return qs.filter(models.Q(is_published=True, is_archived=False) | models.Q(instructor=self.request.user))
        if self.request.user.is_authenticated:
            return qs.filter(models.Q(is_published=True, is_archived=False) | models.Q(is_archived=True, enrollments__learner=self.request.user, enrollments__status="active")).distinct()
        return qs.filter(is_published=True, is_archived=False)
    def perform_create(self, serializer): serializer.save(instructor=self.request.user)
    def perform_update(self, serializer):
        if serializer.instance.is_archived: raise PermissionDenied("Archived courses are read-only until restored.")
        serializer.save()
    def perform_destroy(self, instance):
        if instance.enrollments.exists() or instance.documents.exists(): raise PermissionDenied("Protected course history exists; archive the course instead.")
        instance.delete()
    @decorators.action(detail=True, methods=("post",))
    def archive(self, request, pk=None):
        course = self.get_object()
        if request.user.role != "admin" and course.instructor_id != request.user.id: raise PermissionDenied("Only the course instructor or an administrator may archive it.")
        course.is_archived = True; course.is_published = False; course.archived_at = timezone.now(); course.archived_by = request.user
        course.save(update_fields=("is_archived", "is_published", "archived_at", "archived_by", "updated_at"))
        AuditEvent.objects.create(actor=request.user, action="course.archive", target_type="course", target_id=str(course.pk), request_id=getattr(request, "request_id", ""))
        return response.Response(self.get_serializer(course).data)
    @decorators.action(detail=True, methods=("post",))
    def restore(self, request, pk=None):
        if request.user.role != "admin" and not request.user.is_superuser: raise PermissionDenied("Only an administrator may restore a course.")
        course = self.get_object(); course.is_archived = False; course.archived_at = None; course.archived_by = None
        course.save(update_fields=("is_archived", "archived_at", "archived_by", "updated_at"))
        AuditEvent.objects.create(actor=request.user, action="course.restore", target_type="course", target_id=str(course.pk), request_id=getattr(request, "request_id", ""))
        return response.Response(self.get_serializer(course).data)

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.select_related("course").prefetch_related("lessons__questions")
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsInstructorOwnerOrReadOnly]
    filterset_fields = ("course",)
    ordering_fields = ("position", "title")
    def get_queryset(self):
        qs = self.queryset
        user = self.request.user
        if not user.is_authenticated: return qs.none()
        if user.role == "admin": return qs
        if user.role == "instructor": return qs.filter(course__instructor=user)
        return qs.filter(course__enrollments__learner=user, course__enrollments__status="active").distinct()

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.select_related("module__course").prefetch_related("questions")
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated, IsInstructorOwnerOrReadOnly]
    filterset_fields = ("module", "kind")
    ordering_fields = ("position", "title")
    def get_queryset(self):
        qs = self.queryset; user = self.request.user
        if not user.is_authenticated: return qs.none()
        if user.role == "admin": return qs
        if user.role == "instructor": return qs.filter(module__course__instructor=user)
        return qs.filter(module__course__enrollments__learner=user, module__course__enrollments__status="active").distinct()

class ConceptViewSet(viewsets.ModelViewSet):
    queryset = Concept.objects.prefetch_related("lessons", "prerequisites")
    serializer_class = ConceptSerializer
    permission_classes = [permissions.IsAuthenticated, IsInstructorOwnerOrReadOnly]
    search_fields = ("name", "description")
    filterset_fields = ("course",)
    def get_queryset(self):
        qs = self.queryset; user = self.request.user
        if user.role == "admin": return qs
        if user.role == "instructor": return qs.filter(models.Q(created_by=user) | models.Q(lessons__module__course__instructor=user)).distinct()
        return qs.filter(lessons__module__course__enrollments__learner=user, lessons__module__course__enrollments__status="active").distinct()
    def perform_create(self, serializer): serializer.save(created_by=self.request.user)

class QuizQuestionViewSet(viewsets.ModelViewSet):
    queryset = QuizQuestion.objects.select_related("lesson__module__course", "concept")
    serializer_class = QuizQuestionSerializer
    permission_classes = [permissions.IsAuthenticated, IsInstructorOwnerOrReadOnly]
    filterset_fields = ("quiz", "lesson", "concept", "kind")
    def get_queryset(self):
        qs = self.queryset; user = self.request.user
        if user.role == "admin": return qs
        if user.role == "instructor": return qs.filter(lesson__module__course__instructor=user)
        return qs.filter(lesson__module__course__enrollments__learner=user, lesson__module__course__enrollments__status="active").distinct()

class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.select_related("lesson__module__course").prefetch_related("questions__answer_options")
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated, IsInstructorOwnerOrReadOnly]
    filterset_fields = ("lesson", "is_published")
    ordering_fields = ("available_from", "created_at", "title")
    def get_queryset(self):
        qs = self.queryset; user = self.request.user
        if user.role == "admin": return qs
        if user.role == "instructor": return qs.filter(lesson__module__course__instructor=user)
        return qs.filter(is_published=True, lesson__module__course__enrollments__learner=user, lesson__module__course__enrollments__status="active").distinct()
    @decorators.action(detail=True, methods=("get",), permission_classes=(permissions.IsAuthenticated,))
    def analytics(self, request, pk=None):
        quiz = self.get_object()
        if request.user.role not in {"admin", "instructor"}: return response.Response({"detail": "Instructor access required."}, status=403)
        submissions = quiz.submissions.filter(status="submitted")
        summary = submissions.aggregate(attempts=Count("id"), unique_students=Count("learner", distinct=True), average_score=Avg("percentage_score"), highest_score=Max("percentage_score"), lowest_score=Min("percentage_score"))
        passed = submissions.filter(passed=True).count(); summary["pass_rate"] = (passed / summary["attempts"] * 100) if summary["attempts"] else 0
        scores = list(submissions.values_list("percentage_score", flat=True)); summary["median_score"] = median(scores) if scores else None
        enrolled = quiz.lesson.module.course.enrollments.filter(status="active").count(); summary["completion_rate"] = (summary["unique_students"] / enrolled * 100) if enrolled else 0
        summary["recent_attempts"] = list(submissions.order_by("-submitted_at").values("id", "submitted_at", "percentage_score", "passed")[:10])
        summary["questions"] = list(quiz.questions.annotate(answer_count=Count("submission_answers"), correct_count=Count("submission_answers", filter=Q(submission_answers__is_correct=True))).values("id", "prompt", "answer_count", "correct_count"))
        return response.Response(summary)

class QuizAnswerOptionViewSet(viewsets.ModelViewSet):
    queryset = QuizAnswerOption.objects.select_related("question__lesson__module__course")
    serializer_class = QuizAnswerOptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsInstructorOwnerOrReadOnly]
    filterset_fields = ("question",)
    ordering_fields = ("position",)
    def get_queryset(self):
        qs = self.queryset; user = self.request.user
        if user.role == "admin": return qs
        if user.role == "instructor": return qs.filter(question__lesson__module__course__instructor=user)
        return qs.none()
