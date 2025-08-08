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
from datetime import datetime
from django.db import transaction


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

    @action(detail=True, methods=['post'])
    def set_priority(self, request, pk=None):
        """İşin öncelik sırasını değiştir"""
        work = self.get_object()
        new_priority = request.data.get('priority')
        
        # Yetki kontrolü
        if not request.user.is_superuser and not self._can_reorder_works(request.user):
            return Response(
                {'message': 'İşleri sıralama yetkiniz yok'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validasyon
        if new_priority is None:
            return Response(
                {'message': 'Yeni sıra numarası gerekli'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_priority = int(new_priority)
            if new_priority < 1:
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {'message': 'Geçerli bir sıra numarası girin (1 veya daha büyük)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Sıralama işlemi
        with transaction.atomic():
            old_priority = work.priority
            
            if new_priority == old_priority:
                return Response({'message': 'İş zaten bu sırada'})
            
            # Tüm işleri priority'e göre sırala
            all_works = Work.objects.all().order_by('priority')
            
            # Mevcut işi listeden çıkar
            works_list = list(all_works.exclude(id=work.id))
            
            # Yeni pozisyona ekle (0-indexed to 1-indexed)
            works_list.insert(new_priority - 1, work)
            
            # Tüm priority'leri güncelle
            for index, w in enumerate(works_list, start=1):
                if w.priority != index:
                    Work.objects.filter(id=w.id).update(priority=index)
            
            # Log
            log_work_action(
                user=request.user,
                work=work,
                action='update',
                old_data={'priority': old_priority},
                new_data={'priority': new_priority}
            )
        
        # Güncel veriyi döndür
        work.refresh_from_db()
        serializer = self.get_serializer(work)
        filtered_data = self._filter_by_permissions(serializer.data, request.user)
        
        return Response({
            'message': 'Sıralama güncellendi',
            'data': filtered_data
        })
    
    @action(detail=False, methods=['post'])
    def reorder_bulk(self, request):
        """Toplu sıralama güncelleme"""
        # Yetki kontrolü
        if not request.user.is_superuser and not self._can_reorder_works(request.user):
            return Response(
                {'message': 'İşleri sıralama yetkiniz yok'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        reorder_data = request.data.get('reorder', [])
        
        if not isinstance(reorder_data, list):
            return Response(
                {'message': 'Geçersiz veri formatı'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            for item in reorder_data:
                work_id = item.get('id')
                new_priority = item.get('priority')
                
                if work_id and new_priority is not None:
                    try:
                        Work.objects.filter(id=work_id).update(priority=new_priority)
                    except Exception:
                        pass
            
            # Log
            log_work_action(
                user=request.user,
                work=None,
                action='update',
                description=f'{len(reorder_data)} işin sıralaması güncellendi'
            )
        
        return Response({'message': 'Sıralama güncellendi'})
    
    @action(detail=False, methods=['post'])
    def normalize_priorities(self, request):
        """Priority değerlerini normalize et (1'den başlayarak sıralı yap)"""
        # Sadece superuser
        if not request.user.is_superuser:
            return Response(
                {'message': 'Bu işlem için yetkiniz yok'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        with transaction.atomic():
            works = Work.objects.all().order_by('priority', '-created')
            
            for index, work in enumerate(works, start=1):
                if work.priority != index:
                    Work.objects.filter(id=work.id).update(priority=index)
        
        return Response({'message': 'Sıralama normalize edildi'})
    
    def _can_reorder_works(self, user):
        """Kullanıcının iş sıralama yetkisi var mı?"""
        try:
            from permissions.models import UserRole, SystemPermission
            # Kullanıcının rollerini al
            user_roles = UserRole.objects.filter(user=user).values_list('role', flat=True)
            
            # Bu roller için work_reorder izni var mı kontrol et
            return SystemPermission.objects.filter(
                role__in=user_roles,
                permission_type='work_reorder',
                granted=True
            ).exists()
        except Exception as e:
            print(f"Permission check error: {e}")
            return False

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
    
    @action(detail=True, methods=['post'])
    def add_confirmation(self, request, pk=None):
        """Onay ekleme"""
        work = self.get_object()
        
        # Yeni yetki kontrolü - confirmations field'ı için
        if not PermissionChecker.can_write_column(request.user, 'confirmations'):
            return Response({'message': 'Onay ekleme yetkiniz yok'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        confirmation_data = {
            'date': request.data.get('date'),
            'text': request.data.get('text', '').strip() or None
        }
        
        # Tarih validasyonu
        if not confirmation_data['date']:
            return Response({'message': 'Tarih alanı zorunludur'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        try:
            datetime.strptime(confirmation_data['date'], '%Y-%m-%d')
        except ValueError:
            return Response({'message': 'Geçersiz tarih formatı (YYYY-MM-DD olmalı)'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Onay ekle
        current_confirmations = work.confirmations or []
        
        # Aynı tarihte onay var mı kontrol et
        if any(conf.get('date') == confirmation_data['date'] for conf in current_confirmations):
            return Response({'message': 'Bu tarihte zaten bir onay mevcut'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        confirmation_data['added_by'] = f"{request.user.get_full_name() or request.user.username} ({request.user.id})"
        confirmation_data['added_at'] = timezone.now().isoformat()
        
        current_confirmations.append(confirmation_data)
        work.confirmations = current_confirmations
        work.save()
        
        # Log
        log_work_action(
            user=request.user,
            work=work,
            action='update',
            old_data={'confirmations_count': len(current_confirmations) - 1},
            new_data={'confirmations_count': len(current_confirmations)}
        )
        
        return Response({'message': 'Onay eklendi', 'confirmations': work.confirmations})
    
    @action(detail=True, methods=['post'])
    def remove_confirmation(self, request, pk=None):
        """Onay silme"""
        work = self.get_object()
        
        if not PermissionChecker.can_write_column(request.user, 'confirmations'):
            return Response({'message': 'Onay silme yetkiniz yok'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        date_to_remove = request.data.get('date')
        if not date_to_remove:
            return Response({'message': 'Silinecek onay tarihi gerekli'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        current_confirmations = work.confirmations or []
        new_confirmations = [conf for conf in current_confirmations if conf.get('date') != date_to_remove]
        
        if len(new_confirmations) == len(current_confirmations):
            return Response({'message': 'Onay bulunamadı'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        work.confirmations = new_confirmations
        work.save()
        
        # Log
        log_work_action(
            user=request.user,
            work=work,
            action='update',
            old_data={'confirmations_count': len(current_confirmations)},
            new_data={'confirmations_count': len(new_confirmations)}
        )
        
        return Response({'message': 'Onay silindi', 'confirmations': work.confirmations})
    
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
            return Response({'message': error_message}, status=status.HTTP_403_FORBIDDEN)
        
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
    

    @action(detail=True, methods=['post'])
    def add_printing_location(self, request, pk=None):
        """Baskı lokasyonu ekleme"""
        work = self.get_object()
        
        if not PermissionChecker.can_write_column(request.user, 'printing_locations'):
            return Response({'message': 'Baskı lokasyonu ekleme yetkiniz yok'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        location_data = {
            'location': request.data.get('location', '').strip(),
            'description': request.data.get('description', '').strip() or None
        }
        
        # Validasyon
        if not location_data['location']:
            return Response({'message': 'Lokasyon alanı zorunludur'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Aynı lokasyon var mı kontrol et
        current_locations = work.printing_locations or []
        if any(loc.get('location') == location_data['location'] for loc in current_locations):
            return Response({'message': 'Bu lokasyon zaten eklenmiş'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Lokasyon ekle
        location_data['added_by'] = f"{request.user.get_full_name() or request.user.username} ({request.user.id})"
        location_data['added_at'] = timezone.now().isoformat()
        
        current_locations.append(location_data)
        work.printing_locations = current_locations
        work.save()
        
        # Log
        log_work_action(
            user=request.user,
            work=work,
            action='update',
            description=f'Baskı lokasyonu eklendi: {location_data["location"]}'
        )
        
        return Response({
            'message': 'Baskı lokasyonu eklendi', 
            'printing_locations': work.printing_locations
        })
    
    @action(detail=True, methods=['post'])
    def remove_printing_location(self, request, pk=None):
        """Baskı lokasyonu silme"""
        work = self.get_object()
        
        if not PermissionChecker.can_write_column(request.user, 'printing_locations'):
            return Response({'message': 'Baskı lokasyonu silme yetkiniz yok'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        location_to_remove = request.data.get('location')
        if not location_to_remove:
            return Response({'message': 'Silinecek lokasyon belirtilmeli'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        current_locations = work.printing_locations or []
        new_locations = [loc for loc in current_locations if loc.get('location') != location_to_remove]
        
        if len(new_locations) == len(current_locations):
            return Response({'message': 'Lokasyon bulunamadı'}, 
                          status=status.HTTP_404_NOT_FOUND)
        
        work.printing_locations = new_locations
        work.save()
        
        # Log
        log_work_action(
            user=request.user,
            work=work,
            action='update',
            description=f'Baskı lokasyonu silindi: {location_to_remove}'
        )
        
        return Response({
            'message': 'Baskı lokasyonu silindi', 
            'printing_locations': work.printing_locations
        })


class MovementViewSet(viewsets.ReadOnlyModelViewSet):
    """Movement kayıtları - sadece okunabilir"""
    queryset = Movement.objects.all()
    serializer_class = MovementSerializer
    permission_classes = [IsAdminUser]