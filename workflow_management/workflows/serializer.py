from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from workflows.models import Work, Movement, Category, SalesChannel, WorkType
from permissions.utils import PermissionChecker
from datetime import datetime


class LinkListField(serializers.ListField):
    """Bağlantı listesi için özel field"""
    
    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError('Bağlantılar liste formatında olmalıdır.')
        
        validated_links = []
        url_validator = URLValidator()
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f'Bağlantı {i+1}: Geçersiz format')
            
            url = item.get('url', '').strip()
            if not url:
                raise serializers.ValidationError(f'Bağlantı {i+1}: URL alanı zorunludur')
            
            try:
                url_validator(url)
            except DjangoValidationError:
                raise serializers.ValidationError(f'Bağlantı {i+1}: Geçerli bir URL giriniz')
            
            validated_links.append({
                'url': url,
                'title': item.get('title', '').strip() or None,
                'description': item.get('description', '').strip() or None,
                'added_at': item.get('added_at') or timezone.now().isoformat(),
                'added_by': item.get('added_by')
            })
        
        return validated_links
    
    def to_representation(self, value):
        """Çıktıda gereksiz None değerleri temizle"""
        if not value:
            return []
        
        return [{
            'url': link.get('url'),
            **{k: v for k, v in link.items() if k != 'url' and v is not None}
        } for link in value]


class ConfirmationListField(serializers.ListField):
    """Onay listesi için özel field"""
    
    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError('Onaylar liste formatında olmalıdır.')
        
        validated_confirmations = []
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f'Onay {i+1}: Geçersiz format')
            
            date_str = item.get('date', '').strip()
            if not date_str:
                raise serializers.ValidationError(f'Onay {i+1}: Tarih alanı zorunludur')
            
            # Tarih formatı kontrolü
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise serializers.ValidationError(f'Onay {i+1}: Geçersiz tarih formatı (YYYY-MM-DD olmalı)')
            
            validated_confirmations.append({
                'date': date_str,
                'text': item.get('text', '').strip() or None,
                'added_at': item.get('added_at') or timezone.now().isoformat(),
                'added_by': item.get('added_by')
            })
        
        return validated_confirmations
    
    def to_representation(self, value):
        """Çıktıda gereksiz None değerleri temizle"""
        if not value:
            return []
        
        return [{
            'date': confirmation.get('date'),
            **{k: v for k, v in confirmation.items() if k != 'date' and v is not None}
        } for confirmation in value]


class PrintingLocationListField(serializers.ListField):
    """Baskı lokasyonları için özel field"""
    
    def to_internal_value(self, data):
        if not isinstance(data, list):
            raise serializers.ValidationError('Baskı lokasyonları liste formatında olmalıdır.')
        
        validated_locations = []
        seen_locations = set()
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f'Lokasyon {i+1}: Geçersiz format')
            
            location = item.get('location', '').strip()
            if not location:
                raise serializers.ValidationError(f'Lokasyon {i+1}: Lokasyon alanı zorunludur')
            
            # Duplicate kontrolü
            if location in seen_locations:
                raise serializers.ValidationError(f'Lokasyon {i+1}: "{location}" zaten eklenmiş')
            
            seen_locations.add(location)
            
            validated_locations.append({
                'location': location,
                'description': item.get('description', '').strip() or None,
                'added_at': item.get('added_at') or timezone.now().isoformat(),
                'added_by': item.get('added_by')
            })
        
        return validated_locations
    
    def to_representation(self, value):
        """Çıktıda gereksiz None değerleri temizle"""
        if not value:
            return []
        
        return [{
            'location': loc.get('location'),
            **{k: v for k, v in loc.items() if k != 'location' and v is not None}
        } for loc in value]


class BaseDropdownSerializer(serializers.ModelSerializer):
    """Dropdown modelleri için base serializer"""
    class Meta:
        fields = ['id', 'name']


class CategorySerializer(BaseDropdownSerializer):
    class Meta(BaseDropdownSerializer.Meta):
        model = Category


class WorkTypeSerializer(BaseDropdownSerializer):
    class Meta(BaseDropdownSerializer.Meta):
        model = WorkType


class SalesChannelSerializer(BaseDropdownSerializer):
    class Meta(BaseDropdownSerializer.Meta):
        model = SalesChannel


class WorkflowSerializer(serializers.ModelSerializer):
    """İş akışı serializer"""
    
    # Calculated fields
    status_code = serializers.ReadOnlyField()
    status_text = serializers.ReadOnlyField()
    status_color = serializers.ReadOnlyField()
    
    # Detail fields
    category_detail = CategorySerializer(source='category', read_only=True)
    type_detail = WorkTypeSerializer(source='type', read_only=True)
    sales_channel_detail = SalesChannelSerializer(source='sales_channel', read_only=True)
    designer_detail = serializers.SerializerMethodField()
    printing_controller_detail = serializers.SerializerMethodField()
    
    # JSON fields
    links = LinkListField(required=False, allow_empty=True)
    confirmations = ConfirmationListField(required=False, allow_empty=True)
    printing_locations = PrintingLocationListField(required=False, allow_empty=True)  # YENİ EKLENEN
    
    # Foreign key fields
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    type = serializers.PrimaryKeyRelatedField(
        queryset=WorkType.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    sales_channel = serializers.PrimaryKeyRelatedField(
        queryset=SalesChannel.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    designer = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    printing_controller = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Work
        fields = [
            'id', 'name', 'category', 'price', 'type', 'sales_channel',
            'designer', 'designer_text', 'design_start_date', 'design_end_date',
            'confirmations', 'material_info', 'printing_location', 'printing_locations',  # printing_locations eklendi
            'printing_confirm', 'printing_control', 'printing_controller', 'printing_controller_text',
            'printing_control_date', 'printing_start_date', 'printing_end_date',
            'mixed', 'packaging_date', 'stock_entry', 'shipping_date',
            'links', 'note', 'priority', 'created', 'updated',
            # Calculated fields
            'status_code', 'status_text', 'status_color',
            # Detail fields
            'category_detail', 'type_detail', 'sales_channel_detail',
            'designer_detail', 'printing_controller_detail'
        ]
    
    def get_user_detail(self, user):
        """Kullanıcı detay bilgisi"""
        if not user:
            return None
        return {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'email': user.email
        }
    
    def get_designer_detail(self, obj):
        return self.get_user_detail(obj.designer)
    
    def get_printing_controller_detail(self, obj):
        return self.get_user_detail(obj.printing_controller)

    def to_representation(self, instance):
        """Frontend uyumluluğu için ek alanlar"""
        data = super().to_representation(instance)
        
        # Dropdown name'leri ekle
        detail_mappings = {
            'category_detail': 'category_name',
            'type_detail': 'type_name',
            'sales_channel_detail': 'sales_channel_name',
            'designer_detail': 'designer_name',
            'printing_controller_detail': 'printing_controller_name'
        }
        
        for detail_field, name_field in detail_mappings.items():
            if detail_field in data and data[detail_field]:
                if 'name' in data[detail_field]:
                    data[name_field] = data[detail_field]['name']
                elif 'full_name' in data[detail_field]:
                    data[name_field] = data[detail_field]['full_name']
        
        # Legacy link alanları
        if instance.links and len(instance.links) > 0:
            data['link'] = instance.links[0].get('url')
            data['link_title'] = instance.links[0].get('title', '')
        
        # Legacy confirm_date alanı (geriye uyumluluk için)
        if instance.confirmations and len(instance.confirmations) > 0:
            # En son onay tarihini al
            sorted_confirmations = sorted(instance.confirmations, key=lambda x: x.get('date', ''), reverse=True)
            data['confirm_date'] = sorted_confirmations[0].get('date')
        
        return data
            
    def create(self, validated_data):
        """Oluştururken kullanıcı bilgisini ekle"""
        request = self.context.get('request')
        if request:
            user = request.user
            user_info = f"{user.get_full_name() or user.username} ({user.id})"
            timestamp = timezone.now().isoformat()
            
            # Links'e kullanıcı bilgisi ekle
            if validated_data.get('links'):
                for link in validated_data['links']:
                    link['added_by'] = user_info
                    link['added_at'] = timestamp
            
            # Confirmations'a kullanıcı bilgisi ekle
            if validated_data.get('confirmations'):
                for confirmation in validated_data['confirmations']:
                    confirmation['added_by'] = user_info
                    confirmation['added_at'] = timestamp
            
            # Printing locations'a kullanıcı bilgisi ekle
            if validated_data.get('printing_locations'):
                for location in validated_data['printing_locations']:
                    location['added_by'] = user_info
                    location['added_at'] = timestamp
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        """Güncelleme işlemleri"""
        request = self.context.get('request')
        
        # Confirmations güncellemesi için kullanıcı bilgisi ekle
        if 'confirmations' in validated_data and request:
            user = request.user
            user_info = f"{user.get_full_name() or user.username} ({user.id})"
            timestamp = timezone.now().isoformat()
            
            # Yeni eklenen onayları tespit et ve kullanıcı bilgisi ekle
            new_confirmations = validated_data.get('confirmations', [])
            existing_confirmations = instance.confirmations or []
            
            # Yeni onayları bul (tarih bazlı karşılaştırma)
            existing_dates = {conf.get('date') for conf in existing_confirmations}
            
            for confirmation in new_confirmations:
                if confirmation.get('date') not in existing_dates:
                    confirmation['added_by'] = user_info
                    confirmation['added_at'] = timestamp
        
        # Printing locations güncellemesi için kullanıcı bilgisi ekle
        if 'printing_locations' in validated_data and request:
            user = request.user
            user_info = f"{user.get_full_name() or user.username} ({user.id})"
            timestamp = timezone.now().isoformat()
            
            # Yeni eklenen lokasyonları tespit et
            new_locations = validated_data.get('printing_locations', [])
            existing_locations = instance.printing_locations or []
            
            # Yeni lokasyonları bul
            existing_location_names = {loc.get('location') for loc in existing_locations}
            
            for location in new_locations:
                if location.get('location') not in existing_location_names:
                    location['added_by'] = user_info
                    location['added_at'] = timestamp
        
        # Printing control date
        if validated_data.get('printing_control') and not instance.printing_control:
            validated_data['printing_control_date'] = timezone.now()
        elif 'printing_control' in validated_data and not validated_data['printing_control']:
            validated_data['printing_controller'] = None
            validated_data['printing_control_date'] = None
        
        return super().update(instance, validated_data)
    
    def validate(self, attrs):
        """İş mantığı ve yetki kontrolü"""
        # Printing control validation
        printing_control = attrs.get('printing_control', 
                                   self.instance.printing_control if self.instance else False)
        printing_controller = attrs.get('printing_controller', 
                                      self.instance.printing_controller if self.instance else None)
        
        if not printing_control and printing_controller:
            raise serializers.ValidationError({
                'printing_controller': 'Baskı kontrolü seçili değilken kontrolü yapan kişi atanamaz.'
            })
        
        # Yetki kontrolü
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not request.user.is_superuser and self.instance:
            is_valid, error_message = PermissionChecker.validate_writable_fields(request.user, attrs)
            if not is_valid:
                raise serializers.ValidationError(error_message)
        
        return attrs


class MovementSerializer(serializers.ModelSerializer):
    """İşlem kayıtları serializer"""
    user_display = serializers.SerializerMethodField()
    work_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Movement
        fields = '__all__'
    
    def get_user_display(self, obj):
        """Kullanıcı görüntüleme adı"""
        if obj.user_fullname:
            return obj.user_fullname
        elif obj.user:
            return obj.user.get_full_name() or obj.user.username
        return 'Bilinmiyor'
    
    def get_work_display(self, obj):
        """İş görüntüleme adı"""
        if obj.work_name:
            return obj.work_name
        elif obj.work:
            return obj.work.name
        return '-'