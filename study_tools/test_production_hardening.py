from datetime import date, time
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import AuditEvent, User
from courses.models import Course
from learning.models import Enrollment
from study_tools.models import Document, Routine, ScheduleBlock
from study_tools.services.malware import FakeScanner
from study_tools.services.schedule_overlap import overlap_warnings

class ProductionHardeningTests(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(email="teacher@x.test", password="LongPassword123!", full_name="Teacher", role="instructor")
        self.student = User.objects.create_user(email="student@x.test", password="LongPassword123!", full_name="Student")
        self.admin = User.objects.create_user(email="admin@x.test", password="LongPassword123!", full_name="Admin", role="admin")
        self.course = Course.objects.create(instructor=self.instructor, slug="secure-course", title="Secure course", is_published=True)
        self.client = APIClient()

    def test_archive_preserves_history_and_blocks_enrollment(self):
        Enrollment.objects.create(learner=self.student, course=self.course)
        self.client.force_authenticate(self.instructor)
        response = self.client.post(f"/api/v1/courses/{self.course.pk}/archive/")
        self.assertEqual(response.status_code, 200)
        self.course.refresh_from_db()
        self.assertTrue(self.course.is_archived)
        self.assertTrue(self.course.enrollments.filter(learner=self.student).exists())
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.post("/api/v1/enrollments/", {"course": self.course.pk}).status_code, 400)
        self.assertTrue(AuditEvent.objects.filter(action="course.archive", target_id=str(self.course.pk)).exists())

    def test_only_admin_role_restores(self):
        self.course.is_archived = True; self.course.save()
        self.client.force_authenticate(self.instructor)
        self.assertEqual(self.client.post(f"/api/v1/courses/{self.course.pk}/restore/").status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f"/api/v1/courses/{self.course.pk}/restore/").status_code, 200)

    def test_overlap_is_warning_and_adjacent_is_not(self):
        routine = Routine.objects.create(owner=self.student, name="Plan")
        first = ScheduleBlock.objects.create(routine=routine, activity_name="Math", start_time=time(9), end_time=time(10), category="study", weekday=0, timezone="UTC")
        overlapping = ScheduleBlock.objects.create(routine=routine, activity_name="Physics", start_time=time(9, 30), end_time=time(10, 30), category="study", weekday=0, timezone="UTC")
        adjacent = ScheduleBlock.objects.create(routine=routine, activity_name="English", start_time=time(10), end_time=time(11), category="study", weekday=0, timezone="UTC")
        self.assertEqual(overlap_warnings(first)[0]["conflicting_block_id"], overlapping.pk)
        self.assertNotIn(adjacent.pk, [item["conflicting_block_id"] for item in overlap_warnings(first)])

    def test_different_users_do_not_conflict(self):
        one = Routine.objects.create(owner=self.student, name="One")
        two = Routine.objects.create(owner=self.instructor, name="Two")
        block = ScheduleBlock.objects.create(routine=one, activity_name="Mine", start_time=time(9), end_time=time(10), category="study", calendar_date=date.today(), recurrence="once")
        ScheduleBlock.objects.create(routine=two, activity_name="Theirs", start_time=time(9), end_time=time(10), category="study", calendar_date=date.today(), recurrence="once")
        self.assertEqual(overlap_warnings(block), [])

    def test_fake_scanner_detects_eicar_and_clean(self):
        infected = SimpleUploadedFile("eicar.txt", b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE")
        clean = SimpleUploadedFile("notes.txt", b"safe study notes")
        self.assertEqual(FakeScanner().scan(infected).status, "infected")
        self.assertEqual(FakeScanner().scan(clean).status, "clean")

    def test_processing_rejects_unscanned_file(self):
        document = Document.objects.create(owner=self.student, title="Pending", file=SimpleUploadedFile("notes.txt", b"text"), scan_status="pending")
        from study_tools.services.document_processing import process_document
        with self.assertRaises(PermissionError): process_document(document.pk)

    def test_liveness_and_readiness(self):
        self.assertEqual(self.client.get("/health/live/").status_code, 200)
        self.assertEqual(self.client.get("/health/ready/").status_code, 200)

    def test_private_file_key_does_not_reuse_filename(self):
        self.client.force_authenticate(self.student)
        response = self.client.post("/api/v1/documents/", {"title": "Private", "file": SimpleUploadedFile("personal-name.txt", b"safe content", content_type="text/plain")}, format="multipart")
        self.assertEqual(response.status_code, 201)
        document = Document.objects.get(pk=response.data["id"])
        self.assertNotIn("personal-name", document.file.name)
