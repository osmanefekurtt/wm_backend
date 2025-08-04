# wm_backend/workflow_management/workflow_management/settings/development.py
"""Development settings"""

from .base import *
import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-*ebl69a6+no5-b5#dy5&+722+g!=bi!i)$-=f7j+0&^c24lvec'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Development için tüm host'lara izin ver
ALLOWED_HOSTS = ['*']

# Database - Development için SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS - Development
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

# Email Backend - Development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
}