# authentication/urls.py
from django.urls import path
from .views import login_view, register_view, list_users, user_detail, search_users

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('users/', list_users, name='list_users'),
    path('users/search/', search_users, name='search_users'),  # Yeni endpoint
    path('users/<int:pk>/', user_detail, name='user_detail'),
]