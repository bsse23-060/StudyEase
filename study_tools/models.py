from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone as django_timezone
from pgvector.django import HnswIndex, VectorField
from courses.models import Concept, Course, Lesson
from pathlib import Path
import uuid

def private_document_key(_instance, filename):
    suffix = Path(filename).suffix.lower()[:10]
    return f"documents/{uuid.uuid4().hex[:2]}/{uuid.uuid4().hex}{suffix}"

class Document(models.Model):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        COURSE = "course", "Course"
    class ScanStatus(models.TextChoices):
        PENDING = "pending", "Awaiting scan"
        SCANNING = "scanning", "Scanning"
        CLEAN = "clean", "Clean"
        SUSPICIOUS = "suspicious", "Suspicious"
        INFECTED = "infected", "Infected"
        UNAVAILABLE = "unavailable", "Scanner unavailable"
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=private_document_key, blank=True)
    source_url = models.URLField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.UPLOADED, db_index=True)
    visibility = models.CharField(max_length=16, choices=Visibility.choices, default=Visibility.PRIVATE, db_index=True)
    processing_error = models.TextField(blank=True)
    scan_status = models.CharField(max_length=16, choices=ScanStatus.choices, default=ScanStatus.CLEAN, db_index=True)
    scan_provider = models.CharField(max_length=64, blank=True)
    scanned_at = models.DateTimeField(null=True, blank=True)
    scan_result = models.CharField(max_length=255, blank=True)
    quarantine_reason = models.CharField(max_length=255, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=128, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    chunk_count = models.PositiveIntegerField(default=0)
    embedding_provider = models.CharField(max_length=64, blank=True)
    embedding_model = models.CharField(max_length=128, blank=True)
    embedding_dimensions = models.PositiveIntegerField(default=0)
    processing_version = models.PositiveIntegerField(default=1)
    topics = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    class Meta:
        indexes = [models.Index(fields=("course", "status", "deleted_at")), models.Index(fields=("owner", "status"))]
        constraints = [models.UniqueConstraint(fields=("owner", "checksum"), condition=models.Q(deleted_at__isnull=True) & ~models.Q(checksum=""), name="unique_active_owner_document_checksum")]

class DocumentChunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    text = models.TextField()
    position = models.PositiveIntegerField()
    page = models.PositiveIntegerField(null=True, blank=True)
    section_title = models.CharField(max_length=255, blank=True)
    start_position = models.PositiveIntegerField(default=0)
    end_position = models.PositiveIntegerField(default=0)
    character_count = models.PositiveIntegerField(default=0)
    token_count = models.PositiveIntegerField(default=0)
    content_checksum = models.CharField(max_length=64, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    embedding = models.JSONField(default=list, blank=True)
    embedding_vector = VectorField(dimensions=1536, null=True, blank=True)
    embedding_model = models.CharField(max_length=128, blank=True)
    embedding_dimensions = models.PositiveIntegerField(default=0)
    embedding_ref = models.CharField(max_length=255, blank=True)
    processing_version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    class Meta:
        ordering = ("position",)
        indexes = [HnswIndex(name="chunk_embedding_hnsw", fields=["embedding_vector"], m=16, ef_construction=64, opclasses=["vector_cosine_ops"])]
        constraints = [models.UniqueConstraint(fields=("document", "processing_version", "position"), name="unique_chunk_version_position"), models.UniqueConstraint(fields=("document", "processing_version", "content_checksum"), condition=~models.Q(content_checksum=""), name="unique_chunk_version_checksum")]

class Conversation(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations")
    title = models.CharField(max_length=255, blank=True)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="conversations")
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True)

class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Assistant"
        SYSTEM = "system", "System"
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=Role.choices)
    content = models.TextField()
    citations = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ("created_at", "id")

class Citation(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="source_citations")
    chunk = models.ForeignKey(DocumentChunk, on_delete=models.PROTECT, related_name="citations")
    quote = models.TextField(blank=True)
    score = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    class Meta:
        constraints = [models.UniqueConstraint(fields=("message", "chunk"), name="unique_message_chunk_citation")]

class ProviderUsage(models.Model):
    class Operation(models.TextChoices):
        EMBEDDING = "embedding", "Embedding"
        GENERATION = "generation", "Generation"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="provider_usage")
    provider = models.CharField(max_length=64)
    model = models.CharField(max_length=128)
    operation = models.CharField(max_length=16, choices=Operation.choices)
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    input_characters = models.PositiveIntegerField(default=0)
    success = models.BooleanField(default=True)
    latency_ms = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

class FlashcardDeck(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="flashcard_decks")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    topics = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Flashcard(models.Model):
    deck = models.ForeignKey(FlashcardDeck, on_delete=models.CASCADE, related_name="cards")
    question = models.TextField()
    answer = models.TextField()
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="flashcards")
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL, related_name="flashcards")
    concept = models.ForeignKey(Concept, null=True, blank=True, on_delete=models.SET_NULL, related_name="flashcards")
    source_documents = models.ManyToManyField(Document, blank=True, related_name="flashcards")
    easiness = models.FloatField(default=2.5, validators=[MinValueValidator(1.3)])
    interval_days = models.PositiveIntegerField(default=0)
    repetitions = models.PositiveIntegerField(default=0)
    next_review_at = models.DateTimeField(null=True, blank=True, db_index=True)
    total_reviews = models.PositiveIntegerField(default=0)
    correct_reviews = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=django_timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

class FlashcardReview(models.Model):
    card = models.ForeignKey(Flashcard, on_delete=models.CASCADE, related_name="reviews")
    quality = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(5)])
    reviewed_at = models.DateTimeField(auto_now_add=True)
    previous_interval_days = models.PositiveIntegerField(default=0)
    next_interval_days = models.PositiveIntegerField(default=0)
    idempotency_key = models.CharField(max_length=64, blank=True)
    class Meta:
        ordering = ("-reviewed_at",)
        constraints = [models.UniqueConstraint(fields=("card", "idempotency_key"), condition=~models.Q(idempotency_key=""), name="unique_card_review_idempotency")]

class Routine(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="routines")
    name = models.CharField(max_length=255)
    preferences = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    suggestions = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ScheduleBlock(models.Model):
    class Recurrence(models.TextChoices):
        ONCE = "once", "One time"
        WEEKLY = "weekly", "Weekly"
    routine = models.ForeignKey(Routine, on_delete=models.CASCADE, related_name="blocks")
    activity_name = models.CharField(max_length=255)
    start_time = models.TimeField()
    end_time = models.TimeField()
    category = models.CharField(max_length=32)
    is_flexible = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    recurrence = models.CharField(max_length=16, choices=Recurrence.choices, default=Recurrence.WEEKLY)
    weekday = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(6)])
    calendar_date = models.DateField(null=True, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    recurrence_start = models.DateField(null=True, blank=True)
    recurrence_end = models.DateField(null=True, blank=True)
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.SET_NULL, related_name="schedule_blocks")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=django_timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
