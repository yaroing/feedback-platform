import logging
import re
from django.conf import settings
from .models import Feedback, Category
from .utils import send_whatsapp

logger = logging.getLogger(__name__)

# Commandes WhatsApp
COMMANDS = {
    'help': r'^(?i)(?:aide|help)$',
    'categories': r'^(?i)(?:categories|catégories|liste)$',
    'set_category': r'^(?i)(?:categorie|catégorie|category)\s*:\s*(.+)$',
    'set_priority': r'^(?i)(?:priorite|priorité|priority)\s*:\s*(haute|high|moyenne|medium|basse|low)$',
}

# Messages de réponse
MESSAGES = {
    'welcome': "Merci pour votre message ! Votre feedback a été enregistré avec succès. Un membre de notre équipe le traitera prochainement.",
    'help': "Comment utiliser ce service :\n"
            "- Envoyez simplement votre message pour soumettre un feedback\n"
            "- 'categories' : voir la liste des catégories disponibles\n"
            "- 'categorie: [nom]' : définir la catégorie de votre dernier feedback\n"
            "- 'priorite: [haute/moyenne/basse]' : définir la priorité de votre feedback\n"
            "- 'help' : afficher ce message d'aide",
    'categories_not_found': "Aucune catégorie n'est disponible pour le moment.",
    'category_set': "La catégorie de votre feedback a été mise à jour : {}",
    'category_not_found': "Catégorie non trouvée. Envoyez 'categories' pour voir la liste des catégories disponibles.",
    'priority_set': "La priorité de votre feedback a été mise à jour : {}",
    'error': "Une erreur s'est produite lors du traitement de votre demande. Veuillez réessayer plus tard."
}

def process_whatsapp_command(message_body, from_number, feedback=None):
    """
    Traite les commandes spéciales dans les messages WhatsApp
    
    Args:
        message_body (str): Contenu du message
        from_number (str): Numéro de téléphone de l'expéditeur
        feedback (Feedback, optional): Feedback associé au message
        
    Returns:
        tuple: (bool, str) - (True si une commande a été traitée, message de réponse)
    """
    # Commande d'aide
    if re.match(COMMANDS['help'], message_body):
        return True, MESSAGES['help']
    
    # Liste des catégories
    if re.match(COMMANDS['categories'], message_body):
        categories = Category.objects.filter(active=True)
        if not categories.exists():
            return True, MESSAGES['categories_not_found']
        
        categories_list = "\n".join([f"- {cat.name}" for cat in categories])
        return True, f"Catégories disponibles :\n{categories_list}"
    
    # Définir la catégorie
    category_match = re.match(COMMANDS['set_category'], message_body)
    if category_match:
        category_name = category_match.group(1).strip()
        
        # Vérifier si l'utilisateur a un feedback récent
        if not feedback:
            recent_feedback = Feedback.objects.filter(
                contact_phone=from_number,
                channel=Feedback.ChannelChoices.WHATSAPP
            ).order_by('-created_at').first()
            
            if recent_feedback:
                feedback = recent_feedback
        
        if not feedback:
            return True, "Aucun feedback récent trouvé. Veuillez d'abord envoyer un message."
        
        # Rechercher la catégorie
        try:
            category = Category.objects.get(name__iexact=category_name, active=True)
            feedback.category = category
            feedback.save()
            
            return True, MESSAGES['category_set'].format(category.name)
        except Category.DoesNotExist:
            return True, MESSAGES['category_not_found']
    
    # Définir la priorité
    priority_match = re.match(COMMANDS['set_priority'], message_body)
    if priority_match:
        priority_name = priority_match.group(1).lower()
        
        # Vérifier si l'utilisateur a un feedback récent
        if not feedback:
            recent_feedback = Feedback.objects.filter(
                contact_phone=from_number,
                channel=Feedback.ChannelChoices.WHATSAPP
            ).order_by('-created_at').first()
            
            if recent_feedback:
                feedback = recent_feedback
        
        if not feedback:
            return True, "Aucun feedback récent trouvé. Veuillez d'abord envoyer un message."
        
        # Mapper le nom de priorité à la valeur
        priority_map = {
            'haute': Feedback.PriorityChoices.HIGH,
            'high': Feedback.PriorityChoices.HIGH,
            'moyenne': Feedback.PriorityChoices.MEDIUM,
            'medium': Feedback.PriorityChoices.MEDIUM,
            'basse': Feedback.PriorityChoices.LOW,
            'low': Feedback.PriorityChoices.LOW
        }
        
        priority = priority_map.get(priority_name)
        if priority:
            feedback.priority = priority
            feedback.save()
            
            # Traduire la priorité pour l'affichage
            priority_display = {
                Feedback.PriorityChoices.HIGH: "Haute",
                Feedback.PriorityChoices.MEDIUM: "Moyenne",
                Feedback.PriorityChoices.LOW: "Basse"
            }
            
            return True, MESSAGES['priority_set'].format(priority_display[priority])
    
    # Aucune commande reconnue
    return False, None

def send_whatsapp_response(to, message, provider='facebook'):
    """
    Envoie une réponse WhatsApp avec mécanisme de fallback
    
    Args:
        to (str): Numéro de téléphone du destinataire
        message (str): Contenu du message
        provider (str): Fournisseur à utiliser ('facebook' ou 'twilio')
        
    Returns:
        bool: True si le message a été envoyé avec succès
    """
    # Normaliser le numéro de téléphone si nécessaire
    if not to.startswith('+'):
        to = '+' + to
    
    try:
        # Essayer d'envoyer via le fournisseur spécifié
        result = send_whatsapp(to, message, provider)
        
        if result:
            logger.info(f"Message WhatsApp envoyé avec succès via {provider} à {to}")
            return True
        
        # Si le premier fournisseur échoue, essayer l'autre
        fallback_provider = 'twilio' if provider == 'facebook' else 'facebook'
        logger.warning(f"Échec d'envoi via {provider}, tentative via {fallback_provider}")
        
        result = send_whatsapp(to, message, fallback_provider)
        
        if result:
            logger.info(f"Message WhatsApp envoyé avec succès via {fallback_provider} (fallback) à {to}")
            return True
        
        logger.error(f"Échec d'envoi du message WhatsApp à {to} via les deux fournisseurs")
        return False
        
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message WhatsApp à {to}: {str(e)}")
        return False
