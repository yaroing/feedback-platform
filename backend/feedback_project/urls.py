"""
URL configuration for feedback_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from django.conf.urls.static import static

# Configuration de Swagger/OpenAPI
schema_view = get_schema_view(
   openapi.Info(
      title="Feedback Platform API",
      default_version='v1',
      description="API pour la plateforme de feedback communautaire",
      contact=openapi.Contact(email="contact@example.com"),
      license=openapi.License(name="MIT License"),
   ),
   public=True,
)

# Initialisation du routeur DRF
router = routers.DefaultRouter()

# Inclure les routes de l'application feedback_api
from feedback_api.urls import router as feedback_router
router.registry.extend(feedback_router.registry)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # Keep old URLs for backward compatibility
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair_old'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh_old'),
    path('api/auth/user/', include('feedback_api.auth_urls')),
    path('api/', include(router.urls)),
    path('api/inbound/', include('feedback_api.urls')),
    path('', TemplateView.as_view(template_name='index.html')),
    
    # URLs de test pour Twilio (uniquement en développement)
    path('api/test/', include('feedback_api.test_views')),
    
    # Documentation API
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Servir les fichiers statiques en développement
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
