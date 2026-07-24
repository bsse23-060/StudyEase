from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter
from accounts.auth_views import AuditedTokenObtainPairView, ThrottledTokenRefreshView

from accounts.views import AuditEventViewSet, LogoutView, MeView, RegisterView, UserViewSet
from courses.views import ConceptViewSet, CourseViewSet, LessonViewSet, ModuleViewSet, QuizAnswerOptionViewSet, QuizQuestionViewSet, QuizViewSet
from learning.views import EnrollmentViewSet, EventViewSet, LearningProfileViewSet, MasteryViewSet, QuizAttemptViewSet, QuizSubmissionViewSet, RoadmapStepViewSet
from study_tools.views import ConversationViewSet, DocumentChunkViewSet, DocumentViewSet, FlashcardDeckViewSet, FlashcardViewSet, RoutineViewSet, ScheduleBlockViewSet
from config.health import DetailedHealthView, live, metrics, ready

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("audit-events", AuditEventViewSet, basename="audit-event")
router.register("courses", CourseViewSet, basename="course")
router.register("modules", ModuleViewSet, basename="module")
router.register("lessons", LessonViewSet, basename="lesson")
router.register("concepts", ConceptViewSet, basename="concept")
router.register("questions", QuizQuestionViewSet, basename="question")
router.register("quizzes", QuizViewSet, basename="quiz")
router.register("quiz-options", QuizAnswerOptionViewSet, basename="quiz-option")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("learning-profiles", LearningProfileViewSet, basename="learning-profile")
router.register("masteries", MasteryViewSet, basename="mastery")
router.register("attempts", QuizAttemptViewSet, basename="attempt")
router.register("quiz-submissions", QuizSubmissionViewSet, basename="quiz-submission")
router.register("roadmap-steps", RoadmapStepViewSet, basename="roadmap-step")
router.register("events", EventViewSet, basename="event")
router.register("documents", DocumentViewSet, basename="document")
router.register("document-chunks", DocumentChunkViewSet, basename="document-chunk")
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("flashcard-decks", FlashcardDeckViewSet, basename="flashcard-deck")
router.register("flashcards", FlashcardViewSet, basename="flashcard")
router.register("routines", RoutineViewSet, basename="routine")
router.register("schedule-blocks", ScheduleBlockViewSet, basename="schedule-block")

urlpatterns = [
    path("health/live/", live, name="health-live"), path("health/ready/", ready, name="health-ready"),
    path("api/v1/admin/health/", DetailedHealthView.as_view(), name="health-detailed"), path("internal/metrics/", metrics, name="metrics"),
    path("admin/", admin.site.urls), path("api/v1/", include(router.urls)),
    path("api/v1/auth/register/", RegisterView.as_view(), name="register"), path("api/v1/auth/token/", AuditedTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token_refresh"), path("api/v1/auth/me/", MeView.as_view(), name="me"),
    path("api/v1/auth/logout/", LogoutView.as_view(), name="logout"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
