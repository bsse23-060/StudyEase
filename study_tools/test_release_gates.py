import io
import socket
from unittest.mock import Mock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from study_tools.services.locking import document_lock
from study_tools.services.malware import ClamAVScanner


class LockOwnershipTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_active_lock_cannot_be_stolen_and_owner_releases(self):
        with document_lock("release-gate-lock", "owner-one", 10) as first:
            self.assertTrue(first)
            with document_lock("release-gate-lock", "owner-two", 10) as second:
                self.assertFalse(second)
            self.assertEqual(cache.get("release-gate-lock"), "owner-one")
        self.assertIsNone(cache.get("release-gate-lock"))

    def test_expired_lock_can_be_reacquired(self):
        cache.set("release-gate-lock", "stale", timeout=0.001)
        import time; time.sleep(0.01)
        with document_lock("release-gate-lock", "new-owner", 10) as acquired:
            self.assertTrue(acquired)


@override_settings(CLAMAV_TIMEOUT_SECONDS=0.1, CLAMAV_HOST="scanner", CLAMAV_PORT=3310)
class ClamAVProtocolFailureTests(SimpleTestCase):
    @patch("study_tools.services.malware.socket.create_connection")
    def test_malformed_response_is_never_clean(self, connect):
        client = Mock(); client.__enter__ = Mock(return_value=client); client.__exit__ = Mock(return_value=False)
        client.recv.return_value = b"malformed response\0"; connect.return_value = client
        result = ClamAVScanner().scan(io.BytesIO(b"safe test data"))
        self.assertEqual(result.status, "suspicious")

    @patch("study_tools.services.malware.socket.create_connection", side_effect=socket.timeout)
    def test_timeout_propagates_for_bounded_task_retry(self, _connect):
        with self.assertRaises(socket.timeout): ClamAVScanner().scan(io.BytesIO(b"safe test data"))

    @patch("study_tools.services.malware.socket.create_connection")
    def test_unexpected_close_is_never_clean(self, connect):
        client = Mock(); client.__enter__ = Mock(return_value=client); client.__exit__ = Mock(return_value=False)
        client.recv.return_value = b""; connect.return_value = client
        result = ClamAVScanner().scan(io.BytesIO(b"safe test data"))
        self.assertEqual(result.status, "suspicious")
