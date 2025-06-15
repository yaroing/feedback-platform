import logging
import json
import os
import time
from django.urls import path
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response as DRFResponse
from django.conf import settings

from .utils import send_sms_via_twilio, send_whatsapp_via_twilio, send_whatsapp_via_facebook, send_whatsapp, SMS_LOG_FILE

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def test_twilio_sms(request):
    """
    Vue de test pour envoyer un SMS via Twilio
    
    GET: Affiche un formulaire simple pour tester l'envoi
    POST: Envoie le SMS et affiche le résultat
    """
    if request.method == "POST":
        to_number = request.POST.get('to_number', '')
        message = request.POST.get('message', '')
        
        if not to_number or not message:
            return JsonResponse({
                'success': False,
                'error': 'Numéro de téléphone et message requis'
            }, status=400)
        
        # Envoyer le SMS
        result = send_sms_via_twilio(to_number, message)
        
        if result:
            return JsonResponse({
                'success': True,
                'message': f"SMS envoyé avec succès à {to_number}",
                'sid': result['sid'],
                'status': result['status']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': "Échec de l'envoi du SMS. Vérifiez les logs pour plus de détails."
            }, status=500)
    
    # Afficher un formulaire simple pour tester
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Twilio SMS</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; }
            input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
            button { padding: 10px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; }
            .result { margin-top: 20px; padding: 10px; border: 1px solid #ddd; display: none; }
        </style>
    </head>
    <body>
        <h1>Test Twilio SMS</h1>
        <p>Utilisez ce formulaire pour tester l'envoi de SMS via Twilio.</p>
        
        <form id="smsForm" method="post">
            <div class="form-group">
                <label for="to_number">Numéro de téléphone (format E.164, ex: +33612345678):</label>
                <input type="text" id="to_number" name="to_number" required>
            </div>
            
            <div class="form-group">
                <label for="message">Message:</label>
                <textarea id="message" name="message" rows="4" required></textarea>
            </div>
            
            <button type="submit">Envoyer SMS</button>
        </form>
        
        <div id="result" class="result"></div>
        
        <script>
            document.getElementById('smsForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                
                fetch('', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    const resultDiv = document.getElementById('result');
                    resultDiv.style.display = 'block';
                    
                    if (data.success) {
                        resultDiv.style.backgroundColor = '#dff0d8';
                        resultDiv.innerHTML = `<strong>Succès!</strong> ${data.message}<br>SID: ${data.sid}<br>Status: ${data.status}`;
                    } else {
                        resultDiv.style.backgroundColor = '#f2dede';
                        resultDiv.innerHTML = `<strong>Erreur!</strong> ${data.error}`;
                    }
                })
                .catch(error => {
                    const resultDiv = document.getElementById('result');
                    resultDiv.style.display = 'block';
                    resultDiv.style.backgroundColor = '#f2dede';
                    resultDiv.innerHTML = `<strong>Erreur!</strong> Une erreur s'est produite lors de la requête.`;
                    console.error('Error:', error);
                });
            });
        </script>
    </body>
    </html>
    """
    
    from django.http import HttpResponse
    return HttpResponse(html)

@csrf_exempt
@require_http_methods(["GET", "POST"])
def test_twilio_webhook(request):
    """
    Vue de test pour simuler un webhook Twilio entrant
    
    GET: Affiche un formulaire simple pour simuler un webhook Twilio
    POST: Simule un webhook Twilio et affiche la réponse
    """
    if request.method == "POST":
        from_number = request.POST.get('From', '')
        body = request.POST.get('Body', '')
        is_whatsapp = request.POST.get('is_whatsapp') == 'on'
        
        if not from_number or not body:
            return JsonResponse({
                'success': False,
                'error': 'Numéro de téléphone et message requis'
            }, status=400)
        
        # Formater le numéro pour WhatsApp si nécessaire
        if is_whatsapp:
            from_number = f"whatsapp:{from_number}"
        
        # Préparer les données du webhook
        import uuid
        webhook_data = {
            'From': from_number,
            'Body': body,
            'MessageSid': f"SM{uuid.uuid4().hex[:30]}",
            'To': settings.TWILIO_PHONE_NUMBER if not is_whatsapp else f"whatsapp:{settings.TWILIO_WHATSAPP_NUMBER}"
        }
        
        # Créer directement un feedback à partir des données du webhook
        try:
            # Importer les modules nécessaires
            from .models import Feedback
            import logging
            
            # Configurer le logger pour le débogage
            logger = logging.getLogger(__name__)
            logger.info(f"Création d'un feedback à partir des données: {webhook_data}")
            
            # Déterminer le canal (SMS ou WhatsApp)
            channel = Feedback.ChannelChoices.SMS
            from_number = webhook_data['From']
            
            if is_whatsapp:
                channel = Feedback.ChannelChoices.WHATSAPP
                # Ajouter le préfixe whatsapp: pour la simulation
                webhook_data['From'] = f"whatsapp:{from_number}"
            
            # Créer le feedback directement
            feedback = Feedback.objects.create(
                content=webhook_data['Body'],
                channel=channel,
                phone_number=from_number,
                status=Feedback.StatusChoices.NEW
            )
            
            logger.info(f"Feedback créé avec succès: ID={feedback.id}")
            
            # Simuler un message dans le fichier de logs
            from .utils import log_simulated_message
            
            # Simuler la réception d'un message
            log_simulated_message(
                message_type="sms" if channel == Feedback.ChannelChoices.SMS else "whatsapp",
                to_number=settings.TWILIO_PHONE_NUMBER if channel == Feedback.ChannelChoices.SMS else settings.TWILIO_WHATSAPP_NUMBER,
                from_number=from_number,
                body=webhook_data['Body'],
                direction="inbound"
            )
            
            return JsonResponse({
                'success': True,
                'feedback_id': feedback.id,
                'message': f"Feedback créé avec succès (ID: {feedback.id})",
                'webhook_data': webhook_data
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du feedback: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f"Erreur lors de la création du feedback: {str(e)}"
            }, status=500)
    
    # Afficher un formulaire simple pour tester
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Webhook Twilio</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; }
            input, textarea { width: 100%; padding: 8px; box-sizing: border-box; }
            button { padding: 10px 15px; background: #4CAF50; color: white; border: none; cursor: pointer; }
            .result { margin-top: 20px; padding: 10px; border: 1px solid #ddd; display: none; }
            .checkbox-group { display: flex; align-items: center; }
            .checkbox-group input { width: auto; margin-right: 10px; }
        </style>
    </head>
    <body>
        <h1>Test Webhook Twilio</h1>
        <p>Utilisez ce formulaire pour simuler un webhook Twilio entrant.</p>
        
        <form id="webhookForm" method="post">
            <div class="form-group">
                <label for="From">Numéro de téléphone expéditeur (format E.164, ex: +33612345678):</label>
                <input type="text" id="From" name="From" value="+33612345678" required>
            </div>
            
            <div class="form-group">
                <label for="Body">Contenu du message:</label>
                <textarea id="Body" name="Body" rows="4" required>J'ai un problème avec mon compte, pouvez-vous m'aider?</textarea>
            </div>
            
            <div class="form-group checkbox-group">
                <input type="checkbox" id="is_whatsapp" name="is_whatsapp">
                <label for="is_whatsapp">Message WhatsApp</label>
                <p class="help-text">Laissez la case WhatsApp décochée pour simuler un SMS standard</p>
            </div>
            
            <button type="submit">Simuler Webhook</button>
        </form>
        
        <div id="result" class="result"></div>
        
        <script>
            document.getElementById('webhookForm').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                
                fetch('', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    const resultDiv = document.getElementById('result');
                    resultDiv.style.display = 'block';
                    
                    if (data.success) {
                        resultDiv.style.backgroundColor = '#dff0d8';
                        let content = `<strong>Succès!</strong><br>`;
                        content += `<strong>Status Code:</strong> ${data.status_code}<br>`;
                        content += `<strong>Réponse:</strong><br><pre>${data.content}</pre><br>`;
                        content += `<strong>Données du webhook:</strong><br><pre>${JSON.stringify(data.webhook_data, null, 2)}</pre>`;
                        resultDiv.innerHTML = content;
                    } else {
                        resultDiv.style.backgroundColor = '#f2dede';
                        resultDiv.innerHTML = `<strong>Erreur!</strong> ${data.error}`;
                    }
                })
                .catch(error => {
                    const resultDiv = document.getElementById('result');
                    resultDiv.style.display = 'block';
                    resultDiv.style.backgroundColor = '#f2dede';
                    resultDiv.innerHTML = `<strong>Erreur!</strong> Une erreur s'est produite lors de la requête.`;
                    console.error('Error:', error);
                });
            });
        </script>
    </body>
    </html>
    """
    
    from django.http import HttpResponse
    return HttpResponse(html)

@api_view(['GET'])
def simulated_messages(request):
    """
    Retourne la liste des messages SMS et WhatsApp simulés
    """
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
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def test_facebook_whatsapp(request):
    """
    Vue de test pour envoyer un message WhatsApp via l'API Facebook
    
    GET: Affiche un formulaire simple pour tester l'envoi
    POST: Envoie le message WhatsApp et affiche le résultat
    """
    if request.method == "POST":
        to_number = request.POST.get('to_number', '')
        message = request.POST.get('message', '')
        provider = request.POST.get('provider', 'facebook')
        
        if not to_number or not message:
            return JsonResponse({
                'success': False,
                'error': 'Numéro de téléphone et message requis'
            }, status=400)
        
        # Envoyer le message WhatsApp via l'API spécifiée
        if provider == 'facebook':
            result = send_whatsapp_via_facebook(to_number, message)
        elif provider == 'twilio':
            result = send_whatsapp_via_twilio(to_number, message)
        else:
            # Utiliser la fonction avec fallback automatique
            result = send_whatsapp(to_number, message, provider=provider)
        
        if result:
            response_data = {
                'success': True,
                'message': f"Message WhatsApp envoyé avec succès à {to_number} via {provider}",
                'provider': provider,
                'details': result
            }
            
            # Ajouter l'ID ou SID selon le fournisseur
            if 'sid' in result:
                response_data['sid'] = result['sid']
            elif 'id' in result:
                response_data['id'] = result['id']
                
            return JsonResponse(response_data)
        else:
            return JsonResponse({
                'success': False,
                'error': f"\u00c9chec de l'envoi du message WhatsApp via {provider}. Vérifiez les logs pour plus de détails."
            }, status=500)
    
    # Afficher le formulaire HTML pour tester l'envoi de messages WhatsApp
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test WhatsApp Facebook</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            h1 {{ color: #4285f4; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            label {{ display: block; margin-top: 10px; font-weight: bold; }}
            input[type="text"], textarea, select {{ width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ddd; border-radius: 3px; }}
            textarea {{ height: 100px; }}
            button {{ background-color: #4285f4; color: white; border: none; padding: 10px 15px; margin-top: 15px; border-radius: 3px; cursor: pointer; }}
            button:hover {{ background-color: #3b78e7; }}
            .result {{ margin-top: 20px; padding: 10px; border-radius: 3px; }}
            .success {{ background-color: #d4edda; color: #155724; }}
            .error {{ background-color: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Test WhatsApp Facebook</h1>
            <p>Utilisez ce formulaire pour tester l'envoi de messages WhatsApp via l'API Facebook.</p>
            
            <form method="post" id="whatsappForm">
                <label for="to_number">Numéro de téléphone (format E.164, ex: +33612345678):</label>
                <input type="text" id="to_number" name="to_number" placeholder="+33612345678" required>
                
                <label for="message">Message:</label>
                <textarea id="message" name="message" placeholder="Votre message..." required></textarea>
                
                <label for="provider">Fournisseur:</label>
                <select id="provider" name="provider">
                    <option value="facebook">Facebook (par défaut)</option>
                    <option value="twilio">Twilio</option>
                    <option value="auto">Auto (avec fallback)</option>
                </select>
                
                <button type="submit">Envoyer le message</button>
            </form>
            
            <div id="result" class="result" style="display: none;"></div>
            
            <script>
                document.getElementById('whatsappForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    
                    fetch(window.location.href, {{
                        method: 'POST',
                        body: formData
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        const resultDiv = document.getElementById('result');
                        resultDiv.style.display = 'block';
                        
                        if (data.success) {{
                            resultDiv.className = 'result success';
                            let details = '';
                            if (data.id) {{
                                details = `<br>ID: ${{data.id}}`;
                            }} else if (data.sid) {{
                                details = `<br>SID: ${{data.sid}}`;
                            }}
                            resultDiv.innerHTML = `<strong>Succès!</strong> ${{data.message}}${{details}}`;
                        }} else {{
                            resultDiv.className = 'result error';
                            resultDiv.innerHTML = `<strong>Erreur!</strong> ${{data.error}}`;
                        }}
                    }})
                    .catch(error => {{
                        const resultDiv = document.getElementById('result');
                        resultDiv.style.display = 'block';
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<strong>Erreur!</strong> Une erreur s'est produite: ${{error.message}}`;
                    }});
                }});
            </script>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def test_facebook_webhook(request):
    """
    Vue de test pour simuler un webhook Facebook WhatsApp entrant
    
    GET: Affiche un formulaire simple pour simuler un webhook Facebook
    POST: Simule un webhook Facebook et affiche la réponse
    """
    from django.conf import settings
    
    if request.method == "POST":
        # Récupérer les données du formulaire
        phone_number = request.POST.get('phone_number', '')
        message_body = request.POST.get('message_body', '')
        message_type = request.POST.get('message_type', 'text')
        
        if not phone_number or not message_body:
            return JsonResponse({
                'success': False,
                'error': 'Numéro de téléphone et message requis'
            }, status=400)
        
        # Construire le payload du webhook Facebook
        if message_type == 'text':
            webhook_payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "id": settings.FACEBOOK_WHATSAPP_BUSINESS_ACCOUNT_ID,
                    "changes": [{
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": settings.FACEBOOK_WHATSAPP_PHONE_NUMBER_ID,
                                "phone_number_id": settings.FACEBOOK_WHATSAPP_PHONE_NUMBER_ID
                            },
                            "contacts": [{
                                "profile": {
                                    "name": "Test User"
                                },
                                "wa_id": phone_number.replace("+", "")
                            }],
                            "messages": [{
                                "from": phone_number.replace("+", ""),
                                "id": f"wamid.test{int(time.time())}",
                                "timestamp": str(int(time.time())),
                                "text": {
                                    "body": message_body
                                },
                                "type": "text"
                            }]
                        },
                        "field": "messages"
                    }]
                }]
            }
        elif message_type == 'image':
            webhook_payload = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "id": settings.FACEBOOK_WHATSAPP_BUSINESS_ACCOUNT_ID,
                    "changes": [{
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": settings.FACEBOOK_WHATSAPP_PHONE_NUMBER_ID,
                                "phone_number_id": settings.FACEBOOK_WHATSAPP_PHONE_NUMBER_ID
                            },
                            "contacts": [{
                                "profile": {
                                    "name": "Test User"
                                },
                                "wa_id": phone_number.replace("+", "")
                            }],
                            "messages": [{
                                "from": phone_number.replace("+", ""),
                                "id": f"wamid.test{int(time.time())}",
                                "timestamp": str(int(time.time())),
                                "image": {
                                    "caption": message_body,
                                    "mime_type": "image/jpeg",
                                    "sha256": "hash-test-image",
                                    "id": "test-image-id"
                                },
                                "type": "image"
                            }]
                        },
                        "field": "messages"
                    }]
                }]
            }
        
        # Envoyer le webhook à l'endpoint Facebook
        import requests
        
        # Construire l'URL du webhook Facebook
        # Utiliser l'URL basée sur le chemin sans paramètre source
        webhook_url = request.build_absolute_uri('/api/inbound/facebook-webhook/')
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            webhook_response = requests.post(
                webhook_url,
                json=webhook_payload,
                headers=headers
            )
            
            return JsonResponse({
                'success': True,
                'message': f"Webhook Facebook simulé envoyé avec succès",
                'webhook_url': webhook_url,
                'status_code': webhook_response.status_code,
                'response': webhook_response.text,
                'payload': webhook_payload
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f"\u00c9chec de l'envoi du webhook simulé: {str(e)}",
                'webhook_url': webhook_url,
                'payload': webhook_payload
            }, status=500)
    
    # Afficher le formulaire HTML pour tester les webhooks Facebook
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Webhook Facebook WhatsApp</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
            h1 {{ color: #4285f4; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            label {{ display: block; margin-top: 10px; font-weight: bold; }}
            input[type="text"], textarea, select {{ width: 100%; padding: 8px; margin-top: 5px; border: 1px solid #ddd; border-radius: 3px; }}
            textarea {{ height: 100px; }}
            button {{ background-color: #4285f4; color: white; border: none; padding: 10px 15px; margin-top: 15px; border-radius: 3px; cursor: pointer; }}
            button:hover {{ background-color: #3b78e7; }}
            .result {{ margin-top: 20px; padding: 10px; border-radius: 3px; }}
            .success {{ background-color: #d4edda; color: #155724; }}
            .error {{ background-color: #f8d7da; color: #721c24; }}
            pre {{ background-color: #f8f9fa; padding: 10px; overflow: auto; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Test Webhook Facebook WhatsApp</h1>
            <p>Utilisez ce formulaire pour simuler un webhook entrant de Facebook WhatsApp.</p>
            
            <form method="post" id="webhookForm">
                <label for="phone_number">Numéro de téléphone (format E.164, ex: +33612345678):</label>
                <input type="text" id="phone_number" name="phone_number" placeholder="+33612345678" required>
                
                <label for="message_body">Message:</label>
                <textarea id="message_body" name="message_body" placeholder="Votre message..." required></textarea>
                
                <label for="message_type">Type de message:</label>
                <select id="message_type" name="message_type">
                    <option value="text">Texte</option>
                    <option value="image">Image avec caption</option>
                </select>
                
                <button type="submit">Simuler le webhook</button>
            </form>
            
            <div id="result" class="result" style="display: none;"></div>
            
            <script>
                document.getElementById('webhookForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    
                    const formData = new FormData(this);
                    
                    fetch(window.location.href, {{
                        method: 'POST',
                        body: formData
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        const resultDiv = document.getElementById('result');
                        resultDiv.style.display = 'block';
                        
                        if (data.success) {{
                            resultDiv.className = 'result success';
                            resultDiv.innerHTML = `
                                <strong>Succès!</strong> ${{data.message}}<br>
                                URL: ${{data.webhook_url}}<br>
                                Code de statut: ${{data.status_code}}<br>
                                Réponse: <pre>${{data.response}}</pre>
                                Payload: <pre>${{JSON.stringify(data.payload, null, 2)}}</pre>
                            `;
                        }} else {{
                            resultDiv.className = 'result error';
                            resultDiv.innerHTML = `
                                <strong>Erreur!</strong> ${{data.error}}<br>
                                URL: ${{data.webhook_url}}<br>
                                Payload: <pre>${{JSON.stringify(data.payload, null, 2)}}</pre>
                            `;
                        }}
                    }})
                    .catch(error => {{
                        const resultDiv = document.getElementById('result');
                        resultDiv.style.display = 'block';
                        resultDiv.className = 'result error';
                        resultDiv.innerHTML = `<strong>Erreur!</strong> Une erreur s'est produite: ${{error.message}}`;
                    }});
                }});
            </script>
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(html)


# URLs pour les vues de test
urlpatterns = [
    path('test-sms/', test_twilio_sms, name='test-twilio-sms'),
    path('test-webhook/', test_twilio_webhook, name='test-twilio-webhook'),
    path('test-whatsapp-facebook/', test_facebook_whatsapp, name='test-facebook-whatsapp'),
    path('test-facebook-webhook/', test_facebook_webhook, name='test-facebook-webhook'),
    path('simulated-messages/', simulated_messages, name='simulated-messages'),
]
