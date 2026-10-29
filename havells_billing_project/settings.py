"""
Django settings for Havells Billing Intelligence & MIS Analytics Dashboard.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Security settings
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-havells-billing-intelligence-key-prod-2026')
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '*').split(',') if host.strip()]
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    'https://havells-dashboard.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    
    # Local apps
    'apps.core',
    'apps.imports',
    'apps.analytics',
    'apps.quality',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'havells_billing_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.app_context',
            ],
            'builtins': [
                'apps.core.templatetags.mis_tags',
            ],
        },
    },
]

WSGI_APPLICATION = 'havells_billing_project.wsgi.application'

# Database Configuration
# Primary: PostgreSQL (configured via env variables)
# Fallback: SQLite for seamless local execution if PostgreSQL is not active
DB_ENGINE = os.getenv('DB_ENGINE', '')
DB_NAME = os.getenv('DB_NAME', '')

if DB_ENGINE == 'django.db.backends.postgresql' or (DB_NAME and not DB_ENGINE.endswith('sqlite3')):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'havells_billing_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
            'OPTIONS': {
                'sslmode': os.getenv('DB_SSLMODE', 'require'),
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise production static files handling & compression
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_USE_FINDERS = True

# Media files (Uploaded Excel workbooks)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Rest Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# Authentication URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Max upload size (50MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800
FILE_UPLOAD_MAX_MEMORY_SIZE = 52428800
