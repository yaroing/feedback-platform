"""
Celery configuration for feedback_project.
"""

import os
from celery import Celery

# Définir la variable d'environnement par défaut pour les settings Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feedback_project.settings')

# Créer l'instance Celery
app = Celery('feedback_project')

# Utiliser la configuration Django pour Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Découverte automatique des tâches dans les applications Django
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
