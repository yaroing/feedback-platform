#!/usr/bin/env python
"""
Script de test pour le webhook JSON SMS
"""

import requests
import json
import datetime
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG)

# Configuration
webhook_url = "http://localhost:5000/webhook"
backend_url = "http://localhost:8000/api/webhook/json-sms/"
test_data = {
    "from": "+33612345678",
    "text": "Ceci est un test de SMS envoyé depuis Python",
    "sentStamp": datetime.datetime.now().isoformat(),
    "receivedStamp": datetime.datetime.now().isoformat(),
    "sim": "SIM1"
}

# Vérification du backend
print(f"Vérification de l'accès au backend à {backend_url}")
try:
    backend_response = requests.get(
        "http://localhost:8000/api/",
        timeout=5
    )
    print(f"Backend accessible: {backend_response.status_code}")
    print(f"Contenu de la réponse: {backend_response.text[:200]}...")
    
    # Test direct de l'endpoint du webhook dans le backend
    print(f"\nTest direct de l'endpoint du webhook dans le backend: {backend_url}")
    try:
        direct_response = requests.post(
            backend_url,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        print(f"Réponse directe du backend: {direct_response.status_code}")
        print(f"Contenu de la réponse: {direct_response.text}")
    except Exception as e:
        print(f"Erreur lors de l'accès direct à l'endpoint du webhook: {e}")
except Exception as e:
    print(f"Erreur lors de l'accès au backend: {e}")
    print("Le webhook pourrait ne pas fonctionner correctement si le backend n'est pas accessible.")


# Envoi de la requête
print(f"Envoi d'une requête à {webhook_url}")
print(f"Données: {json.dumps(test_data, indent=2)}")

try:
    response = requests.post(
        webhook_url,
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    
    # Affichage de la réponse
    print(f"\nCode de statut: {response.status_code}")
    print(f"Réponse: {response.text}")
    
    # Analyse de la réponse JSON si possible
    try:
        response_json = response.json()
        print("\nRéponse JSON:")
        print(json.dumps(response_json, indent=2))
    except:
        print("\nLa réponse n'est pas au format JSON")
        
except Exception as e:
    print(f"Erreur lors de l'envoi de la requête: {e}")
