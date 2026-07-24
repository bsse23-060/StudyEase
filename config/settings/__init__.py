"""Select settings with DJANGO_ENV=development|test|production."""
import os

environment = os.environ.get("DJANGO_ENV", "development").lower()
if environment == "production":
    from .production import *  # noqa: F403
elif environment == "test":
    from .test import *  # noqa: F403
else:
    from .development import *  # noqa: F403
