from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from .serializers import UserSerializer

class CurrentUserView(APIView):
    """
    Endpoint pour récupérer les informations de l'utilisateur actuellement connecté
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Retourne les informations de l'utilisateur connecté, y compris ses groupes
        """
        serializer = UserSerializer(request.user)
        data = serializer.data
        
        # Ajouter les groupes de l'utilisateur
        data['groups'] = list(request.user.groups.values_list('name', flat=True))
        
        return Response(data)
