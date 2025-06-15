"""
Django settings for feedback_project project.
"""

import os
from pathlib import Path
from datetime import timedelta
import dj_database_url
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env s'il existe
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == '1'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') + ['a5a7-2001-4278-80-f224-c939-1db8-1e37-c09a.ngrok-free.app', '.ngrok-free.app', 'backend', 'backend:8000']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party apps
    'rest_framework',
    'corsheaders',
    'drf_yasg',
    'django_celery_beat',
    'django_filters',
    # Local apps
    'feedback_api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Configuration CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# Configuration CSRF
CSRF_TRUSTED_ORIGINS = ['https://a5a7-2001-4278-80-f224-c939-1db8-1e37-c09a.ngrok-free.app', 'https://*.ngrok-free.app', 'http://localhost:8000', 'http://localhost:3000']

ROOT_URLCONF = 'feedback_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, '../frontend/build'),
            os.path.join(BASE_DIR, 'templates'),  # Ajout du répertoire templates
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'feedback_project.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', 'postgres://postgres:postgres@db:5432/feedback_platform'),
        conn_max_age=600
    )
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'fr-fr'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Définir les répertoires de fichiers statiques
# En mode développement, nous n'avons pas besoin de référencer le répertoire frontend/build/static
STATICFILES_DIRS = []

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# JWT settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': False,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': False,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'VERIFYING_KEY': None,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# CORS settings
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000').split(',')

# Celery settings
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

# Configuration NLP
NLP_SETTINGS = {
    # Seuil de confiance pour la classification automatique des catégories
    'CATEGORY_CONFIDENCE_THRESHOLD': float(os.environ.get('NLP_CATEGORY_CONFIDENCE_THRESHOLD', '0.2')),
    
    # Seuil de confiance pour la classification automatique des priorités
    'PRIORITY_CONFIDENCE_THRESHOLD': float(os.environ.get('NLP_PRIORITY_CONFIDENCE_THRESHOLD', '0.3')),
    
    # Utiliser la classification par mots-clés comme fallback si le modèle ML n'est pas disponible
    'USE_KEYWORDS_FALLBACK': os.environ.get('NLP_USE_KEYWORDS_FALLBACK', 'True') == 'True',
    
    # Chemin vers le dossier des modèles NLP
    'MODELS_DIR': os.path.join(BASE_DIR, 'nlp_models'),
    
    # Nombre minimum d'échantillons par catégorie pour l'entraînement
    'MIN_SAMPLES_PER_CATEGORY': int(os.environ.get('NLP_MIN_SAMPLES', '5')),
}

# Configuration des tâches périodiques Celery
CELERY_BEAT_SCHEDULE = {
    'generate-weekly-report': {
        'task': 'feedback_api.tasks.generate_weekly_report',
        'schedule': timedelta(days=7),  # Exécution hebdomadaire
    },
    'check-active-nlp-models': {
        'task': 'feedback_api.advanced_tasks.check_active_nlp_models',
        'schedule': timedelta(hours=12),  # Vérification deux fois par jour
    },
    'process-pending-notifications': {
        'task': 'feedback_api.advanced_tasks.process_pending_notifications',
        'schedule': timedelta(minutes=15),  # Vérification toutes les 15 minutes
    },
}

# Twilio settings
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER', '')

# Facebook WhatsApp Business API settings
FACEBOOK_WHATSAPP_TOKEN = os.environ.get('FACEBOOK_WHATSAPP_TOKEN', '')
FACEBOOK_WHATSAPP_PHONE_NUMBER_ID = os.environ.get('FACEBOOK_WHATSAPP_PHONE_NUMBER_ID', '')
FACEBOOK_WHATSAPP_BUSINESS_ACCOUNT_ID = os.environ.get('FACEBOOK_WHATSAPP_BUSINESS_ACCOUNT_ID', '')
FACEBOOK_WHATSAPP_API_VERSION = os.environ.get('FACEBOOK_WHATSAPP_API_VERSION', 'v18.0')
FACEBOOK_WEBHOOK_VERIFY_TOKEN = os.environ.get('FACEBOOK_WEBHOOK_VERIFY_TOKEN', 'feedback_platform_token')
