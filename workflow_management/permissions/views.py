# permissions/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .models import Role, UserRole, ColumnPermission, SystemPermission
from .serializers import (
    RoleSerializer, RoleCreateUpdateSerializer, 
    UserRoleSerializer, ColumnPermissionSerializer
)
from .utils import PermissionChecker
from django.contrib.auth.models import User

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_system_permissions(request):
    """Kullanıcının sistem izinlerini döndür"""
    if request.user.is_superuser:
        return Response({
            'success': True,
            'data': {
                'work_create': True,
                'work_delete': True,
                'work_reorder': True  # YENİ
            }
        })
    
    permissions = {
        'work_create': False,
        'work_delete': False,
        'work_reorder': False  # YENİ
    }
    
    # Kullanıcının rollerini al
    user_roles = UserRole.objects.filter(user=request.user).values_list('role', flat=True)
    
    # Bu roller için sistem izinlerini kontrol et
    system_perms = SystemPermission.objects.filter(
        role__in=user_roles,
        granted=True
    ).values('permission_type')
    
    for perm in system_perms:
        perm_type = perm['permission_type']
        if perm_type in permissions:
            permissions[perm_type] = True
    
    return Response({
        'success': True,
        'data': permissions
    })

class RoleViewSet(viewsets.ModelViewSet):
    """
    Rol yönetimi için ViewSet
    Sadece admin kullanıcılar erişebilir
    """
    queryset = Role.objects.all()
    permission_classes = [IsAdminUser]
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RoleCreateUpdateSerializer
        return RoleSerializer
    
    @action(detail=False, methods=['get'])
    def available_columns(self, request):
        """
        Work modelindeki tüm kolonları ve açıklamalarını döndürür
        """
        columns = []
        for column_value, column_display in ColumnPermission.COLUMN_CHOICES:
            columns.append({
                'column_name': column_value,
                'display_name': column_display
            })
        
        return Response({
            'message': 'Work modelindeki tüm kolonlar',
            'columns': columns,
            'permission_types': [
                {'value': 'none', 'display': 'Yetki Yok'},
                {'value': 'read', 'display': 'Sadece Okuma'},
                {'value': 'write', 'display': 'Okuma ve Yazma'}
            ]
        })
    
    @action(detail=True, methods=['post'])
    def update_permissions(self, request, pk=None):
        """
        Bir rolün kolon yetkilerini toplu güncelleme
        """
        role = self.get_object()
        permissions_data = request.data.get('permissions', {})
        
        # Mevcut yetkileri sil
        role.column_permissions.all().delete()
        
        # Yeni yetkileri oluştur
        created_permissions = []
        for column_name, permission in permissions_data.items():
            if column_name in [choice[0] for choice in ColumnPermission.COLUMN_CHOICES]:
                perm = ColumnPermission.objects.create(
                    role=role,
                    column_name=column_name,
                    permission=permission
                )
                created_permissions.append(perm)
        
        serializer = ColumnPermissionSerializer(created_permissions, many=True)
        return Response({
            'message': 'Rol yetkileri güncellendi',
            'permissions': serializer.data
        })


class UserRoleViewSet(viewsets.ModelViewSet):
    """
    Kullanıcı-Rol atamaları için ViewSet
    Sadece admin kullanıcılar erişebilir
    """
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def my_permissions(self, request):
        """
        Giriş yapan kullanıcının kolon yetkilerini döndürür
        """
        permissions = PermissionChecker.get_user_column_permissions(request.user)
        
        # Detaylı format
        detailed_permissions = []
        for column_value, column_display in ColumnPermission.COLUMN_CHOICES:
            perm = permissions.get(column_value, 'none')
            detailed_permissions.append({
                'column_name': column_value,
                'display_name': column_display,
                'permission': perm,
                'can_read': perm in ['read', 'write'],
                'can_write': perm == 'write'
            })
        
        # Kullanıcının rolleri
        user_roles = UserRole.objects.filter(user=request.user).select_related('role')
        roles = [{'id': ur.role.id, 'name': ur.role.name} for ur in user_roles]
        
        return Response({
            'message': 'Kolon yetkileri',
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'is_superuser': request.user.is_superuser
            },
            'roles': roles,
            'permissions': detailed_permissions
        })
    
    @action(detail=False, methods=['get'])
    def user_permissions(self, request):
        """
        Belirli bir kullanıcının yetkilerini görüntüle
        Query param: user_id
        """
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({
                'message': 'user_id parametresi gerekli'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({
                'message': 'Kullanıcı bulunamadı'
            }, status=status.HTTP_404_NOT_FOUND)
        
        permissions = PermissionChecker.get_user_column_permissions(user)
        
        # Detaylı format
        detailed_permissions = []
        for column_value, column_display in ColumnPermission.COLUMN_CHOICES:
            perm = permissions.get(column_value, 'none')
            detailed_permissions.append({
                'column_name': column_value,
                'display_name': column_display,
                'permission': perm,
                'can_read': perm in ['read', 'write'],
                'can_write': perm == 'write'
            })
        
        # Kullanıcının rolleri
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        roles = [{'id': ur.role.id, 'name': ur.role.name} for ur in user_roles]
        
        return Response({
            'message': 'Kullanıcı kolon yetkileri',
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name() or user.username,
                'is_superuser': user.is_superuser
            },
            'roles': roles,
            'permissions': detailed_permissions
        })
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_my_work_permissions(request):
    """
    Kullanıcının Work modeli için kolon yetkilerini döndürür
    Sadece 'r' (read), 'w' (write), 'rw' (read-write) formatında
    """
    # Superuser kontrolü
    if request.user.is_superuser:
        # Superuser için tüm kolonlara tam yetki
        all_permissions = {}
        for column_value, column_display in ColumnPermission.COLUMN_CHOICES:
            all_permissions[column_value] = 'rw'
        
        return Response({
            'message': 'Kolon yetkileri (Superuser)',
            **all_permissions  # Direkt permissions'ı spread et
        })
    
    # Normal kullanıcılar için yetki kontrolü
    permissions = PermissionChecker.get_user_column_permissions(request.user)
    
    # Formatı sadeleştir
    simple_permissions = {}
    for column, permission in permissions.items():
        if permission == 'write':
            simple_permissions[column] = 'rw'  # write yetkisi olanlar okuyabilir de
        elif permission == 'read':
            simple_permissions[column] = 'r'
        # 'none' olanları ekleme, frontend'de olmayan = yetki yok
    
    return Response({
        'message': 'Kolon yetkileri',
        **simple_permissions
    })