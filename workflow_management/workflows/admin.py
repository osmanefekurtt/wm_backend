# workflows/admin.py güncelleme
from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Work, Movement, Category, WorkType, SalesChannel


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'order', 'created')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('order', 'name')


@admin.register(WorkType)
class WorkTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'order', 'created')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('order', 'name')


@admin.register(SalesChannel)
class SalesChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'order', 'created')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('order', 'name')


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'category', 
        'price', 
        'type', 
        'sales_channel',
        'display_confirmations',
        'display_links',
        'status_display',
        'created'
    )
    list_filter = (
        'category',
        'type',
        'sales_channel',
        'stock_entry',
        'printing_confirm',
        'printing_control',
        'created'
    )
    search_fields = (
        'name',
        'designer__username',
        'designer__first_name',
        'designer__last_name',
        'designer_text',
        'material_info',
        'note'
    )
    date_hierarchy = 'created'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'category', 'price', 'type', 'sales_channel')
        }),
        ('Tasarım Bilgileri', {
            'fields': (
                ('designer', 'designer_text'),
                ('design_start_date', 'design_end_date'),
                'confirmations',
                'material_info'
            )
        }),
        ('Baskı Bilgileri', {
            'fields': (
                'printing_location',
                'printing_confirm',
                ('printing_control', 'printing_controller', 'printing_controller_text', 'printing_control_date'),
                ('printing_start_date', 'printing_end_date')
            )
        }),
        ('Paketleme ve Sevkiyat', {
            'fields': (
                'mixed',
                'packaging_date',
                'stock_entry',
                'shipping_date'
            )
        }),
        ('Ek Bilgiler', {
            'fields': ('links', 'note')
        })
    )
    
    readonly_fields = ('printing_control_date', 'created', 'updated')
    
    def display_confirmations(self, obj):
        """Onayları görüntüle"""
        if not obj.confirmations:
            return '-'
        
        confirmations_html = []
        for conf in obj.confirmations:
            date = conf.get('date', 'Tarih yok')
            text = conf.get('text', '')
            added_by = conf.get('added_by', 'Bilinmiyor')
            
            html = f'<div style="margin-bottom: 5px;">'
            html += f'<strong>{date}</strong>'
            if text:
                html += f' - {text}'
            html += f'<br><small>Ekleyen: {added_by}</small>'
            html += '</div>'
            
            confirmations_html.append(html)
        
        return format_html(''.join(confirmations_html))
    
    display_confirmations.short_description = 'Onaylar'
    
    def display_links(self, obj):
        """Bağlantıları görüntüle"""
        if not obj.links:
            return '-'
        
        links_html = []
        for link in obj.links:
            url = link.get('url', '#')
            title = link.get('title', url[:30] + '...' if len(url) > 30 else url)
            html = f'<a href="{url}" target="_blank" style="display: block; margin-bottom: 3px;">{title}</a>'
            links_html.append(html)
        
        return format_html(''.join(links_html))
    
    display_links.short_description = 'Bağlantılar'
    
    def status_display(self, obj):
        """Durum rengini göster"""
        status = obj.calculated_status
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            status['color'],
            status['text']
        )
    
    status_display.short_description = 'Durum'
    
    def save_model(self, request, obj, form, change):
        """Admin'den kaydederken printing_control_date'i otomatik ayarla"""
        if obj.printing_control and not obj.printing_control_date:
            obj.printing_control_date = timezone.now()
        elif not obj.printing_control:
            obj.printing_control_date = None
            obj.printing_controller = None
            obj.printing_controller_text = ''
        
        super().save_model(request, obj, form, change)


@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = (
        'get_action_display',
        'user_display',
        'work_display',
        'description',
        'created'
    )
    list_filter = ('action', 'created')
    search_fields = (
        'user__username',
        'user_fullname',
        'work__name',
        'work_name',
        'description'
    )
    date_hierarchy = 'created'
    readonly_fields = (
        'user',
        'user_fullname',
        'work',
        'work_name',
        'action',
        'description',
        'changes',
        'created'
    )
    
    def get_action_display(self, obj):
        """İşlem tipini renkli göster"""
        colors = {
            'create': '#28a745',
            'update': '#ffc107',
            'delete': '#dc3545'
        }
        color = colors.get(obj.action, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_action_display()
        )
    
    get_action_display.short_description = 'İşlem'
    
    def user_display(self, obj):
        """Kullanıcı adını göster"""
        if obj.user_fullname:
            return obj.user_fullname
        elif obj.user:
            return f"{obj.user.get_full_name() or obj.user.username}"
        return 'Bilinmiyor'
    
    user_display.short_description = 'Kullanıcı'
    
    def work_display(self, obj):
        """İş adını göster"""
        if obj.work_name:
            return obj.work_name
        elif obj.work:
            return obj.work.name
        return '-'
    
    work_display.short_description = 'İş'
    
    def has_add_permission(self, request):
        """Movement kayıtları manuel eklenemez"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Movement kayıtları silinemez"""
        return False