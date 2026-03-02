import json
import logging
from datetime import datetime
from confluent_kafka import Producer
from django.conf import settings

logger = logging.getLogger(__name__)

class KafkaProducerService:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KafkaProducerService, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        try:
            self.producer = Producer(settings.KAFKA_PRODUCER_CONFIG)
            logger.info("✅ Kafka Producer инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Kafka Producer: {e}")
            self.producer = None

    def delivery_report(self, err, msg):
        if err is not None:
            logger.error(f'❌ Ошибка доставки сообщения: {err}')
        else:
            logger.info(f'✅ Сообщение доставлено в {msg.topic()} [{msg.partition()}] @ offset {msg.offset()}')

    def send_message(self, topic, key, value):
        if self.producer is None:
            logger.error("❌ Kafka Producer не инициализирован")
            return False

        try:
            message_value = json.dumps(value, default=self.json_serializer)

            self.producer.produce(
                topic=topic,
                key=str(key).encode('utf-8'),
                value=message_value.encode('utf-8'),
                callback=self.delivery_report
            )

            self.producer.poll(1)

            logger.info(f"📤 Сообщение отправлено в топик '{topic}', ключ: {key}")
            return True

        except BufferError as e:
            logger.error(f"❌ Буфер Producer переполнен: {e}")
            self.producer.flush()
            return self.send_message(topic, key, value)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки сообщения в Kafka: {e}")
            return False

    def flush(self):
        if self.producer:
            self.producer.flush()
            logger.info("✅ Все сообщения отправлены")

    @staticmethod
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")