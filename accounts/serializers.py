from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import AuditEvent, User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "role", "level_preference", "weekly_hours", "goal", "language_preference", "onboarding_data", "onboarded_at", "date_joined")
        read_only_fields = ("id", "role", "onboarded_at", "date_joined")

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password], style={"input_type": "password"})
    class Meta:
        model = User
        fields = ("id", "email", "full_name", "password", "level_preference")
        read_only_fields = ("id",)
    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ("id", "actor", "action", "target_type", "target_id", "request_id", "metadata", "created_at")
        read_only_fields = fields

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True)
