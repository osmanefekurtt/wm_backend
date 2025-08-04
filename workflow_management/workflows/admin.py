# workflows/admin.py
from django.contrib import admin
from .models import Work, Movement, Category, SalesChannel, WorkType
from django import forms
from django.contrib import admin
import json

class PrettyJSONWidget(forms.Textarea):
    """JSON verilerini düzgün göstermek için widget"""
    
    def format_value(self, value):
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = json.loads(value)
            return json.dumps(value, indent=2, ensure_ascii=False)
        except:
            return super().format_value(value)

class WorkAdminForm(forms.ModelForm):
    """Work admin formu"""
    
    class Meta:
        model = Work
        fields = '__all__'
        widgets = {
            'links': PrettyJSONWidget(attrs={'rows': 10, 'cols': 80})
        }

@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    form = WorkAdminForm
    list_display = ['name', 'category', 'get_links_count', 'created', 'updated']
    list_filter = ['category', 'created']
    search_fields = ['name', 'note']
    date_hierarchy = 'created'
    
    def get_links_count(self, obj):
        """Bağlantı sayısını göster"""
        if obj.links:
            return f"{len(obj.links)} bağlantı"
        return "0 bağlantı"
    get_links_count.short_description = 'Bağlantılar'

@admin.register(Movement)
class MovementAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'get_work_name', 'created']
    list_filter = ['action', 'created', 'user']
    search_fields = ['description', 'work__name']
    readonly_fields = ['user', 'work', 'action', 'description', 'changes', 'created']
    date_hierarchy = 'created'
    
    def get_work_name(self, obj):
        return obj.work.name if obj.work else '-'
    get_work_name.short_description = 'İş'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'order', 'created']
    list_filter = ['is_active', 'created']
    search_fields = ['name']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'name']


@admin.register(WorkType)
class WorkTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'order', 'created']
    list_filter = ['is_active', 'created']
    search_fields = ['name']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'name']


@admin.register(SalesChannel)
class SalesChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'order', 'created']
    list_filter = ['is_active', 'created']
    search_fields = ['name']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'name']