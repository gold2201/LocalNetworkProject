from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime
from .models import User, Equipment
from .services.kafka_service import KafkaProducerService
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    logger.info(f"ПОЛЗОВАТЕЛЬ СОЗДАН")

    try:
        kafka_producer = KafkaProducerService()

        if created:
            message = {
                'event_type': 'USER_CREATED',
                'event_id': f'user_{instance.id}_{datetime.now().timestamp()}',
                'user_id': instance.id,
                'user_name': instance.full_name,
                'user_email': instance.email,
                'department_id': instance.department_id,
                'position_id': instance.position_id,
                'timestamp': datetime.now().isoformat(),
                'source': 'network-app'
            }

            success = kafka_producer.send_message(
                topic=settings.KAFKA_TOPICS['USER_CREATED'],
                key=str(instance.id),
                value=message
            )

            if success:
                logger.info(f"✅ Событие USER_CREATED отправлено для пользователя {instance.id}")
            else:
                logger.error(f"❌ Не удалось отправить USER_CREATED для пользователя {instance.id}")

            kafka_producer.flush()

        else:
            # Сообщение об обновлении пользователя
            message = {
                'event_type': 'USER_UPDATED',
                'event_id': f'user_update_{instance.id}_{datetime.now().timestamp()}',
                'user_id': instance.id,
                'user_name': instance.full_name,
                'changes': list(kwargs.get('update_fields', [])),
                'timestamp': datetime.now().isoformat(),
                'source': 'network-app'
            }

            kafka_producer.send_message(
                topic=settings.KAFKA_TOPICS['USER_UPDATED'],
                key=str(instance.id),
                value=message
            )

    except Exception as e:
        logger.error(f"❌ Ошибка в обработчике пользователя: {e}")


@receiver(post_save, sender=Equipment)
def equipment_changed_handler(sender, instance, created, **kwargs):
    try:
        kafka_producer = KafkaProducerService()
        action = 'created' if created else 'updated'

        message = {
            'event_type': 'EQUIPMENT_CHANGED',
            'event_id': f'equipment_{action}_{instance.id}_{datetime.now().timestamp()}',
            'equipment_id': instance.id,
            'equipment_type': instance.type,
            'action': action,
            'port_count': instance.port_count,
            'bandwidth': instance.bandwidth,
            'timestamp': datetime.now().isoformat(),
            'source': 'network-app'
        }

        success = kafka_producer.send_message(
            topic=settings.KAFKA_TOPICS['EQUIPMENT_CHANGED'],
            key=str(instance.id),
            value=message
        )

        if success:
            logger.info(f"✅ Событие EQUIPMENT_CHANGED отправлено для оборудования {instance.id}")
        else:
            logger.error(f"❌ Не удалось отправить EQUIPMENT_CHANGED для оборудования {instance.id}")

    except Exception as e:
        logger.error(f"❌ Ошибка в обработчике оборудования: {e}")