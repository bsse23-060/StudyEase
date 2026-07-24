from django.urls import reverse
from rest_framework.test import APITestCase
from accounts.models import User
from .models import Conversation, Flashcard, FlashcardDeck, Message, Routine

class StudyToolCompletionTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("completion@example.com", "long-password", full_name="Student")
        self.other = User.objects.create_user("completion-other@example.com", "long-password", full_name="Other")
        self.deck = FlashcardDeck.objects.create(owner=self.user, name="Deck")
        self.card = Flashcard.objects.create(deck=self.deck, question="Q", answer="A")
        self.client.force_authenticate(self.user)

    def test_flashcard_crud_duplicate_and_review_idempotency(self):
        self.assertEqual(self.client.post(reverse("flashcard-list"), {"deck": self.deck.id, "question": "", "answer": "A"}).status_code, 400)
        self.assertEqual(self.client.post(reverse("flashcard-list"), {"deck": self.deck.id, "question": "Q", "answer": "A"}).status_code, 400)
        url = reverse("flashcard-deck-review", args=(self.deck.id, self.card.id))
        self.client.post(url, {"quality": 5, "idempotency_key": "same"}); self.client.post(url, {"quality": 5, "idempotency_key": "same"})
        self.card.refresh_from_db(); self.assertEqual(self.card.total_reviews, 1)
        self.assertEqual(self.client.get(reverse("flashcard-reviews", args=(self.card.id,))).status_code, 200)
        other_deck = FlashcardDeck.objects.create(owner=self.other, name="Other")
        self.assertEqual(self.client.patch(reverse("flashcard-detail", args=(self.card.id,)), {"deck": other_deck.id}).status_code, 400)

    def test_schedule_recurrence_timezone_and_ownership(self):
        routine = Routine.objects.create(owner=self.user, name="Routine")
        base = {"routine": routine.id, "activity_name": "Study", "start_time": "09:00", "end_time": "10:00", "category": "study"}
        self.assertEqual(self.client.post(reverse("schedule-block-list"), {**base, "recurrence": "once"}).status_code, 400)
        self.assertEqual(self.client.post(reverse("schedule-block-list"), {**base, "recurrence": "weekly"}).status_code, 400)
        self.assertEqual(self.client.post(reverse("schedule-block-list"), {**base, "recurrence": "weekly", "weekday": 1, "timezone": "Not/AZone"}).status_code, 400)
        good = self.client.post(reverse("schedule-block-list"), {**base, "recurrence": "weekly", "weekday": 1, "timezone": "Asia/Karachi"})
        self.assertEqual(good.status_code, 201)

    def test_conversation_history_is_paginated_and_ordered(self):
        conversation = Conversation.objects.create(owner=self.user, title="Long")
        for index in range(40): Message.objects.create(conversation=conversation, role="user", content=str(index))
        response = self.client.get(reverse("conversation-history", args=(conversation.id,)))
        self.assertEqual(response.status_code, 200); self.assertEqual(len(response.data["results"]), 30); self.assertEqual(response.data["results"][0]["content"], "10"); self.assertEqual(response.data["results"][-1]["content"], "39")
        self.client.force_authenticate(self.other); self.assertEqual(self.client.get(reverse("conversation-history", args=(conversation.id,))).status_code, 404)
