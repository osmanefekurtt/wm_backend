from django.db import models
from django.conf import settings
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError


class BaseDropdownModel(models.Model):
    """Dropdown modelleri için base class"""
    name = models.CharField(max_length=100, unique=True, verbose_name='Ad')
    is_active = models.BooleanField(default=True, verbose_name='Aktif')
    order = models.IntegerField(default=0, verbose_name='Sıralama')
    created = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma Tarihi')
    
    def __str__(self):
        return self.name
    
    class Meta:
        abstract = True
        ordering = ['order', 'name']


class Category(BaseDropdownModel):
    """Kategori seçenekleri"""
    class Meta(BaseDropdownModel.Meta):
        verbose_name = 'Kategori'
        verbose_name_plural = 'Kategoriler'


class WorkType(BaseDropdownModel):
    """İş tipi seçenekleri"""
    class Meta(BaseDropdownModel.Meta):
        verbose_name = 'İş Tipi'
        verbose_name_plural = 'İş Tipleri'


class SalesChannel(BaseDropdownModel):
    """Satış kanalı seçenekleri"""
    class Meta(BaseDropdownModel.Meta):
        verbose_name = 'Satış Kanalı'
        verbose_name_plural = 'Satış Kanalları'


class Work(models.Model):
    """İş kayıtları"""
    
    # Temel bilgiler
    name = models.CharField(max_length=200, verbose_name='İsim')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Kategori')
    price = models.FloatField(verbose_name='Fiyat', blank=True, null=True)
    type = models.ForeignKey(WorkType, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Tip')
    sales_channel = models.ForeignKey(SalesChannel, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Satış Kanalı')
    
    # Tasarım bilgileri
    designer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='designed_works',
        verbose_name='Tasarımcı'
    )
    designer_text = models.CharField(max_length=200, blank=True, null=True, verbose_name='Tasarımcı (Metin)')
    design_start_date = models.DateField(verbose_name='Tasarım Başlangıç Tarihi', blank=True, null=True)
    design_end_date = models.DateField(verbose_name='Tasarım Bitiş Tarihi', blank=True, null=True)
    
    # Onay bilgileri - Yeni JSON field
    confirmations = models.JSONField(
        verbose_name='Onaylar',
        default=list,
        blank=True,
        help_text='[{"date": "2024-01-01", "text": "Onay metni", "added_by": "User Name", "added_at": "2024-01-01T12:00:00"}]'
    )
    
    # Eski confirm_date field'ı - migration için geçici olarak tutulacak
    confirm_date = models.DateField(verbose_name='Onay Tarihi (Eski)', blank=True, null=True)
    
    material_info = models.TextField(verbose_name='Malzeme Bilgileri', blank=True, null=True)
    
    # Baskı bilgileri
    printing_location = models.CharField(max_length=100, verbose_name='Baskı Lokasyonu', blank=True, null=True)
    printing_confirm = models.BooleanField(verbose_name='Baskı Onayı', default=False)
    printing_control = models.BooleanField(verbose_name='Baskı Kontrolü', default=False)
    printing_controller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='controlled_prints',
        verbose_name='Kontrolü Yapan Kişi'
    )
    printing_controller_text = models.CharField(max_length=200, blank=True, null=True, verbose_name='Kontrolü Yapan (Metin)')
    printing_control_date = models.DateTimeField(verbose_name='Kontrol Tarihi', blank=True, null=True)
    printing_start_date = models.DateField(verbose_name='Baskı Başlangıç Tarihi', blank=True, null=True)
    printing_end_date = models.DateField(verbose_name='Baskı Bitiş Tarihi', blank=True, null=True)
    
    # Paketleme ve sevkiyat
    mixed = models.CharField(max_length=200, verbose_name='Karışık', blank=True, null=True)
    packaging_date = models.DateField(verbose_name='Paketleme Tarihi', blank=True, null=True)
    stock_entry = models.BooleanField(verbose_name='Stok Girişi', default=False)
    shipping_date = models.DateField(verbose_name='Sevkiyat Tarihi', blank=True, null=True)
    
    # Diğer
    links = models.JSONField(
        verbose_name='Bağlantılar',
        default=list,
        blank=True,
        help_text='[{"url": "https://...", "title": "Başlık", "description": "Açıklama"}]'
    )
    note = models.TextField(verbose_name='Not', blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True, verbose_name='Oluşturulma Tarihi')
    updated = models.DateTimeField(auto_now=True, verbose_name='Güncellenme Tarihi')
    
    def __str__(self):
        return f"{self.name} - {self.category}"
    
    def clean(self):
        """Link ve onay formatlarını validate et"""
        # Link validasyonu
        if self.links:
            validator = URLValidator()
            for i, link_data in enumerate(self.links):
                if not isinstance(link_data, dict):
                    raise ValidationError(f'Bağlantı {i+1}: Geçersiz format')
                
                url = link_data.get('url')
                if not url:
                    raise ValidationError(f'Bağlantı {i+1}: URL zorunludur')
                
                try:
                    validator(url)
                except ValidationError:
                    raise ValidationError(f'Bağlantı {i+1}: Geçersiz URL formatı')
        
        # Onay validasyonu
        if self.confirmations:
            for i, confirmation in enumerate(self.confirmations):
                if not isinstance(confirmation, dict):
                    raise ValidationError(f'Onay {i+1}: Geçersiz format')
                
                if not confirmation.get('date'):
                    raise ValidationError(f'Onay {i+1}: Tarih zorunludur')
                
                # Tarih formatı kontrolü için
                try:
                    from datetime import datetime
                    datetime.strptime(str(confirmation['date']), '%Y-%m-%d')
                except ValueError:
                    raise ValidationError(f'Onay {i+1}: Geçersiz tarih formatı (YYYY-MM-DD olmalı)')
    
    @property
    def calculated_status(self):
        """İşin durumunu otomatik hesapla"""
        if self.stock_entry:
            return {'code': 'completed', 'text': 'Tamamlandı', 'color': '#dc3545'}
        elif self.printing_confirm:
            return {'code': 'printing', 'text': 'Baskı', 'color': '#28a745'}
        else:
            return {'code': 'waiting', 'text': 'Beklemede', 'color': '#6c757d'}
    
    @property
    def status_code(self):
        return self.calculated_status['code']
    
    @property
    def status_text(self):
        return self.calculated_status['text']
    
    @property
    def status_color(self):
        return self.calculated_status['color']
    
    @property
    def designer_display(self):
        """Tasarımcı görüntüleme adı"""
        if self.designer_text:
            return self.designer_text
        elif self.designer:
            return self.designer.get_full_name() or self.designer.username
        return None
    
    @property
    def printing_controller_display(self):
        """Kontrolör görüntüleme adı"""
        if self.printing_controller_text:
            return self.printing_controller_text
        elif self.printing_controller:
            return self.printing_controller.get_full_name() or self.printing_controller.username
        return None
    
    class Meta:
        verbose_name = 'İş'
        verbose_name_plural = 'İşler'
        ordering = ['-created']


class Movement(models.Model):
    """İşlem kayıtları"""
    
    ACTION_CHOICES = [
        ('create', 'Oluşturma'),
        ('update', 'Güncelleme'),
        ('delete', 'Silme')
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Kullanıcı'
    )
    user_fullname = models.CharField(max_length=200, verbose_name='Kullanıcı Adı', blank=True, null=True)
    work = models.ForeignKey(Work, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='İş')
    work_name = models.CharField(max_length=200, verbose_name='İş Adı', blank=True, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name='İşlem')
    description = models.TextField(verbose_name='Açıklama')
    changes = models.JSONField(
        verbose_name='Değişiklikler',
        blank=True,
        null=True,
        help_text='Güncelleme durumunda eski ve yeni değerler'
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name='Tarih')
    
    def __str__(self):
        user_display = self.user_fullname or (self.user.username if self.user else 'Bilinmiyor')
        return f"{user_display} - {self.action} - {self.created}"
    
    class Meta:
        verbose_name = 'Hareket'
        verbose_name_plural = 'Hareketler'
        ordering = ['-created']