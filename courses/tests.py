from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APITestCase
from accounts.models import User
from learning.models import Enrollment
from .models import Concept, Course, Lesson, Module, QuizQuestion

class CoursePermissionTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner@example.com", "long-password", full_name="Owner", role=User.Role.INSTRUCTOR)
        self.other = User.objects.create_user("other@example.com", "long-password", full_name="Other", role=User.Role.INSTRUCTOR)
        self.course = Course.objects.create(instructor=self.owner, slug="python", title="Python")
    def test_other_instructor_cannot_edit_course(self):
        self.client.force_authenticate(self.other)
        response = self.client.patch(reverse("course-detail", args=(self.course.pk,)), {"title": "Taken over"})
        self.assertIn(response.status_code, (403, 404))
    def test_owner_can_edit_course(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(reverse("course-detail", args=(self.course.pk,)), {"title": "Advanced Python"})
        self.assertEqual(response.status_code, 200)
    def test_student_cannot_create_course_or_child_content(self):
        student = User.objects.create_user("student@example.com", "long-password", full_name="Student")
        self.client.force_authenticate(student)
        self.assertEqual(self.client.post(reverse("course-list"), {"slug": "x", "title": "X"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("module-list"), {"course": self.course.pk, "title": "X", "position": 1}).status_code, 403)
    def test_instructor_cannot_add_module_to_another_course(self):
        self.client.force_authenticate(self.other)
        response = self.client.post(reverse("module-list"), {"course": self.course.pk, "title": "Attack", "position": 1})
        self.assertEqual(response.status_code, 400)
    def test_unenrolled_student_cannot_read_modules_or_lessons(self):
        module = Module.objects.create(course=self.course, title="Private", position=1)
        lesson = Lesson.objects.create(module=module, title="Secret", position=1)
        student = User.objects.create_user("student@example.com", "long-password", full_name="Student")
        self.client.force_authenticate(student)
        self.assertEqual(self.client.get(reverse("module-detail", args=(module.pk,))).status_code, 404)
        self.assertEqual(self.client.get(reverse("lesson-detail", args=(lesson.pk,))).status_code, 404)
        Enrollment.objects.create(learner=student, course=self.course)
        self.assertEqual(self.client.get(reverse("lesson-detail", args=(lesson.pk,))).status_code, 200)
    def test_module_and_lesson_positions_are_unique(self):
        module = Module.objects.create(course=self.course, title="One", position=1)
        with self.assertRaises(IntegrityError), transaction.atomic(): Module.objects.create(course=self.course, title="Duplicate", position=1)
        Lesson.objects.create(module=module, title="One", position=1)
        with self.assertRaises(IntegrityError), transaction.atomic(): Lesson.objects.create(module=module, title="Duplicate", position=1)
    def test_question_validation_hides_answer_and_rejects_bad_index(self):
        module = Module.objects.create(course=self.course, title="One", position=1); lesson = Lesson.objects.create(module=module, title="Quiz", position=1)
        self.client.force_authenticate(self.owner)
        bad = self.client.post(reverse("question-list"), {"lesson": lesson.pk, "kind": "multiple_choice", "prompt": "?", "options": ["a", "b"], "correct_answer": 4}, format="json")
        self.assertEqual(bad.status_code, 400)
        good = self.client.post(reverse("question-list"), {"lesson": lesson.pk, "kind": "multiple_choice", "prompt": "?", "options": ["a", "b"], "correct_answer": 1}, format="json")
        self.assertEqual(good.status_code, 201); self.assertNotIn("correct_answer", good.data)
    def test_prerequisite_cycles_are_rejected(self):
        a = Concept.objects.create(slug="a", name="A"); b = Concept.objects.create(slug="b", name="B"); b.prerequisites.add(a)
        admin = User.objects.create_superuser("admin@example.com", "long-password", full_name="Admin"); self.client.force_authenticate(admin)
        self.assertEqual(self.client.patch(reverse("concept-detail", args=(a.pk,)), {"prerequisites": [b.pk]}).status_code, 400)
    def test_course_search_ordering_and_pagination(self):
        self.course.is_published = True; self.course.save(); Course.objects.create(instructor=self.owner, slug="django", title="Django", is_published=True)
        response = self.client.get(reverse("course-list"), {"search": "Django", "ordering": "title"})
        self.assertEqual(response.status_code, 200); self.assertEqual(response.data["count"], 1); self.assertIn("results", response.data)
