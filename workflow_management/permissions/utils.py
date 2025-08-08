# permissions/utils.py
from .models import UserRole, ColumnPermission, SystemPermission

class PermissionChecker:
    """Yetki kontrolü için yardımcı sınıf"""
    
    @staticmethod
    def get_user_column_permissions(user):
        """Kullanıcının kolon yetkilerini döndürür"""
        if user.is_superuser:
            # Superuser tüm kolonlara yazma yetkisine sahip
            from workflows.models import Work
            all_fields = [f.name for f in Work._meta.get_fields() if not f.auto_created]
            return {field: 'write' for field in all_fields}
        
        permissions = {}
        
        # Kullanıcının rollerini al
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        
        for user_role in user_roles:
            # Her rol için kolon yetkilerini al
            column_perms = ColumnPermission.objects.filter(role=user_role.role)
            
            for perm in column_perms:
                # Daha yüksek yetki varsa onu kullan
                current_perm = permissions.get(perm.column_name, 'none')
                
                if perm.permission == 'write':
                    permissions[perm.column_name] = 'write'
                elif perm.permission == 'read' and current_perm != 'write':
                    permissions[perm.column_name] = 'read'
        
        return permissions
    
    @staticmethod
    def can_read_column(user, column_name):
        """Kullanıcının belirtilen kolonu okuma yetkisi var mı?"""
        if user.is_superuser:
            return True
        
        permissions = PermissionChecker.get_user_column_permissions(user)
        perm = permissions.get(column_name, 'none')
        return perm in ['read', 'write']
    
    @staticmethod
    def can_write_column(user, column_name):
        """Kullanıcının belirtilen kolona yazma yetkisi var mı?"""
        if user.is_superuser:
            return True
        
        permissions = PermissionChecker.get_user_column_permissions(user)
        return permissions.get(column_name) == 'write'
    
    @staticmethod
    def filter_readable_fields(user, data):
        """Kullanıcının okuma yetkisi olmadığı alanları filtreler"""
        if user.is_superuser:
            return data
        
        if isinstance(data, list):
            return [PermissionChecker.filter_readable_fields(user, item) for item in data]
        
        if not isinstance(data, dict):
            return data
        
        permissions = PermissionChecker.get_user_column_permissions(user)
        filtered_data = {}
        
        # Her zaman görünmesi gereken alanlar
        always_visible = [
            'id', 'created', 'updated',
            # Status alanları
            'status_code', 'status_text', 'status_color',
            # Detail alanları - read-only oldukları için
            'category_detail', 'type_detail', 'sales_channel_detail',
            'designer_detail', 'printing_controller_detail',
            # Uyumluluk için eklenen name alanları
            'category_name', 'type_name', 'sales_channel_name',
            'designer_name', 'printing_controller_name',
            # Diğer calculated/readonly alanlar
            'designer_display', 'printing_controller_display',
            'confirm_date',  # Legacy alan
            'link', 'link_title'  # Legacy alanlar
        ]
        
        for key, value in data.items():
            # Her zaman görünür alanlar veya yetkili alanlar
            if key in always_visible or permissions.get(key) in ['read', 'write']:
                filtered_data[key] = value
        
        return filtered_data
    
    @staticmethod
    def validate_writable_fields(user, data):
        """Kullanıcının yazma yetkisi olmadığı alanları kontrol eder"""
        if user.is_superuser:
            return True, None
        
        permissions = PermissionChecker.get_user_column_permissions(user)
        
        # Read-only ve sistem alanları - bunlar zaten değiştirilemez
        read_only_fields = [
            'id', 'created', 'updated', 'printing_control_date',
            'status_code', 'status_text', 'status_color',
            'category_detail', 'type_detail', 'sales_channel_detail',
            'designer_detail', 'printing_controller_detail',
            'category_name', 'type_name', 'sales_channel_name',
            'designer_name', 'printing_controller_name',
            'designer_display', 'printing_controller_display',
            'link', 'link_title', 'confirm_date'
        ]
        
        for field in data.keys():
            if field not in read_only_fields:
                if permissions.get(field) != 'write':
                    return False, f"'{field}' alanına yazma yetkiniz yok"
        
        return True, None
    
    @staticmethod
    def get_user_system_permissions(user):
        """Kullanıcının sistem izinlerini döndürür"""
        if user.is_superuser:
            return {'work_create': True, 'work_delete': True, 'work_reorder': True}
        
        permissions = {'work_create': False, 'work_delete': False, 'work_reorder': False}
        
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        
        for user_role in user_roles:
            system_perms = SystemPermission.objects.filter(role=user_role.role, granted=True)
            for perm in system_perms:
                permissions[perm.permission_type] = True
        
        return permissions
    
    @staticmethod
    def can_create_work(user):
        """Kullanıcının iş oluşturma yetkisi var mı?"""
        if user.is_superuser:
            return True
        
        permissions = PermissionChecker.get_user_system_permissions(user)
        return permissions.get('work_create', False)
    
    @staticmethod
    def can_delete_work(user):
        """Kullanıcının iş silme yetkisi var mı?"""
        if user.is_superuser:
            return True
        
        permissions = PermissionChecker.get_user_system_permissions(user)
        return permissions.get('work_delete', False)
    
    @staticmethod
    def can_reorder_work(user):
        """Kullanıcının iş sıralama yetkisi var mı?"""
        if user.is_superuser:
            return True
        
        permissions = PermissionChecker.get_user_system_permissions(user)
        return permissions.get('work_reorder', False)