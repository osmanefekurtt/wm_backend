# permissions/apps.py
from django.apps import AppConfig

class PermissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'permissions'
    verbose_name = 'Yetkilendirme Sistemi'
    
    def ready(self):
        # Signal'leri import et
        import permissions.signals