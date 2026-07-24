from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APITestCase
from accounts.models import User
from courses.models import Concept, Course, Lesson, Module, QuizQuestion
from .models import EngagementEvent, Enrollment, LearningProfile, Mastery, RoadmapStep

class AttemptTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("student@example.com", "long-password", full_name="Student")
        instructor = User.objects.create_user("teacher@example.com", "long-password", full_name="Teacher", role=User.Role.INSTRUCTOR)
        course = Course.objects.create(instructor=instructor, slug="math", title="Math", is_published=True)
        module = Module.objects.create(course=course, title="Basics", position=1)
        lesson = Lesson.objects.create(module=module, title="Addition", kind=Lesson.Kind.QUIZ, position=1)
        concept = Concept.objects.create(slug="addition", name="Addition")
        self.question = QuizQuestion.objects.create(lesson=lesson, concept=concept, kind=QuizQuestion.Kind.MULTIPLE_CHOICE, prompt="1+1", options=["1", "2"], correct_answer=1)
        self.enrollment = Enrollment.objects.create(learner=self.user, course=course)
    def test_submission_is_graded_and_updates_mastery(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("attempt-list"), {"question": self.question.pk, "answer": 1, "seconds_spent": 5}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["is_correct"])
        self.assertEqual(Mastery.objects.get(learner=self.user, concept=self.question.concept).probability, .4)
    def test_wrong_and_invalid_answers(self):
        self.client.force_authenticate(self.user)
        wrong = self.client.post(reverse("attempt-list"), {"question": self.question.pk, "answer": 0}, format="json")
        self.assertEqual(wrong.status_code, 201); self.assertFalse(wrong.data["is_correct"])
        self.assertEqual(self.client.post(reverse("attempt-list"), {"question": self.question.pk, "answer": 99}, format="json").status_code, 400)
    def test_unenrolled_student_cannot_attempt(self):
        other = User.objects.create_user("other@example.com", "long-password", full_name="Other"); self.client.force_authenticate(other)
        self.assertEqual(self.client.post(reverse("attempt-list"), {"question": self.question.pk, "answer": 1}, format="json").status_code, 400)
    def test_duplicate_enrollment_and_mastery_constraints(self):
        with self.assertRaises(IntegrityError), transaction.atomic(): Enrollment.objects.create(learner=self.user, course=self.enrollment.course)
        Mastery.objects.create(learner=self.user, concept=self.question.concept)
        with self.assertRaises(IntegrityError), transaction.atomic(): Mastery.objects.create(learner=self.user, concept=self.question.concept)
    def test_profiles_and_attempts_are_isolated(self):
        other = User.objects.create_user("other@example.com", "long-password", full_name="Other"); LearningProfile.objects.create(user=other)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get(reverse("learning-profile-list")).data["count"], 0)
        created = self.client.post(reverse("learning-profile-list"), {"pace": .7})
        self.assertEqual(created.status_code, 201); self.assertEqual(self.client.post(reverse("learning-profile-list"), {}).status_code, 400)
    def test_student_cannot_author_roadmap_but_can_complete_own(self):
        step = RoadmapStep.objects.create(enrollment=self.enrollment, module=self.question.lesson.module, position=1)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(reverse("roadmap-step-list"), {"enrollment": self.enrollment.pk, "module": step.module_id, "position": 2}).status_code, 403)
        self.assertEqual(self.client.post(reverse("roadmap-step-complete", args=(step.pk,))).status_code, 200)
    def test_event_module_must_be_in_active_enrollment(self):
        other_teacher = User.objects.create_user("t2@example.com", "long-password", full_name="T2", role=User.Role.INSTRUCTOR)
        other_course = Course.objects.create(instructor=other_teacher, slug="other", title="Other", is_published=True); other_module = Module.objects.create(course=other_course, title="Other", position=1)
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.post(reverse("event-list"), {"kind": "view", "module": other_module.pk}).status_code, 400)
        self.assertEqual(self.client.post(reverse("event-list"), {"kind": "view", "module": self.question.lesson.module_id}).status_code, 201)
