# permissions/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Role, ColumnPermission

@receiver(post_save, sender=Role)
def create_default_permissions(sender, instance, created, **kwargs):
    """
    Yeni rol oluşturulduğunda tüm kolonlara otomatik olarak okuma yetkisi ver
    """
    if created:
        # Tüm kolonlar için okuma yetkisi oluştur
        for column_value, column_display in ColumnPermission.COLUMN_CHOICES:
            ColumnPermission.objects.create(
                role=instance,
                column_name=column_value,
                permission='read'  # Varsayılan olarak okuma yetkisi
            )
        
        print(f"'{instance.name}' rolü için varsayılan okuma yetkileri oluşturuldu.")