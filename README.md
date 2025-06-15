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

## Licence

MIT

admin', 'admin@example.com', 'adminpassword'