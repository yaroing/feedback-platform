import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from feedback_api.models import (
    NLPModel, NLPTrainingData, KeywordRule, 
    Alert, Notification, NotificationChannel, 
    Feedback, Category
)
from feedback_api.advanced_tasks import (
    train_nlp_model, apply_keyword_rules, send_alert, 
    send_notification, test_notification_channel,
    check_active_nlp_models, process_pending_notifications
)


class AdvancedTasksTestCase(TestCase):
    """Tests pour les tâches Celery avancées"""
    
    def setUp(self):
        """Configuration initiale pour les tests"""
        # Créer un utilisateur de test
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Créer une catégorie de test
        self.category = Category.objects.create(
            name='Test Category',
            description='A test category'
        )
        
        # Créer un feedback de test
        self.feedback = Feedback.objects.create(
            content='This is a test feedback',
            channel='web',
            status='new',
            priority='medium'
        )
        
        # Créer un modèle NLP de test
        self.nlp_model = NLPModel.objects.create(
            name='Test Model',
            description='A test model',
            model_type='tfidf+nb',
            version='1.0',
            is_active=False,
            is_trained=False
        )
        
        # Créer des données d'entraînement
        self.training_data = NLPTrainingData.objects.create(
            content='Training data for test category',
            category=self.category,
            is_validated=True,
            added_by=self.user,
            validated_by=self.user
        )
        
        # Créer une règle de mots-clés
        self.keyword_rule = KeywordRule.objects.create(
            name='Test Rule',
            category=self.category,
            keywords=['test', 'feedback', 'important'],
            priority='medium',
            confidence_boost=0.2,
            created_by=self.user
        )
        
        # Créer un canal de notification
        self.notification_channel = NotificationChannel.objects.create(
            name='Test Channel',
            channel_type='email',
            configuration={
                'sender': 'test@example.com',
                'subject_prefix': '[TEST] '
            },
            is_active=True
        )
        
        # Créer une alerte
        self.alert = Alert.objects.create(
            title='Test Alert',
            description='This is a test alert',
            feedback=self.feedback,
            severity='medium',
            region='Test Region',
            status='approved',
            created_by=self.user
        )
        self.alert.recipients.add(self.user)
        
        # Créer une notification
        self.notification = Notification.objects.create(
            title='Test Notification',
            content='This is a test notification',
            user=self.user,
            channel=self.notification_channel,
            status='pending',
            link='/dashboard'
        )

    @patch('feedback_api.advanced_tasks.train_nlp_classifier')
    def test_train_nlp_model(self, mock_train_nlp_classifier):
        """Test de la tâche d'entraînement du modèle NLP"""
        # Configuration du mock
        mock_train_nlp_classifier.return_value = {
            'accuracy': 0.85,
            'precision': 0.82,
            'recall': 0.80,
            'f1_score': 0.81,
            'training_data_size': 100,
            'model_file': 'path/to/model.pkl'
        }
        
        # Exécution de la tâche
        result = train_nlp_model(self.nlp_model.id)
        
        # Vérifications
        mock_train_nlp_classifier.assert_called_once()
        
        # Récupérer le modèle mis à jour depuis la base de données
        updated_model = NLPModel.objects.get(id=self.nlp_model.id)
        
        # Vérifier que le modèle a été correctement mis à jour
        self.assertTrue(updated_model.is_trained)
        self.assertEqual(updated_model.accuracy, 0.85)
        self.assertEqual(updated_model.precision, 0.82)
        self.assertEqual(updated_model.recall, 0.80)
        self.assertEqual(updated_model.f1_score, 0.81)
        self.assertEqual(updated_model.training_data_size, 100)
        self.assertIsNotNone(updated_model.last_trained)

    @patch('feedback_api.advanced_tasks.apply_keyword_rule_to_feedback')
    def test_apply_keyword_rules(self, mock_apply_rule):
        """Test de la tâche d'application des règles de mots-clés"""
        # Configuration du mock
        mock_apply_rule.return_value = (True, self.category, 'medium', 0.75)
        
        # Exécution de la tâche
        result = apply_keyword_rules(self.feedback.id)
        
        # Vérifications
        mock_apply_rule.assert_called()
        
        # Récupérer le feedback mis à jour depuis la base de données
        updated_feedback = Feedback.objects.get(id=self.feedback.id)
        
        # Vérifier que le feedback a été correctement mis à jour
        self.assertEqual(updated_feedback.category, self.category)
        self.assertEqual(updated_feedback.priority, 'medium')
        self.assertEqual(updated_feedback.confidence_score, 0.75)
        self.assertTrue(updated_feedback.auto_categorized)

    @patch('feedback_api.advanced_tasks.send_notification')
    def test_send_alert(self, mock_send_notification):
        """Test de la tâche d'envoi d'alerte"""
        # Configuration du mock
        mock_send_notification.return_value = True
        
        # Exécution de la tâche
        result = send_alert(self.alert.id)
        
        # Vérifications
        mock_send_notification.assert_called()
        
        # Récupérer l'alerte mise à jour depuis la base de données
        updated_alert = Alert.objects.get(id=self.alert.id)
        
        # Vérifier que l'alerte a été correctement mise à jour
        self.assertEqual(updated_alert.status, 'sent')
        self.assertIsNotNone(updated_alert.sent_at)

    @patch('feedback_api.advanced_tasks.send_email')
    @patch('feedback_api.advanced_tasks.send_sms')
    @patch('feedback_api.advanced_tasks.send_whatsapp')
    @patch('feedback_api.advanced_tasks.send_push_notification')
    @patch('feedback_api.advanced_tasks.send_webhook_notification')
    def test_send_notification(self, mock_webhook, mock_push, mock_whatsapp, mock_sms, mock_email):
        """Test de la tâche d'envoi de notification"""
        # Configuration des mocks
        mock_email.return_value = True
        mock_sms.return_value = True
        mock_whatsapp.return_value = True
        mock_push.return_value = True
        mock_webhook.return_value = True
        
        # Exécution de la tâche pour différents types de canaux
        
        # Email
        self.notification_channel.channel_type = 'email'
        self.notification_channel.save()
        result_email = send_notification(self.notification.id)
        mock_email.assert_called_once()
        
        # SMS
        mock_email.reset_mock()
        self.notification_channel.channel_type = 'sms'
        self.notification_channel.save()
        result_sms = send_notification(self.notification.id)
        mock_sms.assert_called_once()
        
        # WhatsApp
        mock_sms.reset_mock()
        self.notification_channel.channel_type = 'whatsapp'
        self.notification_channel.save()
        result_whatsapp = send_notification(self.notification.id)
        mock_whatsapp.assert_called_once()
        
        # Push
        mock_whatsapp.reset_mock()
        self.notification_channel.channel_type = 'push'
        self.notification_channel.save()
        result_push = send_notification(self.notification.id)
        mock_push.assert_called_once()
        
        # Webhook
        mock_push.reset_mock()
        self.notification_channel.channel_type = 'webhook'
        self.notification_channel.save()
        result_webhook = send_notification(self.notification.id)
        mock_webhook.assert_called_once()
        
        # Vérifier que la notification a été correctement mise à jour
        updated_notification = Notification.objects.get(id=self.notification.id)
        self.assertEqual(updated_notification.status, 'sent')
        self.assertIsNotNone(updated_notification.sent_at)

    @patch('feedback_api.advanced_tasks.send_test_message')
    def test_test_notification_channel(self, mock_send_test):
        """Test de la tâche de test de canal de notification"""
        # Configuration du mock
        mock_send_test.return_value = True
        
        # Exécution de la tâche
        result = test_notification_channel(
            self.notification_channel.id, 
            'test@example.com', 
            'Test message'
        )
        
        # Vérifications
        mock_send_test.assert_called_once_with(
            self.notification_channel, 
            'test@example.com', 
            'Test message'
        )
        self.assertTrue(result)

    @patch('feedback_api.advanced_tasks.train_nlp_model')
    def test_check_active_nlp_models(self, mock_train):
        """Test de la tâche de vérification des modèles NLP actifs"""
        # Configuration du mock
        mock_train.return_value = True
        
        # Créer un modèle actif mais non entraîné
        active_model = NLPModel.objects.create(
            name='Active Model',
            description='An active model that needs training',
            model_type='tfidf+nb',
            version='1.0',
            is_active=True,
            is_trained=False
        )
        
        # Exécution de la tâche
        result = check_active_nlp_models()
        
        # Vérifications
        mock_train.assert_called_once_with(active_model.id)

    @patch('feedback_api.advanced_tasks.send_notification')
    def test_process_pending_notifications(self, mock_send):
        """Test de la tâche de traitement des notifications en attente"""
        # Configuration du mock
        mock_send.return_value = True
        
        # Créer plusieurs notifications en attente
        for i in range(3):
            Notification.objects.create(
                title=f'Pending Notification {i}',
                content=f'This is pending notification {i}',
                user=self.user,
                channel=self.notification_channel,
                status='pending',
                link='/dashboard'
            )
        
        # Compter les notifications en attente avant l'exécution
        pending_before = Notification.objects.filter(status='pending').count()
        
        # Exécution de la tâche
        result = process_pending_notifications()
        
        # Vérifications
        self.assertEqual(mock_send.call_count, pending_before)
        
        # Vérifier qu'il n'y a plus de notifications en attente
        pending_after = Notification.objects.filter(status='pending').count()
        self.assertEqual(pending_after, 0)


if __name__ == '__main__':
    unittest.main()
