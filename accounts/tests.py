from datetime import timedelta
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from .models import User

class AuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("student1@example.com", "ValidPass123!", full_name="Student One")
    def test_registration_hashes_password_and_forces_student_role(self):
        response = self.client.post(reverse("register"), {"email": "new@example.com", "full_name": "New", "password": "ComplexPass123!", "level_preference": "college"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = User.objects.get(email="new@example.com")
        self.assertTrue(created.check_password("ComplexPass123!")); self.assertEqual(created.role, User.Role.STUDENT)
    def test_login_access_refresh_and_profile_update(self):
        token = self.client.post(reverse("token_obtain_pair"), {"email": self.user.email, "password": "ValidPass123!"})
        self.assertEqual(token.status_code, 200); self.assertIn("refresh", token.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.data['access']}")
        me = self.client.patch(reverse("me"), {"goal": "Learn APIs", "role": "admin"})
        self.assertEqual(me.status_code, 200); self.assertEqual(me.data["goal"], "Learn APIs"); self.assertEqual(me.data["role"], "student")
        refreshed = self.client.post(reverse("token_refresh"), {"refresh": token.data["refresh"]})
        self.assertEqual(refreshed.status_code, 200); self.assertIn("access", refreshed.data)
    def test_invalid_credentials_and_tokens_are_rejected(self):
        self.assertEqual(self.client.post(reverse("token_obtain_pair"), {"email": self.user.email, "password": "wrong"}).status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION="Bearer broken")
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)
        expired = AccessToken.for_user(self.user); expired.set_exp(lifetime=timedelta(seconds=-1))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired}")
        self.assertEqual(self.client.get(reverse("me")).status_code, 401)
    def test_admin_sees_all_users_instructor_only_own_students(self):
        admin = User.objects.create_superuser("admin@example.com", "ValidPass123!", full_name="Admin")
        instructor = User.objects.create_user("teacher@example.com", "ValidPass123!", full_name="Teacher", role=User.Role.INSTRUCTOR)
        self.client.force_authenticate(instructor); self.assertEqual(self.client.get(reverse("user-list")).data["count"], 0)
        self.client.force_authenticate(admin); self.assertGreaterEqual(self.client.get(reverse("user-list")).data["count"], 3)
