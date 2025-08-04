from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework import exceptions


class CustomJWTAuthentication(JWTAuthentication):
    """JWT Authentication with Turkish error messages"""
    
    ERROR_MESSAGES = {
        'expired': ('Token süresi dolmuş. Lütfen tekrar giriş yapın.', 'token_expired'),
        'invalid': ('Geçersiz token. Lütfen tekrar giriş yapın.', 'invalid_token'),
        'not found': ('Token bulunamadı. Lütfen giriş yapın.', 'token_not_found'),
        'default': ('Kimlik doğrulama başarısız. Lütfen tekrar giriş yapın.', 'authentication_failed'),
        'format': ('Geçersiz token formatı.', 'invalid_token_format')
    }
    
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except InvalidToken as e:
            messages = e.detail.get('messages', [])
            
            if messages:
                first_message = str(messages[0]).lower()
                
                for key, (message, code) in self.ERROR_MESSAGES.items():
                    if key in first_message:
                        raise exceptions.AuthenticationFailed(detail=message, code=code)
            
            message, code = self.ERROR_MESSAGES['default']
            raise exceptions.AuthenticationFailed(detail=message, code=code)
            
        except TokenError:
            message, code = self.ERROR_MESSAGES['format']
            raise exceptions.AuthenticationFailed(detail=message, code=code)