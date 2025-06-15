from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Category, Feedback, Response, Log, UserProfile, Tag, FeedbackTag, 
    Attachment, Alert, NLPModel, NLPTrainingData, KeywordRule,
    NotificationChannel, NotificationTemplate, Notification
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour les utilisateurs"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class CategorySerializer(serializers.ModelSerializer):
    """Serializer pour les catégories"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ResponseSerializer(serializers.ModelSerializer):
    """Serializer pour les réponses"""
    responder = UserSerializer(read_only=True)
    
    class Meta:
        model = Response
        fields = ['id', 'feedback', 'responder', 'content', 'created_at', 'sent']
        read_only_fields = ['id', 'created_at', 'sent']
    
    def create(self, validated_data):
        # Récupérer l'utilisateur actuel comme répondant
        user = self.context['request'].user
        validated_data['responder'] = user
        return super().create(validated_data)


class LogSerializer(serializers.ModelSerializer):
    """Serializer pour les journaux"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Log
        fields = ['id', 'feedback', 'user', 'action', 'details', 'timestamp']
        read_only_fields = ['id', 'timestamp']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer pour les profils utilisateurs"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'role', 'phone_number', 'location', 'organization',
            'profile_picture', 'preferred_language', 'notification_preferences', 'last_active'
        ]
        read_only_fields = ['id', 'last_active']


class TagSerializer(serializers.ModelSerializer):
    """Serializer pour les tags"""
    class Meta:
        model = Tag
        fields = ['id', 'name', 'color']
        read_only_fields = ['id']


class FeedbackTagSerializer(serializers.ModelSerializer):
    """Serializer pour les associations feedback-tag"""
    tag = TagSerializer(read_only=True)
    tag_id = serializers.PrimaryKeyRelatedField(queryset=Tag.objects.all(), source='tag', write_only=True)
    added_by = UserSerializer(read_only=True)
    
    class Meta:
        model = FeedbackTag
        fields = ['id', 'feedback', 'tag', 'tag_id', 'added_by', 'added_at']
        read_only_fields = ['id', 'added_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['added_by'] = request.user
        return super().create(validated_data)


class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer pour les pièces jointes"""
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Attachment
        fields = ['id', 'feedback', 'file', 'file_name', 'file_type', 'file_size', 'uploaded_at', 'uploaded_by']
        read_only_fields = ['id', 'file_name', 'file_type', 'file_size', 'uploaded_at']
    
    def create(self, validated_data):
        # Récupérer les métadonnées du fichier
        file = validated_data.get('file')
        if file:
            validated_data['file_name'] = file.name
            validated_data['file_type'] = file.content_type
            validated_data['file_size'] = file.size
        
        # Associer l'utilisateur actuel
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['uploaded_by'] = request.user
        
        return super().create(validated_data)


class AlertSerializer(serializers.ModelSerializer):
    """Serializer pour les alertes"""
    created_by = UserSerializer(read_only=True)
    approved_by = UserSerializer(read_only=True)
    recipients = UserSerializer(many=True, read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'feedback', 'title', 'description', 'region', 'severity', 'status',
            'created_by', 'approved_by', 'created_at', 'updated_at', 'sent_at',
            'recipients', 'recipient_groups'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'sent_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class NLPModelSerializer(serializers.ModelSerializer):
    """Serializer pour les modèles NLP"""
    class Meta:
        model = NLPModel
        fields = [
            'id', 'name', 'description', 'model_type', 'version', 'file', 'is_active',
            'accuracy', 'precision', 'recall', 'f1_score', 'training_data_size',
            'created_at', 'last_trained'
        ]
        read_only_fields = ['id', 'created_at', 'accuracy', 'precision', 'recall', 'f1_score']


class NLPTrainingDataSerializer(serializers.ModelSerializer):
    """Serializer pour les données d'entraînement NLP"""
    added_by = UserSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = NLPTrainingData
        fields = ['id', 'content', 'category', 'category_name', 'is_validated', 'added_by', 'added_at']
        read_only_fields = ['id', 'added_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['added_by'] = request.user
        return super().create(validated_data)


class KeywordRuleSerializer(serializers.ModelSerializer):
    """Serializer pour les règles de mots-clés"""
    created_by = UserSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = KeywordRule
        fields = ['id', 'category', 'category_name', 'keywords', 'priority', 'confidence_boost', 'created_by', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class NotificationChannelSerializer(serializers.ModelSerializer):
    """Serializer pour les canaux de notification"""
    class Meta:
        model = NotificationChannel
        fields = ['id', 'name', 'channel_type', 'configuration', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer pour les modèles de notification"""
    channel_name = serializers.CharField(source='channel.name', read_only=True)
    
    class Meta:
        model = NotificationTemplate
        fields = ['id', 'name', 'subject', 'content', 'channel', 'channel_name']
        read_only_fields = ['id']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications"""
    user = UserSerializer(read_only=True)
    template = NotificationTemplateSerializer(read_only=True)
    channel = NotificationChannelSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'template', 'title', 'content', 'link', 'channel',
            'status', 'created_at', 'sent_at', 'read_at'
        ]
        read_only_fields = ['id', 'created_at', 'sent_at', 'read_at']


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer pour les feedbacks"""
    user = UserSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    responses = ResponseSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True, source='tag_set')
    attachments = AttachmentSerializer(many=True, read_only=True)
    assigned_to = UserSerializer(read_only=True)
    
    class Meta:
        model = Feedback
        fields = [
            'id', 'user', 'channel', 'content', 'status', 'category', 'category_name',
            'priority', 'created_at', 'updated_at', 'contact_phone', 'contact_email',
            'reference_number', 'external_id', 'source_url', 'location', 'latitude', 'longitude',
            'auto_categorized', 'confidence_score', 'assigned_to', 'resolved_at', 'local_id',
            'sync_status', 'responses', 'tags', 'attachments'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'auto_categorized', 'confidence_score']
    
    def create(self, validated_data):
        # Si l'utilisateur est authentifié, l'associer au feedback
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        feedback = super().create(validated_data)
        
        # Créer un log pour la création du feedback
        Log.objects.create(
            feedback=feedback,
            user=feedback.user,
            action=Log.ActionChoices.CREATED,
            details="Feedback créé"
        )
        
        return feedback
    
    def update(self, instance, validated_data):
        old_status = instance.status
        old_category = instance.category
        
        updated_instance = super().update(instance, validated_data)
        
        # Créer des logs pour les changements importants
        if 'status' in validated_data and old_status != updated_instance.status:
            Log.objects.create(
                feedback=updated_instance,
                user=self.context['request'].user,
                action=Log.ActionChoices.STATUS_CHANGED,
                details=f"Statut modifié de {old_status} à {updated_instance.status}"
            )
        
        if 'category' in validated_data and old_category != updated_instance.category:
            Log.objects.create(
                feedback=updated_instance,
                user=self.context['request'].user,
                action=Log.ActionChoices.CATEGORIZED,
                details=f"Catégorie modifiée"
            )
        
        return updated_instance


class FeedbackCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de feedback (sans authentification)"""
    class Meta:
        model = Feedback
        fields = ['channel', 'content', 'contact_phone', 'contact_email']
    
    def create(self, validated_data):
        feedback = Feedback.objects.create(**validated_data)
        
        # Créer un log pour la création du feedback
        Log.objects.create(
            feedback=feedback,
            action=Log.ActionChoices.CREATED,
            details="Feedback créé via API publique"
        )
        
        return feedback
