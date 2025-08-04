from rest_framework import serializers
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.contrib.auth.models import User
from workflows.models import Work, Movement, Category, SalesChannel, WorkType
from permissions.utils import PermissionChecker


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
    
    # Links field
    links = LinkListField(required=False, allow_empty=True)
    
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
        fields = '__all__'
    
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
        
        return data
            
    def create(self, validated_data):
        """Link eklerken kullanıcı bilgisini ekle"""
        request = self.context.get('request')
        if request and validated_data.get('links'):
            user = request.user
            user_info = f"{user.get_full_name() or user.username} ({user.id})"
            timestamp = timezone.now().isoformat()
            
            for link in validated_data['links']:
                link['added_by'] = user_info
                link['added_at'] = timestamp
        
        return super().create(validated_data)
    
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
    
    def update(self, instance, validated_data):
        """Güncelleme işlemleri"""
        # Printing control date
        if validated_data.get('printing_control') and not instance.printing_control:
            validated_data['printing_control_date'] = timezone.now()
        elif 'printing_control' in validated_data and not validated_data['printing_control']:
            validated_data['printing_controller'] = None
            validated_data['printing_control_date'] = None
        
        return super().update(instance, validated_data)


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