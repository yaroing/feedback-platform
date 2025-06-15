from django.apps import AppConfig


class FeedbackApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'feedback_api'
    
    def ready(self):
        import feedback_api.signals  # Importer les signaux
        
        # Enregistrer les tâches périodiques
        # Uniquement en mode serveur, pas pendant les migrations
        import sys
        if 'runserver' in sys.argv or 'celery' in sys.argv:
            from feedback_api.periodic_tasks import register_periodic_tasks
            register_periodic_tasks()
