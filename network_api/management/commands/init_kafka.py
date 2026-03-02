import time
import logging
from django.core.management.base import BaseCommand
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Инициализация Kafka: создание топиков'

    def add_arguments(self, parser):
        parser.add_argument(
            '--wait',
            type=int,
            default=30,
            help='Время ожидания Kafka (секунды)'
        )
        parser.add_argument(
            '--retry',
            type=int,
            default=5,
            help='Количество попыток подключения'
        )

    def handle(self, *args, **options):
        wait_time = options['wait']
        max_retries = options['retry']

        logger.info('🚀 Инициализация Kafka...')

        for attempt in range(max_retries):
            try:
                logger.info(f'⏳ Попытка подключения к Kafka ({attempt + 1}/{max_retries})...')
                admin_client = KafkaAdminClient(
                    bootstrap_servers=settings.KAFKA_CONSUMER_CONFIG['bootstrap.servers'],
                    client_id='django-kafka-init'
                )
                logger.info('✅ Подключение к Kafka успешно')
                break
            except NoBrokersAvailable:
                if attempt < max_retries - 1:
                    logger.warning(f'⏳ Kafka не доступен, жду {wait_time} сек...')
                    time.sleep(wait_time)
                else:
                    logger.error('❌ Не удалось подключиться к Kafka')
                    return

        topic_list = [
            NewTopic(
                name='user-created',
                num_partitions=1,
                replication_factor=1,
                topic_configs={
                    'retention.ms': '604800000',
                    'cleanup.policy': 'delete'
                }
            ),
            # NewTopic(name='user-updated', num_partitions=1, replication_factor=1),
        ]

        try:
            admin_client.create_topics(new_topics=topic_list, validate_only=False)
            logger.info('✅ Топики созданы успешно')

            topics = admin_client.list_topics()
            logger.info(f'📋 Доступные топики: {", ".join(topics)}')

        except TopicAlreadyExistsError:
            logger.warning('⚠️ Топики уже существуют')
        except Exception as e:
            logger.error(f'❌ Ошибка создания топиков: {e}')
        finally:
            admin_client.close()
