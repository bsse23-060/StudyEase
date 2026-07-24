from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class StudyEaseUserAdmin(UserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (("studyEase", {"fields": ("full_name", "role", "level_preference", "weekly_hours", "goal", "language_preference", "onboarding_data", "onboarded_at")}),)
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "full_name", "password1", "password2", "role")}),)
