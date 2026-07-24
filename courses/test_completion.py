from django.urls import reverse
from rest_framework.test import APITestCase
from accounts.models import User
from .models import Concept, Course, Lesson, Module, Quiz

class CompletedBuilderTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user("builder@example.com", "long-password", full_name="Builder", role="instructor")
        self.other = User.objects.create_user("other-builder@example.com", "long-password", full_name="Other", role="instructor")
        self.course = Course.objects.create(instructor=self.owner, slug="owned", title="Owned")
        self.other_course = Course.objects.create(instructor=self.other, slug="other-owned", title="Other")
        self.module = Module.objects.create(course=self.course, title="M", position=1)
        self.lesson = Lesson.objects.create(module=self.module, title="L", position=1)
        self.client.force_authenticate(self.owner)

    def test_quiz_crud_and_nested_ownership(self):
        created = self.client.post(reverse("quiz-list"), {"lesson": self.lesson.id, "title": "Assessment", "pass_mark": 70, "is_published": True})
        self.assertEqual(created.status_code, 201)
        other_lesson = Lesson.objects.create(module=Module.objects.create(course=self.other_course, title="Other", position=1), title="Other", position=1)
        self.assertEqual(self.client.post(reverse("quiz-list"), {"lesson": other_lesson.id, "title": "Attack"}).status_code, 400)
        self.assertEqual(self.client.patch(reverse("quiz-detail", args=(created.data["id"],)), {"title": "Updated"}).status_code, 200)
        self.assertEqual(self.client.delete(reverse("quiz-detail", args=(created.data["id"],))).status_code, 204)

    def test_concept_self_direct_indirect_and_cross_course_cycles(self):
        a = Concept.objects.create(created_by=self.owner, course=self.course, slug="completion-a", name="A")
        b = Concept.objects.create(created_by=self.owner, course=self.course, slug="completion-b", name="B")
        c = Concept.objects.create(created_by=self.owner, course=self.course, slug="completion-c", name="C")
        b.prerequisites.add(a); c.prerequisites.add(b)
        self.assertEqual(self.client.patch(reverse("concept-detail", args=(a.id,)), {"prerequisites": [a.id]}).status_code, 400)
        self.assertEqual(self.client.patch(reverse("concept-detail", args=(a.id,)), {"prerequisites": [b.id]}).status_code, 400)
        self.assertEqual(self.client.patch(reverse("concept-detail", args=(a.id,)), {"prerequisites": [c.id]}).status_code, 400)
        foreign = Concept.objects.create(created_by=self.other, course=self.other_course, slug="completion-foreign", name="Foreign")
        self.assertEqual(self.client.patch(reverse("concept-detail", args=(a.id,)), {"prerequisites": [foreign.id]}).status_code, 400)

    def test_valid_prerequisite_chain_and_student_denial(self):
        a = Concept.objects.create(created_by=self.owner, course=self.course, slug="valid-a", name="A")
        b = Concept.objects.create(created_by=self.owner, course=self.course, slug="valid-b", name="B")
        response = self.client.patch(reverse("concept-detail", args=(b.id,)), {"prerequisites": [a.id]})
        self.assertEqual(response.status_code, 200)
        student = User.objects.create_user("builder-student@example.com", "long-password", full_name="Student")
        self.client.force_authenticate(student)
        self.assertEqual(self.client.post(reverse("quiz-list"), {"lesson": self.lesson.id, "title": "Attack"}).status_code, 403)
