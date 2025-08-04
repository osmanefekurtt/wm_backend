# permissions/urls.py dosyasına ekleyin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RoleViewSet, UserRoleViewSet, get_my_work_permissions, get_my_system_permissions

router = DefaultRouter()
router.register('roles', RoleViewSet)
router.register('user-roles', UserRoleViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('my-work-permissions/', get_my_work_permissions, name='my-work-permissions'),
    path('my-system-permissions/', get_my_system_permissions, name='my-system-permissions'), 
]