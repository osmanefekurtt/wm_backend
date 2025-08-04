from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


class LoginSerializer(serializers.Serializer):
    """Kullanıcı giriş doğrulaması"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if not (username and password):
            raise serializers.ValidationError('Kullanıcı adı ve şifre gerekli.')
        
        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError('Kullanıcı adı veya şifre hatalı.')
        
        if not user.is_active:
            raise serializers.ValidationError('Bu hesap aktif değil.')
        
        data['user'] = user
        return data


class UserSerializer(serializers.ModelSerializer):
    """Kullanıcı bilgileri"""
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff')


class RegisterSerializer(serializers.Serializer):
    """Yeni kullanıcı kaydı"""
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    re_password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Bu kullanıcı adı zaten kullanılıyor.")
        return value
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Bu email adresi zaten kullanılıyor.")
        return value
    
    def validate(self, data):
        if data['password'] != data['re_password']:
            raise serializers.ValidationError({"password": "Şifreler eşleşmiyor."})
        return data
    
    def create(self, validated_data):
        validated_data.pop('re_password')
        return User.objects.create_user(**validated_data)