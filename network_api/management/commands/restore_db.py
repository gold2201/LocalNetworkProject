import os
import json
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    help = 'Восстановление базы данных из резервной копии'

    def add_arguments(self, parser):
        parser.add_argument('backup_file', type=str, help='Путь к файлу резервной копии')
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Не запрашивать подтверждение'
        )

    def handle(self, *args, **options):
        backup_file = options['backup_file']

        if not os.path.exists(backup_file):
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            full_path = os.path.join(backup_dir, backup_file)
            if os.path.exists(full_path):
                backup_file = full_path
            else:
                raise CommandError(f'Файл не найден: {backup_file}')

        self.stdout.write(f'Восстановление из файла: {backup_file}')

        meta_file = backup_file + '.meta.json'
        if os.path.exists(meta_file):
            with open(meta_file, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            self.stdout.write(f'  Дата бэкапа: {meta.get("timestamp", "unknown")}')
            self.stdout.write(f'  Формат: {meta.get("format", "unknown")}')
            self.stdout.write(f'  Включенные таблицы: {len(meta.get("tables_included", []))}')

        if not options['noinput']:
            confirm = input('Восстановление удалит все текущие данные. Продолжить? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Операция отменена.')
                return

        try:
            self.stdout.write('Очистка базы данных...')
            call_command('flush', '--noinput')

            self.stdout.write('Восстановление данных...')
            call_command('loaddata', backup_file)

            self.stdout.write(self.style.SUCCESS('✓ База данных успешно восстановлена'))

            from django.apps import apps
            self.stdout.write('\nСтатистика после восстановления:')
            for model in apps.get_models():
                if model._meta.app_label == 'network_api':
                    count = model.objects.count()
                    if count > 0:
                        self.stdout.write(f'  {model._meta.verbose_name}: {count}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Ошибка при восстановлении: {str(e)}'))

            self.stdout.write('Восстановление миграций...')
            try:
                call_command('migrate')
                self.stdout.write(self.style.SUCCESS('✓ Миграции восстановлены'))
            except Exception as migrate_error:
                self.stdout.write(self.style.ERROR(f'✗ Ошибка восстановления миграций: {migrate_error}'))

            raise