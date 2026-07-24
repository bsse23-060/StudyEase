from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase
from accounts.models import User
from courses.models import Course, QuizQuestion
from learning.models import Enrollment, RoadmapStep
from study_tools.models import Conversation, DocumentChunk, FlashcardDeck

@override_settings(DEBUG=True)
class SeededJourneyTests(APITestCase):
    @classmethod
    def setUpTestData(cls): call_command("seed_demo", verbosity=0)

    def login(self, email):
        response = self.client.post(reverse("token_obtain_pair"), {"email": email, "password": "StudyEaseDemo123!"})
        self.assertEqual(response.status_code, 200); self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")

    def test_complete_student_journey(self):
        self.login("student1@studyease.local")
        courses = self.client.get(reverse("course-list")); self.assertGreaterEqual(courses.data["count"], 2)
        course = Course.objects.get(slug="python-foundations")
        self.assertEqual(self.client.get(reverse("course-detail", args=(course.pk,))).status_code, 200)
        module = course.modules.get(position=1); lesson = module.lessons.get(position=1)
        self.assertEqual(self.client.get(reverse("module-detail", args=(module.pk,))).status_code, 200)
        self.assertEqual(self.client.get(reverse("lesson-detail", args=(lesson.pk,))).status_code, 200)
        question = QuizQuestion.objects.get(lesson=lesson)
        attempt = self.client.post(reverse("attempt-list"), {"question": question.pk, "answer": question.correct_answer, "seconds_spent": 9}, format="json")
        self.assertEqual(attempt.status_code, 201); self.assertTrue(attempt.data["is_correct"])
        self.assertGreater(self.client.get(reverse("mastery-list")).data["count"], 0)
        self.assertGreater(self.client.get(reverse("roadmap-step-list")).data["count"], 0)
        deck = FlashcardDeck.objects.get(owner__email="student1@studyease.local")
        card = self.client.post(reverse("flashcard-list"), {"deck": deck.pk, "question": "What is mutability?", "answer": "Ability to change"})
        self.assertEqual(card.status_code, 201)
        self.assertEqual(self.client.post(reverse("flashcard-deck-review", args=(deck.pk, card.data["id"])), {"quality": 4}).status_code, 200)
        self.assertEqual(self.client.post(reverse("routine-list"), {"name": "Exam routine", "preferences": {"break_style": "pomodoro"}}, format="json").status_code, 201)
        conversation = self.client.post(reverse("conversation-list"), {"title": "More help", "course": course.pk})
        self.assertEqual(conversation.status_code, 201)
        seeded = Conversation.objects.get(owner__email="student1@studyease.local", title="Lists help")
        detail = self.client.get(reverse("conversation-detail", args=(seeded.pk,)))
        self.assertEqual(detail.data["messages"][0]["citations"][0]["document_title"], "Python Notes")

    def test_complete_instructor_journey_and_isolation(self):
        self.login("instructor1@studyease.local")
        course = self.client.post(reverse("course-list"), {"slug": "api-design", "title": "API Design", "description": "REST", "is_published": True})
        self.assertEqual(course.status_code, 201)
        module = self.client.post(reverse("module-list"), {"course": course.data["id"], "title": "HTTP", "position": 1}); self.assertEqual(module.status_code, 201)
        lesson = self.client.post(reverse("lesson-list"), {"module": module.data["id"], "title": "Methods", "kind": "quiz", "position": 1}); self.assertEqual(lesson.status_code, 201)
        base = self.client.post(reverse("concept-list"), {"slug": "http", "name": "HTTP", "lessons": [lesson.data["id"]]}); self.assertEqual(base.status_code, 201)
        advanced = self.client.post(reverse("concept-list"), {"slug": "http-methods", "name": "HTTP Methods", "lessons": [lesson.data["id"]], "prerequisites": [base.data["id"]]}); self.assertEqual(advanced.status_code, 201)
        question = self.client.post(reverse("question-list"), {"lesson": lesson.data["id"], "concept": advanced.data["id"], "kind": "multiple_choice", "prompt": "Which reads data?", "options": ["GET", "DELETE"], "correct_answer": 0}, format="json"); self.assertEqual(question.status_code, 201)
        students = self.client.get(reverse("user-list")); self.assertGreaterEqual(students.data["count"], 1)
        other_course = Course.objects.get(slug="web-foundations")
        self.assertEqual(self.client.patch(reverse("course-detail", args=(other_course.pk,)), {"title": "Hijacked"}).status_code, 403)

    def test_seed_command_is_idempotent(self):
        before = (User.objects.count(), Course.objects.count(), Enrollment.objects.count(), DocumentChunk.objects.count())
        call_command("seed_demo", verbosity=0)
        after = (User.objects.count(), Course.objects.count(), Enrollment.objects.count(), DocumentChunk.objects.count())
        self.assertEqual(before, after)
