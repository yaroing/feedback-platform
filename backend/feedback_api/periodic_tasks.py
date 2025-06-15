from django.utils import timezone
from datetime import timedelta
from celery import shared_task
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django.db import transaction

from feedback_api.advanced_tasks import (
    check_active_nlp_models, 
    process_pending_notifications
)

@shared_task
def setup_periodic_tasks():
    """
    Configure les tâches périodiques pour l'application.
    Cette fonction est appelée au démarrage de l'application pour s'assurer
    que toutes les tâches périodiques sont correctement configurées.
    """
    # Supprime les anciennes tâches pour éviter les duplications
    PeriodicTask.objects.filter(
        name__in=[
            'check_active_nlp_models_hourly',
            'process_pending_notifications_every_5_minutes'
        ]
    ).delete()
    
    # Crée ou récupère les intervalles de temps
    hourly_schedule, _ = IntervalSchedule.objects.get_or_create(
        every=1,
        period=IntervalSchedule.HOURS,
    )
    
    five_minutes_schedule, _ = IntervalSchedule.objects.get_or_create(
        every=5,
        period=IntervalSchedule.MINUTES,
    )
    
    # Crée ou récupère les horaires cron
    midnight_schedule, _ = CrontabSchedule.objects.get_or_create(
        minute='0',
        hour='0',
        day_of_week='*',
        day_of_month='*',
        month_of_year='*',
    )
    
    # Tâche pour vérifier les modèles NLP actifs toutes les heures
    PeriodicTask.objects.create(
        name='check_active_nlp_models_hourly',
        task='feedback_api.advanced_tasks.check_active_nlp_models',
        interval=hourly_schedule,
        args='[]',
        kwargs='{}',
        description='Vérifie les modèles NLP actifs toutes les heures et les entraîne si nécessaire',
        enabled=True,
    )
    
    # Tâche pour traiter les notifications en attente toutes les 5 minutes
    PeriodicTask.objects.create(
        name='process_pending_notifications_every_5_minutes',
        task='feedback_api.advanced_tasks.process_pending_notifications',
        interval=five_minutes_schedule,
        args='[]',
        kwargs='{}',
        description='Traite les notifications en attente toutes les 5 minutes',
        enabled=True,
    )
    
    # Ajouter d'autres tâches périodiques ici si nécessaire
    
    return {
        'status': 'success',
        'message': 'Tâches périodiques configurées avec succès',
        'timestamp': timezone.now().isoformat()
    }


def register_periodic_tasks():
    """
    Fonction à appeler dans le fichier ready() de AppConfig pour configurer les tâches périodiques
    au démarrage de l'application.
    """
    # Utilise transaction.on_commit pour s'assurer que les tâches sont créées après la migration
    transaction.on_commit(lambda: setup_periodic_tasks.delay())
