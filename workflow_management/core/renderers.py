from rest_framework.renderers import JSONRenderer
from datetime import datetime
import json


class CustomJSONRenderer(JSONRenderer):
    """API response'larını standart formata dönüştürür"""
    
    STATUS_MESSAGES = {
        200: "İşlem başarıyla tamamlandı",
        201: "Kayıt başarıyla oluşturuldu",
        204: "Kayıt başarıyla silindi",
        400: "Geçersiz istek. Lütfen bilgileri kontrol edin",
        401: "Bu işlem için giriş yapmanız gerekiyor",
        403: "Bu işlem için yetkiniz bulunmuyor",
        404: "Aradığınız kayıt bulunamadı",
        405: "Bu istek yöntemi desteklenmiyor",
        500: "Beklenmeyen bir hata oluştu. Lütfen daha sonra tekrar deneyin"
    }
    
    ERROR_CODES = {
        400: 'VALIDATION_ERROR',
        401: 'AUTHENTICATION_REQUIRED',
        403: 'PERMISSION_DENIED',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        500: 'INTERNAL_SERVER_ERROR'
    }
    
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response') if renderer_context else None
        status_code = response.status_code if response else 200
        success = 200 <= status_code < 400
        
        formatted_response = {
            'success': success,
            'message': self._get_message(data, status_code),
            'data': self._get_data(data, success),
            'errors': self._get_errors(data, status_code, success),
            'timestamp': datetime.now().isoformat(),
            'status_code': status_code
        }
        
        return super().render(formatted_response, accepted_media_type, renderer_context)
    
    def _get_message(self, data, status_code):
        """Duruma göre mesaj döndür"""
        if isinstance(data, dict):
            if 'message' in data:
                return data['message']
            if 'detail' in data:
                return str(data['detail'])
        
        return self.STATUS_MESSAGES.get(status_code, "İşlem tamamlandı")
    
    def _get_data(self, data, success):
        """Başarılı durumlarda veriyi döndür"""
        if not success:
            return None
            
        if isinstance(data, dict):
            # Hata alanlarını temizle
            excluded_keys = ['message', 'detail', 'errors', 'non_field_errors']
            clean_data = {k: v for k, v in data.items() if k not in excluded_keys}
            return clean_data if clean_data else data
        
        return data
    
    def _get_errors(self, data, status_code, success):
        """Hata durumlarında error bilgilerini döndür"""
        if success:
            return None
        
        errors = {'error_code': self.ERROR_CODES.get(status_code, 'UNKNOWN_ERROR')}
        
        if isinstance(data, dict):
            field_errors = {}
            non_field_errors = []
            
            for key, value in data.items():
                if key in ['detail', 'message']:
                    non_field_errors.append(str(value))
                elif key == 'non_field_errors':
                    non_field_errors.extend([str(v) for v in value])
                elif isinstance(value, list) and key not in ['error_code']:
                    field_errors[key] = [str(v) for v in value]
                elif key not in ['error_code']:
                    field_errors[key] = [str(value)]
            
            if field_errors:
                errors['field_errors'] = field_errors
            if non_field_errors:
                errors['non_field_errors'] = non_field_errors
        
        return errors