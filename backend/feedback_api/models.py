from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class UserProfile(models.Model):
    """
    Extension du modèle User standard avec des champs supplémentaires
    pour les fonctionnalités avancées de Feedback-Platform
    """
    ROLE_CHOICES = [
        ('VOLUNTEER', _('Volontaire')),
        ('MODERATOR', _('Modérateur')),
        ('COORDINATOR', _('Coordinateur')),
        ('ADMIN', _('Administrateur')),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('Utilisateur')
    )
    role = models.CharField(
        _('Rôle'),
        max_length=20,
        choices=ROLE_CHOICES,
        default='VOLUNTEER'
    )
    phone_number = models.CharField(
        _('Numéro de téléphone'),
        max_length=15,
        blank=True,
        null=True
    )
    location = models.CharField(
        _('Localisation'),
        max_length=100,
        blank=True
    )
    organization = models.CharField(
        _('Organisation'),
        max_length=100,
        blank=True
    )
    profile_picture = models.ImageField(
        _('Photo de profil'),
        upload_to='profile_pics/',
        blank=True,
        null=True
    )
    preferred_language = models.CharField(
        _('Langue préférée'),
        max_length=10,
        default='fr'
    )
    notification_preferences = models.JSONField(
        _('Préférences de notification'),
        default=dict
    )
    last_active = models.DateTimeField(
        _('Dernière activité'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Profil utilisateur')
        verbose_name_plural = _('Profils utilisateurs')
    
    def __str__(self):
        return f"Profil de {self.user.username}"


class Category(models.Model):
    """Catégorie de feedback pour la classification"""
    name = models.CharField(_("Nom"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    created_at = models.DateTimeField(_("Date de création"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Catégorie")
        verbose_name_plural = _("Catégories")
        ordering = ["name"]
    
    def __str__(self):
        return self.name


class Feedback(models.Model):
    """Modèle principal pour les feedbacks des utilisateurs"""
    
    class ChannelChoices(models.TextChoices):
        WEB = 'web', _('Site Web')
        SMS = 'sms', _('SMS')
        WHATSAPP = 'whatsapp', _('WhatsApp')
        EMAIL = 'email', _('Email')
        API = 'api', _('API')
    
    class StatusChoices(models.TextChoices):
        NEW = 'new', _('Nouveau')
        IN_PROGRESS = 'in_progress', _('En cours')
        RESOLVED = 'resolved', _('Résolu')
        REJECTED = 'rejected', _('Rejeté')
    
    class PriorityChoices(models.TextChoices):
        LOW = 'low', _('Basse')
        MEDIUM = 'medium', _('Moyenne')
        HIGH = 'high', _('Haute')
        URGENT = 'urgent', _('Urgente')
    
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='feedbacks',
        verbose_name=_("Utilisateur")
    )
    channel = models.CharField(
        _("Canal"), 
        max_length=20, 
        choices=ChannelChoices.choices, 
        default=ChannelChoices.WEB
    )
    content = models.TextField(_("Contenu"))
    status = models.CharField(
        _("Statut"), 
        max_length=20, 
        choices=StatusChoices.choices, 
        default=StatusChoices.NEW
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='feedbacks',
        verbose_name=_("Catégorie")
    )
    priority = models.CharField(
        _("Priorité"), 
        max_length=20, 
        choices=PriorityChoices.choices, 
        default=PriorityChoices.MEDIUM
    )
    created_at = models.DateTimeField(_("Date de création"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Date de mise à jour"), auto_now=True)
    
    # Informations de contact pour les canaux non-web
    contact_phone = models.CharField(_("Téléphone de contact"), max_length=20, blank=True)
    contact_email = models.EmailField(_("Email de contact"), blank=True)
    # Nouveaux champs supplémentaires
    reference_number = models.CharField(_("Numéro de référence"), max_length=20, blank=True)
    external_id = models.CharField(_("ID externe"), max_length=50, blank=True)
    source_url = models.URLField(_("URL de source"), blank=True)
    
    # Géolocalisation
    location = models.CharField(_("Localisation"), max_length=100, blank=True)
    latitude = models.FloatField(_("Latitude"), null=True, blank=True)
    longitude = models.FloatField(_("Longitude"), null=True, blank=True)
    
    # Classification automatique
    auto_categorized = models.BooleanField(_("Catégorisé automatiquement"), default=False)
    confidence_score = models.FloatField(_("Score de confiance"), default=0.0)
    
    # Assignation
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_feedbacks',
        verbose_name=_("Assigné à")
    )
    resolved_at = models.DateTimeField(_("Date de résolution"), null=True, blank=True)
    
    # Champs pour le mode hors-ligne
    local_id = models.CharField(_("ID local"), max_length=100, blank=True)
    sync_status = models.CharField(_("Statut de synchronisation"), max_length=20, default='SYNCED')
    
    class Meta:
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedbacks")
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Feedback #{self.id} - {self.get_status_display()}"


class Response(models.Model):
    """Réponses aux feedbacks par les modérateurs"""
    feedback = models.ForeignKey(
        Feedback, 
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name=_("Feedback")
    )
    responder = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='responses',
        verbose_name=_("Répondant")
    )
    content = models.TextField(_("Contenu"))
    created_at = models.DateTimeField(_("Date de création"), auto_now_add=True)
    sent = models.BooleanField(_("Envoyé"), default=False)
    
    class Meta:
        verbose_name = _("Réponse")
        verbose_name_plural = _("Réponses")
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Réponse à #{self.feedback.id} par {self.responder}"


class Log(models.Model):
    """Journal des actions sur les feedbacks"""
    
    class ActionChoices(models.TextChoices):
        CREATED = 'created', _('Créé')
        UPDATED = 'updated', _('Mis à jour')
        CATEGORIZED = 'categorized', _('Catégorisé')
        RESPONDED = 'responded', _('Répondu')
        STATUS_CHANGED = 'status_changed', _('Statut modifié')
    
    feedback = models.ForeignKey(
        Feedback, 
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name=_("Feedback")
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='logs',
        verbose_name=_("Utilisateur")
    )
    action = models.CharField(
        _("Action"), 
        max_length=20, 
        choices=ActionChoices.choices
    )
    details = models.TextField(_("Détails"), blank=True)
    timestamp = models.DateTimeField(_("Horodatage"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Journal")
        verbose_name_plural = _("Journaux")
        ordering = ["-timestamp"]
    
    def __str__(self):
        return f"Log #{self.id} - {self.get_action_display()} sur #{self.feedback.id}"


class Tag(models.Model):
    """Tags pour marquer les feedbacks"""
    name = models.CharField(_('Nom'), max_length=50, unique=True)
    color = models.CharField(_('Couleur'), max_length=7, default="#cccccc")
    
    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')
        ordering = ["name"]
    
    def __str__(self):
        return self.name


class FeedbackTag(models.Model):
    """Association entre feedbacks et tags"""
    feedback = models.ForeignKey(
        Feedback, 
        on_delete=models.CASCADE,
        related_name='feedback_tags',
        verbose_name=_('Feedback'))
    tag = models.ForeignKey(
        Tag, 
        on_delete=models.CASCADE,
        related_name='feedback_tags',
        verbose_name=_('Tag'))
    added_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='added_tags',
        verbose_name=_('Ajouté par'))
    added_at = models.DateTimeField(_('Date d\'ajout'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Tag de feedback')
        verbose_name_plural = _('Tags de feedback')
        unique_together = ('feedback', 'tag')
    
    def __str__(self):
        return f"{self.feedback} - {self.tag}"


class Attachment(models.Model):
    """Pièces jointes aux feedbacks"""
    feedback = models.ForeignKey(
        Feedback, 
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('Feedback'))
    file = models.FileField(_('Fichier'), upload_to='attachments/')
    file_name = models.CharField(_('Nom du fichier'), max_length=255)
    file_type = models.CharField(_('Type de fichier'), max_length=100)
    file_size = models.IntegerField(_('Taille du fichier'))  # Taille en octets
    uploaded_at = models.DateTimeField(_('Date d\'upload'), auto_now_add=True)
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='uploaded_attachments',
        verbose_name=_('Uploadé par'))
    
    class Meta:
        verbose_name = _('Pièce jointe')
        verbose_name_plural = _('Pièces jointes')
        ordering = ["-uploaded_at"]
    
    def __str__(self):
        return self.file_name


class Alert(models.Model):
    """Alertes générées à partir des feedbacks"""
    
    class SeverityChoices(models.TextChoices):
        LOW = 'low', _('Basse')
        MEDIUM = 'medium', _('Moyenne')
        HIGH = 'high', _('Haute')
        CRITICAL = 'critical', _('Critique')
    
    class StatusChoices(models.TextChoices):
        DRAFT = 'draft', _('Brouillon')
        PENDING = 'pending', _('En attente')
        SENT = 'sent', _('Envoyée')
        CANCELLED = 'cancelled', _('Annulée')
    
    feedback = models.OneToOneField(
        Feedback, 
        on_delete=models.CASCADE,
        related_name='alert',
        verbose_name=_('Feedback'))
    title = models.CharField(_('Titre'), max_length=100)
    description = models.TextField(_('Description'))
    region = models.CharField(_('Région'), max_length=100)
    severity = models.CharField(
        _('Sévérité'), 
        max_length=10, 
        choices=SeverityChoices.choices, 
        default=SeverityChoices.MEDIUM)
    status = models.CharField(
        _('Statut'), 
        max_length=10, 
        choices=StatusChoices.choices, 
        default=StatusChoices.DRAFT)
    
    # Métadonnées
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_alerts',
        verbose_name=_('Créée par'))
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='approved_alerts',
        verbose_name=_('Approuvée par'))
    
    # Dates
    created_at = models.DateTimeField(_('Date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Date de mise à jour'), auto_now=True)
    sent_at = models.DateTimeField(_('Date d\'envoi'), null=True, blank=True)
    
    # Destinataires
    recipients = models.ManyToManyField(
        User, 
        related_name='received_alerts', 
        blank=True,
        verbose_name=_('Destinataires'))
    recipient_groups = models.CharField(
        _('Groupes de destinataires'), 
        max_length=255, 
        blank=True,
        help_text=_('Groupes de destinataires séparés par virgule'))
    
    class Meta:
        verbose_name = _('Alerte')
        verbose_name_plural = _('Alertes')
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.title


class NLPModel(models.Model):
    """Modèles d'apprentissage automatique pour la classification"""
    name = models.CharField(_('Nom'), max_length=100)
    description = models.TextField(_('Description'), blank=True)
    model_type = models.CharField(_('Type de modèle'), max_length=50)  # TF-IDF+NB, BERT, etc.
    version = models.CharField(_('Version'), max_length=20)
    file = models.FileField(_('Fichier'), upload_to='nlp_models/')
    is_active = models.BooleanField(_('Actif'), default=False)
    is_trained = models.BooleanField(_('Entraîné'), default=False)
    
    # Métriques de performance
    accuracy = models.FloatField(_('Précision'), default=0.0)
    precision = models.FloatField(_('Precision'), default=0.0)
    recall = models.FloatField(_('Recall'), default=0.0)
    f1_score = models.FloatField(_('F1 Score'), default=0.0)
    
    # Métadonnées
    training_data_size = models.IntegerField(_('Taille des données d\'entraînement'), default=0)
    usage_count = models.IntegerField(_('Nombre d\'utilisations'), default=0)
    last_used = models.DateTimeField(_('Dernière utilisation'), null=True, blank=True)
    created_at = models.DateTimeField(_('Date de création'), auto_now_add=True)
    last_trained = models.DateTimeField(_('Dernière formation'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Modèle NLP')
        verbose_name_plural = _('Modèles NLP')
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.name} v{self.version}"


class NLPTrainingData(models.Model):
    """Données d'entraînement pour les modèles NLP"""
    content = models.TextField(_('Contenu'))
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        related_name='training_data',
        verbose_name=_('Catégorie'))
    is_validated = models.BooleanField(_('Validé'), default=False)
    added_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='added_training_data',
        verbose_name=_('Ajouté par'))
    validated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        related_name='validated_training_data',
        verbose_name=_('Validé par'))
    added_at = models.DateTimeField(_('Date d\'ajout'), auto_now_add=True)
    validated_at = models.DateTimeField(_('Date de validation'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Donnée d\'entraînement NLP')
        verbose_name_plural = _('Données d\'entraînement NLP')
        ordering = ["-added_at"]
    
    def __str__(self):
        return f"Donnée d'entraînement pour {self.category.name}"


class KeywordRule(models.Model):
    """Règles de mots-clés pour la classification"""
    name = models.CharField(_('Nom'), max_length=100, default="Règle sans nom")
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE,
        related_name='keyword_rules',
        verbose_name=_('Catégorie'))
    keywords = models.JSONField(_('Mots-clés'))  # Liste de mots-clés
    priority = models.CharField(
        _('Priorité'), 
        max_length=10, 
        choices=Feedback.PriorityChoices.choices, 
        null=True, 
        blank=True)
    confidence_boost = models.FloatField(_('Boost de confiance'), default=0.0)  # Boost de confiance
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_keyword_rules',
        verbose_name=_('Créée par'))
    created_at = models.DateTimeField(_('Date de création'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Règle de mots-clés')
        verbose_name_plural = _('Règles de mots-clés')
        ordering = ["category__name"]
    
    def __str__(self):
        return f"Règle de mots-clés pour {self.category.name}"


class NotificationChannel(models.Model):
    """Canaux de notification disponibles"""
    
    class ChannelChoices(models.TextChoices):
        EMAIL = 'email', _('Email')
        SMS = 'sms', _('SMS')
        PUSH = 'push', _('Notification push')
        WHATSAPP = 'whatsapp', _('WhatsApp')
        WEBHOOK = 'webhook', _('Webhook')
    
    name = models.CharField(_('Nom'), max_length=100)
    channel_type = models.CharField(
        _('Type de canal'), 
        max_length=20, 
        choices=ChannelChoices.choices)
    configuration = models.JSONField(_('Configuration'), default=dict)  # Configuration du canal
    is_active = models.BooleanField(_('Actif'), default=True)
    created_at = models.DateTimeField(_('Date de création'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Canal de notification')
        verbose_name_plural = _('Canaux de notification')
        ordering = ["name"]
    
    def __str__(self):
        return self.name


class NotificationTemplate(models.Model):
    """Modèles de notifications"""
    name = models.CharField(_('Nom'), max_length=100)
    subject = models.CharField(_('Sujet'), max_length=200)
    content = models.TextField(_('Contenu'))
    channel = models.ForeignKey(
        NotificationChannel, 
        on_delete=models.CASCADE,
        related_name='templates',
        verbose_name=_('Canal'))
    
    class Meta:
        verbose_name = _('Modèle de notification')
        verbose_name_plural = _('Modèles de notification')
        ordering = ["name"]
    
    def __str__(self):
        return self.name


class Notification(models.Model):
    """Notifications envoyées aux utilisateurs"""
    
    class StatusChoices(models.TextChoices):
        PENDING = 'pending', _('En attente')
        SENT = 'sent', _('Envoyée')
        DELIVERED = 'delivered', _('Livrée')
        READ = 'read', _('Lue')
        FAILED = 'failed', _('Échec')
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Utilisateur'))
    template = models.ForeignKey(
        NotificationTemplate, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='notifications',
        verbose_name=_('Modèle'))
    title = models.CharField(_('Titre'), max_length=200)
    content = models.TextField(_('Contenu'))
    link = models.CharField(_('Lien'), max_length=255, blank=True)  # Lien vers la ressource concernée
    channel = models.ForeignKey(
        NotificationChannel, 
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Canal'))
    status = models.CharField(
        _('Statut'), 
        max_length=10, 
        choices=StatusChoices.choices, 
        default=StatusChoices.PENDING)
    created_at = models.DateTimeField(_('Date de création'), auto_now_add=True)
    sent_at = models.DateTimeField(_('Date d\'envoi'), null=True, blank=True)
    read_at = models.DateTimeField(_('Date de lecture'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"Notification pour {self.user.username}: {self.title}"
