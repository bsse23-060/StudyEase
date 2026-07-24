from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from accounts.models import User
from courses.models import Course
from learning.models import Enrollment
from .models import Citation, Conversation, Document, DocumentChunk, Flashcard, FlashcardDeck, Message, Routine, ScheduleBlock

class FlashcardReviewTests(APITestCase):
    def test_review_updates_sm2_fields(self):
        user = User.objects.create_user("student@example.com", "long-password", full_name="Student")
        deck = FlashcardDeck.objects.create(owner=user, name="Python")
        card = Flashcard.objects.create(deck=deck, question="What is a list?", answer="A sequence")
        self.client.force_authenticate(user)
        response = self.client.post(reverse("flashcard-deck-review", args=(deck.pk, card.pk)), {"quality": 5}, format="json")
        self.assertEqual(response.status_code, 200)
        card.refresh_from_db()
        self.assertEqual(card.repetitions, 1)
        self.assertEqual(card.interval_days, 1)
    def test_new_cards_are_due_and_bad_quality_resets_schedule(self):
        user = User.objects.create_user("due@example.com", "long-password", full_name="Due"); deck = FlashcardDeck.objects.create(owner=user, name="Due"); card = Flashcard.objects.create(deck=deck, question="Q", answer="A", repetitions=3, interval_days=10)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(reverse("flashcard-deck-due", args=(deck.pk,))).data[0]["id"], card.pk)
        self.client.post(reverse("flashcard-deck-review", args=(deck.pk, card.pk)), {"quality": 1}); card.refresh_from_db()
        self.assertEqual((card.repetitions, card.interval_days), (0, 1))

class StudyToolOwnershipTests(APITestCase):
    def setUp(self):
        self.one = User.objects.create_user("one@example.com", "long-password", full_name="One")
        self.two = User.objects.create_user("two@example.com", "long-password", full_name="Two")
        self.doc_one = Document.objects.create(owner=self.one, title="One", source_url="https://example.com/one")
        self.doc_two = Document.objects.create(owner=self.two, title="Two", source_url="https://example.com/two")
        self.deck_one = FlashcardDeck.objects.create(owner=self.one, name="One")
        self.deck_two = FlashcardDeck.objects.create(owner=self.two, name="Two")
        self.routine_two = Routine.objects.create(owner=self.two, name="Two")
        self.client.force_authenticate(self.one)
    def test_documents_and_chunks_are_isolated(self):
        self.assertEqual(self.client.get(reverse("document-detail", args=(self.doc_two.pk,))).status_code, 404)
        denied = self.client.post(reverse("document-chunk-list"), {"document": self.doc_two.pk, "text": "stolen", "position": 1})
        self.assertEqual(denied.status_code, 405)
        allowed = self.client.post(reverse("document-chunk-list"), {"document": self.doc_one.pk, "text": "owned", "position": 1})
        self.assertEqual(allowed.status_code, 405)
    def test_document_requires_exactly_one_source_and_partial_update_works(self):
        neither = self.client.post(reverse("document-list"), {"title": "No source"})
        both = self.client.post(reverse("document-list"), {"title": "Both", "source_url": "https://example.com", "file": SimpleUploadedFile("x.txt", b"x")}, format="multipart")
        self.assertEqual(neither.status_code, 400); self.assertEqual(both.status_code, 400)
        self.assertEqual(self.client.patch(reverse("document-detail", args=(self.doc_one.pk,)), {"title": "Renamed"}).status_code, 200)
    def test_flashcard_cannot_move_or_link_across_owners(self):
        card = Flashcard.objects.create(deck=self.deck_one, question="Q", answer="A")
        self.assertEqual(self.client.patch(reverse("flashcard-detail", args=(card.pk,)), {"deck": self.deck_two.pk}).status_code, 400)
        self.assertEqual(self.client.patch(reverse("flashcard-detail", args=(card.pk,)), {"source_documents": [self.doc_two.pk]}).status_code, 400)
    def test_schedule_block_cannot_use_another_users_routine(self):
        response = self.client.post(reverse("schedule-block-list"), {"routine": self.routine_two.pk, "activity_name": "Attack", "start_time": "10:00", "end_time": "11:00", "category": "study"})
        self.assertEqual(response.status_code, 400)
    def test_conversations_and_structured_citations_are_isolated(self):
        chunk = DocumentChunk.objects.create(document=self.doc_one, text="Evidence", position=1)
        conversation = Conversation.objects.create(owner=self.one, title="Help"); message = Message.objects.create(conversation=conversation, role=Message.Role.ASSISTANT, content="Answer")
        Citation.objects.create(message=message, chunk=chunk, quote="Evidence", score=.9)
        other_conversation = Conversation.objects.create(owner=self.two, title="Private")
        response = self.client.get(reverse("conversation-detail", args=(conversation.pk,)))
        self.assertEqual(response.status_code, 200); self.assertEqual(response.data["messages"][0]["citations"][0]["chunk"], chunk.pk)
        self.assertEqual(self.client.get(reverse("conversation-detail", args=(other_conversation.pk,))).status_code, 404)
        posted = self.client.post(reverse("conversation-messages", args=(conversation.pk,)), {"content": "Follow up", "role": "assistant"})
        self.assertEqual(posted.status_code, 201); self.assertEqual(posted.data["role"], "user")
    def test_student_cannot_link_conversation_to_unenrolled_course(self):
        instructor = User.objects.create_user("teacher@example.com", "long-password", full_name="Teacher", role=User.Role.INSTRUCTOR)
        course = Course.objects.create(instructor=instructor, slug="private", title="Private", is_published=True)
        self.assertEqual(self.client.post(reverse("conversation-list"), {"title": "X", "course": course.pk}).status_code, 400)
        Enrollment.objects.create(learner=self.one, course=course)
        self.assertEqual(self.client.post(reverse("conversation-list"), {"title": "X", "course": course.pk}).status_code, 201)
    def test_routine_ordering_validation_and_pagination(self):
        routine = Routine.objects.create(owner=self.one, name="Mine")
        bad = self.client.post(reverse("schedule-block-list"), {"routine": routine.pk, "activity_name": "Bad", "start_time": "11:00", "end_time": "10:00", "category": "study"})
        self.assertEqual(bad.status_code, 400)
        self.assertIn("results", self.client.get(reverse("routine-list")).data)
