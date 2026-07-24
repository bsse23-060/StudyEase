import json

from django.core.management.base import BaseCommand
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


class Command(BaseCommand):
    help = "Generate short-lived local load-test tokens for pre-created synthetic users."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=25)

    def handle(self, *args, **options):
        tokens = []
        for index in range(1, options["count"] + 1):
            user, _ = User.objects.get_or_create(email=f"load{index}@example.test", defaults={"role": User.Role.STUDENT})
            refresh = RefreshToken.for_user(user)
            tokens.append({"access": str(refresh.access_token), "refresh": str(refresh)})
        self.stdout.write(json.dumps(tokens))
