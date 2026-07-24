from django.utils import timezone
from rest_framework import decorators, permissions, response, status, viewsets
from accounts.permissions import IsInstructorOrAdmin
from .models import EngagementEvent, Enrollment, LearningProfile, Mastery, QuizAttempt, QuizSubmission, RoadmapStep
from .permissions import IsSelfOrTeachingStaff
from .serializers import EngagementEventSerializer, EnrollmentSerializer, LearningProfileSerializer, MasterySerializer, QuizAttemptSerializer, QuizSubmissionSerializer, QuizSubmitSerializer, RoadmapStepSerializer

class LearnerScopedMixin:
    permission_classes = [IsSelfOrTeachingStaff]
    def learner_queryset(self, qs):
        user = self.request.user
        if getattr(self, "swagger_fake_view", False): return qs.none()
        if user.role == "admin": return qs
        if user.role == "instructor": return qs.filter(learner__enrollments__course__instructor=user).distinct()
        return qs.filter(learner=user)

class EnrollmentViewSet(LearnerScopedMixin, viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    def get_queryset(self):
        qs = Enrollment.objects.select_related("learner", "course").order_by("id")
        if getattr(self, "swagger_fake_view", False): return qs.none()
        if self.request.user.role == "admin": return qs
        if self.request.user.role == "instructor": return qs.filter(course__instructor=self.request.user)
        return qs.filter(learner=self.request.user)
    def perform_create(self, serializer): serializer.save(learner=self.request.user)

class MasteryViewSet(LearnerScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Mastery.objects.all()
    serializer_class = MasterySerializer
    filterset_fields = ("concept",)
    def get_queryset(self):
        qs = Mastery.objects.select_related("learner", "concept").order_by("id")
        if getattr(self, "swagger_fake_view", False): return qs.none()
        if self.request.user.role == "admin": return qs
        if self.request.user.role == "instructor": return qs.filter(concept__lessons__module__course__instructor=self.request.user, learner__enrollments__course__instructor=self.request.user).distinct()
        return qs.filter(learner=self.request.user)

class LearningProfileViewSet(viewsets.ModelViewSet):
    queryset = LearningProfile.objects.all()
    serializer_class = LearningProfileSerializer
    http_method_names = ("get", "post", "patch", "head", "options")
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): return self.queryset.none()
        return self.queryset.filter(user=self.request.user).order_by("id")
    def perform_create(self, serializer): serializer.save(user=self.request.user)

class QuizAttemptViewSet(LearnerScopedMixin, viewsets.ModelViewSet):
    queryset = QuizAttempt.objects.all()
    serializer_class = QuizAttemptSerializer
    http_method_names = ("get", "post", "head", "options")
    def get_queryset(self):
        qs = QuizAttempt.objects.select_related("learner", "question__lesson__module__course").order_by("id")
        if getattr(self, "swagger_fake_view", False): return qs.none()
        if self.request.user.role == "admin": return qs
        if self.request.user.role == "instructor": return qs.filter(question__lesson__module__course__instructor=self.request.user)
        return qs.filter(learner=self.request.user)

class QuizSubmissionViewSet(viewsets.ModelViewSet):
    queryset = QuizSubmission.objects.select_related("learner", "quiz__lesson__module__course").prefetch_related("answers__question")
    serializer_class = QuizSubmissionSerializer
    http_method_names = ("get", "post", "head", "options")
    filterset_fields = ("quiz", "status")
    def get_queryset(self):
        qs = self.queryset; user = self.request.user
        if getattr(self, "swagger_fake_view", False): return qs.none()
        if user.role == "admin": return qs
        if user.role == "instructor": return qs.filter(quiz__lesson__module__course__instructor=user)
        return qs.filter(learner=user)
    def perform_create(self, serializer): serializer.save(learner=self.request.user)
    @decorators.action(detail=True, methods=("post",))
    def submit(self, request, pk=None):
        submission = self.get_object(); serializer = QuizSubmitSerializer(data=request.data, context={"request": request, "submission": submission})
        serializer.is_valid(raise_exception=True); result = serializer.save()
        return response.Response(QuizSubmissionSerializer(result, context=self.get_serializer_context()).data, status=status.HTTP_200_OK)

class RoadmapStepViewSet(viewsets.ModelViewSet):
    queryset = RoadmapStep.objects.all()
    serializer_class = RoadmapStepSerializer
    permission_classes = [IsSelfOrTeachingStaff]
    def get_queryset(self):
        qs = RoadmapStep.objects.select_related("enrollment__learner", "enrollment__course", "module").order_by("position")
        if getattr(self, "swagger_fake_view", False): return qs.none()
        if self.request.user.role == "admin": return qs
        if self.request.user.role == "instructor": return qs.filter(enrollment__course__instructor=self.request.user)
        return qs.filter(enrollment__learner=self.request.user)
    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}: return [IsInstructorOrAdmin()]
        return super().get_permissions()
    @decorators.action(detail=True, methods=("post",))
    def complete(self, request, pk=None):
        step = self.get_object(); step.completed_at = timezone.now(); step.save(update_fields=("completed_at",)); return response.Response(self.get_serializer(step).data)

class EventViewSet(LearnerScopedMixin, viewsets.ModelViewSet):
    queryset = EngagementEvent.objects.all()
    serializer_class = EngagementEventSerializer
    http_method_names = ("get", "post", "head", "options")
    filterset_fields = ("kind", "module")
    def get_queryset(self):
        qs = EngagementEvent.objects.select_related("learner", "module__course").order_by("id")
        if getattr(self, "swagger_fake_view", False): return qs.none()
        if self.request.user.role == "admin": return qs
        if self.request.user.role == "instructor": return qs.filter(module__course__instructor=self.request.user)
        return qs.filter(learner=self.request.user)
    def perform_create(self, serializer): serializer.save(learner=self.request.user)
