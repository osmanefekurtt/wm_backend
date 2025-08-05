# permissions/serializers.py
from rest_framework import serializers
from .models import Role, ColumnPermission, UserRole, SystemPermission
from django.contrib.auth.models import User


class ColumnPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColumnPermission
        fields = ['column_name', 'permission']


class SystemPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemPermission
        fields = ['permission_type', 'granted']


class RoleSerializer(serializers.ModelSerializer):
    column_permissions = ColumnPermissionSerializer(many=True, read_only=True)
    system_permissions = SystemPermissionSerializer(many=True, read_only=True)
    permissions = serializers.DictField(write_only=True, required=False)
    system_permissions_data = serializers.DictField(write_only=True, required=False)
    
    class Meta:
        model = Role
        fields = ['id', 'name', 'description', 'created', 'updated', 
                  'column_permissions', 'system_permissions', 
                  'permissions', 'system_permissions_data']
        read_only_fields = ['id', 'created', 'updated', 'column_permissions', 'system_permissions']
    
    def create(self, validated_data):
        permissions_data = validated_data.pop('permissions', {})
        system_permissions_data = validated_data.pop('system_permissions_data', {})
        
        role = Role.objects.create(**validated_data)
        
        # Create column permissions
        self._handle_permissions(role, permissions_data, ColumnPermission, 'COLUMN_CHOICES')
        
        # Create system permissions
        self._handle_permissions(role, system_permissions_data, SystemPermission, 'PERMISSION_TYPE_CHOICES')
        
        return role
    
    def _handle_permissions(self, role, permissions_data, permission_model, choices_attr):
        """Handle both column and system permissions"""
        if permission_model == ColumnPermission:
            # Handle column permissions
            valid_choices = [choice[0] for choice in getattr(permission_model, choices_attr)]
            
            for column_name, permission in permissions_data.items():
                if column_name in valid_choices:
                    permission_model.objects.update_or_create(
                        role=role,
                        column_name=column_name,
                        defaults={'permission': permission}
                    )
        
        elif permission_model == SystemPermission:
            # Handle system permissions
            print(f"Handling system permissions: {permissions_data}")  # Debug
            valid_choices = [choice[0] for choice in getattr(permission_model, choices_attr)]
            print(f"Valid choices: {valid_choices}")  # Debug
            
            for permission_type, granted in permissions_data.items():
                if permission_type in valid_choices:
                    obj, created = permission_model.objects.update_or_create(
                        role=role,
                        permission_type=permission_type,
                        defaults={'granted': granted}
                    )
                    print(f"{'Created' if created else 'Updated'} {permission_type}: {granted}")  # Debug
    
    def update(self, instance, validated_data):
        permissions_data = validated_data.pop('permissions', {})
        system_permissions_data = validated_data.pop('system_permissions_data', {})
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update column permissions
        if permissions_data:
            # Clear existing permissions
            ColumnPermission.objects.filter(role=instance).delete()
            
            # Create new permissions
            self._handle_permissions(instance, permissions_data, ColumnPermission, 'COLUMN_CHOICES')
        
        # Update system permissions
        if system_permissions_data:
            # Don't delete existing, just update
            self._handle_permissions(instance, system_permissions_data, SystemPermission, 'PERMISSION_TYPE_CHOICES')
        
        return instance
    
    def to_representation(self, instance):
        """Include permissions in the response"""
        data = super().to_representation(instance)
        
        # Add column permissions as dict
        column_perms = {}
        for perm in instance.column_permissions.all():
            column_perms[perm.column_name] = perm.permission
        data['permissions'] = column_perms
        
        # Add system permissions as dict
        system_perms = {}
        # Varsayılan değerleri ayarla
        default_system_perms = {
            'work_create': False,
            'work_delete': False,
            'work_reorder': False
        }
        
        # Veritabanındaki değerleri al
        for perm in instance.system_permissions.all():
            system_perms[perm.permission_type] = perm.granted
        
        # Eksik olanları varsayılan değerlerle doldur
        for perm_type, default_value in default_system_perms.items():
            if perm_type not in system_perms:
                system_perms[perm_type] = default_value
                
        data['system_permissions_dict'] = system_perms
        
        return data


class UserRoleSerializer(serializers.ModelSerializer):
    user_display = serializers.CharField(source='user.username', read_only=True)
    role_display = serializers.CharField(source='role.name', read_only=True)
    
    class Meta:
        model = UserRole
        fields = ['id', 'user', 'role', 'user_display', 'role_display', 
                  'assigned_by', 'assigned_at']
        read_only_fields = ['id', 'assigned_by', 'assigned_at']


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                  'is_active', 'is_staff', 'is_superuser', 'roles']
    
    def get_roles(self, obj):
        user_roles = UserRole.objects.filter(user=obj).select_related('role')
        return [{'id': ur.role.id, 'name': ur.role.name} for ur in user_roles]