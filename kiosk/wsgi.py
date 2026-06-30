"""
WSGI config for kiosk project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

# import os

# from django.core.wsgi import get_wsgi_application

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kiosk.settings')

# application = get_wsgi_application()



# kiosk/wsgi.py یا فایل اصلی اجرا

import logging
import sys

# تنظیم لاگینگ برای نمایش در کنسول


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)





# python -m waitress --listen=0.0.0.0:8000 --log-level=INFO kiosk.wsgi:application
# python -m waitress --listen=0.0.0.0:8000 kiosk.wsgi:application      


# اگر می‌خواهید لاگ‌های Django را هم ببینید
import django
django.setup()

from django.core.management import call_command



