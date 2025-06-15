from django.urls import path
from .auth_views import CurrentUserView

urlpatterns = [
    path('', CurrentUserView.as_view(), name='current-user'),
]
