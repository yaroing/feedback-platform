from celery import shared_task
import logging
import json
import os
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.core.mail import send_mail
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .models import (
    Feedback, NLPModel, NLPTrainingData, KeywordRule, 
    Alert, Notification, NotificationChannel, NotificationTemplate
)
from .utils import send_sms_via_twilio, send_whatsapp

logger = logging.getLogger(__name__)


@shared_task
def train_nlp_model(model_id):
    """
    Entraîne un modèle NLP avec les données d'entraînement validées
    """
    try:
        model = NLPModel.objects.get(id=model_id)
        training_data = NLPTrainingData.objects.filter(is_validated=True)
        
        if not training_data.exists():
            logger.error(f"Pas de données d'entraînement validées disponibles pour le modèle {model_id}")
            return False
        
        # Préparer les données d'entraînement
        training_texts = []
        training_labels = []
        
        for data in training_data:
            training_texts.append(data.content)
            training_labels.append(data.category.name)
        
        # Ici, vous intégreriez votre code d'entraînement NLP
        # Par exemple, avec scikit-learn, spaCy, ou une autre bibliothèque
        
        # Exemple simplifié (à remplacer par votre implémentation réelle)
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import Pipeline
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        import pickle
        
        # Créer un pipeline de classification
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000)),
            ('clf', MultinomialNB())
        ])
        
        # Entraîner le modèle
        pipeline.fit(training_texts, training_labels)
        
        # Évaluer le modèle (idéalement avec un ensemble de validation)
        # Pour simplifier, nous utilisons les mêmes données
        predictions = pipeline.predict(training_texts)
        
        # Calculer les métriques
        accuracy = accuracy_score(training_labels, predictions)
        precision = precision_score(training_labels, predictions, average='weighted', zero_division=0)
        recall = recall_score(training_labels, predictions, average='weighted', zero_division=0)
        f1 = f1_score(training_labels, predictions, average='weighted', zero_division=0)
        
        # Sauvegarder le modèle entraîné
        model_path = os.path.join(settings.MEDIA_ROOT, 'nlp_models', f'model_{model.id}.pkl')
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        with open(model_path, 'wb') as f:
            pickle.dump(pipeline, f)
        
        # Mettre à jour les métriques du modèle
        model.accuracy = accuracy
        model.precision = precision
        model.recall = recall
        model.f1_score = f1
        model.training_data_size = training_data.count()
        model.last_trained = timezone.now()
        model.file.name = f'nlp_models/model_{model.id}.pkl'
        model.save()
        
        logger.info(f"Modèle NLP {model.id} entraîné avec succès. Accuracy: {accuracy:.2f}")
        return True
        
    except NLPModel.DoesNotExist:
        logger.error(f"Modèle NLP {model_id} non trouvé")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'entraînement du modèle NLP {model_id}: {str(e)}")
        return False


@shared_task
def apply_keyword_rules(feedback_id):
    """
    Applique les règles de mots-clés à un feedback pour suggérer une catégorie
    """
    try:
        feedback = Feedback.objects.get(id=feedback_id)
        content = feedback.content.lower()
        
        # Récupérer toutes les règles de mots-clés
        rules = KeywordRule.objects.all()
        
        best_match = None
        highest_confidence = 0
        
        for rule in rules:
            keywords = rule.keywords
            matches = 0
            
            # Vérifier combien de mots-clés correspondent
            for keyword in keywords:
                if keyword.lower() in content:
                    matches += 1
            
            # Calculer un score de confiance simple
            if matches > 0 and len(keywords) > 0:
                confidence = (matches / len(keywords)) + rule.confidence_boost
                
                # Si cette règle donne une meilleure confiance, la retenir
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = rule
        
        # Appliquer la meilleure règle si elle existe
        if best_match and highest_confidence > 0.5:  # Seuil de confiance
            feedback.category = best_match.category
            feedback.auto_categorized = True
            feedback.confidence_score = highest_confidence
            
            # Appliquer la priorité si définie dans la règle
            if best_match.priority:
                feedback.priority = best_match.priority
                
            feedback.save()
            
            logger.info(f"Feedback {feedback_id} catégorisé automatiquement: {best_match.category.name} (confiance: {highest_confidence:.2f})")
            return True
        else:
            logger.info(f"Aucune règle de mots-clés ne correspond au feedback {feedback_id} avec une confiance suffisante")
            return False
            
    except Feedback.DoesNotExist:
        logger.error(f"Feedback {feedback_id} non trouvé")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'application des règles de mots-clés au feedback {feedback_id}: {str(e)}")
        return False


@shared_task
def send_alert(alert_id):
    """
    Envoie une alerte aux destinataires spécifiés
    """
    try:
        alert = Alert.objects.get(id=alert_id)
        
        # Vérifier que l'alerte est approuvée
        if alert.status != Alert.StatusChoices.APPROVED:
            logger.error(f"Impossible d'envoyer l'alerte {alert_id}: elle n'est pas approuvée")
            return False
        
        # Récupérer les destinataires
        recipients = alert.recipients.all()
        
        # Préparer le contenu de l'alerte
        subject = f"ALERTE {alert.severity.upper()}: {alert.title}"
        content = f"""
        {alert.description}
        
        Région concernée: {alert.region}
        Sévérité: {alert.severity}
        
        Cette alerte concerne le feedback #{alert.feedback.id}.
        """
        
        # Envoyer l'alerte par email à tous les destinataires
        recipient_emails = [user.email for user in recipients if user.email]
        if recipient_emails:
            send_mail(
                subject,
                content,
                settings.DEFAULT_FROM_EMAIL,
                recipient_emails,
                fail_silently=False,
            )
        
        # Créer des notifications dans l'application pour chaque destinataire
        for user in recipients:
            Notification.objects.create(
                user=user,
                title=subject,
                content=content,
                link=f"/feedback/{alert.feedback.id}",
                status=Notification.StatusChoices.SENT
            )
        
        # Marquer l'alerte comme envoyée
        alert.status = Alert.StatusChoices.SENT
        alert.sent_at = timezone.now()
        alert.save()
        
        logger.info(f"Alerte {alert_id} envoyée à {len(recipients)} destinataires")
        return True
        
    except Alert.DoesNotExist:
        logger.error(f"Alerte {alert_id} non trouvée")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'alerte {alert_id}: {str(e)}")
        return False


@shared_task
def send_notification(notification_id):
    """
    Envoie une notification via le canal spécifié
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Vérifier que la notification n'a pas déjà été envoyée
        if notification.status != Notification.StatusChoices.PENDING:
            logger.error(f"Notification {notification_id} déjà envoyée ou annulée")
            return False
        
        # Récupérer le canal de notification
        channel = notification.channel
        
        # Envoyer la notification via le canal approprié
        result = False
        
        if channel.channel_type == NotificationChannel.ChannelChoices.EMAIL:
            # Envoyer par email
            result = send_notification_email(notification)
            
        elif channel.channel_type == NotificationChannel.ChannelChoices.SMS:
            # Envoyer par SMS
            result = send_notification_sms(notification)
            
        elif channel.channel_type == NotificationChannel.ChannelChoices.WHATSAPP:
            # Envoyer par WhatsApp
            result = send_notification_whatsapp(notification)
            
        elif channel.channel_type == NotificationChannel.ChannelChoices.PUSH:
            # Envoyer une notification push
            result = send_notification_push(notification)
            
        # Mettre à jour le statut de la notification
        if result:
            notification.status = Notification.StatusChoices.SENT
            notification.sent_at = timezone.now()
            notification.save()
            logger.info(f"Notification {notification_id} envoyée via {channel.channel_type}")
            return True
        else:
            logger.error(f"Échec de l'envoi de la notification {notification_id} via {channel.channel_type}")
            return False
            
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} non trouvée")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la notification {notification_id}: {str(e)}")
        return False


def send_notification_email(notification):
    """Envoie une notification par email"""
    try:
        user = notification.user
        if not user.email:
            logger.error(f"Impossible d'envoyer la notification {notification.id} par email: utilisateur sans email")
            return False
        
        send_mail(
            notification.title,
            notification.content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email pour la notification {notification.id}: {str(e)}")
        return False


def send_notification_sms(notification):
    """Envoie une notification par SMS"""
    try:
        # Récupérer le numéro de téléphone de l'utilisateur
        user_profile = notification.user.userprofile
        if not user_profile.phone_number:
            logger.error(f"Impossible d'envoyer la notification {notification.id} par SMS: utilisateur sans numéro de téléphone")
            return False
        
        # Préparer le message
        message = f"{notification.title}\n\n{notification.content}"
        
        # Envoyer le SMS via Twilio
        result = send_sms_via_twilio(user_profile.phone_number, message)
        return bool(result)
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du SMS pour la notification {notification.id}: {str(e)}")
        return False


def send_notification_whatsapp(notification):
    """Envoie une notification par WhatsApp"""
    try:
        # Récupérer le numéro de téléphone de l'utilisateur
        user_profile = notification.user.userprofile
        if not user_profile.phone_number:
            logger.error(f"Impossible d'envoyer la notification {notification.id} par WhatsApp: utilisateur sans numéro de téléphone")
            return False
        
        # Préparer le message
        message = f"{notification.title}\n\n{notification.content}"
        
        # Envoyer le message WhatsApp
        result = send_whatsapp(user_profile.phone_number, message)
        return bool(result)
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du WhatsApp pour la notification {notification.id}: {str(e)}")
        return False


def send_notification_push(notification):
    """Envoie une notification push"""
    try:
        # Ici, vous intégreriez votre code pour envoyer une notification push
        # Par exemple, avec Firebase Cloud Messaging ou une autre solution
        
        # Pour l'instant, nous simulons un succès
        logger.info(f"Notification push simulée pour {notification.id}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de la notification push pour {notification.id}: {str(e)}")
        return False


@shared_task
def test_notification_channel(channel_id):
    """
    Teste un canal de notification en envoyant un message de test
    """
    try:
        channel = NotificationChannel.objects.get(id=channel_id)
        
        # Créer un message de test
        test_title = f"Test du canal {channel.name}"
        test_content = f"Ceci est un message de test envoyé le {timezone.now().strftime('%d/%m/%Y à %H:%M')}."
        
        # Créer une notification de test pour l'administrateur
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            logger.error(f"Impossible de tester le canal {channel_id}: aucun administrateur trouvé")
            return False
        
        notification = Notification.objects.create(
            user=admin,
            title=test_title,
            content=test_content,
            channel=channel,
            status=Notification.StatusChoices.PENDING
        )
        
        # Envoyer la notification de test
        send_notification.delay(notification.id)
        
        logger.info(f"Test du canal {channel_id} lancé")
        return True
        
    except NotificationChannel.DoesNotExist:
        logger.error(f"Canal de notification {channel_id} non trouvé")
        return False
    except Exception as e:
        logger.error(f"Erreur lors du test du canal de notification {channel_id}: {str(e)}")
        return False


@shared_task
def check_active_nlp_models():
    """
    Vérifie les modèles NLP actifs et effectue des actions de maintenance si nécessaire
    Cette tâche est exécutée périodiquement via Celery Beat
    """
    try:
        from .models import NLPModel
        
        # Vérifier s'il y a un modèle actif
        active_model = NLPModel.objects.filter(is_active=True).first()
        
        if not active_model:
            # Activer le modèle avec le meilleur score F1 s'il n'y a pas de modèle actif
            best_model = NLPModel.objects.filter(is_trained=True).order_by('-f1_score').first()
            if best_model:
                best_model.is_active = True
                best_model.save(update_fields=['is_active'])
                logger.info(f"Modèle NLP {best_model.id} activé automatiquement (meilleur score F1: {best_model.f1_score})")
        else:
            # Vérifier si le modèle actif a besoin d'être réentraîné
            if active_model.is_trained and active_model.last_trained:
                # Réentraîner le modèle s'il a plus de 30 jours
                days_since_training = (timezone.now() - active_model.last_trained).days
                if days_since_training > 30:
                    logger.info(f"Planification du réentraînement du modèle NLP {active_model.id} (dernier entraînement il y a {days_since_training} jours)")
                    train_nlp_model.delay(active_model.id)
        
        # Vérifier les modèles non entraînés avec suffisamment de données
        from .models import NLPTrainingData
        untrained_models = NLPModel.objects.filter(is_trained=False)
        
        for model in untrained_models:
            # Compter les données d'entraînement validées disponibles
            validated_data_count = NLPTrainingData.objects.filter(is_validated=True).count()
            
            # Si nous avons au moins 100 exemples validés, planifier l'entraînement
            if validated_data_count >= 100:
                logger.info(f"Planification de l'entraînement initial du modèle NLP {model.id} ({validated_data_count} exemples validés disponibles)")
                train_nlp_model.delay(model.id)
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des modèles NLP: {str(e)}")
        return False


@shared_task
def process_pending_notifications():
    """
    Traite toutes les notifications en attente
    Cette tâche est exécutée périodiquement via Celery Beat
    """
    try:
        from .models import Notification
        
        # Récupérer toutes les notifications en attente
        pending_notifications = Notification.objects.filter(
            status=Notification.StatusChoices.PENDING
        )
        
        count = 0
        for notification in pending_notifications:
            # Envoyer chaque notification
            send_notification.delay(notification.id)
            count += 1
        
        if count > 0:
            logger.info(f"Traitement de {count} notifications en attente")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors du traitement des notifications en attente: {str(e)}")
        return False
