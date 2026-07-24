from locust import HttpUser, between, task


class AuthenticationThrottleUser(HttpUser):
    wait_time = between(0.1, 0.3)

    @task
    def invalid_login_is_throttled(self):
        with self.client.post(
            "/api/v1/auth/token/",
            json={"email": "nonexistent@example.test", "password": "deliberately-invalid"},
            name="invalid login throttle",
            catch_response=True,
        ) as response:
            if response.status_code in (401, 429): response.success()
            else: response.failure(f"unexpected status {response.status_code}")
