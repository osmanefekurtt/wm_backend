# workflow_management/urls.py - Güncelleme
"""
URL configuration for workflow_management project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('api/', include('workflows.urls')),
    path('api/auth/', include('authentication.urls')),
    path('api/permissions/', include('permissions.urls')),  # Yeni eklendi
]