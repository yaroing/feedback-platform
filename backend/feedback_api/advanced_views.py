import logging
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from .models import (
    UserProfile, Tag, FeedbackTag, Attachment, Alert, 
    NLPModel, NLPTrainingData, KeywordRule, 
    NotificationChannel, NotificationTemplate, Notification
)
from .serializers import (
    UserProfileSerializer, TagSerializer, FeedbackTagSerializer, 
    AttachmentSerializer, AlertSerializer, NLPModelSerializer, 
    NLPTrainingDataSerializer, KeywordRuleSerializer,
    NotificationChannelSerializer, NotificationTemplateSerializer, 
    NotificationSerializer
)
from .permissions import IsModeratorOrReadOnly, IsOwnerOrModerator


class UserProfileViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les profils utilisateurs"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsOwnerOrModerator]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'role', 'organization']
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Récupérer le profil de l'utilisateur connecté"""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(profile)
        return Response(serializer.data)


class TagViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les tags"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class FeedbackTagViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les associations feedback-tag"""
    queryset = FeedbackTag.objects.all()
    serializer_class = FeedbackTagSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['feedback', 'tag', 'added_by']


class AttachmentViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les pièces jointes"""
    queryset = Attachment.objects.all()
    serializer_class = AttachmentSerializer
    permission_classes = [IsOwnerOrModerator]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['feedback', 'uploaded_by', 'file_type']


class AlertViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les alertes"""
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'severity', 'region', 'created_by']
    search_fields = ['title', 'description']
    
    @action(detail=True, methods=['post'], permission_classes=[IsModeratorOrReadOnly])
    def approve(self, request, pk=None):
        """Approuver une alerte"""
        alert = self.get_object()
        if alert.status != Alert.StatusChoices.PENDING:
            return Response(
                {"detail": "Seules les alertes en attente peuvent être approuvées."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alert.status = Alert.StatusChoices.APPROVED
        alert.approved_by = request.user
        alert.save()
        
        # Déclencher l'envoi de l'alerte de manière asynchrone
        from .tasks import send_alert
        send_alert.delay(alert.id)
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsModeratorOrReadOnly])
    def reject(self, request, pk=None):
        """Rejeter une alerte"""
        alert = self.get_object()
        if alert.status != Alert.StatusChoices.PENDING:
            return Response(
                {"detail": "Seules les alertes en attente peuvent être rejetées."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        alert.status = Alert.StatusChoices.REJECTED
        alert.save()
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data)


class NLPModelViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les modèles NLP"""
    queryset = NLPModel.objects.all()
    serializer_class = NLPModelSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'model_type']
    
    @action(detail=True, methods=['post'], permission_classes=[IsModeratorOrReadOnly])
    def activate(self, request, pk=None):
        """Activer un modèle NLP et désactiver les autres du même type"""
        model = self.get_object()
        
        # Désactiver tous les autres modèles du même type
        NLPModel.objects.filter(model_type=model.model_type).update(is_active=False)
        
        # Activer ce modèle
        model.is_active = True
        model.save()
        
        serializer = self.get_serializer(model)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsModeratorOrReadOnly])
    def train(self, request, pk=None):
        """Déclencher l'entraînement d'un modèle NLP"""
        model = self.get_object()
        
        # Déclencher l'entraînement de manière asynchrone
        from .tasks import train_nlp_model
        task = train_nlp_model.delay(model.id)
        
        return Response({"detail": "Entraînement du modèle lancé.", "task_id": task.id})


class NLPTrainingDataViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les données d'entraînement NLP"""
    queryset = NLPTrainingData.objects.all()
    serializer_class = NLPTrainingDataSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_validated', 'added_by']
    search_fields = ['content']
    
    @action(detail=True, methods=['post'], permission_classes=[IsModeratorOrReadOnly])
    def validate(self, request, pk=None):
        """Valider une donnée d'entraînement"""
        training_data = self.get_object()
        training_data.is_validated = True
        training_data.save()
        
        serializer = self.get_serializer(training_data)
        return Response(serializer.data)


class KeywordRuleViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les règles de mots-clés"""
    queryset = KeywordRule.objects.all()
    serializer_class = KeywordRuleSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'priority', 'created_by']


class NotificationChannelViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les canaux de notification"""
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'channel_type']
    
    @action(detail=True, methods=['post'], permission_classes=[IsModeratorOrReadOnly])
    def test(self, request, pk=None):
        """Tester un canal de notification"""
        channel = self.get_object()
        
        # Déclencher l'envoi d'un message de test
        from .tasks import test_notification_channel
        task = test_notification_channel.delay(channel.id)
        
        return Response({"detail": "Test du canal de notification lancé.", "task_id": task.id})


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les modèles de notification"""
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsModeratorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['channel']
    search_fields = ['name', 'subject', 'content']


class NotificationViewSet(viewsets.ModelViewSet):
    """API endpoint pour gérer les notifications"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsOwnerOrModerator]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user', 'status', 'channel']
    search_fields = ['title', 'content']
    
    def get_queryset(self):
        """Filtrer les notifications pour n'afficher que celles de l'utilisateur connecté"""
        if self.request.user.is_staff:
            return Notification.objects.all()
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_as_read(self, request, pk=None):
        """Marquer une notification comme lue"""
        notification = self.get_object()
        
        # Vérifier que l'utilisateur est bien le destinataire
        if notification.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": "Vous n'êtes pas autorisé à marquer cette notification comme lue."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification.status = Notification.StatusChoices.READ
        notification.read_at = timezone.now()
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_all_as_read(self, request):
        """Marquer toutes les notifications de l'utilisateur comme lues"""
        notifications = Notification.objects.filter(
            user=request.user,
            status=Notification.StatusChoices.SENT
        )
        
        count = notifications.count()
        notifications.update(
            status=Notification.StatusChoices.READ,
            read_at=timezone.now()
        )
        
        return Response({"detail": f"{count} notifications marquées comme lues."})
