from django.db import models
from .models import Movement, Work


def serialize_value(value):
    """Değerleri JSON serializable hale getir"""
    if isinstance(value, models.Model):
        return {'id': value.pk, 'display': str(value)}
    elif hasattr(value, 'isoformat'):
        return value.isoformat()
    elif value is None:
        return None
    else:
        return str(value)


def format_display_value(value):
    """Görüntüleme için değer formatla"""
    if isinstance(value, models.Model):
        return str(value)
    elif value is None:
        return 'Boş'
    elif isinstance(value, bool):
        return 'Evet' if value else 'Hayır'
    else:
        return str(value)


def log_work_action(user, work, action, old_data=None, new_data=None):
    """Work modelindeki değişiklikleri loglar"""
    
    if not user or not user.is_authenticated:
        return
    
    user_fullname = f"{user.first_name} {user.last_name}".strip() or user.username
    work_name = work.name if work else None
    
    if action == 'create':
        description = f"{work_name} isimli yeni iş oluşturuldu"
        changes = None
        
    elif action == 'update':
        changes = _get_changes(work, old_data, new_data, work_name)
        description = changes['description']
        changes = changes['data'] if changes['data'] and changes['data']['old'] else None
        
    elif action == 'delete':
        description = f"{work_name} isimli iş silindi"
        changes = None
    
    else:
        return
    
    Movement.objects.create(
        user=user,
        user_fullname=user_fullname,
        work=work if action != 'delete' else None,
        work_name=work_name,
        action=action,
        description=description,
        changes=changes
    )


def _get_changes(work, old_data, new_data, work_name):
    """Değişiklikleri hesapla ve formatla"""
    changed_data = {'old': {}, 'new': {}}
    change_details = []
    
    if old_data and new_data:
        for field_name, old_value in old_data.items():
            new_value = new_data.get(field_name)
            
            if old_value != new_value:
                # Serialize et
                changed_data['old'][field_name] = serialize_value(old_value)
                changed_data['new'][field_name] = serialize_value(new_value)
                
                # Verbose name al
                try:
                    field_verbose = work._meta.get_field(field_name).verbose_name
                except:
                    field_verbose = field_name
                
                # Görüntüleme formatı
                old_display = format_display_value(old_value)
                new_display = format_display_value(new_value)
                
                change_details.append(f"{field_verbose}: {old_display} → {new_display}")
    
    description = f"{work_name} isimli iş güncellendi"
    if change_details:
        description += f". Değişiklikler: {', '.join(change_details)}"
    
    return {
        'description': description,
        'data': changed_data
    }