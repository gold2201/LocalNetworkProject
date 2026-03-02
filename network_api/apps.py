from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class NetworkApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'network_api'
