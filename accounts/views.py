from rest_framework import generics, permissions, response, viewsets
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.views import APIView
from rest_framework.throttling import AnonRateThrottle
from .models import AuditEvent, User
from .permissions import IsInstructorOrAdmin
from .serializers import AuditEventSerializer, LogoutSerializer, RegisterSerializer, UserSerializer

class RegistrationThrottle(AnonRateThrottle): scope = "registration"

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = (RegistrationThrottle,)

class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    def get_object(self): return self.request.user

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [IsInstructorOrAdmin]
    filterset_fields = ("role", "level_preference")
    search_fields = ("email", "full_name")
    def get_queryset(self):
        qs = self.queryset
        if self.request.user.role == User.Role.ADMIN or self.request.user.is_superuser:
            return qs
        return qs.filter(enrollments__course__instructor=self.request.user).distinct()

class LogoutView(APIView):
    serializer_class = LogoutSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data); serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["refresh"]
        try: RefreshToken(token).blacklist()
        except TokenError: return response.Response({"detail": "Invalid or expired refresh token."}, status=400)
        AuditEvent.objects.create(actor=request.user, action="auth.logout", request_id=getattr(request, "request_id", ""))
        return response.Response(status=204)

class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditEvent.objects.select_related("actor")
    serializer_class = AuditEventSerializer
    permission_classes = (permissions.IsAdminUser,)
    filterset_fields = ("action", "actor", "target_type")
