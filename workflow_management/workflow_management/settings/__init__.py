# wm_backend/workflow_management/workflow_management/settings/__init__.py
import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle - settings klasöründe
SETTINGS_DIR = Path(__file__).resolve().parent
env_path = os.path.join(SETTINGS_DIR, '.env')

# .env dosyasını yükle
if os.path.exists(env_path):
    load_dotenv(env_path)

# BASE_DIR'i ayarla (base.py için gerekli)
BASE_DIR = SETTINGS_DIR.parent.parent

# Ortam değişkenini oku, varsayılan olarak development kullan
environment = os.environ.get('DJANGO_ENV', 'development')

if environment == 'production':
    from .production import *
else:
    from .development import *