# authentication/views.py
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from datetime import datetime, timezone
from django.contrib.auth.models import User
from django.db.models import Q
from .serializers import LoginSerializer, UserSerializer, RegisterSerializer
from .permissions import IsSuperUser


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_users(request):
    """Kullanıcı arama - isim, soyisim veya username ile"""
    search_term = request.query_params.get('q', '').strip()
    limit = int(request.query_params.get('limit', 20))
    
    users_query = User.objects.filter(is_active=True)
    
    if search_term:
        users_query = users_query.filter(
            Q(first_name__icontains=search_term) |
            Q(last_name__icontains=search_term) |
            Q(username__icontains=search_term)
        )
    
    users = users_query.order_by('first_name', 'last_name')[:limit]
    
    users_data = [{
        'id': user.id,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'email': user.email,
        'display_name': f"{user.get_full_name() or user.username} ({user.username})",
        'is_staff': user.is_staff
    } for user in users]
    
    return Response({
        'message': f'{len(users_data)} kullanıcı bulundu',
        'users': users_data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Kullanıcı girişi"""
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        
        access_token_lifetime = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']
        refresh_token_lifetime = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
        
        now = datetime.now(timezone.utc)
        
        return Response({
            'message': 'Giriş başarılı',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'token_type': 'Bearer',
            'access_expires_at': (now + access_token_lifetime).isoformat(),
            'refresh_expires_at': (now + refresh_token_lifetime).isoformat(),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsSuperUser])
def register_view(request):
    """Yeni kullanıcı kaydı - Sadece superuser"""
    serializer = RegisterSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'Kullanıcı başarıyla oluşturuldu',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_users(request):
    """Tüm kullanıcıları listele"""
    users = User.objects.all().order_by('-date_joined')
    
    users_data = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'is_active': user.is_active,
        'date_joined': user.date_joined,
        'last_login': user.last_login
    } for user in users]
    
    return Response(users_data)


@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsSuperUser])
def user_detail(request, pk):
    """Kullanıcı detay, güncelleme ve silme"""
    try:
        user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({'message': 'Kullanıcı bulunamadı'}, status=status.HTTP_404_NOT_FOUND)
    
    if request.method == 'GET':
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
            'roles': list(user.user_roles.values_list('role_id', flat=True))
        }
        return Response(user_data)
    
    elif request.method == 'PATCH':
        data = request.data
        
        # Email benzersizlik kontrolü
        if 'email' in data and User.objects.filter(email=data['email']).exclude(pk=pk).exists():
            return Response({'message': 'Bu email adresi zaten kullanılıyor'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Güncellenebilir alanlar
        update_fields = ['email', 'first_name', 'last_name', 'is_active', 'is_superuser']
        for field in update_fields:
            if field in data:
                if field == 'is_superuser' and user.id == request.user.id and not data[field]:
                    return Response({'message': 'Kendi superuser yetkinizi kaldıramazsınız'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                setattr(user, field, data[field])
        
        user.save()
        
        return Response({
            'message': 'Kullanıcı başarıyla güncellendi',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            }
        })
    
    elif request.method == 'DELETE':
        if user.id == request.user.id:
            return Response({'message': 'Kendinizi silemezsiniz'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        username = user.username
        user.delete()
        return Response({'message': f'{username} kullanıcısı başarıyla silindi'})
