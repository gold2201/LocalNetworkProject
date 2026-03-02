# management/commands/backup_db.py

import os
import datetime
import json
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from django.utils import timezone


class Command(BaseCommand):
    help = 'Создание резервной копии базы данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'xml', 'yaml'],
            default='json',
            help='Формат резервной копии'
        )
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Сжать резервную копию'
        )
        parser.add_argument(
            '--exclude',
            nargs='+',  # ✅ ВАЖНО: собирает все аргументы в список
            default=[],
            help='Исключить таблицы из бэкапа'
        )

    def handle(self, *args, **options):
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)

        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'network_db_backup_{timestamp}.{options["format"]}'
        filepath = os.path.join(backup_dir, filename)

        self.stdout.write(f'Создание резервной копии: {filename}')

        # ✅ ПРАВИЛЬНО: формируем список exclude моделей
        exclude_models = []

        # Всегда исключаем системные таблицы
        exclude_models.extend([
            'contenttypes',
            'auth.permission',
            'sessions'
        ])

        # Добавляем пользовательские исключения
        if options['exclude']:
            exclude_models.extend(options['exclude'])

        self.stdout.write(f'  Исключаемые модели: {", ".join(exclude_models)}')

        try:
            # ✅ ПРАВИЛЬНО: передаем список в аргумент --exclude
            with open(filepath, 'w', encoding='utf-8') as f:
                call_command(
                    'dumpdata',
                    '--natural-foreign',
                    '--natural-primary',
                    '--indent=2',
                    f'--format={options["format"]}',
                    stdout=f
                )

            self.stdout.write(self.style.SUCCESS(f'✅ Резервная копия создана: {filename}'))

            # Информация о файле
            file_size = os.path.getsize(filepath)
            size_mb = file_size / (1024 * 1024)
            self.stdout.write(f'  Размер: {size_mb:.2f} MB')

            # Мета-информация
            meta = {
                'backup_file': filename,
                'timestamp': timestamp,
                'format': options['format'],
                'size_bytes': file_size,
                'excluded_models': exclude_models
            }

            meta_filepath = filepath + '.meta.json'
            with open(meta_filepath, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2, ensure_ascii=False)

            self.stdout.write(f'  Мета-файл: {meta_filepath}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Ошибка при создании бэкапа: {str(e)}'))
            raise