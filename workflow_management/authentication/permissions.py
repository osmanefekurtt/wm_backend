# authentication/permissions.py
from rest_framework import permissions

class IsSuperUser(permissions.BasePermission):
    """
    Sadece superuser'lar erişebilir
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_superuser