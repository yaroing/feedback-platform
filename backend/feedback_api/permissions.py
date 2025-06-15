from rest_framework import permissions


class IsModeratorOrReadOnly(permissions.BasePermission):
    """
    Permission personnalisée pour permettre aux modérateurs de modifier,
    mais autoriser uniquement la lecture pour les autres utilisateurs.
    """
    
    def has_permission(self, request, view):
        # Autoriser les requêtes en lecture pour tous les utilisateurs, même non authentifiés
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Autoriser les requêtes en écriture uniquement pour les modérateurs
        return request.user.is_authenticated and request.user.groups.filter(name='Moderators').exists()


class IsOwnerOrModerator(permissions.BasePermission):
    """
    Permission personnalisée pour permettre aux propriétaires d'un feedback ou aux modérateurs
    d'accéder et de modifier un feedback.
    """
    
    def has_permission(self, request, view):
        # Autoriser les requêtes en lecture pour tous les utilisateurs, même non authentifiés
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Autoriser les requêtes en lecture pour tous les utilisateurs, même non authentifiés
        if request.method in permissions.SAFE_METHODS:
            return True
            
        # Vérifier si l'utilisateur est authentifié
        if not request.user.is_authenticated:
            return False
        
        # Autoriser les modérateurs
        if request.user.groups.filter(name='Moderators').exists():
            return True
        
        # Autoriser le propriétaire du feedback
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        # Pour les objets liés à un feedback (comme Response)
        if hasattr(obj, 'feedback') and obj.feedback.user:
            return obj.feedback.user == request.user
        
        return False
