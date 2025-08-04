from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Role(models.Model):
    """Kullanıcılara atanabilecek roller"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Rol Adı')
    description = models.TextField(blank=True, null=True, verbose_name='Açıklama')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma Tarihi')
    updated = models.DateTimeField(auto_now=True, verbose_name='Güncellenme Tarihi')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roller'
        ordering = ['name']


class ColumnPermission(models.Model):
    """Work modelindeki kolonlar için yetki tanımları"""
    
    PERMISSION_CHOICES = [
        ('none', 'Yetki Yok'),
        ('read', 'Sadece Okuma'),
        ('write', 'Okuma ve Yazma'),
    ]
    
    COLUMN_CHOICES = [
        ('name', 'İsim'),
        ('category', 'Kategori'),
        ('price', 'Fiyat'),
        ('type', 'Tip'),
        ('sales_channel', 'Satış Kanalı'),
        ('designer', 'Tasarımcı'),
        ('designer_text', 'Tasarımcı (Metin)'),  # YENİ
        ('design_start_date', 'Tasarım Başlangıç Tarihi'),
        ('design_end_date', 'Tasarım Bitiş Tarihi'),
        ('confirm_date', 'Onay Tarihi'),
        ('material_info', 'Malzeme Bilgileri'),
        ('printing_location', 'Baskı Lokasyonu'),
        ('printing_confirm', 'Baskı Onayı'),
        ('printing_control', 'Baskı Kontrolü'),
        ('printing_controller', 'Kontrolü Yapan Kişi'),
        ('printing_controller_text', 'Kontrolü Yapan (Metin)'),  # YENİ
        ('printing_start_date', 'Baskı Başlangıç Tarihi'),
        ('printing_end_date', 'Baskı Bitiş Tarihi'),
        ('mixed', 'Karışık'),
        ('packaging_date', 'Paketleme Tarihi'),
        ('stock_entry', 'Stok Girişi'),
        ('shipping_date', 'Sevkiyat Tarihi'),
        ('links', 'Bağlantılar'),
        ('note', 'Not'),
    ]
    
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='column_permissions', verbose_name='Rol')
    column_name = models.CharField(max_length=50, choices=COLUMN_CHOICES, verbose_name='Kolon Adı')
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES, default='none', verbose_name='Yetki')
    
    def __str__(self):
        return f"{self.role.name} - {self.get_column_name_display()} - {self.get_permission_display()}"
    
    class Meta:
        verbose_name = 'Kolon Yetkisi'
        verbose_name_plural = 'Kolon Yetkileri'
        unique_together = ['role', 'column_name']
        ordering = ['role', 'column_name']


class SystemPermission(models.Model):
    """Sistem genelinde işlem izinleri"""
    
    PERMISSION_CHOICES = [
        ('work_create', 'İş Oluşturma'),
        ('work_delete', 'İş Silme'),
    ]
    
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='system_permissions', verbose_name='Rol')
    permission_type = models.CharField(max_length=50, choices=PERMISSION_CHOICES, verbose_name='İzin Tipi')
    granted = models.BooleanField(default=False, verbose_name='İzin Verildi mi?')
    
    def __str__(self):
        status = '✓' if self.granted else '✗'
        return f"{self.role.name} - {self.get_permission_type_display()} - {status}"
    
    class Meta:
        verbose_name = 'Sistem İzni'
        verbose_name_plural = 'Sistem İzinleri'
        unique_together = ['role', 'permission_type']


class UserRole(models.Model):
    """Kullanıcı-Rol ilişkisi"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles', verbose_name='Kullanıcı')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_users', verbose_name='Rol')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assigned_roles', verbose_name='Atayan')
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name='Atanma Tarihi')
    
    def __str__(self):
        return f"{self.user.username} - {self.role.name}"
    
    def clean(self):
        if UserRole.objects.filter(user=self.user, role=self.role).exclude(pk=self.pk).exists():
            raise ValidationError('Bu kullanıcıya bu rol zaten atanmış.')
    
    class Meta:
        verbose_name = 'Kullanıcı Rolü'
        verbose_name_plural = 'Kullanıcı Rolleri'
        unique_together = ['user', 'role']
        ordering = ['user__username', 'role__name']