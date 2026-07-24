from datetime import timedelta
import hashlib
import zipfile
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path
from django.utils import timezone
from rest_framework import serializers
from accounts.models import User
from courses.models import Course, Lesson
from learning.models import Enrollment
from .models import Citation, Conversation, Document, DocumentChunk, Flashcard, FlashcardDeck, FlashcardReview, Message, Routine, ScheduleBlock
from .services.access import authorised_documents
from .services.schedule_overlap import overlap_warnings

PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

def inspect_upload(upload):
    if upload.size == 0: raise serializers.ValidationError("Empty files are not supported.")
    from django.conf import settings
    if upload.size > settings.RAG_MAX_DOCUMENT_BYTES: raise serializers.ValidationError(f"File exceeds the {settings.RAG_MAX_DOCUMENT_BYTES}-byte limit.")
    position = upload.tell(); head = upload.read(min(upload.size, 8192)); upload.seek(position)
    if head.startswith(b"%PDF-"): mime = PDF
    elif head.startswith(b"PK\x03\x04"):
        try:
            with zipfile.ZipFile(upload) as archive:
                names = set(archive.namelist())
                if "word/document.xml" not in names or "[Content_Types].xml" not in names: raise serializers.ValidationError("ZIP uploads must be valid DOCX files.")
            mime = DOCX
        except zipfile.BadZipFile as exc: raise serializers.ValidationError("The DOCX container is corrupted.") from exc
        finally: upload.seek(position)
    else:
        if b"\x00" in head: raise serializers.ValidationError("Unsupported binary file type.")
        try: head.decode("utf-8-sig")
        except UnicodeDecodeError as exc: raise serializers.ValidationError("Text and Markdown uploads must be UTF-8.") from exc
        supplied = (getattr(upload, "content_type", "") or "").split(";", 1)[0].lower()
        if supplied not in {"text/plain", "text/markdown", "application/octet-stream"}: raise serializers.ValidationError("Unsupported MIME type. Upload PDF, UTF-8 text, Markdown, or DOCX.")
        mime = "text/markdown" if Path(upload.name).suffix.lower() in {".md", ".markdown"} else "text/plain"
    digest = hashlib.sha256()
    for part in upload.chunks(): digest.update(part)
    upload.seek(position)
    return mime, digest.hexdigest()

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ("id", "owner", "course", "lesson", "title", "file", "source_url", "status", "visibility", "processing_error", "scan_status", "scan_provider", "scanned_at", "scan_result", "quarantine_reason", "original_filename", "mime_type", "file_size", "checksum", "processed_at", "processing_started_at", "chunk_count", "embedding_provider", "embedding_model", "embedding_dimensions", "processing_version", "topics", "metadata", "created_at", "updated_at", "deleted_at")
        read_only_fields = ("owner", "status", "processing_error", "scan_status", "scan_provider", "scanned_at", "scan_result", "quarantine_reason", "original_filename", "mime_type", "file_size", "checksum", "processed_at", "processing_started_at", "chunk_count", "embedding_provider", "embedding_model", "embedding_dimensions", "processing_version", "created_at", "updated_at", "deleted_at")
        extra_kwargs = {"file": {"write_only": True}, "source_url": {"write_only": True}}
    def validate(self, attrs):
        file = attrs.get("file", getattr(self.instance, "file", None)); source_url = attrs.get("source_url", getattr(self.instance, "source_url", ""))
        if not file and not source_url: raise serializers.ValidationError("Provide either a file or source_url.")
        if file and source_url: raise serializers.ValidationError("Provide a file or source_url, not both.")
        course = attrs.get("course", getattr(self.instance, "course", None)); lesson = attrs.get("lesson", getattr(self.instance, "lesson", None)); user = self.context["request"].user
        if lesson:
            lesson_course = lesson.module.course
            if course and course.pk != lesson_course.pk: raise serializers.ValidationError({"lesson": "The lesson must belong to the selected course."})
            course = lesson_course; attrs["course"] = course
        if course and user.role == User.Role.INSTRUCTOR and course.instructor_id != user.id: raise serializers.ValidationError({"course": "You do not own this course."})
        if user.role == User.Role.STUDENT and course: raise serializers.ValidationError({"course": "Students may upload only private personal documents."})
        visibility = attrs.get("visibility", getattr(self.instance, "visibility", Document.Visibility.PRIVATE))
        if course and visibility != Document.Visibility.COURSE: attrs["visibility"] = Document.Visibility.COURSE
        if not course and visibility == Document.Visibility.COURSE: raise serializers.ValidationError({"visibility": "Course visibility requires a course."})
        if "file" in attrs:
            mime, checksum = inspect_upload(attrs["file"])
            duplicate = Document.objects.filter(owner=user, checksum=checksum, deleted_at__isnull=True)
            if self.instance: duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists(): raise serializers.ValidationError({"file": "This file has already been uploaded."})
            attrs.update(original_filename=Path(attrs["file"].name).name[:255], mime_type=mime, file_size=attrs["file"].size, checksum=checksum, status=Document.Status.UPLOADED, scan_status=Document.ScanStatus.PENDING)
        return attrs

class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ("id", "document", "text", "position", "page", "section_title", "start_position", "end_position", "character_count", "token_count", "content_checksum", "metadata", "embedding_model", "embedding_dimensions", "processing_version")
        read_only_fields = fields

class CitationSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source="chunk.document.title", read_only=True)
    page = serializers.IntegerField(source="chunk.page", read_only=True)
    class Meta:
        model = Citation
        fields = ("id", "chunk", "document_title", "page", "quote", "score")

class MessageSerializer(serializers.ModelSerializer):
    citations = CitationSerializer(source="source_citations", many=True, read_only=True)
    class Meta:
        model = Message
        fields = ("id", "role", "content", "citations", "metadata", "created_at")
        read_only_fields = ("role", "citations", "metadata", "created_at")

class ConversationSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()
    class Meta:
        model = Conversation
        fields = ("id", "owner", "title", "course", "lesson", "messages", "created_at", "updated_at", "archived_at")
        read_only_fields = ("owner", "created_at", "updated_at", "archived_at")
    def get_messages(self, obj) -> list:
        view = self.context.get("view")
        if getattr(view, "action", None) == "list": return []
        recent = list(obj.messages.filter(deleted_at__isnull=True).order_by("-created_at", "-id")[:30])
        return MessageSerializer(reversed(recent), many=True).data
    def validate(self, attrs):
        user = self.context["request"].user; course = attrs.get("course", getattr(self.instance, "course", None)); lesson = attrs.get("lesson", getattr(self.instance, "lesson", None))
        if lesson:
            lesson_course = lesson.module.course
            if course and course.pk != lesson_course.pk: raise serializers.ValidationError({"lesson": "The lesson must belong to the conversation course."})
            course = lesson_course; attrs["course"] = course
        if course and user.role == User.Role.INSTRUCTOR and course.instructor_id != user.id: raise serializers.ValidationError("You do not own this course.")
        if course and user.role == User.Role.STUDENT and not course.enrollments.filter(learner=user, status=Enrollment.Status.ACTIVE).exists(): raise serializers.ValidationError("You are not actively enrolled in this course.")
        if self.instance and self.instance.messages.exists() and any(field in attrs for field in ("course", "lesson")): raise serializers.ValidationError("Conversation scope cannot change after messages exist.")
        return attrs

class DocumentActionSerializer(serializers.Serializer):
    force = serializers.BooleanField(default=False, required=False)

class DocumentDownloadSerializer(serializers.Serializer):
    url = serializers.CharField()
    expires_in = serializers.IntegerField()

class RetrievalPreviewSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=4000, trim_whitespace=True)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(), required=False, allow_null=True)
    lesson = serializers.PrimaryKeyRelatedField(queryset=Lesson.objects.all(), required=False, allow_null=True)
    document_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, max_length=50)
    top_k = serializers.IntegerField(min_value=1, required=False)
    def validate(self, attrs):
        user = self.context["request"].user; course = attrs.get("course"); lesson = attrs.get("lesson")
        if lesson and course and lesson.module.course_id != course.id: raise serializers.ValidationError("Lesson and course scopes do not match.")
        if course and user.role == User.Role.INSTRUCTOR and course.instructor_id != user.id and user.role != User.Role.ADMIN: raise serializers.ValidationError("You do not control this course.")
        if lesson and user.role == User.Role.INSTRUCTOR and lesson.module.course.instructor_id != user.id and user.role != User.Role.ADMIN: raise serializers.ValidationError("You do not control this lesson.")
        ids = set(attrs.get("document_ids", []))
        if ids and set(authorised_documents(user).filter(id__in=ids).values_list("id", flat=True)) != ids: raise serializers.ValidationError({"document_ids": "One or more documents are inaccessible."})
        return attrs

class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=1, max_length=4000, trim_whitespace=True)
    document_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, max_length=50)
    top_k = serializers.IntegerField(min_value=1, required=False)
    def validate_question(self, value):
        if not value.strip(): raise serializers.ValidationError("Question cannot be empty.")
        return value
    def validate_document_ids(self, ids):
        qs = authorised_documents(self.context["request"].user).filter(id__in=ids); conversation = self.context.get("conversation")
        if conversation and conversation.course_id: qs = qs.filter(course_id=conversation.course_id)
        if conversation and conversation.lesson_id: qs = qs.filter(lesson_id=conversation.lesson_id)
        accessible = set(qs.values_list("id", flat=True))
        if accessible != set(ids): raise serializers.ValidationError("One or more documents are inaccessible.")
        return ids

class RetrievalResultItemSerializer(serializers.Serializer):
    chunk_id = serializers.IntegerField()
    score = serializers.FloatField()
    document_title = serializers.CharField()
    page = serializers.IntegerField(allow_null=True)
    section_title = serializers.CharField()

class RetrievalResultSerializer(serializers.Serializer):
    query = serializers.CharField()
    results = RetrievalResultItemSerializer(many=True)

class FlashcardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flashcard
        fields = "__all__"
        read_only_fields = ("easiness", "interval_days", "repetitions", "next_review_at", "total_reviews", "correct_reviews", "created_at", "updated_at")
    def validate(self, attrs):
        deck = attrs.get("deck", getattr(self.instance, "deck", None)); question = attrs.get("question", getattr(self.instance, "question", "")); answer = attrs.get("answer", getattr(self.instance, "answer", ""))
        if not question.strip(): raise serializers.ValidationError({"question": "Question cannot be empty."})
        if not answer.strip(): raise serializers.ValidationError({"answer": "Answer cannot be empty."})
        duplicate = Flashcard.objects.filter(deck=deck, question__iexact=question.strip(), answer__iexact=answer.strip())
        if self.instance: duplicate = duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists(): raise serializers.ValidationError("This card already exists in the deck.")
        course = attrs.get("course", getattr(self.instance, "course", None)); lesson = attrs.get("lesson", getattr(self.instance, "lesson", None)); concept = attrs.get("concept", getattr(self.instance, "concept", None))
        if lesson and course and lesson.module.course_id != course.id: raise serializers.ValidationError({"lesson": "Lesson and course must match."})
        if concept and course and concept.course_id and concept.course_id != course.id: raise serializers.ValidationError({"concept": "Concept and course must match."})
        user = self.context["request"].user
        if course and user.role == User.Role.STUDENT and not course.enrollments.filter(learner=user, status=Enrollment.Status.ACTIVE).exists(): raise serializers.ValidationError({"course": "You are not enrolled in this course."})
        return attrs
    def validate_deck(self, deck):
        if deck.owner_id != self.context["request"].user.id: raise serializers.ValidationError("You do not own this deck.")
        return deck
    def validate_source_documents(self, documents):
        user = self.context["request"].user
        if any(document.owner_id != user.id for document in documents): raise serializers.ValidationError("Every source document must belong to you.")
        return documents

class FlashcardDeckSerializer(serializers.ModelSerializer):
    cards = FlashcardSerializer(many=True, read_only=True)
    class Meta:
        model = FlashcardDeck
        fields = ("id", "owner", "name", "description", "topics", "cards", "created_at")
        read_only_fields = ("owner", "created_at")

class ReviewSerializer(serializers.Serializer):
    quality = serializers.IntegerField(min_value=0, max_value=5)
    idempotency_key = serializers.CharField(max_length=64, required=False, allow_blank=True)
    def save(self, **kwargs):
        card = self.context["card"]; quality = self.validated_data["quality"]; key = self.validated_data.get("idempotency_key", "")
        if key:
            existing = card.reviews.filter(idempotency_key=key).first()
            if existing: return card
        previous = card.interval_days
        card.total_reviews += 1
        if quality >= 3:
            card.correct_reviews += 1; card.repetitions += 1
            card.interval_days = 1 if card.repetitions == 1 else 6 if card.repetitions == 2 else max(1, round(card.interval_days * card.easiness))
        else:
            card.repetitions = 0; card.interval_days = 1
        card.easiness = max(1.3, card.easiness + (.1 - (5-quality) * (.08 + (5-quality) * .02)))
        card.next_review_at = timezone.now() + timedelta(days=card.interval_days); card.save(); FlashcardReview.objects.create(card=card, quality=quality, previous_interval_days=previous, next_interval_days=card.interval_days, idempotency_key=key); return card

class FlashcardReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlashcardReview
        fields = ("id", "quality", "reviewed_at", "previous_interval_days", "next_interval_days")
        read_only_fields = fields

class ScheduleBlockSerializer(serializers.ModelSerializer):
    warnings = serializers.SerializerMethodField()
    acknowledge_warnings = serializers.BooleanField(write_only=True, required=False, default=False)
    class Meta:
        model = ScheduleBlock
        fields = ("id", "routine", "activity_name", "start_time", "end_time", "category", "is_flexible", "notes", "recurrence", "weekday", "calendar_date", "timezone", "recurrence_start", "recurrence_end", "course", "is_active", "created_at", "updated_at", "warnings", "acknowledge_warnings")
        read_only_fields = ("created_at", "updated_at", "warnings")
    def get_warnings(self, obj) -> list[dict]: return overlap_warnings(obj)
    def validate(self, attrs):
        start = attrs.get("start_time", getattr(self.instance, "start_time", None)); end = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start and end and end <= start: raise serializers.ValidationError("end_time must be after start_time.")
        recurrence = attrs.get("recurrence", getattr(self.instance, "recurrence", ScheduleBlock.Recurrence.WEEKLY)); weekday = attrs.get("weekday", getattr(self.instance, "weekday", None)); date = attrs.get("calendar_date", getattr(self.instance, "calendar_date", None))
        if recurrence == ScheduleBlock.Recurrence.ONCE and not date: raise serializers.ValidationError({"calendar_date": "One-time blocks require a date."})
        if recurrence == ScheduleBlock.Recurrence.WEEKLY and weekday is None: raise serializers.ValidationError({"weekday": "Weekly blocks require a weekday."})
        recurrence_start = attrs.get("recurrence_start", getattr(self.instance, "recurrence_start", None)); recurrence_end = attrs.get("recurrence_end", getattr(self.instance, "recurrence_end", None))
        if recurrence_start and recurrence_end and recurrence_end < recurrence_start: raise serializers.ValidationError({"recurrence_end": "Recurrence end cannot precede its start."})
        tz = attrs.get("timezone", getattr(self.instance, "timezone", "UTC"))
        try: ZoneInfo(tz)
        except ZoneInfoNotFoundError: raise serializers.ValidationError({"timezone": "Use a valid IANA timezone name."})
        course = attrs.get("course", getattr(self.instance, "course", None)); user = self.context["request"].user
        if course and user.role == User.Role.STUDENT and not course.enrollments.filter(learner=user, status=Enrollment.Status.ACTIVE).exists(): raise serializers.ValidationError({"course": "You are not enrolled in this course."})
        return attrs
    def create(self, validated_data):
        validated_data.pop("acknowledge_warnings", None); return super().create(validated_data)
    def update(self, instance, validated_data):
        validated_data.pop("acknowledge_warnings", None); return super().update(instance, validated_data)
    def validate_routine(self, routine):
        if routine.owner_id != self.context["request"].user.id: raise serializers.ValidationError("You do not own this routine.")
        return routine

class RoutineSerializer(serializers.ModelSerializer):
    blocks = ScheduleBlockSerializer(many=True, read_only=True)
    class Meta:
        model = Routine
        fields = ("id", "owner", "name", "preferences", "is_active", "suggestions", "blocks", "created_at", "updated_at")
        read_only_fields = ("owner", "suggestions", "created_at", "updated_at")
