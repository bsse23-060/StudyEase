from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    use_in_migrations = True
    def create_user(self, email, password=None, **extra):
        if not email: raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password); user.save(using=self._db); return user
    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True); extra.setdefault("is_superuser", True); extra.setdefault("role", User.Role.ADMIN)
        if extra.get("is_staff") is not True or extra.get("is_superuser") is not True: raise ValueError("Superusers must have is_staff=True and is_superuser=True.")
        return self.create_user(email, password, **extra)

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        INSTRUCTOR = "instructor", "Instructor"
        ADMIN = "admin", "Admin"
    class Level(models.TextChoices):
        CHILD = "child", "Child"
        HIGHSCHOOL = "highschool", "High school"
        COLLEGE = "college", "College"
        EXPERT = "expert", "Expert"
    username = None
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.STUDENT)
    level_preference = models.CharField(max_length=16, choices=Level.choices, default=Level.COLLEGE)
    weekly_hours = models.PositiveSmallIntegerField(default=5)
    goal = models.CharField(max_length=255, blank=True)
    language_preference = models.CharField(max_length=16, default="auto")
    onboarding_data = models.JSONField(default=dict, blank=True)
    onboarded_at = models.DateTimeField(null=True, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]
    objects = UserManager()

class AuditEvent(models.Model):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_events")
    action = models.CharField(max_length=96, db_index=True)
    target_type = models.CharField(max_length=96, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    request_id = models.CharField(max_length=128, blank=True, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    class Meta:
        ordering = ("-created_at",)

    def delete(self, *args, **kwargs):
        raise TypeError("Audit events are append-only.")
