#!/usr/bin/env python
"""
Webhook JSON SMS pour la plateforme de feedback

Ce script crée un serveur web qui reçoit des SMS au format JSON et les transmet
à la plateforme de feedback via son API REST.

Format attendu:
{
    "from": "%from%",
    "text": "%text%",
    "sentStamp": "%sentStamp%",
    "receivedStamp": "%receivedStamp%",
    "sim": "%sim%"
}

Usage:
    python app.py [--port PORT] [--host HOST] [--feedback-url URL]
"""
from dotenv import load_dotenv
load_dotenv()  # prend les variables d'environnement du fichier .env
import os
import json
import logging
import argparse
import datetime
from flask import Flask, request, jsonify
import requests

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('webhook.log')
    ]
)
logger = logging.getLogger('sms_webhook')

# Création de l'application Flask
app = Flask(__name__)

# Configuration par défaut
DEFAULT_PORT = 5000
DEFAULT_HOST = '0.0.0.0'
DEFAULT_FEEDBACK_URL = 'http://backend:8000/api/inbound/webhook/json-sms/'
DEFAULT_API_KEY = None

# Variables globales pour la configuration
config = {
    'feedback_url': os.environ.get('FEEDBACK_URL', DEFAULT_FEEDBACK_URL),
    'api_key': os.environ.get('API_KEY', DEFAULT_API_KEY),
    'verify_ssl': os.environ.get('VERIFY_SSL', 'true').lower() == 'true',
    'public_url': os.environ.get('WEBHOOK_PUBLIC_URL', 'http://localhost:5000')
}

# Afficher la configuration au démarrage
print(f"\n\n==== CONFIGURATION DU WEBHOOK ====")
print(f"FEEDBACK_URL (env): {os.environ.get('FEEDBACK_URL', 'Non défini')}")
print(f"DEFAULT_FEEDBACK_URL: {DEFAULT_FEEDBACK_URL}")
print(f"URL utilisée: {config['feedback_url']}")
print(f"VERIFY_SSL: {config['verify_ssl']}")
print(f"DEBUG: {os.environ.get('DEBUG', 'Non défini')}")
print(f"URL PUBLIQUE (ngrok): {config['public_url']}")

print(f"==== FIN DE LA CONFIGURATION ====\n\n")

# Logger également la configuration
api_key_status = 'Défini' if config['api_key'] else 'Non défini'
logger.info(f"Configuration du webhook: URL={config['feedback_url']}, VERIFY_SSL={config['verify_ssl']}, API_KEY={api_key_status}")


@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de vérification de santé du service"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.datetime.now().isoformat(),
        'config': {
            'feedback_url': config['feedback_url'],
            'has_api_key': config['api_key'] is not None,
            'verify_ssl': config['verify_ssl']
        }
    })

@app.route('/webhook', methods=['POST'])
def receive_sms():
    """
    Endpoint principal pour recevoir les SMS au format JSON
    """
    try:
        # Vérifier si le contenu est du JSON
        logger.info(f"Headers reçus: {dict(request.headers)}")
        if request.headers.get('Content-Type') != 'application/json':
            logger.error(f"Content-Type incorrect: {request.headers.get('Content-Type')}")
            return jsonify({"status": "error", "message": "Content-Type must be application/json"}), 400
        
        # Récupérer les données JSON
        data = request.get_json()
        logger.info(f"Données reçues: {data}")
        
        # Adapter les données selon le format (Android app ou format standard)
        feedback_data = {}
        
        # Format Android app
        if 'sender' in data and 'body' in data:
            feedback_data = {
                'from': data.get('sender', ''),
                'text': data.get('body', ''),
                'sentStamp': data.get('timestamp', datetime.datetime.now().isoformat()),
                'receivedStamp': datetime.datetime.now().isoformat(),
                'sim': 'android'
            }
            logger.info(f"Format Android détecté, données adaptées: {feedback_data}")
        # Format standard
        elif 'from' in data and 'text' in data:
            feedback_data = {
                'from': data.get('from', ''),
                'text': data.get('text', ''),
                'sentStamp': data.get('sentStamp', datetime.datetime.now().isoformat()),
                'receivedStamp': data.get('receivedStamp', datetime.datetime.now().isoformat()),
                'sim': data.get('sim', 'default')
            }
        else:
            logger.error("Champs obligatoires manquants")
            return jsonify({"status": "error", "message": "Missing required fields: 'from'/'sender' and 'text'/'body' are required"}), 400
        
        # Préparer les en-têtes
        headers = {'Content-Type': 'application/json'}
        if config['api_key']:
            headers['X-API-Key'] = config['api_key']
        
        logger.info(f"Envoi des données à {config['feedback_url']} avec les headers: {headers}")
        logger.info(f"Données envoyées: {feedback_data}")
        
        # Envoyer les données à la plateforme de feedback
        try:
            logger.info(f"Tentative de connexion à {config['feedback_url']}")
            
            # Tester d'abord si le backend est accessible
            try:
                test_url = config['feedback_url'].rsplit('/', 2)[0] + '/'
                logger.info(f"Test d'accessibilité du backend: {test_url}")
                test_response = requests.get(
                    test_url,
                    verify=config['verify_ssl'],
                    timeout=5
                )
                logger.info(f"Test d'accessibilité du backend: {test_response.status_code}")
                logger.info(f"Contenu de la réponse de test: {test_response.text[:200]}...")
            except Exception as test_e:
                logger.error(f"Erreur lors du test d'accessibilité du backend: {str(test_e)}")
            
            # Envoi de la requête réelle
            response = requests.post(
                config['feedback_url'],
                json=feedback_data,
                headers=headers,
                verify=config['verify_ssl'],
                timeout=10  # Ajouter un timeout pour éviter les blocages
            )
            
            logger.info(f"Réponse reçue du backend: Status={response.status_code}, Content={response.text}")
            
            # Essayer de parser la réponse JSON si possible
            try:
                response_json = response.json()
                logger.info(f"Réponse JSON: {response_json}")
            except:
                logger.warning("La réponse n'est pas au format JSON")
            
            # Vérifier la réponse
            if response.status_code == 200:
                logger.info("SMS transmis avec succès au backend")
                return jsonify({"status": "success", "message": "SMS transmis avec succès"}), 200
            else:
                logger.error(f"Erreur du backend: {response.status_code} - {response.text}")
                return jsonify({
                    "status": "error", 
                    "message": f"Erreur du backend: {response.status_code}",
                    "backend_response": response.text
                }), 500
                
        except requests.exceptions.ConnectionError as conn_err:
            error_details = str(conn_err)
            logger.error(f"Erreur de connexion au backend: {config['feedback_url']}")
            logger.error(f"Détails de l'erreur de connexion: {error_details}")
            return jsonify({
                "status": "error", 
                "message": "Impossible de se connecter au backend",
                "error_details": error_details
            }), 500
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout lors de la connexion au backend: {config['feedback_url']}")
            return jsonify({"status": "error", "message": "Timeout lors de la connexion au backend"}), 500
            
        except Exception as e:
            error_details = str(e)
            logger.error(f"Erreur inattendue: {error_details}")
            logger.exception("Stacktrace de l'erreur:")
            return jsonify({
                "status": "error", 
                "message": f"Erreur inattendue",
                "error_details": error_details
            }), 500
    except Exception as e:
        logger.exception("Erreur lors du traitement de la requête")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}'
        }), 500

@app.route('/test', methods=['GET'])
def test_form():
    """Page de test pour envoyer des SMS manuellement"""
    public_url = config['public_url']
    webhook_endpoint = f"{public_url}/webhook" if not public_url.endswith('/webhook') else public_url
    feedback_url = config['feedback_url']
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test SMS Webhook</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
            .form-group {{ margin-bottom: 15px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input, textarea {{ width: 100%; padding: 8px; box-sizing: border-box; }}
            button {{ background-color: #4CAF50; color: white; padding: 10px 15px; border: none; cursor: pointer; }}
            button:hover {{ background-color: #45a049; }}
            #response {{ margin-top: 20px; padding: 10px; background-color: #f8f8f8; border-left: 5px solid #4CAF50; }}
            .error {{ color: red; }}
            .info-box {{ background-color: #e7f3fe; border-left: 6px solid #2196F3; padding: 10px; margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        <h1>Test SMS Webhook</h1>
        <div class="info-box">
            <p><strong>Configuration actuelle:</strong></p>
            <p>URL publique (ngrok): <code>{webhook_endpoint}</code></p>
            <p>URL backend: <code>{feedback_url}</code></p>
        </div>
        <div class="form-group">
            <label for="from">Numéro de téléphone expéditeur:</label>
            <input type="text" id="from" name="from" placeholder="+33612345678" required>
        </div>
        <div class="form-group">
            <label for="text">Contenu du message:</label>
            <textarea id="text" name="text" rows="4" placeholder="Votre message ici..." required></textarea>
        </div>
        <div class="form-group">
            <label for="sentStamp">Horodatage d'envoi (optionnel):</label>
            <input type="text" id="sentStamp" name="sentStamp" placeholder="2025-06-01T18:45:00Z">
        </div>
        <div class="form-group">
            <label for="receivedStamp">Horodatage de réception (optionnel):</label>
            <input type="text" id="receivedStamp" name="receivedStamp" placeholder="2025-06-01T18:45:02Z">
        </div>
        <div class="form-group">
            <label for="sim">SIM (optionnel):</label>
            <input type="text" id="sim" name="sim" placeholder="SIM1">
        </div>
        <button id="send">Envoyer</button>
        <div id="response" style="display: none;"></div>

        <script>
            document.getElementById('send').addEventListener('click', function() {{
                const from = document.getElementById('from').value;
                const text = document.getElementById('text').value;
                const sentStamp = document.getElementById('sentStamp').value || new Date().toISOString();
                const receivedStamp = document.getElementById('receivedStamp').value || new Date().toISOString();
                const sim = document.getElementById('sim').value || 'default';
                
                if (!from || !text) {{
                    alert('Le numéro de téléphone et le contenu du message sont obligatoires.');
                    return;
                }}
                
                const data = {{
                    from: from,
                    text: text,
                    sentStamp: sentStamp,
                    receivedStamp: receivedStamp,
                    sim: sim
                }};
                
                const responseDiv = document.getElementById('response');
                responseDiv.style.display = 'block';
                responseDiv.innerHTML = 'Envoi en cours...';
                
                fetch('/webhook', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify(data)
                }})
                .then(response => response.json())
                .then(data => {{
                    responseDiv.innerHTML = `<pre>${{JSON.stringify(data, null, 2)}}</pre>`;
                    if (data.status === 'success') {{
                        responseDiv.style.borderLeft = '5px solid #4CAF50';
                    }} else {{
                        responseDiv.style.borderLeft = '5px solid #f44336';
                    }}
                }})
                .catch(error => {{
                    responseDiv.innerHTML = `<pre class="error">Erreur: ${{error.message}}</pre>`;
                    responseDiv.style.borderLeft = '5px solid #f44336';
                }});
            }});
        </script>
    </body>
    </html>
    """
    return html

def parse_args():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description='Webhook JSON SMS pour la plateforme de feedback')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Port d\'écoute (défaut: {DEFAULT_PORT})')
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                        help=f'Hôte d\'écoute (défaut: {DEFAULT_HOST})')
    parser.add_argument('--feedback-url', type=str, default=config['feedback_url'],
                        help=f'URL de l\'API de la plateforme de feedback (défaut: {DEFAULT_FEEDBACK_URL})')
    parser.add_argument('--api-key', type=str, default=config['api_key'],
                        help='Clé API pour l\'authentification (optionnel)')
    parser.add_argument('--no-verify-ssl', action='store_true',
                        help='Désactiver la vérification SSL pour les requêtes vers la plateforme de feedback')
    return parser.parse_args()

if __name__ == '__main__':
    # Récupérer les arguments
    args = parse_args()
    
    # Mettre à jour la configuration
    config['feedback_url'] = args.feedback_url
    config['api_key'] = args.api_key
    if args.no_verify_ssl:
        config['verify_ssl'] = False
    
    # Afficher la configuration
    logger.info(f"Démarrage du webhook sur {args.host}:{args.port}")
    logger.info(f"URL de la plateforme de feedback: {config['feedback_url']}")
    logger.info(f"Vérification SSL: {config['verify_ssl']}")
    logger.info(f"Clé API configurée: {config['api_key'] is not None}")
    
    # Démarrer le serveur
    app.run(host=args.host, port=args.port)
