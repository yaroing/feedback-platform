from django.urls import path, include
from rest_framework import routers
from .views import CategoryViewSet, FeedbackViewSet, ResponseViewSet, LogViewSet, InboundWebhookView, simulated_messages, FacebookWebhookVerificationView, JSONSMSWebhookView
from .advanced_views import (
    UserProfileViewSet, TagViewSet, FeedbackTagViewSet, AttachmentViewSet, AlertViewSet,
    NLPModelViewSet, NLPTrainingDataViewSet, KeywordRuleViewSet,
    NotificationChannelViewSet, NotificationTemplateViewSet, NotificationViewSet
)

# Initialiser le routeur
router = routers.DefaultRouter()

# Routes de base
router.register(r'categories', CategoryViewSet)
router.register(r'feedback', FeedbackViewSet)
router.register(r'responses', ResponseViewSet)
router.register(r'logs', LogViewSet)

# Routes pour les fonctionnalités avancées
router.register(r'profiles', UserProfileViewSet)
router.register(r'tags', TagViewSet)
router.register(r'feedback-tags', FeedbackTagViewSet)
router.register(r'attachments', AttachmentViewSet)
router.register(r'alerts', AlertViewSet)
router.register(r'nlp-models', NLPModelViewSet)
router.register(r'nlp-training-data', NLPTrainingDataViewSet)
router.register(r'keyword-rules', KeywordRuleViewSet)
router.register(r'notification-channels', NotificationChannelViewSet)
router.register(r'notification-templates', NotificationTemplateViewSet)
router.register(r'notifications', NotificationViewSet)

# URLs de l'API
urlpatterns = [
    path('', include(router.urls)),
    path('inbound/', InboundWebhookView.as_view({'post': 'create'}), name='inbound-webhook'),
    # Endpoint spécifique pour les webhooks Facebook WhatsApp
    path('facebook-webhook/', FacebookWebhookVerificationView.as_view(), name='facebook-webhook-verification'),
    path('facebook-webhook/messages/', InboundWebhookView.as_view({'post': 'create'}), name='facebook-webhook-messages'),
    # Endpoint pour le webhook JSON SMS personnalisé
    path('webhook/json-sms/', JSONSMSWebhookView.as_view(), name='json-sms-webhook'),
]
