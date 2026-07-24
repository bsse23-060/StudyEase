from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import decorators, permissions, response, status, viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.throttling import UserRateThrottle
from accounts.permissions import IsInstructorOrAdmin
from accounts.models import AuditEvent
from .models import Conversation, Document, DocumentChunk, Flashcard, FlashcardDeck, FlashcardReview, Message, Routine, ScheduleBlock
from .providers.base import ProviderConfigurationError, ProviderRequestError
from .serializers import ConversationSerializer, DocumentActionSerializer, DocumentChunkSerializer, DocumentDownloadSerializer, DocumentSerializer, FlashcardDeckSerializer, FlashcardReviewSerializer, FlashcardSerializer, MessageSerializer, QuestionSerializer, RetrievalPreviewSerializer, RetrievalResultSerializer, ReviewSerializer, RoutineSerializer, ScheduleBlockSerializer
from .services.access import authorised_documents, can_control_document
from .services.generation import InvalidGenerationError
from .services.rag_pipeline import answer_question
from .services.retrieval import retrieve_chunks
from .services.vector_store import VectorBackendConfigurationError

class RAGQuestionThrottle(UserRateThrottle): scope = "rag_question"
class RAGProcessingThrottle(UserRateThrottle): scope = "rag_processing"

class OwnedViewSet(viewsets.ModelViewSet):
    owner_field = "owner"
    def get_queryset(self): return self.queryset.filter(**{self.owner_field: self.request.user})
    def perform_create(self, serializer): serializer.save(**{self.owner_field: self.request.user})

class DocumentViewSet(OwnedViewSet):
    queryset = Document.objects.all().order_by("id")
    serializer_class = DocumentSerializer
    filterset_fields = ("course", "status")
    search_fields = ("title",)
    ordering_fields = ("created_at", "title")
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): return self.queryset.none()
        return authorised_documents(self.request.user).order_by("id")
    def perform_create(self, serializer):
        has_file = bool(serializer.validated_data.get("file")); document = serializer.save(owner=self.request.user, status=Document.Status.UPLOADED)
        if has_file:
            from .tasks import scan_document_task
            transaction.on_commit(lambda: scan_document_task.delay(document.pk, document.processing_version))
        AuditEvent.objects.create(actor=self.request.user, action="document.upload", target_type="document", target_id=str(document.pk), request_id=getattr(self.request, "request_id", ""), metadata={"size": document.file_size, "mime_type": document.mime_type})
    def _controlled(self):
        document = self.get_object()
        if not can_control_document(self.request.user, document): raise PermissionDenied("You do not control this document.")
        return document
    @extend_schema(responses=DocumentSerializer)
    @decorators.action(detail=True, methods=("get",))
    def processing_status(self, request, pk=None): return response.Response(self.get_serializer(self.get_object()).data)
    @extend_schema(responses=DocumentDownloadSerializer)
    @decorators.action(detail=True, methods=("post",))
    def download(self, request, pk=None):
        document = self.get_object()
        if not document.file or document.deleted_at: raise ValidationError("This document has no downloadable file.")
        if document.scan_status != Document.ScanStatus.CLEAN: raise PermissionDenied("Only documents that passed malware scanning can be downloaded.")
        from django.conf import settings
        return response.Response({"url": document.file.storage.url(document.file.name), "expires_in": int(getattr(settings, "AWS_QUERYSTRING_EXPIRE", 300))})
    @extend_schema(request=DocumentActionSerializer, responses=DocumentSerializer)
    @decorators.action(detail=True, methods=("post",), throttle_classes=(RAGProcessingThrottle,))
    def retry(self, request, pk=None):
        document = self._controlled()
        if document.status != Document.Status.FAILED: raise ValidationError("Only failed documents can be retried.")
        if not document.file: raise ValidationError("Only failed uploaded files can be retried; remote URL ingestion is disabled.")
        document.status = Document.Status.QUEUED; document.processing_error = ""; document.save(update_fields=("status", "processing_error", "updated_at"))
        from .tasks import process_document_task
        transaction.on_commit(lambda: process_document_task.delay(document.pk, False, document.processing_version))
        return response.Response(self.get_serializer(document).data, status=status.HTTP_202_ACCEPTED)
    @extend_schema(request=DocumentActionSerializer, responses=DocumentSerializer)
    @decorators.action(detail=True, methods=("post",), throttle_classes=(RAGProcessingThrottle,))
    def reprocess(self, request, pk=None):
        document = self._controlled()
        if document.status == Document.Status.PROCESSING: raise ValidationError("A processing document cannot be reprocessed.")
        if not document.file: raise ValidationError("Only uploaded files can be reprocessed.")
        document.status = Document.Status.QUEUED; document.processing_error = ""; document.save(update_fields=("status", "processing_error", "updated_at"))
        from .tasks import process_document_task
        transaction.on_commit(lambda: process_document_task.delay(document.pk, True, document.processing_version))
        return response.Response(self.get_serializer(document).data, status=status.HTTP_202_ACCEPTED)
    @extend_schema(request=RetrievalPreviewSerializer, responses=RetrievalResultSerializer)
    @decorators.action(detail=False, methods=("post",), permission_classes=(IsInstructorOrAdmin,), throttle_classes=(RAGQuestionThrottle,), url_path="retrieval-preview")
    def retrieval_preview(self, request):
        serializer = RetrievalPreviewSerializer(data=request.data, context={"request": request}); serializer.is_valid(raise_exception=True)
        try: result = retrieve_chunks(request.user, serializer.validated_data["query"], course=serializer.validated_data.get("course"), lesson=serializer.validated_data.get("lesson"), document_ids=serializer.validated_data.get("document_ids"), top_k=serializer.validated_data.get("top_k"))
        except (ProviderConfigurationError, VectorBackendConfigurationError) as exc: return response.Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ProviderRequestError: return response.Response({"detail": "The configured embedding provider is temporarily unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
        payload = {"query": result.query, "results": [{"chunk_id": item.id, "score": item.score, "document_title": item.document_title, "page": item.page, "section_title": item.section_title} for item in result.chunks]}
        return response.Response(RetrievalResultSerializer(payload).data)
    def perform_destroy(self, instance):
        if not can_control_document(self.request.user, instance): raise PermissionDenied("You do not control this document.")
        instance.deleted_at = timezone.now(); instance.status = Document.Status.FAILED; instance.processing_error = "Deleted by owner."
        instance.chunks.update(is_active=False)
        if instance.file: instance.file.delete(save=False); instance.file = ""
        instance.save(update_fields=("deleted_at", "status", "processing_error", "file", "updated_at"))
        AuditEvent.objects.create(actor=self.request.user, action="document.delete", target_type="document", target_id=str(instance.pk), request_id=getattr(self.request, "request_id", ""))

class DocumentChunkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = DocumentChunk.objects.select_related("document")
    serializer_class = DocumentChunkSerializer
    filterset_fields = ("document", "page")
    ordering_fields = ("position", "page")
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): return self.queryset.none()
        user = self.request.user
        if user.role == "admin" or user.is_superuser: return self.queryset.filter(document__deleted_at__isnull=True, is_active=True)
        return self.queryset.filter(Q(document__owner=user) | Q(document__course__instructor=user), document__deleted_at__isnull=True, is_active=True).distinct()

class ConversationViewSet(OwnedViewSet):
    queryset = Conversation.objects.prefetch_related("messages__source_citations__chunk__document").order_by("id")
    serializer_class = ConversationSerializer
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): return self.queryset.none()
        return self.queryset.filter(owner=self.request.user)
    @decorators.action(detail=True, methods=("post",))
    def messages(self, request, pk=None):
        conversation = self.get_object(); serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True); serializer.save(conversation=conversation, role=Message.Role.USER)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)
    @decorators.action(detail=True, methods=("get",), url_path="history")
    def history(self, request, pk=None):
        conversation = self.get_object(); queryset = conversation.messages.filter(deleted_at__isnull=True).prefetch_related("source_citations__chunk__document").order_by("-created_at", "-id")
        paginator = PageNumberPagination(); paginator.page_size = 30; page = paginator.paginate_queryset(queryset, request, view=self)
        data = MessageSerializer(reversed(page), many=True).data
        return paginator.get_paginated_response(data)
    @extend_schema(request=QuestionSerializer, responses=MessageSerializer)
    @decorators.action(detail=True, methods=("post",), throttle_classes=(RAGQuestionThrottle,))
    def ask(self, request, pk=None):
        conversation = self.get_object(); serializer = QuestionSerializer(data=request.data, context={"request": request, "conversation": conversation}); serializer.is_valid(raise_exception=True)
        try: assistant = answer_question(request.user, conversation, serializer.validated_data["question"], document_ids=serializer.validated_data.get("document_ids"), top_k=serializer.validated_data.get("top_k"))
        except (ProviderConfigurationError, VectorBackendConfigurationError) as exc: return response.Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ProviderRequestError: return response.Response({"detail": "The configured AI provider is temporarily unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
        except InvalidGenerationError as exc: return response.Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return response.Response(MessageSerializer(assistant).data, status=status.HTTP_201_CREATED)
    @extend_schema(responses=ConversationSerializer)
    @decorators.action(detail=True, methods=("post",))
    def archive(self, request, pk=None):
        conversation = self.get_object(); conversation.archived_at = timezone.now(); conversation.save(update_fields=("archived_at",)); return response.Response(self.get_serializer(conversation).data)
    def perform_destroy(self, instance):
        instance.archived_at = timezone.now(); instance.save(update_fields=("archived_at",))

class FlashcardDeckViewSet(OwnedViewSet):
    queryset = FlashcardDeck.objects.prefetch_related("cards__source_documents").order_by("id")
    serializer_class = FlashcardDeckSerializer
    @extend_schema(responses=FlashcardSerializer(many=True))
    @decorators.action(detail=True, methods=("get",))
    def due(self, request, pk=None):
        cards = self.get_object().cards.filter(Q(next_review_at__isnull=True) | Q(next_review_at__lte=timezone.now()))
        return response.Response(FlashcardSerializer(cards, many=True).data)
    @extend_schema(parameters=[OpenApiParameter("card_id", int, OpenApiParameter.PATH)], request=ReviewSerializer, responses=FlashcardSerializer)
    @decorators.action(detail=True, methods=("post",), url_path=r"cards/(?P<card_id>[^/.]+)/review")
    def review(self, request, pk=None, card_id: int = None):
        card = self.get_object().cards.get(pk=card_id); serializer = ReviewSerializer(data=request.data, context={"card": card})
        serializer.is_valid(raise_exception=True); serializer.save(); return response.Response(FlashcardSerializer(card).data)

class RoutineViewSet(OwnedViewSet):
    queryset = Routine.objects.prefetch_related("blocks").order_by("id")
    serializer_class = RoutineSerializer

class FlashcardViewSet(viewsets.ModelViewSet):
    queryset = Flashcard.objects.all()
    serializer_class = FlashcardSerializer
    filterset_fields = ("deck", "course", "lesson", "concept")
    search_fields = ("question", "answer")
    ordering_fields = ("next_review_at", "created_at", "question")
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): return self.queryset.none()
        return self.queryset.filter(deck__owner=self.request.user).prefetch_related("source_documents")
    @decorators.action(detail=True, methods=("get",))
    def reviews(self, request, pk=None):
        card = self.get_object(); return response.Response(FlashcardReviewSerializer(card.reviews.all()[:50], many=True).data)

class ScheduleBlockViewSet(viewsets.ModelViewSet):
    queryset = ScheduleBlock.objects.all()
    serializer_class = ScheduleBlockSerializer
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): return self.queryset.none()
        return self.queryset.filter(routine__owner=self.request.user)
    filterset_fields = ("routine", "recurrence", "weekday", "calendar_date", "is_active")
    ordering_fields = ("calendar_date", "start_time", "weekday")
