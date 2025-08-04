# permissions/admin.py düzeltmesi
from django.contrib import admin
from .models import Role, UserRole, ColumnPermission, SystemPermission


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created')
    search_fields = ('name', 'description')
    ordering = ('name',)


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'role__name')
    autocomplete_fields = ('user', 'role')


@admin.register(ColumnPermission)
class ColumnPermissionAdmin(admin.ModelAdmin):
    list_display = ('get_user_role', 'column_name', 'permission')
    list_filter = ('permission', 'column_name')
    search_fields = ('role__name',)
    
    def get_user_role(self, obj):
        # Eğer model'de role field'ı varsa
        if hasattr(obj, 'role'):
            return obj.role.name
        # Eğer user_role field'ı varsa
        elif hasattr(obj, 'user_role'):
            return f"{obj.user_role.user.username} - {obj.user_role.role.name}"
        return '-'
    get_user_role.short_description = 'Rol'


@admin.register(SystemPermission)
class SystemPermissionAdmin(admin.ModelAdmin):
    list_display = ('get_user_role', 'permission_type', 'granted')
    list_filter = ('permission_type', 'granted')
    search_fields = ('user_role__user__username', 'user_role__role__name')
    
    def get_user_role(self, obj):
        if hasattr(obj, 'user_role'):
            return f"{obj.user_role.user.username} - {obj.user_role.role.name}"
        return '-'
    get_user_role.short_description = 'Kullanıcı - Rol'