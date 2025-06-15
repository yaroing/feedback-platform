from django.contrib import admin
from .models import (
    Category, Feedback, Response, Log, Tag, FeedbackTag, Attachment, Alert,
    NLPModel, NLPTrainingData, KeywordRule, NotificationChannel, NotificationTemplate, Notification,
    UserProfile
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 0
    readonly_fields = ('created_at', 'sent')


class LogInline(admin.TabularInline):
    model = Log
    extra = 0
    readonly_fields = ('timestamp', 'action', 'user', 'details')
    can_delete = False


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'channel', 'status', 'priority', 'category', 'created_at')
    list_filter = ('channel', 'status', 'priority', 'category', 'created_at')
    search_fields = ('content', 'contact_email', 'contact_phone')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ResponseInline, LogInline]
    date_hierarchy = 'created_at'
    list_per_page = 20


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'feedback', 'responder', 'created_at', 'sent')
    list_filter = ('sent', 'created_at')
    search_fields = ('content',)
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('id', 'feedback', 'action', 'user', 'timestamp')
    list_filter = ('action', 'timestamp')
    search_fields = ('details',)
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    list_per_page = 50


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    search_fields = ('name',)


@admin.register(FeedbackTag)
class FeedbackTagAdmin(admin.ModelAdmin):
    list_display = ('feedback', 'tag')
    list_filter = ('tag',)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('feedback', 'file', 'uploaded_at')
    list_filter = ('uploaded_at',)
    date_hierarchy = 'uploaded_at'


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'feedback', 'severity', 'status', 'created_at')
    list_filter = ('severity', 'status', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    filter_horizontal = ('recipients',)


@admin.register(NLPModel)
class NLPModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'model_type', 'version', 'is_active', 'is_trained', 'accuracy', 'last_trained')
    list_filter = ('model_type', 'is_active', 'is_trained')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'last_trained', 'last_used')


@admin.register(NLPTrainingData)
class NLPTrainingDataAdmin(admin.ModelAdmin):
    list_display = ('category', 'is_validated', 'added_by', 'validated_by', 'added_at', 'validated_at')
    list_filter = ('category', 'is_validated', 'added_at')
    search_fields = ('content',)
    readonly_fields = ('added_at', 'validated_at')


@admin.register(KeywordRule)
class KeywordRuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'priority', 'confidence_boost', 'created_by', 'created_at')
    list_filter = ('category', 'priority', 'created_at')
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'channel_type', 'is_active')
    list_filter = ('channel_type', 'is_active')
    search_fields = ('name',)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'channel')
    list_filter = ('channel',)
    search_fields = ('name', 'subject', 'content')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'channel', 'status', 'created_at', 'sent_at')
    list_filter = ('status', 'channel', 'created_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'sent_at')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'location')
    list_filter = ('role', 'location')
    search_fields = ('user__username', 'user__email')
