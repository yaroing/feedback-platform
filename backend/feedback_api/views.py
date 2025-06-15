import json
import logging
from rest_framework import viewsets, permissions, status, filters
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, JsonResponse
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.views import APIView
from rest_framework.response import Response as DRFResponse
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import uuid
import base64
import requests

# Configurer le logger
logger = logging.getLogger(__name__)

from .models import Category, Feedback, Response, Log
from .serializers import (
    CategorySerializer, 
    FeedbackSerializer, 
    FeedbackCreateSerializer,
    ResponseSerializer, 
    LogSerializer
)
from .permissions import IsModeratorOrReadOnly, IsOwnerOrModerator
from .tasks import send_response_message


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint pour gérer les catégories de feedback
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    pagination_class = None  # Désactiver la pagination pour les catégories


class FeedbackViewSet(viewsets.ModelViewSet):
    """
    API endpoint pour gérer les feedbacks
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsOwnerOrModerator]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'category', 'channel']
    search_fields = ['content', 'contact_email', 'contact_phone']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create' and not self.request.user.is_authenticated:
            return FeedbackCreateSerializer
        return FeedbackSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def perform_create(self, serializer):
        """Crée un feedback et déclenche la classification NLP automatique"""
        # Sauvegarder le feedback
        feedback = serializer.save()
        
        # Créer un log pour la création
        Log.objects.create(
            feedback=feedback,
            action=Log.ActionChoices.CREATED,
            details="Feedback créé"
        )
        
        # Déclencher la classification NLP de manière asynchrone
        from .tasks import classify_feedback
        classify_feedback.delay(feedback.id)
        
        return feedback
    
    @action(detail=True, methods=['post'], permission_classes=[IsModeratorOrReadOnly])
    def respond(self, request, pk=None):
        """
        Ajouter une réponse à un feedback et l'envoyer via le canal approprié
        """
        feedback = self.get_object()
        serializer = ResponseSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            # Créer la réponse
            response = serializer.save(
                feedback=feedback,
                responder=request.user
            )
            
            # Mettre à jour le statut du feedback si nécessaire
            if feedback.status == Feedback.StatusChoices.NEW:
                feedback.status = Feedback.StatusChoices.IN_PROGRESS
                feedback.save()
            
            # Créer un log pour la réponse
            Log.objects.create(
                feedback=feedback,
                user=request.user,
                action=Log.ActionChoices.RESPONDED,
                details=f"Réponse envoyée: {response.content[:50]}..."
            )
            
            # Envoyer la réponse de manière asynchrone via Celery
            if feedback.channel in [Feedback.ChannelChoices.SMS, Feedback.ChannelChoices.WHATSAPP]:
                send_response_message.delay(response.id)
            
            return DRFResponse(serializer.data, status=status.HTTP_201_CREATED)
        
        return DRFResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], permission_classes=[IsModeratorOrReadOnly])
    def stats(self, request):
        """
        Obtenir des statistiques sur les feedbacks
        """
        # Statistiques par canal
        channel_stats = Feedback.objects.values('channel').annotate(count=Count('id'))
        
        # Statistiques par catégorie
        category_stats = Feedback.objects.values('category__name').annotate(count=Count('id'))
        
        # Statistiques par statut
        status_stats = Feedback.objects.values('status').annotate(count=Count('id'))
        
        # Nombre de feedbacks reçus aujourd'hui
        today = Feedback.objects.filter(created_at__date=timezone.now().date()).count()
        
        # Nombre de feedbacks reçus cette semaine
        this_week = Feedback.objects.filter(created_at__week=timezone.now().isocalendar()[1]).count()
        
        # Nombre de feedbacks reçus ce mois-ci
        this_month = Feedback.objects.filter(created_at__month=timezone.now().month).count()
        
        # Temps moyen de résolution (en heures)
        resolved_feedbacks = Feedback.objects.filter(status=Feedback.StatusChoices.RESOLVED)
        if resolved_feedbacks.exists():
            time_diffs = []
            for feedback in resolved_feedbacks:
                if feedback.resolved_at:
                    diff = feedback.resolved_at - feedback.created_at
                    time_diffs.append(diff.total_seconds() / 3600)  # Conversion en heures
            avg_resolution_time = sum(time_diffs) / len(time_diffs) if time_diffs else 0
        else:
            avg_resolution_time = 0
        
        return DRFResponse({
            'total': Feedback.objects.count(),
            'by_channel': list(channel_stats),
            'by_category': list(category_stats),
            'by_status': list(status_stats),
            'today': today,
            'this_week': this_week,
            'this_month': this_month,
            'avg_resolution_time_hours': avg_resolution_time
        })


class ResponseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint pour consulter les réponses (lecture seule)
    """
    queryset = Response.objects.all()
    serializer_class = ResponseSerializer
    permission_classes = [IsOwnerOrModerator]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['feedback', 'sent']


class LogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint pour consulter les journaux d'activité (lecture seule)
    """
    queryset = Log.objects.all()
    serializer_class = LogSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['feedback', 'action']


class InboundWebhookView(viewsets.ViewSet):
    """
    Webhook pour recevoir des feedbacks depuis des canaux externes (SMS, WhatsApp)
    """
    permission_classes = [permissions.AllowAny]
    
    def create(self, request):
        # Vérifier la source du message (Twilio, Facebook, etc.)
        # Détecter automatiquement si c'est une requête Facebook basée sur l'URL
        if 'facebook-webhook' in request.path:
            source = 'facebook'
        else:
            source = request.query_params.get('source', 'twilio')  # Par défaut, on suppose que c'est Twilio
            
        # Vérification spéciale pour les requêtes GET de vérification de webhook Facebook
        # même si elles arrivent sur un autre endpoint
        if request.method == 'GET' and request.query_params.get('hub.mode') == 'subscribe':
            source = 'facebook'
        
        # Log des données reçues pour le débogage
        logger = logging.getLogger(__name__)
        logger.info(f"Webhook reçu de {source}: {request.data}")
        
        if source == 'facebook':
            # Traitement des messages Facebook WhatsApp
            try:
                # Vérifier si c'est une requête de vérification de webhook
                if request.method == 'GET' and request.query_params.get('hub.mode') == 'subscribe':
                    verify_token = request.query_params.get('hub.verify_token')
                    # Vérifier que le token correspond à celui configuré
                    expected_token = getattr(settings, 'FACEBOOK_WEBHOOK_VERIFY_TOKEN', 'feedback_platform_token')
                    
                    if verify_token == expected_token:
                        challenge = request.query_params.get('hub.challenge')
                        logger.info(f"Vérification du webhook Facebook réussie, challenge: {challenge}")
                        return HttpResponse(challenge, content_type='text/plain')
                    else:
                        logger.error(f"Token de vérification Facebook invalide: {verify_token}")
                        return DRFResponse({'error': 'Token de vérification invalide'}, status=status.HTTP_403_FORBIDDEN)
                
                # Traitement des messages entrants
                data = request.data
                
                # Vérifier que c'est bien un message WhatsApp
                if 'object' in data and data['object'] == 'whatsapp_business_account':
                    # Parcourir les entrées du webhook
                    for entry in data.get('entry', []):
                        for change in entry.get('changes', []):
                            value = change.get('value', {})
                            
                            # Vérifier que c'est un message
                            if 'messages' in value:
                                for message in value['messages']:
                                    # Extraire les informations du message
                                    message_id = message.get('id')
                                    from_number = message.get('from')
                                    timestamp = message.get('timestamp')
                                    
                                    # Extraire le contenu du message selon son type
                                    body = ''
                                    if message.get('type') == 'text' and 'text' in message:
                                        body = message['text'].get('body', '')
                                    elif message.get('type') == 'image' and 'image' in message:
                                        body = f"[IMAGE] {message['image'].get('caption', '')}" 
                                    elif message.get('type') == 'audio':
                                        body = "[AUDIO] Message audio reçu"
                                    elif message.get('type') == 'document':
                                        body = f"[DOCUMENT] {message.get('document', {}).get('caption', '')}" 
                                    elif message.get('type') == 'location':
                                        location = message.get('location', {})
                                        latitude = location.get('latitude')
                                        longitude = location.get('longitude')
                                        body = f"[LOCATION] Latitude: {latitude}, Longitude: {longitude}"
                                    else:
                                        body = f"[{message.get('type', 'UNKNOWN').upper()}] Message reçu"
                                    
                                    logger.info(f"Message WhatsApp Facebook reçu: From={from_number}, Body={body[:50]}..., ID={message_id}")
                                    
                                    # Vérifier que nous avons un contenu et un numéro de téléphone
                                    if not body:
                                        continue
                                    
                                    if not from_number:
                                        continue
                                    
                                    # Importer les utilitaires WhatsApp
                                    from .whatsapp_utils import process_whatsapp_command, send_whatsapp_response, MESSAGES
                                    
                                    # Vérifier si c'est une commande spéciale
                                    is_command, response_message = process_whatsapp_command(body, from_number)
                                    
                                    # Si c'est une commande, envoyer la réponse sans créer de feedback
                                    if is_command:
                                        if response_message:
                                            # Envoyer la réponse à la commande
                                            send_whatsapp_response(from_number, response_message, 'facebook')
                                        continue
                                    
                                    # Créer le feedback
                                    feedback = Feedback.objects.create(
                                        channel=Feedback.ChannelChoices.WHATSAPP,
                                        content=body,
                                        contact_phone=from_number,
                                        status=Feedback.StatusChoices.NEW,
                                        priority=Feedback.PriorityChoices.MEDIUM  # Priorité par défaut
                                    )
                                    
                                    # Créer un log
                                    Log.objects.create(
                                        feedback=feedback,
                                        action=Log.ActionChoices.CREATED,
                                        details=f"Feedback reçu via WhatsApp Facebook (ID: {message_id})"
                                    )
                                    
                                    # Déclencher la classification automatique
                                    from .tasks import classify_feedback
                                    classify_feedback.delay(feedback.id)
                                    
                                    # Envoyer un message de confirmation
                                    send_whatsapp_response(from_number, MESSAGES['welcome'], 'facebook')
                
                # Toujours renvoyer un 200 OK pour les webhooks Facebook
                return DRFResponse({'status': 'success'}, status=status.HTTP_200_OK)
                
            except Exception as e:
                logger.error(f"Erreur lors du traitement du webhook Facebook: {str(e)}")
                # Toujours renvoyer un 200 OK pour les webhooks Facebook même en cas d'erreur
                return DRFResponse({'status': 'error', 'message': str(e)}, status=status.HTTP_200_OK)
        
        elif source == 'twilio':
            # Traitement des messages Twilio
            from_number = request.data.get('From', '')
            body = request.data.get('Body', '')
            message_sid = request.data.get('MessageSid', '')
            
            logger.info(f"Webhook Twilio reçu: From={from_number}, Body={body[:50]}..., SID={message_sid}")
            
            # Déterminer le canal (SMS ou WhatsApp)
            channel = Feedback.ChannelChoices.SMS
            if from_number.startswith('whatsapp:'):
                channel = Feedback.ChannelChoices.WHATSAPP
                from_number = from_number.replace('whatsapp:', '')
            
            # Vérifier que nous avons un contenu et un numéro de téléphone
            if not body:
                return DRFResponse(
                    {'error': 'Corps du message vide'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not from_number:
                return DRFResponse(
                    {'error': 'Numéro d\'expéditeur manquant'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Importer les utilitaires WhatsApp
            from .whatsapp_utils import process_whatsapp_command, MESSAGES
            
            # Message de réponse par défaut
            response_message = MESSAGES['welcome']
            
            # Si c'est un message WhatsApp, vérifier s'il s'agit d'une commande spéciale
            if channel == Feedback.ChannelChoices.WHATSAPP:
                is_command, command_response = process_whatsapp_command(body, from_number)
                
                if is_command:
                    if command_response:
                        response_message = command_response
                    
                    # Pour les commandes, on ne crée pas de feedback
                    # Réponse au format TwiML pour Twilio
                    twiml_response = f"""<?xml version='1.0' encoding='UTF-8'?>
                    <Response>
                        <Message>{response_message}</Message>
                    </Response>
                    """
                    
                    return HttpResponse(twiml_response, content_type='text/xml')
            
            # Créer le feedback pour les messages normaux (non-commandes)
            feedback = Feedback.objects.create(
                channel=channel,
                content=body,
                contact_phone=from_number,
                status=Feedback.StatusChoices.NEW,
                priority=Feedback.PriorityChoices.MEDIUM  # Priorité par défaut
            )
            
            # Créer un log
            Log.objects.create(
                feedback=feedback,
                action=Log.ActionChoices.CREATED,
                details=f"Feedback reçu via {channel} (SID: {message_sid})"
            )
            
            # Déclencher la classification automatique
            from .tasks import classify_feedback
            classify_feedback.delay(feedback.id)
            
            # Réponse au format TwiML pour Twilio
            from django.http import HttpResponse
            twiml_response = f"""<?xml version='1.0' encoding='UTF-8'?>
            <Response>
                <Message>{response_message}</Message>
            </Response>
            """
            
            return HttpResponse(twiml_response, content_type='text/xml')
        
        return DRFResponse(
            {'error': 'Source non reconnue'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def simulated_messages(request):
    """
    Retourne la liste des messages SMS et WhatsApp simulés
    """
    from .utils import SMS_LOG_FILE
    
    # Vérifier si le fichier de logs existe
    if not os.path.exists(SMS_LOG_FILE):
        return DRFResponse({
            'messages': [],
            'count': 0,
            'simulation_mode': True,
            'log_file': SMS_LOG_FILE
        })
    
    try:
        # Lire le fichier de logs
        with open(SMS_LOG_FILE, 'r') as f:
            messages = json.load(f)
        
        # Filtrer par type si spécifié
        message_type = request.query_params.get('type')
        if message_type:
            messages = [m for m in messages if m['type'] == message_type]
        
        # Filtrer par numéro si spécifié
        phone_number = request.query_params.get('phone')
        if phone_number:
            messages = [m for m in messages if phone_number in m['to']]
        
        # Trier par date (du plus récent au plus ancien)
        messages.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return DRFResponse({
            'messages': messages,
            'count': len(messages),
            'simulation_mode': True,
            'log_file': SMS_LOG_FILE
        })
    except Exception as e:
        return DRFResponse({
            'error': str(e),
            'simulation_mode': True,
            'log_file': SMS_LOG_FILE
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class JSONSMSWebhookView(APIView):
    """
    Vue pour traiter les webhooks SMS entrants au format JSON personnalisé.
    Format attendu:
    {
        "from": "%from%",
        "text": "%text%",
        "sentStamp": "%sentStamp%",
        "receivedStamp": "%receivedStamp%",
        "sim": "%sim%"
    }
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        try:
            # Essayer de parser le corps de la requête comme JSON
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in webhook request")
                return JsonResponse({"status": "error", "message": "Invalid JSON format"}, status=400)
            
            # Extraire les données du message
            from_number = data.get('from', '')
            body = data.get('text', '')
            sent_stamp = data.get('sentStamp', '')
            received_stamp = data.get('receivedStamp', '')
            sim = data.get('sim', '')
            
            if not from_number or not body:
                logger.error("Missing required fields in JSON webhook")
                return JsonResponse({"status": "error", "message": "Missing required fields"}, status=400)
            
            logger.info(f"Received JSON SMS from {from_number}: {body[:50]}...")
            
            # Créer un nouveau feedback
            # Utiliser un identifiant externe plus court
            import uuid
            feedback = Feedback.objects.create(
                content=body,
                channel=Feedback.ChannelChoices.SMS,
                contact_phone=from_number,
                status=Feedback.StatusChoices.NEW,
                reference_number=sim,
                external_id=str(uuid.uuid4())[:36]  # UUID standard a 36 caractères
            )
            
            # Créer un log pour la création
            Log.objects.create(
                feedback=feedback,
                action=Log.ActionChoices.CREATED,
                details="Feedback créé via webhook JSON SMS"
            )
            
            # Déclencher la classification NLP de manière asynchrone
            from .tasks import classify_feedback
            classify_feedback.delay(feedback.id)
            
            logger.info(f"Created feedback {feedback.id} from JSON SMS webhook")
            
            # Retourner une réponse de succès
            return JsonResponse({
                "status": "success",
                "message": "Feedback created successfully",
                "feedback_id": str(feedback.id)
            })
            
        except Exception as e:
            logger.error(f"Error processing JSON webhook: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)


class FacebookWebhookVerificationView(APIView):
    """
    Vue dédiée à la vérification du webhook Facebook WhatsApp
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        logger = logging.getLogger(__name__)
        logger.info(f"Requête de vérification du webhook Facebook reçue: {request.query_params}")
        
        # Vérifier si c'est une requête de vérification de webhook
        if request.query_params.get('hub.mode') == 'subscribe':
            verify_token = request.query_params.get('hub.verify_token')
            # Vérifier que le token correspond à celui configuré
            expected_token = getattr(settings, 'FACEBOOK_WEBHOOK_VERIFY_TOKEN', 'feedback_platform_token')
            
            if verify_token == expected_token:
                challenge = request.query_params.get('hub.challenge')
                logger.info(f"Vérification du webhook Facebook réussie, challenge: {challenge}")
                return HttpResponse(challenge, content_type='text/plain')
            else:
                logger.error(f"Token de vérification Facebook invalide: {verify_token}")
                return DRFResponse({'error': 'Token de vérification invalide'}, status=status.HTTP_403_FORBIDDEN)
        
        return DRFResponse({'error': 'Requête invalide'}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        logger = logging.getLogger(__name__)
        logger.info(f"Message WhatsApp Facebook reçu: {request.data}")
        
        try:
            data = request.data
            
            # Vérifier que c'est bien un message WhatsApp Business
            if 'object' in data and data['object'] == 'whatsapp_business_account':
                # Traiter chaque entrée (peut contenir plusieurs messages)
                for entry in data.get('entry', []):
                    for change in entry.get('changes', []):
                        value = change.get('value', {})
                        
                        # Traiter les messages entrants
                        if 'messages' in value:
                            for message in value['messages']:
                                # Extraire les informations du message
                                message_type = message.get('type', 'unknown')
                                from_number = message.get('from', '')
                                timestamp = message.get('timestamp', '')
                                message_id = message.get('id', '')
                                
                                # Extraire le contenu du message selon son type
                                body = ''
                                if message_type == 'text':
                                    body = message.get('text', {}).get('body', '')
                                elif message_type == 'image':
                                    body = '[Image]'
                                elif message_type == 'audio':
                                    body = '[Audio]'
                                elif message_type == 'document':
                                    body = '[Document]'
                                elif message_type == 'location':
                                    body = '[Localisation]'
                                else:
                                    body = f'[Message de type {message_type}]'
                                
                                logger.info(f"Message WhatsApp reçu de {from_number}: {body}")
                                
                                # Vérifier si c'est une commande spéciale
                                # Importer les fonctions en dehors du bloc try pour éviter les problèmes d'importation
                                try:
                                    from .whatsapp_utils import process_whatsapp_command, send_whatsapp_response, MESSAGES
                                    is_command, response_message = process_whatsapp_command(body, from_number)
                                except ImportError as e:
                                    logger.error(f"Erreur d'importation des fonctions WhatsApp: {str(e)}")
                                    is_command, response_message = False, None
                                
                                if is_command:
                                    # Répondre à la commande
                                    send_whatsapp_response(from_number, response_message, 'facebook')
                                    logger.info(f"Réponse à la commande envoyée à {from_number}: {response_message}")
                                    continue
                                
                                # Créer un feedback avec le message reçu
                                from .models import Feedback, Log
                                feedback = Feedback.objects.create(
                                    content=body,
                                    contact_phone=from_number,
                                    channel='whatsapp'
                                )
                                
                                # Créer un log pour le feedback avec des informations détaillées
                                Log.objects.create(
                                    feedback=feedback,
                                    action=Log.ActionChoices.CREATED,
                                    details=f"Feedback reçu via WhatsApp Facebook | Type: {message_type} | De: {from_number} | ID: {message_id} | Timestamp: {timestamp}"
                                )
                                
                                # Déclencher la classification automatique
                                from .tasks import classify_feedback
                                classify_feedback.delay(feedback.id)
                                
                                # Envoyer un message de bienvenue
                                try:
                                    # Importer ici si ce n'est pas déjà fait
                                    if 'send_whatsapp_response' not in locals():
                                        from .whatsapp_utils import send_whatsapp_response, MESSAGES
                                    
                                    send_whatsapp_response(from_number, MESSAGES['welcome'], 'facebook')
                                    logger.info(f"Message de bienvenue envoyé à {from_number}")
                                except Exception as e:
                                    logger.error(f"Erreur lors de l'envoi du message de bienvenue: {str(e)}")
                
                return DRFResponse({'status': 'success'}, status=status.HTTP_200_OK)
            
            return DRFResponse({'status': 'ignored'}, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message WhatsApp Facebook: {str(e)}")
            # Toujours renvoyer 200 OK pour que Facebook ne réessaie pas
            return DRFResponse({'status': 'error', 'message': str(e)}, status=status.HTTP_200_OK)
