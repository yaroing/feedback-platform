from celery import shared_task
import logging
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

@shared_task
def send_response_message(response_id):
    """
    Envoie une réponse via le canal approprié (SMS ou WhatsApp)
    """
    from .models import Response, Feedback
    from .utils import send_sms_via_twilio, send_whatsapp
    
    try:
        # Récupérer la réponse
        response = Response.objects.get(id=response_id)
        feedback = response.feedback
        
        # Vérifier si nous avons un numéro de téléphone pour envoyer la réponse
        if not feedback.contact_phone:
            logger.error(f"Impossible d'envoyer la réponse {response_id}: pas de numéro de téléphone")
            return False
        
        # Préparer le message
        message_body = response.content
        
        # Ajouter un identifiant de feedback pour le suivi
        message_body = f"[Feedback #{feedback.id}] {message_body}"
        
        # Envoyer le message via le canal approprié
        result = None
        
        if feedback.channel == Feedback.ChannelChoices.SMS:
            result = send_sms_via_twilio(feedback.contact_phone, message_body)
            if result:
                logger.info(f"SMS envoyé à {feedback.contact_phone}, SID: {result['sid']}")
            
        elif feedback.channel == Feedback.ChannelChoices.WHATSAPP:
            # Utiliser l'API Facebook WhatsApp par défaut
            result = send_whatsapp(feedback.contact_phone, message_body, provider='facebook')
            if result:
                # Gérer différents formats de réponse selon le fournisseur
                if 'sid' in result:
                    logger.info(f"WhatsApp envoyé à {feedback.contact_phone} via Twilio, SID: {result['sid']}")
                elif 'id' in result:
                    logger.info(f"WhatsApp envoyé à {feedback.contact_phone} via Facebook, ID: {result['id']}")
                else:
                    logger.info(f"WhatsApp envoyé à {feedback.contact_phone}, détails: {result}")
        
        # Vérifier si l'envoi a réussi
        if result:
            # Marquer la réponse comme envoyée
            response.sent = True
            response.save()
            return True
        else:
            logger.error(f"Échec de l'envoi de la réponse {response_id} via {feedback.channel}")
            return False
    
    except Response.DoesNotExist:
        logger.error(f"Réponse {response_id} non trouvée")
        return False
    
    except TwilioRestException as e:
        logger.error(f"Erreur Twilio lors de l'envoi de la réponse {response_id}: {str(e)}")
        return False
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la réponse {response_id}: {str(e)}")
        return False


@shared_task
def classify_feedback(feedback_id):
    """
    Classifie automatiquement un feedback en utilisant NLP
    Utilise le module NLP pour suggérer une catégorie et une priorité
    """
    from .models import Feedback, Category, Log
    from .nlp import classify_feedback as nlp_classify
    
    try:
        feedback = Feedback.objects.get(id=feedback_id)
        
        # Utiliser le module NLP pour classifier le contenu
        classification_result = nlp_classify(feedback.content)
        
        # Récupérer la catégorie suggérée
        suggested_category_name = classification_result.get('category')
        confidence = classification_result.get('confidence', 0)
        
        # Définir la priorité basée sur l'analyse NLP
        suggested_priority = classification_result.get('priority', 'medium')
        if suggested_priority:
            feedback.priority = suggested_priority
        
        # Mettre à jour la catégorie si une suggestion a été faite avec confiance suffisante
        category_updated = False
        logger.info(f"Classification NLP: catégorie='{suggested_category_name}', confiance={confidence}")
        
        # Utiliser le seuil de confiance configurable depuis les paramètres
        from django.conf import settings
        confidence_threshold = settings.NLP_SETTINGS.get('CATEGORY_CONFIDENCE_THRESHOLD', 0.1)
        logger.info(f"Seuil de confiance pour la classification: {confidence_threshold}")
        
        if suggested_category_name and confidence > confidence_threshold:
            try:
                # Rechercher la catégorie par nom exact d'abord
                categories = Category.objects.filter(name=suggested_category_name)
                if not categories.exists():
                    # Si pas de correspondance exacte, essayer une correspondance partielle
                    logger.info(f"Pas de correspondance exacte pour '{suggested_category_name}', recherche partielle")
                    categories = Category.objects.filter(name__icontains=suggested_category_name)
                    
                if categories.exists():
                    feedback.category = categories.first()
                    category_updated = True
                    logger.info(f"Catégorie trouvée et attribuée: '{feedback.category.name}'")
                else:
                    logger.warning(f"Aucune catégorie trouvée pour '{suggested_category_name}'")
            except Exception as e:
                logger.warning(f"Erreur lors de la recherche de la catégorie '{suggested_category_name}': {str(e)}")
        else:
            logger.info(f"Confiance trop faible ({confidence}) ou catégorie non déterminée pour '{suggested_category_name}'")
        
        
        feedback.save()
        
        # Créer un log pour la classification automatique
        details = f"Classification automatique par NLP: "
        if category_updated:
            details += f"Catégorie '{feedback.category.name}' (confiance: {confidence:.2f}), "
        details += f"Priorité '{feedback.priority}'"
        
        Log.objects.create(
            feedback=feedback,
            action='categorized',
            details=details
        )
        
        logger.info(f"Feedback #{feedback.id} classifié automatiquement: {details}")
        return True
    
    except Feedback.DoesNotExist:
        logger.error(f"Feedback {feedback_id} non trouvé pour classification")
        return False
    
    except Exception as e:
        logger.error(f"Erreur lors de la classification du feedback {feedback_id}: {str(e)}")
        return False


@shared_task
def generate_weekly_report():
    """
    Génère et envoie un rapport hebdomadaire des feedbacks
    """
    from django.utils import timezone
    from datetime import timedelta
    from django.core.mail import send_mail
    from django.contrib.auth.models import User
    from .models import Feedback
    
    try:
        # Définir la période du rapport (dernière semaine)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)
        
        # Récupérer les statistiques
        total_feedbacks = Feedback.objects.filter(created_at__range=(start_date, end_date)).count()
        resolved_feedbacks = Feedback.objects.filter(
            created_at__range=(start_date, end_date),
            status=Feedback.StatusChoices.RESOLVED
        ).count()
        
        # Statistiques par canal
        channel_stats = {}
        for channel_choice in Feedback.ChannelChoices.choices:
            channel_code = channel_choice[0]
            channel_stats[channel_code] = Feedback.objects.filter(
                created_at__range=(start_date, end_date),
                channel=channel_code
            ).count()
        
        # Construire le contenu du rapport
        report_content = f"""
        Rapport Hebdomadaire des Feedbacks ({start_date.date()} - {end_date.date()})
        
        Total des feedbacks reçus: {total_feedbacks}
        Feedbacks résolus: {resolved_feedbacks}
        
        Répartition par canal:
        - Web: {channel_stats.get('web', 0)}
        - SMS: {channel_stats.get('sms', 0)}
        - WhatsApp: {channel_stats.get('whatsapp', 0)}
        
        Ce rapport a été généré automatiquement.
        """
        
        # Envoyer le rapport aux modérateurs
        moderators = User.objects.filter(groups__name='Moderators')
        moderator_emails = [user.email for user in moderators if user.email]
        
        if moderator_emails:
            send_mail(
                subject='Rapport Hebdomadaire des Feedbacks',
                message=report_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=moderator_emails,
                fail_silently=False,
            )
            
            logger.info(f"Rapport hebdomadaire envoyé à {len(moderator_emails)} modérateurs")
        else:
            logger.warning("Aucun modérateur avec email trouvé pour l'envoi du rapport")
        
        return True
    
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport hebdomadaire: {str(e)}")
        return False
