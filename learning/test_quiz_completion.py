from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from accounts.models import User
from courses.models import Course, Lesson, Module, Quiz, QuizQuestion
from .models import Enrollment, QuizSubmission, QuizSubmissionAnswer

class AtomicQuizTests(APITestCase):
    def setUp(self):
        teacher = User.objects.create_user("quiz-teacher@example.com", "long-password", full_name="Teacher", role="instructor")
        self.student = User.objects.create_user("quiz-student@example.com", "long-password", full_name="Student")
        course = Course.objects.create(instructor=teacher, slug="atomic", title="Atomic", is_published=True)
        lesson = Lesson.objects.create(module=Module.objects.create(course=course, title="M", position=1), title="Quiz", position=1)
        self.quiz = Quiz.objects.create(lesson=lesson, title="Atomic quiz", pass_mark=50, maximum_attempts=1, is_published=True)
        self.one = QuizQuestion.objects.create(quiz=self.quiz, lesson=lesson, position=1, kind="multiple_choice", prompt="One", options=["A", "B"], correct_answer=1, points=2)
        self.two = QuizQuestion.objects.create(quiz=self.quiz, lesson=lesson, position=2, kind="true_false", prompt="Two", options=[], correct_answer=True, points=1)
        Enrollment.objects.create(learner=self.student, course=course)
        self.client.force_authenticate(self.student)

    def start(self):
        return self.client.post(reverse("quiz-submission-list"), {"quiz": self.quiz.id, "idempotency_key": "start-1"}, format="json")

    def test_atomic_grading_and_duplicate_protection(self):
        started = self.start(); self.assertEqual(started.status_code, 201)
        payload = {"idempotency_key": "submit-1", "answers": [{"question_id": self.one.id, "answer": 1}, {"question_id": self.two.id, "answer": False}]}
        result = self.client.post(reverse("quiz-submission-submit", args=(started.data["id"],)), payload, format="json")
        self.assertEqual(result.status_code, 200); self.assertEqual(result.data["total_score"], 2); self.assertAlmostEqual(result.data["percentage_score"], 66.666, places=2); self.assertTrue(result.data["passed"])
        self.assertEqual(self.client.post(reverse("quiz-submission-submit", args=(started.data["id"],)), payload, format="json").status_code, 400)
        self.assertEqual(self.start().status_code, 400)

    def test_invalid_answer_rolls_back_every_answer(self):
        started = self.start()
        result = self.client.post(reverse("quiz-submission-submit", args=(started.data["id"],)), {"answers": [{"question_id": self.one.id, "answer": 1}, {"question_id": 999999, "answer": True}]}, format="json")
        self.assertEqual(result.status_code, 400); self.assertFalse(QuizSubmissionAnswer.objects.filter(submission_id=started.data["id"]).exists())

    def test_duplicate_and_missing_questions_are_rejected(self):
        started = self.start(); url = reverse("quiz-submission-submit", args=(started.data["id"],))
        self.assertEqual(self.client.post(url, {"answers": [{"question_id": self.one.id, "answer": 1}, {"question_id": self.one.id, "answer": 1}]}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"answers": [{"question_id": self.one.id, "answer": 1}]}, format="json").status_code, 400)

    def test_availability_is_enforced(self):
        self.quiz.available_from = timezone.now() + timedelta(days=1); self.quiz.save()
        self.assertEqual(self.start().status_code, 400)

    def test_instructor_analytics_is_authorised_and_correct(self):
        started = self.start(); self.client.post(reverse("quiz-submission-submit", args=(started.data["id"],)), {"answers": [{"question_id": self.one.id, "answer": 1}, {"question_id": self.two.id, "answer": True}]}, format="json")
        self.client.force_authenticate(self.quiz.lesson.module.course.instructor)
        report = self.client.get(reverse("quiz-analytics", args=(self.quiz.id,)))
        self.assertEqual(report.status_code, 200); self.assertEqual(report.data["attempts"], 1); self.assertEqual(report.data["pass_rate"], 100)
