from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from workflows.models import Work, Movement, Category, WorkType, SalesChannel
from workflows.serializer import (
    WorkflowSerializer, MovementSerializer, 
    CategorySerializer, WorkTypeSerializer, SalesChannelSerializer
)
from .audit_utils import log_work_action
from permissions.utils import PermissionChecker


class BaseDropdownViewSet(viewsets.ModelViewSet):
    """Dropdown yönetimi için base viewset"""
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAdminUser]
        return [permission() for permission in permission_classes]


class CategoryViewSet(BaseDropdownViewSet):
    """Kategori yönetimi"""
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer


class WorkTypeViewSet(BaseDropdownViewSet):
    """İş tipi yönetimi"""
    queryset = WorkType.objects.filter(is_active=True)
    serializer_class = WorkTypeSerializer


class SalesChannelViewSet(BaseDropdownViewSet):
    """Satış kanalı yönetimi"""
    queryset = SalesChannel.objects.filter(is_active=True)
    serializer_class = SalesChannelSerializer


class WorkflowViewSet(viewsets.ModelViewSet):
    """İş akışı yönetimi"""
    queryset = Work.objects.all()
    serializer_class = WorkflowSerializer
    permission_classes = [IsAuthenticated]
    
    def _filter_by_permissions(self, data, user):
        """Yetki bazlı filtreleme"""
        if isinstance(data, list):
            return [PermissionChecker.filter_readable_fields(user, item) for item in data]
        return PermissionChecker.filter_readable_fields(user, data)
    
    def _get_instance_data(self, instance):
        """Instance'dan tüm field verilerini al"""
        data = {}
        for field in instance._meta.fields:
            field_name = field.name
            if field_name not in ['id', 'created', 'updated']:
                data[field_name] = getattr(instance, field_name)
        return data

    @action(detail=True, methods=['post'])
    def add_link(self, request, pk=None):
        """Tek bir link ekleme"""
        work = self.get_object()
        
        if not PermissionChecker.can_write_column(request.user, 'links'):
            return Response({'message': 'Bağlantı ekleme yetkiniz yok'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        link_data = {
            'url': request.data.get('url'),
            'title': request.data.get('title'),
            'description': request.data.get('description')
        }
        
        # URL validasyonu
        validator = URLValidator()
        try:
            validator(link_data['url'])
        except (DjangoValidationError, TypeError):
            return Response({'message': 'Geçerli bir URL giriniz'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Link ekle
        current_links = work.links or []
        link_data['added_by'] = f"{request.user.get_full_name() or request.user.username} ({request.user.id})"
        link_data['added_at'] = timezone.now().isoformat()
        
        current_links.append(link_data)
        work.links = current_links
        work.save()
        
        # Log
        log_work_action(
            user=request.user,
            work=work,
            action='update',
            old_data={'links_count': len(current_links) - 1},
            new_data={'links_count': len(current_links)}
        )
        
        return Response({'message': 'Bağlantı eklendi', 'links': work.links})
    
    @action(detail=True, methods=['post'])
    def remove_link(self, request, pk=None):
        """Link silme"""
        work = self.get_object()
        
        if not PermissionChecker.can_write_column(request.user, 'links'):
            return Response({'message': 'Bağlantı silme yetkiniz yok'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        url_to_remove = request.data.get('url')
        if not url_to_remove:
            return Response({'message': 'Silinecek bağlantı URL\'si gerekli'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        current_links = work.links or []
        new_links = [link for link in current_links if link.get('url') != url_to_remove]
        
        if len(new_links) == len(current_links):
            return Response({'message': 'Bağlantı bulunamadı'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        work.links = new_links
        work.save()
        
        # Log
        log_work_action(
            user=request.user,
            work=work,
            action='update',
            old_data={'links_count': len(current_links)},
            new_data={'links_count': len(new_links)}
        )
        
        return Response({'message': 'Bağlantı silindi', 'links': work.links})
    
    def list(self, request, *args, **kwargs):
        """Liste görünümü - yetki filtreli"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            filtered_data = self._filter_by_permissions(serializer.data, request.user)
            return self.get_paginated_response(filtered_data)
        
        serializer = self.get_serializer(queryset, many=True)
        filtered_data = self._filter_by_permissions(serializer.data, request.user)
        return Response(filtered_data)
    
    def retrieve(self, request, *args, **kwargs):
        """Detay görünümü - yetki filtreli"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        filtered_data = self._filter_by_permissions(serializer.data, request.user)
        return Response(filtered_data)
    
    def create(self, request, *args, **kwargs):
        """Yeni kayıt oluştur"""
        # Create yetkisi kontrolü
        if not PermissionChecker.can_create_work(request.user):
            return Response({'message': 'İş oluşturma yetkiniz yok'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Field yazma yetkisi kontrolü
        is_valid, error_message = PermissionChecker.validate_writable_fields(request.user, request.data)
        if not is_valid:
            return Response({'message': error_message}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        work = serializer.save()
        
        # Log
        log_work_action(user=request.user, work=work, action='create')
        
        headers = self.get_success_headers(serializer.data)
        filtered_data = self._filter_by_permissions(serializer.data, request.user)
        
        return Response(filtered_data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Güncelleme işlemi"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Yazma yetkisi kontrolü
        is_valid, error_message = PermissionChecker.validate_writable_fields(request.user, request.data)
        if not is_valid:
            return Response({'message': error_message}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Eski verileri al
        old_data = self._get_instance_data(instance)
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Güncellenmiş verileri al
        instance.refresh_from_db()
        new_data = self._get_instance_data(instance)
        
        # Değişiklik varsa logla
        if old_data != new_data:
            log_work_action(
                user=request.user,
                work=instance,
                action='update',
                old_data=old_data,
                new_data=new_data
            )
        
        filtered_data = self._filter_by_permissions(serializer.data, request.user)
        return Response(filtered_data)
    
    def destroy(self, request, *args, **kwargs):
        """Silme işlemi"""
        if not PermissionChecker.can_delete_work(request.user):
            return Response({'message': 'İş silme yetkiniz yok'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        instance = self.get_object()
        log_work_action(user=request.user, work=instance, action='delete')
        
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MovementViewSet(viewsets.ReadOnlyModelViewSet):
    """Movement kayıtları - sadece okunabilir"""
    queryset = Movement.objects.all()
    serializer_class = MovementSerializer
    permission_classes = [IsAdminUser]