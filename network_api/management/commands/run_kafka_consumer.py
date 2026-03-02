import json
import logging

from django.core.management.base import BaseCommand
from django.conf import settings
from confluent_kafka import Consumer, KafkaError, KafkaException

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Запускает Kafka Consumer для обработки событий'

    def handle(self, *args, **options):
        logger.info('🚀 Запуск Kafka Consumer...')

        consumer_config = {
            'bootstrap.servers': settings.KAFKA_CONSUMER_CONFIG['bootstrap.servers'],
            'group.id': settings.KAFKA_CONSUMER_CONFIG['group.id'],
            'auto.offset.reset': settings.KAFKA_CONSUMER_CONFIG['auto.offset.reset'],
            'enable.auto.commit': settings.KAFKA_CONSUMER_CONFIG['enable.auto.commit'],
        }

        topics = [
            settings.KAFKA_TOPICS['USER_CREATED'],
        ]

        consumer = Consumer(consumer_config)
        consumer.subscribe(topics)

        logger.info(f'✅ Подписался на топики: {topics}')

        try:
            while True:
                msg = consumer.poll(1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Достигнут конец раздела в топике {msg.topic()}")
                        continue
                    if msg.error().code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
                        logger.debug(f"Топика нет или он еще не создан, перепроверьте топик {msg.topic()}")
                        continue
                    else:
                        logger.error(f"❌ Ошибка Consumer: {msg.error()}")
                        break

                try:
                    key = msg.key().decode('utf-8') if msg.key() else None
                    value = json.loads(msg.value().decode('utf-8'))

                    self.process_message(
                        topic=msg.topic(),
                        key=key,
                        value=value,
                        partition=msg.partition(),
                        offset=msg.offset()
                    )

                    consumer.commit(msg)

                except json.JSONDecodeError as e:
                    logger.error(f"❌ Ошибка декодирования JSON: {e}")
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки сообщения: {e}")

        except KeyboardInterrupt:
            logger.warning('🛑 Consumer остановлен пользователем')
        except KafkaException as e:
            logger.error(f"❌ Фатальная ошибка Kafka: {e}")
        finally:
            consumer.close()
            logger.info('👋 Consumer закрыт')

    def process_message(self, topic, key, value, partition, offset):
        event_type = value.get('event_type', 'UNKNOWN')
        log_message = (
            f"📨 Получено сообщение:\n"
            f"  Топик: {topic}\n"
            f"  Тип события: {event_type}\n"
            f"  Partition: {partition}, Offset: {offset}\n"
        )
        logger.info(f"Обработано событие {event_type} из топика {topic}. Данные {log_message}")

        if event_type == 'USER_CREATED':
            self.handle_user_created(value)
        elif event_type == 'USER_UPDATED':
            self.handle_user_created(value)
        elif event_type == 'EQUIPMENT_CHANGED':
            self.handle_user_created(value)

    def handle_user_created(self, data):
        logger.info(f"👤 Новый пользователь: {data.get('user_name')} (ID: {data.get('user_id')})")

    def handle_user_updated(self, data):
        self.stdout.write(self.style.HTTP_INFO(
            f"📝 Обновлен пользователь ID: {data.get('user_id')}"
        ))

    def handle_equipment_changed(self, data):
        self.stdout.write(self.style.HTTP_INFO(
            f"🔧 Оборудование {data.get('action')}: {data.get('equipment_type')}"
        ))
