import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'credit_approval_system.settings')

app = Celery('credit_approval_system')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in your Django apps
app.autodiscover_tasks()
