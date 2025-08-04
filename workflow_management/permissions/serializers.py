from rest_framework import serializers
from .models import Role, ColumnPermission, UserRole, SystemPermission
from django.contrib.auth.models import User


class ColumnPermissionSerializer(serializers.ModelSerializer):
    """Kolon yetkileri"""
    column_display = serializers.CharField(source='get_column_name_display', read_only=True)
    permission_display = serializers.CharField(source='get_permission_display', read_only=True)
    
    class Meta:
        model = ColumnPermission
        fields = ['id', 'column_name', 'column_display', 'permission', 'permission_display']


class SystemPermissionSerializer(serializers.ModelSerializer):
    """Sistem izinleri"""
    permission_display = serializers.CharField(source='get_permission_type_display', read_only=True)
    
    class Meta:
        model = SystemPermission
        fields = ['id', 'permission_type', 'permission_display', 'granted']


class RoleSerializer(serializers.ModelSerializer):
    """Rol detayları"""
    column_permissions = ColumnPermissionSerializer(many=True, read_only=True)
    system_permissions = SystemPermissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'column_permissions', 'system_permissions', 'created', 'updated']
        read_only_fields = ['created', 'updated']


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    """Rol oluşturma ve güncelleme"""
    permissions = serializers.DictField(
        child=serializers.ChoiceField(choices=['none', 'read', 'write']),
        write_only=True,
        required=False
    )
    system_permissions = serializers.DictField(
        child=serializers.BooleanField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Role
        fields = ['name', 'description', 'permissions', 'system_permissions']
    
    def _handle_permissions(self, role, permissions_data, permission_model, choices_attr):
        """Yetki oluşturma/güncelleme için yardımcı method"""
        if permissions_data is None:
            return
            
        # Mevcut yetkileri sil
        if permission_model == ColumnPermission:
            role.column_permissions.all().delete()
        else:
            role.system_permissions.all().delete()
        
        # Yeni yetkileri oluştur
        valid_choices = [choice[0] for choice in getattr(permission_model, choices_attr)]
        
        for key, value in permissions_data.items():
            if key in valid_choices:
                if permission_model == ColumnPermission:
                    permission_model.objects.create(role=role, column_name=key, permission=value)
                else:
                    permission_model.objects.create(role=role, permission_type=key, granted=value)
    
    def create(self, validated_data):
        permissions_data = validated_data.pop('permissions', {})
        system_permissions_data = validated_data.pop('system_permissions', {})
        
        role = Role.objects.create(**validated_data)
        
        # Column permissions
        if permissions_data:
            role.column_permissions.all().delete()
            self._handle_permissions(role, permissions_data, ColumnPermission, 'COLUMN_CHOICES')
        
        # System permissions
        self._handle_permissions(role, system_permissions_data, SystemPermission, 'PERMISSION_CHOICES')
        
        return role
    
    def update(self, instance, validated_data):
        permissions_data = validated_data.pop('permissions', None)
        system_permissions_data = validated_data.pop('system_permissions', None)
        
        # Rol bilgilerini güncelle
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Permissions güncelle
        self._handle_permissions(instance, permissions_data, ColumnPermission, 'COLUMN_CHOICES')
        self._handle_permissions(instance, system_permissions_data, SystemPermission, 'PERMISSION_CHOICES')
        
        return instance


class UserRoleSerializer(serializers.ModelSerializer):
    """Kullanıcı-Rol ilişkisi"""
    user_detail = serializers.SerializerMethodField()
    role_detail = RoleSerializer(source='role', read_only=True)
    assigned_by_detail = serializers.SerializerMethodField()
    
    class Meta:
        model = UserRole
        fields = ['id', 'user', 'user_detail', 'role', 'role_detail', 'assigned_by_detail', 'assigned_at']
        read_only_fields = ['assigned_by', 'assigned_at']
    
    def get_user_detail(self, obj):
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'full_name': obj.user.get_full_name() or obj.user.username
        }
    
    def get_assigned_by_detail(self, obj):
        if not obj.assigned_by:
            return None
        return {
            'id': obj.assigned_by.id,
            'username': obj.assigned_by.username,
            'full_name': obj.assigned_by.get_full_name() or obj.assigned_by.username
        }
    
    def create(self, validated_data):
        validated_data['assigned_by'] = self.context['request'].user
        return super().create(validated_data)