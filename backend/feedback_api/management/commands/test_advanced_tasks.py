import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from feedback_api.models import (
    NLPModel, NLPTrainingData, KeywordRule, 
    Alert, Notification, NotificationChannel, NotificationTemplate,
    Feedback, Category
)
from feedback_api.advanced_tasks import (
    train_nlp_model, apply_keyword_rules, send_alert, 
    send_notification, test_notification_channel,
    check_active_nlp_models, process_pending_notifications
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Teste les tâches Celery avancées'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            help='Tâche spécifique à tester (nlp, keywords, alert, notification, check_models, process_notifications)',
        )

    def handle(self, *args, **options):
        task_name = options.get('task')
        
        if task_name:
            self.stdout.write(f"Test de la tâche: {task_name}")
            
            if task_name == 'nlp':
                self._test_nlp_model_training()
            elif task_name == 'keywords':
                self._test_keyword_rules()
            elif task_name == 'alert':
                self._test_send_alert()
            elif task_name == 'notification':
                self._test_send_notification()
            elif task_name == 'check_models':
                self._test_check_active_nlp_models()
            elif task_name == 'process_notifications':
                self._test_process_pending_notifications()
            else:
                self.stdout.write(self.style.ERROR(f"Tâche inconnue: {task_name}"))
        else:
            self.stdout.write("Test de toutes les tâches avancées")
            self._test_nlp_model_training()
            self._test_keyword_rules()
            self._test_send_alert()
            self._test_send_notification()
            self._test_check_active_nlp_models()
            self._test_process_pending_notifications()
            
        self.stdout.write(self.style.SUCCESS('Tests terminés'))

    def _test_nlp_model_training(self):
        """Teste l'entraînement d'un modèle NLP"""
        self.stdout.write("Test de l'entraînement d'un modèle NLP...")
        
        # Créer un modèle NLP de test si nécessaire
        model, created = NLPModel.objects.get_or_create(
            name="Modèle de test",
            defaults={
                'description': "Modèle créé pour les tests",
                'is_active': False,
                'is_trained': False,
                'accuracy': 0.0,
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'training_data_size': 0,
                'usage_count': 0
            }
        )
        
        # Créer des données d'entraînement si nécessaires
        categories = Category.objects.all()
        if categories.exists() and NLPTrainingData.objects.count() < 5:
            for i, category in enumerate(categories[:3]):  # Utiliser les 3 premières catégories
                for j in range(2):  # 2 exemples par catégorie
                    NLPTrainingData.objects.get_or_create(
                        content=f"Exemple de feedback pour la catégorie {category.name} numéro {j+1}",
                        category=category,
                        defaults={
                            'is_validated': True,
                            'validated_by': User.objects.filter(is_superuser=True).first()
                        }
                    )
        
        # Lancer la tâche d'entraînement
        result = train_nlp_model.delay(model.id)
        
        self.stdout.write(f"Tâche d'entraînement lancée: {result.id}")
        self.stdout.write(self.style.SUCCESS("Test de l'entraînement d'un modèle NLP terminé"))

    def _test_keyword_rules(self):
        """Teste l'application des règles de mots-clés"""
        self.stdout.write("Test de l'application des règles de mots-clés...")
        
        # Créer une règle de mots-clés si nécessaire
        categories = Category.objects.all()
        if categories.exists():
            category = categories.first()
            rule, created = KeywordRule.objects.get_or_create(
                name="Règle de test",
                defaults={
                    'category': category,
                    'keywords': ["test", "exemple", "feedback"],
                    'priority': 'medium',
                    'confidence_boost': 0.1
                }
            )
            
            # Créer un feedback de test
            feedback, created = Feedback.objects.get_or_create(
                content="Ceci est un exemple de feedback de test pour vérifier les règles de mots-clés",
                defaults={
                    'channel': 'web',
                    'status': 'new',
                    'priority': 'low',
                    'auto_categorized': False
                }
            )
            
            # Appliquer les règles de mots-clés
            result = apply_keyword_rules.delay(feedback.id)
            
            self.stdout.write(f"Tâche d'application des règles lancée: {result.id}")
            self.stdout.write(self.style.SUCCESS("Test de l'application des règles de mots-clés terminé"))
        else:
            self.stdout.write(self.style.WARNING("Aucune catégorie trouvée, impossible de tester les règles de mots-clés"))

    def _test_send_alert(self):
        """Teste l'envoi d'une alerte"""
        self.stdout.write("Test de l'envoi d'une alerte...")
        
        # Créer une alerte de test
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            # Récupérer ou créer un feedback
            feedback, created = Feedback.objects.get_or_create(
                content="Feedback pour tester les alertes",
                defaults={
                    'channel': 'web',
                    'status': 'new',
                    'priority': 'high'
                }
            )
            
            # Créer une alerte
            alert, created = Alert.objects.get_or_create(
                title="Alerte de test",
                defaults={
                    'description': "Ceci est une alerte de test créée automatiquement",
                    'feedback': feedback,
                    'severity': 'medium',
                    'region': 'Test',
                    'status': 'approved',
                    'created_by': admin_user
                }
            )
            
            # Ajouter l'administrateur comme destinataire
            alert.recipients.add(admin_user)
            
            # Envoyer l'alerte
            result = send_alert.delay(alert.id)
            
            self.stdout.write(f"Tâche d'envoi d'alerte lancée: {result.id}")
            self.stdout.write(self.style.SUCCESS("Test de l'envoi d'une alerte terminé"))
        else:
            self.stdout.write(self.style.WARNING("Aucun administrateur trouvé, impossible de tester l'envoi d'alerte"))

    def _test_send_notification(self):
        """Teste l'envoi d'une notification"""
        self.stdout.write("Test de l'envoi d'une notification...")
        
        # Créer un canal de notification si nécessaire
        channel, created = NotificationChannel.objects.get_or_create(
            name="Canal de test",
            defaults={
                'channel_type': 'email'
            }
        )
        
        # Créer une notification de test
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            notification, created = Notification.objects.get_or_create(
                title="Notification de test",
                user=admin_user,
                defaults={
                    'content': "Ceci est une notification de test créée automatiquement",
                    'channel': channel,
                    'status': 'pending',
                    'link': '/dashboard'
                }
            )
            
            # Envoyer la notification
            result = send_notification.delay(notification.id)
            
            self.stdout.write(f"Tâche d'envoi de notification lancée: {result.id}")
            self.stdout.write(self.style.SUCCESS("Test de l'envoi d'une notification terminé"))
        else:
            self.stdout.write(self.style.WARNING("Aucun administrateur trouvé, impossible de tester l'envoi de notification"))

    def _test_check_active_nlp_models(self):
        """Teste la vérification des modèles NLP actifs"""
        self.stdout.write("Test de la vérification des modèles NLP actifs...")
        
        # Exécuter la tâche de vérification
        result = check_active_nlp_models.delay()
        
        self.stdout.write(f"Tâche de vérification des modèles lancée: {result.id}")
        self.stdout.write(self.style.SUCCESS("Test de la vérification des modèles NLP actifs terminé"))

    def _test_process_pending_notifications(self):
        """Teste le traitement des notifications en attente"""
        self.stdout.write("Test du traitement des notifications en attente...")
        
        # Créer quelques notifications en attente si nécessaire
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            channel, created = NotificationChannel.objects.get_or_create(
                name="Canal de test",
                defaults={
                    'channel_type': 'email'
                }
            )
            
            # Créer 3 notifications de test
            for i in range(3):
                Notification.objects.get_or_create(
                    title=f"Notification de test {i+1}",
                    user=admin_user,
                    defaults={
                        'content': f"Ceci est la notification de test {i+1} créée automatiquement",
                        'channel': channel,
                        'status': 'pending',
                        'link': '/dashboard'
                    }
                )
            
            # Exécuter la tâche de traitement
            result = process_pending_notifications.delay()
            
            self.stdout.write(f"Tâche de traitement des notifications lancée: {result.id}")
            self.stdout.write(self.style.SUCCESS("Test du traitement des notifications en attente terminé"))
        else:
            self.stdout.write(self.style.WARNING("Aucun administrateur trouvé, impossible de tester le traitement des notifications"))
