"""
ASGI config for feedback_project project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_project.settings')

application = get_asgi_application()
