from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from meditrack.auth_api import RegisterAPIView

urlpatterns = [
    path('admin/', admin.site.urls),

    # ===== REST API =====
    path('api/', include('meditrack.api_urls')),

    # ===== AUTH API =====
    path('api/auth/register/', RegisterAPIView.as_view(), name='api-register'),
    path('api/auth/token/', obtain_auth_token, name='api-token'),

    # ===== SWAGGER (drf-spectacular) =====
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),

    # ===== HTML / Legacy Views =====
    path('', include('meditrack.urls')),
]
