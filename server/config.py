import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
TEMPLATE_ROOT = os.path.join(BASE_DIR, 'templates')

DEBUG = os.getenv('TORNADO_DEBUG') == 'True'

SECRET_KEY = os.getenv('SECRET_KEY', 'fiDSpuZ7QFe8fm0XP9Jb7ZIPNsOegkHYtgKSd4I83Hs=')

PORT = os.getenv('PORT', 8080)

# DATABASE_URI removed as we're using in-memory storage

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file'],
        'propagate': True,
    },
    'formatters': {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s %(lineno)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs/tornado.log'),
            'formatter': 'verbose'
        },
    },
    'loggers': {
        'tornado.general': {
            'handlers': ['console', 'file'],
            'propagate': True,
        },
    }
}