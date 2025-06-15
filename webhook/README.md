# Webhook JSON SMS pour la plateforme de feedback

Ce webhook est un service indépendant qui reçoit des SMS au format JSON et les transmet à la plateforme de feedback. Il sert d'intermédiaire entre les fournisseurs SMS et la plateforme de feedback, permettant une intégration facile avec n'importe quel fournisseur SMS.

## Fonctionnalités

- Réception de SMS au format JSON via HTTP POST
- Validation des données reçues
- Transmission des données à la plateforme de feedback
- Interface de test pour envoyer des SMS manuellement
- Endpoint de vérification de santé
- Configuration flexible via variables d'environnement ou arguments de ligne de commande
- Journalisation complète des événements

## Prérequis

- Python 3.6 ou supérieur
- pip (gestionnaire de paquets Python)
- Accès à la plateforme de feedback

## Installation

1. Clonez ce dépôt ou copiez les fichiers dans un répertoire de votre choix
2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

3. Copiez le fichier de configuration d'exemple et modifiez-le selon vos besoins :

```bash
cp config.env.example config.env
# Modifiez config.env avec vos paramètres
```

## Utilisation

### Démarrage du webhook

```bash
# Avec les paramètres par défaut
python app.py

# Avec des paramètres personnalisés
python app.py --port 5001 --host 127.0.0.1 --feedback-url https://votre-plateforme.com/api/webhook/json-sms/ --api-key votre_cle_secrete
```

### Utilisation avec des variables d'environnement

Vous pouvez également configurer le webhook avec des variables d'environnement :

```bash
# Sur Linux/Mac
export FEEDBACK_URL=https://votre-plateforme.com/api/webhook/json-sms/
export API_KEY=votre_cle_secrete
export VERIFY_SSL=true
python app.py

# Sur Windows
set FEEDBACK_URL=https://votre-plateforme.com/api/webhook/json-sms/
set API_KEY=votre_cle_secrete
set VERIFY_SSL=true
python app.py
```

### Utilisation avec Docker

Un Dockerfile est fourni pour faciliter le déploiement :

```bash
# Construire l'image
docker build -t sms-webhook .

# Exécuter le conteneur
docker run -p 5000:5000 -e FEEDBACK_URL=https://votre-plateforme.com/api/webhook/json-sms/ -e API_KEY=votre_cle_secrete sms-webhook
```

## Format des données attendu

Le webhook attend des requêtes HTTP POST avec un corps au format JSON contenant les champs suivants :

```json
{
  "from": "+33612345678",
  "text": "Contenu du message SMS",
  "sentStamp": "2025-06-01T18:45:00Z",
  "receivedStamp": "2025-06-01T18:45:02Z",
  "sim": "SIM1"
}
```

Champs obligatoires :
- `from` : Numéro de téléphone de l'expéditeur
- `text` : Contenu du message SMS

Champs optionnels :
- `sentStamp` : Horodatage d'envoi du message (ISO 8601)
- `receivedStamp` : Horodatage de réception du message (ISO 8601)
- `sim` : Identifiant de la carte SIM ou du canal de réception

## Endpoints

- `/webhook` : Endpoint principal pour recevoir les SMS (POST)
- `/test` : Interface web de test pour envoyer des SMS manuellement (GET)
- `/health` : Endpoint de vérification de santé du service (GET)

## Intégration avec des fournisseurs SMS

Pour intégrer ce webhook avec un fournisseur SMS, vous devez configurer le fournisseur pour qu'il envoie les SMS reçus à l'URL de votre webhook au format JSON spécifié ci-dessus.

Si votre fournisseur SMS utilise un format différent, vous pouvez créer un adaptateur personnalisé qui convertit le format du fournisseur vers le format attendu par ce webhook.

## Sécurité

Pour sécuriser votre webhook, vous pouvez :

1. Utiliser une clé API (paramètre `--api-key` ou variable d'environnement `API_KEY`)
2. Déployer le webhook derrière un proxy inverse avec HTTPS
3. Configurer des restrictions d'accès basées sur l'IP au niveau du réseau

## Dépannage

### Problèmes courants

1. **Erreur de connexion à la plateforme de feedback**
   - Vérifiez que l'URL de la plateforme est correcte
   - Vérifiez que la plateforme est accessible depuis le webhook
   - Si vous utilisez HTTPS, essayez avec `--no-verify-ssl` si vous rencontrez des problèmes de certificat

2. **Erreur 400 Bad Request**
   - Vérifiez que le format JSON envoyé est correct
   - Vérifiez que les champs obligatoires sont présents

3. **Erreur 500 Internal Server Error**
   - Consultez les logs pour plus de détails sur l'erreur

### Logs

Les logs sont affichés dans la console et enregistrés dans le fichier `webhook.log`. Consultez ce fichier pour diagnostiquer les problèmes.

## Licence

Ce projet est sous licence MIT. Voir le fichier LICENSE pour plus de détails.
