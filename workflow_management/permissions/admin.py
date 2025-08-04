# permissions/admin.py
from django.contrib import admin
from django import forms
from .models import Role, ColumnPermission, UserRole, SystemPermission

class ColumnPermissionInlineForm(forms.ModelForm):
    """
    Inline form için özel form
    """
    class Meta:
        model = ColumnPermission
        fields = ['column_name', 'permission']
        widgets = {
            'column_name': forms.Select(attrs={'style': 'width: 250px;'}),
            'permission': forms.Select(attrs={'style': 'width: 150px;'}),
        }

class ColumnPermissionInline(admin.TabularInline):
    """
    Rol düzenleme sayfasında kolon yetkilerini göstermek için
    """
    model = ColumnPermission
    form = ColumnPermissionInlineForm
    extra = 3
    can_delete = True
    ordering = ['column_name']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'get_permission_count', 'created']
    search_fields = ['name', 'description']
    list_filter = ['created']
    inlines = [ColumnPermissionInline]
    
    def get_permission_count(self, obj):
        count = obj.column_permissions.count()
        return f"{count} kolon yetkisi"
    get_permission_count.short_description = 'Yetki Sayısı'

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'assigned_by', 'assigned_at']
    list_filter = ['role', 'assigned_at']
    search_fields = ['user__username', 'user__email', 'role__name']
    autocomplete_fields = ['user', 'role', 'assigned_by']
    readonly_fields = ['assigned_by', 'assigned_at']
    
    def save_model(self, request, obj, form, change):
        if not change:  # Yeni kayıt
            obj.assigned_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(ColumnPermission)
class ColumnPermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'get_column_display', 'get_permission_display']
    list_filter = ['role', 'permission', 'column_name']
    search_fields = ['role__name']
    ordering = ['role__name', 'column_name']
    
    def get_column_display(self, obj):
        return obj.get_column_name_display()
    get_column_display.short_description = 'Kolon'
    
    def get_permission_display(self, obj):
        return obj.get_permission_display()
    get_permission_display.short_description = 'Yetki'


@admin.register(SystemPermission)
class SystemPermissionAdmin(admin.ModelAdmin):
    list_display = ['role', 'get_permission_type_display', 'granted']
    list_filter = ['role', 'permission_type', 'granted']