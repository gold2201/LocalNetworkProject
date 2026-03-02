from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class NetworkApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'network_api'

    def ready(self):
        from . import signals
        logger.info("✅ Сигналы Django зарегистрированы")

        try:
            from .services.kafka_service import KafkaProducerService
            producer = KafkaProducerService()
            logger.info("✅ Kafka Producer готов к работе")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Kafka: {e}")