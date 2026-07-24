import itertools
import json
import os
from pathlib import Path
from locust import HttpUser, between, task

_tokens_path = os.environ.get("LOAD_TOKENS_FILE", "/mnt/locust/results/tokens.json")
_tokens = json.loads(Path(_tokens_path).read_text(encoding="utf-8")) if Path(_tokens_path).exists() else []
_token_pool = itertools.cycle(_tokens) if _tokens else None

class StudyEaseUser(HttpUser):
    wait_time = between(1, 3)
    def on_start(self):
        if _token_pool:
            token = next(_token_pool)
            self.access = token["access"]
            self.refresh = token["refresh"]
            self.client.headers["Authorization"] = f"Bearer {self.access}"
            return
        credentials = {"email": "student1@studyease.local", "password": "StudyEaseDemo123!"}
        response = self.client.post("/api/v1/auth/token/", json=credentials, name="login")
        if response.ok:
            self.access = response.json()["access"]; self.refresh = response.json()["refresh"]
            self.client.headers["Authorization"] = f"Bearer {self.access}"
        else:
            self.environment.runner.quit()
    @task(4)
    def catalogue(self): self.client.get("/api/v1/courses/", name="course catalogue")
    @task(2)
    def conversations(self): self.client.get("/api/v1/conversations/", name="conversation list")
    @task(1)
    def documents(self): self.client.get("/api/v1/documents/", name="document status")

    @task(1)
    def refresh_token(self):
        if os.environ.get("LOAD_ENABLE_REFRESH") != "1": return
        if not getattr(self, "refresh", None): return
        response = self.client.post("/api/v1/auth/token/refresh/", json={"refresh": self.refresh}, name="token refresh")
        if response.ok:
            data = response.json(); self.access = data["access"]; self.refresh = data.get("refresh", self.refresh)
            self.client.headers["Authorization"] = f"Bearer {self.access}"
