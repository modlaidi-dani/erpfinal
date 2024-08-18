from .base import *

DEBUG = False
env = os.environ.copy()

SECRET_KEY = env.get('SECRET_KEY', 'default_secret_key')

ALLOWED_HOSTS = [
    'erp.divatech.dz',
    'www.erp.divatech.dz'
]


del STATICFILES_STORAGE
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
MEDIA_ROOT = "/home/uxbkzftt/controlsystemis-dossiasi.divatech.dz/"
MEDIA_URL = "https://controlsystemis-dossiasi.divatech.dz/"

# Set SECURE_HSTS_SECONDS to enable HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = 31536000  # Enforce HSTS for a year

# Set SECURE_SSL_REDIRECT to True to always redirect to HTTPS
SECURE_SSL_REDIRECT = True


# Set SESSION_COOKIE_SECURE to True for secure session cookies
SESSION_COOKIE_SECURE = True

# Set CSRF_COOKIE_SECURE to True for secure CSRF cookies
CSRF_COOKIE_SECURE = True

try:
    from .local import *
except ImportError:
    pass
