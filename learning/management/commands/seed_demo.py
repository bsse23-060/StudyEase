from datetime import time, timedelta
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from accounts.models import User
from courses.models import Concept, Course, Lesson, Module, Quiz, QuizQuestion
from learning.models import Enrollment, LearningProfile, Mastery, QuizAttempt, QuizSubmission, QuizSubmissionAnswer, RoadmapStep
from study_tools.models import Citation, Conversation, Document, DocumentChunk, Flashcard, FlashcardDeck, Message, Routine, ScheduleBlock
from study_tools.providers.embeddings.fake import DeterministicEmbeddingProvider
from django.conf import settings
import hashlib

PASSWORD = "StudyEaseDemo123!"

class Command(BaseCommand):
    help = "Create idempotent development-only demo data."

    def handle(self, *args, **options):
        if not settings.DEBUG: raise CommandError("seed_demo is disabled when DJANGO_DEBUG is false.")
        users = {}
        specs = (("admin", "admin@studyease.local", User.Role.ADMIN), ("instructor1", "instructor1@studyease.local", User.Role.INSTRUCTOR), ("instructor2", "instructor2@studyease.local", User.Role.INSTRUCTOR), ("student1", "student1@studyease.local", User.Role.STUDENT), ("student2", "student2@studyease.local", User.Role.STUDENT))
        for name, email, role in specs:
            user, _ = User.objects.get_or_create(email=email, defaults={"full_name": name.title(), "role": role})
            user.full_name = name.title(); user.role = role; user.is_staff = role == User.Role.ADMIN; user.is_superuser = role == User.Role.ADMIN; user.set_password(PASSWORD); user.save()
            users[name] = user

        python, _ = Course.objects.update_or_create(slug="python-foundations", defaults={"instructor": users["instructor1"], "title": "Python Foundations", "description": "Core Python programming.", "is_published": True})
        web, _ = Course.objects.update_or_create(slug="web-foundations", defaults={"instructor": users["instructor2"], "title": "Web Foundations", "description": "HTML and HTTP basics.", "is_published": True})
        py_module, _ = Module.objects.update_or_create(course=python, position=1, defaults={"title": "Python Basics", "summary": "Values, variables and collections."})
        web_module, _ = Module.objects.update_or_create(course=web, position=1, defaults={"title": "Web Basics", "summary": "Documents and requests."})
        py_lesson, _ = Lesson.objects.update_or_create(module=py_module, position=1, defaults={"title": "Lists", "kind": Lesson.Kind.QUIZ, "content": "Python lists are ordered mutable collections."})
        web_lesson, _ = Lesson.objects.update_or_create(module=web_module, position=1, defaults={"title": "HTML", "kind": Lesson.Kind.TEXT, "content": "HTML structures web documents."})
        variables, _ = Concept.objects.update_or_create(slug="variables", defaults={"created_by": users["instructor1"], "course": python, "name": "Variables", "description": "Names bound to values."})
        lists, _ = Concept.objects.update_or_create(slug="python-lists", defaults={"created_by": users["instructor1"], "course": python, "name": "Python Lists", "description": "Ordered mutable collections."})
        html, _ = Concept.objects.update_or_create(slug="html", defaults={"created_by": users["instructor2"], "course": web, "name": "HTML", "description": "HyperText Markup Language."})
        py_lesson.concepts.set((variables, lists)); web_lesson.concepts.set((html,)); lists.prerequisites.set((variables,))
        quiz, _ = Quiz.objects.update_or_create(lesson=py_lesson, defaults={"title": "Python Lists Check", "instructions": "Answer every question, then review before submitting.", "pass_mark": 60, "maximum_attempts": 3, "available_from": timezone.now() - timedelta(days=30), "available_until": timezone.now() + timedelta(days=365), "time_limit_minutes": 15, "is_published": True})
        question, _ = QuizQuestion.objects.update_or_create(lesson=py_lesson, prompt="Which brackets create a Python list?", defaults={"quiz": quiz, "position": 1, "concept": lists, "kind": QuizQuestion.Kind.MULTIPLE_CHOICE, "options": ["()", "[]", "{}"], "correct_answer": 1, "explanation": "List literals use square brackets.", "difficulty": .2})
        enrollment1, _ = Enrollment.objects.get_or_create(learner=users["student1"], course=python)
        Enrollment.objects.get_or_create(learner=users["student2"], course=web)
        users["student2"].enrollments.exclude(course=web).delete()
        for key in ("student1", "student2"): LearningProfile.objects.update_or_create(user=users[key], defaults={"modality": .6, "depth": .5, "pace": .5, "abstraction": .4, "preferred_time": .7})
        Mastery.objects.update_or_create(learner=users["student1"], concept=lists, defaults={"probability": .4, "stability_days": 1, "last_seen_at": timezone.now()})
        QuizAttempt.objects.filter(learner=users["student1"], question=question).delete()
        QuizAttempt.objects.create(learner=users["student1"], question=question, answer=1, is_correct=True, points_earned=1, seconds_spent=12, feedback=question.explanation)
        submission, _ = QuizSubmission.objects.get_or_create(learner=users["student1"], quiz=quiz, idempotency_key="seed-attempt", defaults={"status": QuizSubmission.Status.SUBMITTED, "submitted_at": timezone.now(), "total_score": 1, "maximum_score": 1, "percentage_score": 100, "passed": True})
        quiz.submissions.filter(learner__in=(users["student1"], users["student2"])).exclude(idempotency_key="seed-attempt").delete()
        QuizSubmissionAnswer.objects.get_or_create(submission=submission, question=question, defaults={"answer": 1, "is_correct": True, "points_earned": 1, "feedback": question.explanation})
        RoadmapStep.objects.update_or_create(enrollment=enrollment1, position=1, defaults={"module": py_module, "rationale": "Start with the language fundamentals."})
        embedding_provider = DeterministicEmbeddingProvider(settings.RAG_VECTOR_DIMENSIONS)
        document, _ = Document.objects.update_or_create(title="Python Notes", course=python, defaults={"owner": users["instructor1"], "visibility": Document.Visibility.COURSE, "source_url": "https://docs.python.org/3/tutorial/introduction.html", "status": Document.Status.READY, "topics": ["python", "lists"], "chunk_count": 1, "embedding_provider": embedding_provider.name, "embedding_model": embedding_provider.model, "embedding_dimensions": embedding_provider.dimensions})
        chunk_text = "Python lists may contain items of different types, preserve insertion order, and are mutable."
        chunk, _ = DocumentChunk.objects.update_or_create(document=document, processing_version=document.processing_version, position=0, defaults={"text": chunk_text, "page": 1, "section_title": "Lists", "character_count": len(chunk_text), "token_count": len(chunk_text.split()), "end_position": len(chunk_text), "content_checksum": hashlib.sha256(chunk_text.encode()).hexdigest(), "embedding": embedding_provider.embed_query(chunk_text), "embedding_model": embedding_provider.model, "embedding_dimensions": embedding_provider.dimensions, "is_active": True})
        document.chunks.exclude(pk=chunk.pk).update(is_active=False)
        broken_bytes = b"%PDF-corrupted-demo"
        failed_document, _ = Document.objects.update_or_create(title="Broken Demo Document", owner=users["instructor1"], defaults={"course": python, "visibility": Document.Visibility.COURSE, "source_url": "", "status": Document.Status.FAILED, "processing_error": "Demo extraction failure: corrupted PDF.", "original_filename": "broken-demo.pdf", "mime_type": "application/pdf", "file_size": len(broken_bytes), "checksum": hashlib.sha256(broken_bytes).hexdigest()})
        if not failed_document.file: failed_document.file.save("broken-demo.pdf", ContentFile(broken_bytes))
        conversation, _ = Conversation.objects.get_or_create(owner=users["student1"], title="Lists help", course=python)
        message, _ = Message.objects.get_or_create(conversation=conversation, role=Message.Role.ASSISTANT, content="A list is an ordered, mutable collection.")
        Citation.objects.update_or_create(message=message, chunk=chunk, defaults={"quote": chunk.text, "score": .95})
        conversation.messages.filter(content__startswith="Pagination demo message").delete()
        long_conversation, _ = Conversation.objects.get_or_create(owner=users["student1"], title="Long pagination demo", course=python)
        for index in range(45): Message.objects.get_or_create(conversation=long_conversation, role=Message.Role.USER if index % 2 == 0 else Message.Role.ASSISTANT, content=f"Pagination demo message {index:02d}.")
        deck, _ = FlashcardDeck.objects.get_or_create(owner=users["student1"], name="Python Review", defaults={"topics": ["python"]})
        card, _ = Flashcard.objects.update_or_create(deck=deck, question="Which brackets create a list?", defaults={"answer": "Square brackets: []", "course": python, "lesson": py_lesson, "concept": lists, "next_review_at": timezone.now(), "repetitions": 0, "interval_days": 0, "total_reviews": 0, "correct_reviews": 0})
        card.reviews.all().delete()
        Flashcard.objects.get_or_create(deck=deck, question="What is a tuple?", defaults={"answer": "An immutable ordered collection.", "course": python, "lesson": py_lesson, "concept": variables, "next_review_at": timezone.now() + timedelta(days=7)})
        card.source_documents.set((document,))
        routine, _ = Routine.objects.get_or_create(owner=users["student1"], name="Weekday Study", defaults={"preferences": {"break_style": "pomodoro"}})
        ScheduleBlock.objects.update_or_create(routine=routine, activity_name="Python practice", defaults={"start_time": time(18, 0), "end_time": time(18, 45), "category": "study", "recurrence": ScheduleBlock.Recurrence.WEEKLY, "weekday": 1, "timezone": "Asia/Karachi", "recurrence_start": timezone.localdate(), "course": python})
        ScheduleBlock.objects.update_or_create(routine=routine, activity_name="Mock exam", defaults={"start_time": time(10, 0), "end_time": time(11, 0), "category": "assessment", "recurrence": ScheduleBlock.Recurrence.ONCE, "calendar_date": timezone.localdate() + timedelta(days=3), "timezone": "Asia/Karachi", "course": python})
        self.stdout.write(self.style.SUCCESS(f"Demo data ready. All demo passwords: {PASSWORD}"))
