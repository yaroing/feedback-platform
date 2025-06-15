# Ce fichier configure Celery
from __future__ import absolute_import, unicode_literals

# Cette instruction importe la configuration Celery définie dans celery.py
from .celery import app as celery_app

__all__ = ('celery_app',)
