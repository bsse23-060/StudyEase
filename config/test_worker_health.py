import json
import io
import time
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from config.worker_health import bounded_redis_ping, record_worker_heartbeat, worker_status


class WorkerStatusTests(TestCase):
    @patch("config.worker_health.time.time", return_value=100.0)
    @patch("config.worker_health.health_redis")
    def test_multiple_workers_and_stale_worker(self, redis_factory, _time):
        redis = redis_factory.return_value
        redis.scan_iter.return_value = ["one", "two"]
        redis.get.side_effect = [json.dumps({"last_seen": 99, "queues": ["documents"]}), json.dumps({"last_seen": 50, "queues": ["documents"]})]
        with override_settings(WORKER_HEARTBEAT_STALE_SECONDS=15):
            result = worker_status()
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["healthy_workers"], 1)
        self.assertEqual(result["observed_workers"], 2)

    @patch("config.worker_health.health_redis")
    def test_missing_heartbeat(self, redis_factory):
        redis_factory.return_value.scan_iter.return_value = []
        self.assertEqual(worker_status()["status"], "unavailable")

    @patch("config.worker_health.health_redis")
    def test_record_heartbeat_contains_only_age_and_queue_metadata(self, redis_factory):
        record_worker_heartbeat("test-worker")
        key, payload = redis_factory.return_value.set.call_args.args[:2]
        self.assertEqual(key, "studyease:worker-heartbeat:test-worker")
        self.assertEqual(json.loads(payload)["queues"], ["documents"])

    @patch("config.worker_health.health_redis")
    def test_bounded_ping_returns_healthy_result(self, redis_factory):
        import config.worker_health as health
        health._health_future = None
        redis_factory.return_value.ping.return_value = True
        self.assertTrue(bounded_redis_ping())

    @override_settings(HEALTH_REDIS_TIMEOUT_SECONDS=0.01)
    @patch("config.worker_health.health_redis")
    def test_bounded_ping_times_out_without_spawning_repeated_work(self, redis_factory):
        import config.worker_health as health
        health._health_future = None
        redis_factory.return_value.ping.side_effect = lambda: time.sleep(0.05)
        self.assertFalse(bounded_redis_ping())
        first = health._health_future
        self.assertFalse(bounded_redis_ping())
        self.assertIs(first, health._health_future)

    @patch("config.health.worker_status", side_effect=ConnectionError)
    def test_admin_health_degrades_without_exposing_configuration(self, _status):
        admin = get_user_model().objects.create_superuser(email="health@example.test", password="safe-test-password")
        client = APIClient(); client.force_authenticate(admin)
        response = client.get("/api/v1/admin/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "degraded")
        self.assertNotIn("broker", str(response.json()).lower())

    @override_settings(HEALTH_REQUIRE_REDIS=True)
    @patch("config.health.bounded_redis_ping", return_value=False)
    def test_readiness_fails_when_health_redis_is_unavailable(self, _ping):
        response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["checks"]["redis"], "unavailable")

    def test_load_token_command_creates_distinct_synthetic_users(self):
        from django.core.management import call_command
        output = io.StringIO()
        call_command("generate_load_tokens", count=2, stdout=output)
        payload = json.loads(output.getvalue())
        self.assertEqual(len(payload), 2)
        self.assertNotEqual(payload[0]["refresh"], payload[1]["refresh"])
