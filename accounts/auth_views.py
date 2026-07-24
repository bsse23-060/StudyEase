from accounts.models import AuditEvent
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

class AuthThrottle(AnonRateThrottle): scope = "auth"

class AuditedTokenObtainPairView(TokenObtainPairView):
    throttle_classes = (AuthThrottle,)
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        AuditEvent.objects.create(action="auth.login_success" if response.status_code < 400 else "auth.login_failure", request_id=getattr(request, "request_id", ""), metadata={"email_hash_recorded": False})
        return response

class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_classes = (AuthThrottle,)
