# Feedback Platform

Une plateforme de feedback communautaire multicanal permettant de recueillir, traiter et répondre aux feedbacks via différents canaux (Web, SMS, WhatsApp).

## Fonctionnalités

- **Interface PWA** : Application web progressive avec fonctionnalités hors ligne
- **Multi-canal** : Soumission de feedbacks via Web, SMS et WhatsApp
- **Tableau de bord** : Interface de modération pour traiter les feedbacks
- **Statistiques** : Visualisation des données et KPIs
- **API REST** : Backend robuste avec Django REST Framework
- **Authentification** : Système sécurisé avec JWT

## Architecture

- **Frontend** : React PWA
- **Backend** : Django + Django REST Framework
- **Base de données** : PostgreSQL
- **File d'attente** : Redis + Celery
- **Conteneurisation** : Docker & Docker Compose

## Prérequis

- Docker et Docker Compose
- Git

## Installation

1. Cloner le dépôt :
   ```bash
   git clone https://github.com/votre-utilisateur/feedback-platform.git
   cd feedback-platform
   ```

2. Lancer l'application avec Docker Compose :
   ```bash
   docker-compose up -d
   ```

3. Créer un superutilisateur pour l'administration :
   ```bash
   docker-compose exec backend python manage.py createsuperuser
   ```

4. Accéder à l'application :
   - Frontend : http://localhost:3000
   - Backend API : http://localhost:8000/api/
   - Admin Django : http://localhost:8000/admin/

## Configuration

### Variables d'environnement

Vous pouvez configurer l'application en modifiant les variables d'environnement dans le fichier `docker-compose.yml` :

- `DEBUG` : Mode de débogage (1 pour activer, 0 pour désactiver)
- `SECRET_KEY` : Clé secrète Django
- `DATABASE_URL` : URL de connexion à la base de données
- `REDIS_URL` : URL de connexion à Redis
- `TWILIO_ACCOUNT_SID` : SID du compte Twilio pour SMS/WhatsApp
- `TWILIO_AUTH_TOKEN` : Token d'authentification Twilio
- `TWILIO_PHONE_NUMBER` : Numéro de téléphone Twilio pour SMS
- `TWILIO_WHATSAPP_NUMBER` : Numéro WhatsApp Twilio

## Utilisation

### Soumission de feedback

Les utilisateurs peuvent soumettre des feedbacks via :
- L'interface web
- SMS (via Twilio)
- WhatsApp (via Twilio)

### Modération

Les modérateurs peuvent :
- Consulter les feedbacks dans le tableau de bord
- Catégoriser et prioriser les feedbacks
- Répondre aux feedbacks
- Visualiser les statistiques

## Développement

### Structure du projet

```
feedback-platform/
├── backend/         # Django + DRF
│   ├── feedback_project/  # Configuration du projet
│   └── feedback_api/      # Application principale
├── frontend/        # React PWA
│   ├── public/
│   └── src/
├── docker-compose.yml
└── infra/           # Scripts de déploiement
```

### Commandes utiles

- Lancer les migrations :
  ```bash
  docker-compose exec backend python manage.py migrate
  ```

- Créer des migrations :
  ```bash
  docker-compose exec backend python manage.py makemigrations
  ```

- Lancer les tests :
  ```bash
  docker-compose exec backend python manage.py test
  ```

- Accéder au shell Django :
  ```bash
  docker-compose exec backend python manage.py shell
  ```

- Accéder aux logs :
  ```bash
  docker-compose logs -f [service]
  ```

## Webhook SMS

### Présentation

Le système de webhook SMS permet de recevoir et de traiter automatiquement les feedbacks soumis par SMS. Le service webhook est un microservice Flask qui :

1. Reçoit les messages SMS au format JSON
2. Traite les données entrantes
3. Transmet les feedbacks à l'API principale
4. Déclenche la classification automatique des feedbacks

### Architecture

```
SMS Provider/Aggregateur -> Webhook SMS (Flask) -> API Feedback Platform (Django) -> Classification (Celery)
```

### Configuration

#### 1. Variables d'environnement

Le service webhook utilise les variables d'environnement suivantes (définies dans `webhook/.env`) :

- `FEEDBACK_URL` : URL de l'API principale (par défaut: http://backend:8000/api/webhook/json-sms/)
- `API_KEY` : Clé d'API pour l'authentification avec le backend
- `VERIFY_SSL` : Validation du certificat SSL (false en développement)
- `LOG_LEVEL` : Niveau de détail des logs (INFO, DEBUG, etc.)
- `HOST` : Adresse d'écoute du service (0.0.0.0 par défaut)
- `PORT` : Port d'écoute (5000 par défaut)

#### 2. Configuration du fournisseur SMS

Configurez votre fournisseur SMS pour envoyer des requêtes HTTP POST au format suivant :

```
POST http://votre-serveur:5000/webhook
Content-Type: application/json

{
  "from": "+123456789",
  "text": "Contenu du message SMS"
}
```

#### 3. Sécurité du webhook

Le webhook utilise une clé API pour l'authentification. Assurez-vous que :

- La clé `API_KEY` dans `webhook/.env` correspond à `WEBHOOK_API_KEY` dans `backend/.env`
- Votre fournisseur SMS inclut cette clé dans l'en-tête ou utilise une connexion sécurisée

### Test du webhook

Vous pouvez tester le webhook localement avec la commande :

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"from": "+123456789", "text": "Ceci est un test de feedback par SMS"}'
```

Pour un test plus complet, utilisez le script inclus :

```bash
bash test-facebook-webhook.sh
```

### Classification des feedbacks SMS

Les feedbacks reçus par SMS sont automatiquement classifiés selon les catégories humanitaires :
- Commentaire
- Suggestion
- Plainte
- Question
- Éloge
- Sécurité alimentaire
- Eau/assainissement/hygiène 
- Santé
- Éducation et psychosocial
- Hébergement
- Moyens de subsistance
- Protection
- Qualité des services
- Comportement du personnel
- Information et participation

## Facebook WhatsApp Business API

### Présentation

L'intégration Facebook WhatsApp Business API permet de recevoir et envoyer des messages WhatsApp pour collecter des feedbacks et répondre aux bénéficiaires via ce canal populaire.

### Prérequis

1. Un compte Facebook Business
2. Une application WhatsApp Business API
3. Un numéro de téléphone vérifié
4. Un accès à l'API WhatsApp Cloud

### Configuration

#### 1. Configuration Facebook

1. Créez un compte sur [Facebook Developers](https://developers.facebook.com/)
2. Créez une application Business
3. Activez l'API WhatsApp pour votre application
4. Vérifiez votre numéro de téléphone
5. Obtenez les identifiants suivants :
   - Token d'accès WhatsApp
   - ID de numéro de téléphone
   - ID de compte business

#### 2. Variables d'environnement

Configurez les variables suivantes dans `backend/.env` :

```
FACEBOOK_WHATSAPP_TOKEN=your-facebook-whatsapp-token
FACEBOOK_WHATSAPP_PHONE_NUMBER_ID=your-facebook-phone-number-id
FACEBOOK_WHATSAPP_BUSINESS_ACCOUNT_ID=your-facebook-business-account-id
FACEBOOK_WHATSAPP_API_VERSION=v18.0
FACEBOOK_WEBHOOK_VERIFY_TOKEN=your-facebook-webhook-verify-token
```

#### 3. Configuration du webhook

1. Dans le tableau de bord Facebook Developers, configurez le webhook avec :
   - URL du webhook : `https://votre-domaine.com/api/webhook/whatsapp/`
   - Token de vérification : celui défini dans `FACEBOOK_WEBHOOK_VERIFY_TOKEN`
   - Abonnez-vous aux événements : `messages`

2. Testez la configuration avec l'outil de test de webhook de Facebook

### Utilisation

Une fois configuré, le système :
1. Reçoit automatiquement les messages WhatsApp
2. Les traite comme des feedbacks
3. Déclenche la classification automatique
4. Permet de répondre directement via l'interface de la plateforme

## Déploiement en Production

### Prérequis

- Un serveur Linux (Ubuntu 20.04+ recommandé)
- Docker et Docker Compose installés
- Accès SSH au serveur
- Un domaine avec DNS configuré (recommandé)

### Étapes de déploiement

#### 1. Préparation du serveur

```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Installation de Docker
sudo apt install -y docker.io docker-compose

# Ajout de l'utilisateur au groupe Docker
sudo usermod -aG docker ${USER}
```

#### 2. Configuration du pare-feu

```bash
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 8000
sudo ufw enable
```

#### 3. Déploiement de l'application

```bash
# Clonage du dépôt
git clone https://github.com/yaroing/feedback-platform.git
cd feedback-platform

# Configuration des variables d'environnement
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
cp webhook/.env.example webhook/.env

# Édition des fichiers .env avec les bonnes valeurs
nano backend/.env
nano frontend/.env
nano webhook/.env
```

#### 4. Lancement des services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### 5. Configuration du domaine et HTTPS (avec Certbot et Nginx)

```bash
# Installation de Nginx et Certbot
sudo apt install -y nginx certbot python3-certbot-nginx

# Configuration de Nginx
sudo nano /etc/nginx/sites-available/feedback-platform

# Obtention du certificat SSL
sudo certbot --nginx -d votre-domaine.com
```

Exemple de configuration Nginx :
```nginx
server {
    server_name votre-domaine.com;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /webhook {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    listen 443 ssl;
    # Certbot ajoutera les configurations SSL ici
}
```

### Ajout de l'adresse IP du serveur aux hôtes autorisés

Assurez-vous que l'adresse IP de votre serveur de production est ajoutée à la liste `ALLOWED_HOSTS` dans `backend/.env` :

```
ALLOWED_HOSTS=localhost,127.0.0.1,votre-domaine.com
```

## Maintenance et Mises à jour

### Sauvegardes

#### 1. Sauvegarde de la base de données

```bash
# Sauvegarde de la base PostgreSQL
docker-compose exec -T db pg_dump -U postgres feedback_platform > backup_$(date +%Y-%m-%d).sql

# Restauration
cat backup_2025-06-15.sql | docker-compose exec -T db psql -U postgres feedback_platform
```

#### 2. Sauvegarde des fichiers media

```bash
# Sauvegarde des uploads et médias
tar -czf media_backup_$(date +%Y-%m-%d).tar.gz ./backend/media/

# Restauration
tar -xzf media_backup_2025-06-15.tar.gz -C ./
```

### Mises à jour de l'application

```bash
# Récupération des dernières modifications
git pull

# Reconstruction des images Docker si nécessaire
docker-compose build

# Redémarrage des services
docker-compose down
docker-compose up -d

# Application des migrations
docker-compose exec backend python manage.py migrate
```

### Surveillance et logs

```bash
# Surveillance des logs
docker-compose logs -f

# Surveillance d'un service spécifique
docker-compose logs -f backend

# Surveillance des performances
docker stats
```

### Maintenance périodique

- Nettoyage des données temporaires : `docker-compose exec backend python manage.py clearsessions`
- Optimisation de la base de données : `docker-compose exec db psql -U postgres -c "VACUUM ANALYZE;" feedback_platform`
- Mise à jour des dépendances : Vérifiez régulièrement les mises à jour de sécurité

## Licence

MIT

admin', 'admin@example.com', 'adminpassword'