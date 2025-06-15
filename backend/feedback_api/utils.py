import logging
import json
import os
import requests
from datetime import datetime
from django.conf import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

# Mode de simulation pour les tests
SMS_SIMULATION_MODE = os.environ.get('SMS_SIMULATION_MODE', 'True').lower() in ('true', '1', 't')
SMS_LOG_FILE = os.path.join(settings.BASE_DIR, 'sms_simulation_logs.json')

def get_twilio_client():
    """
    Retourne un client Twilio configuré avec les identifiants des settings
    """
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN
    
    if not account_sid or not auth_token:
        logger.warning("Identifiants Twilio non configurés")
        return None
    
    return Client(account_sid, auth_token)

def log_simulated_message(message_type, to, message_body, from_number):
    """
    Enregistre un message simulé dans un fichier JSON pour les tests
    """
    try:
        # Créer un dictionnaire pour le nouveau message
        message_data = {
            'type': message_type,  # 'sms' ou 'whatsapp'
            'to': to,
            'from': from_number,
            'body': message_body,
            'timestamp': datetime.now().isoformat(),
            'sid': f'SM{datetime.now().strftime("%Y%m%d%H%M%S")}',
            'status': 'simulated'
        }
        
        # Charger les messages existants ou créer une liste vide
        messages = []
        if os.path.exists(SMS_LOG_FILE):
            try:
                with open(SMS_LOG_FILE, 'r') as f:
                    messages = json.load(f)
            except json.JSONDecodeError:
                messages = []
        
        # Ajouter le nouveau message
        messages.append(message_data)
        
        # Enregistrer la liste mise à jour
        with open(SMS_LOG_FILE, 'w') as f:
            json.dump(messages, f, indent=2)
            
        logger.info(f"Message {message_type} simulé enregistré dans {SMS_LOG_FILE}")
        return message_data
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du message simulé: {str(e)}")
        return None

def send_sms_via_twilio(to, message):
    """
    Envoie un SMS via Twilio
    
    Args:
        to (str): Numéro de téléphone du destinataire au format E.164 (ex: +33612345678)
        message (str): Contenu du message à envoyer
        
    Returns:
        dict: Informations sur le message envoyé ou None en cas d'erreur
    """
    # Mode de simulation pour les tests
    if SMS_SIMULATION_MODE:
        logger.info(f"[SIMULATION] Envoi d'un SMS à {to}")
        simulated_message = log_simulated_message('sms', to, message, settings.TWILIO_PHONE_NUMBER)
        if simulated_message:
            logger.info(f"[SIMULATION] SMS envoyé à {to}, SID: {simulated_message['sid']}")
            return {
                'sid': simulated_message['sid'],
                'status': 'simulated',
                'to': to
            }
        return None
    
    # Mode réel avec Twilio
    client = get_twilio_client()
    
    if not client:
        logger.error("Impossible d'envoyer un SMS: client Twilio non configuré")
        return None
    
    try:
        message = client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to
        )
        
        logger.info(f"SMS envoyé à {to}, SID: {message.sid}")
        return {
            'sid': message.sid,
            'status': message.status,
            'to': message.to
        }
    
    except TwilioRestException as e:
        logger.error(f"Erreur Twilio lors de l'envoi du SMS à {to}: {str(e)}")
        return None
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du SMS à {to}: {str(e)}")
        return None

def send_whatsapp_via_facebook(to, message):
    """
    Envoie un message WhatsApp via l'API Facebook Business
    
    Args:
        to (str): Numéro de téléphone du destinataire au format E.164 (ex: +33612345678)
        message (str): Contenu du message à envoyer
        
    Returns:
        dict: Informations sur le message envoyé ou None en cas d'erreur
    """
    # S'assurer que le numéro est au format E.164 (commençant par +)
    if not to.startswith('+'):
        to = f"+{to}"
    
    # Mode de simulation pour les tests
    if SMS_SIMULATION_MODE:
        logger.info(f"[SIMULATION] Envoi d'un message WhatsApp via Facebook à {to}")
        simulated_message = log_simulated_message('whatsapp_facebook', to, message, 'Facebook WhatsApp API')
        if simulated_message:
            logger.info(f"[SIMULATION] Message WhatsApp via Facebook envoyé à {to}, ID: {simulated_message['sid']}")
            return {
                'id': simulated_message['sid'],
                'status': 'simulated',
                'to': to
            }
        return None
    
    # Paramètres de l'API Facebook WhatsApp
    api_version = settings.FACEBOOK_WHATSAPP_API_VERSION
    phone_number_id = settings.FACEBOOK_WHATSAPP_PHONE_NUMBER_ID
    token = settings.FACEBOOK_WHATSAPP_TOKEN
    
    if not token or not phone_number_id:
        logger.error("Impossible d'envoyer un message WhatsApp: paramètres Facebook non configurés")
        return None
    
    # URL de l'API
    url = f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"
    
    # En-têtes de la requête
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Corps de la requête
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "body": message
        }
    }
    
    try:
        # Envoi de la requête à l'API Facebook
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()
        
        # Vérifier si la requête a réussi
        if response.status_code == 200:
            message_id = response_data.get('messages', [{}])[0].get('id', 'unknown')
            logger.info(f"Message WhatsApp via Facebook envoyé à {to}, ID: {message_id}")
            return {
                'id': message_id,
                'status': 'sent',
                'to': to,
                'response': response_data
            }
        else:
            error = response_data.get('error', {})
            logger.error(f"Erreur Facebook lors de l'envoi du message WhatsApp à {to}: {error}")
            return None
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message WhatsApp via Facebook à {to}: {str(e)}")
        return None


def send_whatsapp_via_twilio(to, message):
    """
    Envoie un message WhatsApp via Twilio
    
    Args:
        to (str): Numéro de téléphone du destinataire au format E.164 (ex: +33612345678)
        message (str): Contenu du message à envoyer
        
    Returns:
        dict: Informations sur le message envoyé ou None en cas d'erreur
    """
    # Formater les numéros pour WhatsApp
    whatsapp_from = f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER or '+14155238886'}"
    whatsapp_to = f"whatsapp:{to}"
    
    # Mode de simulation pour les tests
    if SMS_SIMULATION_MODE:
        logger.info(f"[SIMULATION] Envoi d'un message WhatsApp à {to}")
        simulated_message = log_simulated_message('whatsapp', whatsapp_to, message, whatsapp_from)
        if simulated_message:
            logger.info(f"[SIMULATION] Message WhatsApp envoyé à {to}, SID: {simulated_message['sid']}")
            return {
                'sid': simulated_message['sid'],
                'status': 'simulated',
                'to': whatsapp_to
            }
        return None
    
    # Mode réel avec Twilio
    client = get_twilio_client()
    
    if not client:
        logger.error("Impossible d'envoyer un message WhatsApp: client Twilio non configuré")
        return None
    
    try:
        message = client.messages.create(
            body=message,
            from_=whatsapp_from,
            to=whatsapp_to
        )
        
        logger.info(f"Message WhatsApp envoyé à {to}, SID: {message.sid}")
        return {
            'sid': message.sid,
            'status': message.status,
            'to': message.to
        }
    
    except TwilioRestException as e:
        logger.error(f"Erreur Twilio lors de l'envoi du message WhatsApp à {to}: {str(e)}")
        return None
    
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message WhatsApp à {to}: {str(e)}")
        return None


def send_whatsapp(to, message, provider='facebook'):
    """
    Envoie un message WhatsApp en utilisant le fournisseur spécifié
    
    Args:
        to (str): Numéro de téléphone du destinataire au format E.164 (ex: +33612345678)
        message (str): Contenu du message à envoyer
        provider (str): Fournisseur à utiliser ('facebook' ou 'twilio')
        
    Returns:
        dict: Informations sur le message envoyé ou None en cas d'erreur
    """
    # Utiliser le fournisseur spécifié avec fallback sur l'autre en cas d'échec
    if provider == 'facebook':
        # Essayer d'abord Facebook
        result = send_whatsapp_via_facebook(to, message)
        if result:
            return result
        
        # Si Facebook échoue, essayer Twilio comme fallback
        logger.warning(f"Échec de l'envoi via Facebook, tentative via Twilio pour {to}")
        return send_whatsapp_via_twilio(to, message)
    else:
        # Essayer d'abord Twilio
        result = send_whatsapp_via_twilio(to, message)
        if result:
            return result
        
        # Si Twilio échoue, essayer Facebook comme fallback
        logger.warning(f"Échec de l'envoi via Twilio, tentative via Facebook pour {to}")
        return send_whatsapp_via_facebook(to, message)


# Messages prédéfinis pour les réponses automatiques
MESSAGES = {
    'welcome': "Merci pour votre message ! Nous l'avons bien reçu et nous allons le traiter dans les plus brefs délais.",
    'help': "Bienvenue sur notre service de feedback par WhatsApp. Vous pouvez nous envoyer vos commentaires, suggestions ou questions. Commandes disponibles:\n- *aide*: Affiche ce message d'aide\n- *statut*: Vérifie le statut de vos feedbacks précédents",
    'status': "Vous n'avez pas de feedbacks en cours de traitement.",
    'unknown_command': "Commande non reconnue. Envoyez *aide* pour voir les commandes disponibles."
}


def send_whatsapp_response(to, message, provider='facebook'):
    """
    Envoie une réponse WhatsApp à un utilisateur
    
    Args:
        to (str): Numéro de téléphone du destinataire
        message (str): Message à envoyer
        provider (str): Fournisseur à utiliser ('facebook' ou 'twilio')
        
    Returns:
        dict: Informations sur le message envoyé ou None en cas d'erreur
    """
    # Formater le numéro de téléphone si nécessaire
    if not to.startswith('+'):
        # Si le numéro ne commence pas par +, ajouter le préfixe international
        to = '+' + to.lstrip('0')
    
    return send_whatsapp(to, message, provider)


def process_whatsapp_command(message, phone_number):
    """
    Traite les commandes spéciales dans les messages WhatsApp
    
    Args:
        message (str): Contenu du message
        phone_number (str): Numéro de téléphone de l'expéditeur
        
    Returns:
        tuple: (is_command, response_message)
            - is_command (bool): True si le message est une commande, False sinon
            - response_message (str): Message de réponse à envoyer ou None
    """
    if not message:
        return False, None
    
    # Convertir en minuscules pour faciliter la comparaison
    message_lower = message.lower().strip()
    
    # Traiter les commandes spéciales
    if message_lower in ['aide', 'help']:
        return True, MESSAGES['help']
    
    elif message_lower in ['statut', 'status']:
        # Vérifier s'il y a des feedbacks en cours pour ce numéro
        from .models import Feedback
        recent_feedbacks = Feedback.objects.filter(
            contact_phone=phone_number,
            created_at__gte=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        ).count()
        
        if recent_feedbacks > 0:
            return True, f"Vous avez {recent_feedbacks} feedback(s) en cours de traitement aujourd'hui."
        else:
            return True, MESSAGES['status']
    
    # Si ce n'est pas une commande reconnue
    return False, None
