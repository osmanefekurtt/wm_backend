# core/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException
from rest_framework import status

def custom_exception_handler(exc, context):
    """Custom exception handler for consistent error responses"""
    
    # DRF'nin varsayılan exception handler'ını çağır
    response = exception_handler(exc, context)
    
    if response is not None:
        # Response data'yı yeniden düzenle
        custom_response_data = {}
        
        # Eğer response.data dict ise
        if isinstance(response.data, dict):
            custom_response_data = response.data
        # Eğer response.data list ise (field errors)
        elif isinstance(response.data, list):
            custom_response_data = {'non_field_errors': response.data}
        else:
            custom_response_data = {'detail': str(response.data)}
        
        response.data = custom_response_data
    
    return response


class CustomAPIException(APIException):
    """Özelleştirilmiş API Exception"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Bir hata oluştu.'
    default_code = 'error'
    
    def __init__(self, detail=None, code=None, status_code=None):
        if status_code:
            self.status_code = status_code
        super().__init__(detail, code)