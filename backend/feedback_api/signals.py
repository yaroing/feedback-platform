from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Feedback, Response
from .tasks import classify_feedback, send_response_message


@receiver(post_save, sender=Feedback)
def trigger_feedback_classification(sender, instance, created, **kwargs):
    """
    Déclenche la classification automatique d'un nouveau feedback
    """
    if created:
        # Lancer la tâche de classification en arrière-plan
        classify_feedback.delay(instance.id)


@receiver(post_save, sender=Response)
def trigger_response_sending(sender, instance, created, **kwargs):
    """
    Déclenche l'envoi d'une réponse via le canal approprié
    """
    if created and instance.feedback.channel in ['sms', 'whatsapp']:
        # Lancer la tâche d'envoi en arrière-plan
        send_response_message.delay(instance.id)
