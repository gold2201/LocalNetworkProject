"""
Тестирование сервера БД с помощью psql-подобных запросов
Запуск: python manage.py test network_api.tests.test_db_operations
"""
from django.test import TestCase
from django.db import connection
from django.core.management import call_command
from network_api.models import (
    Department, Computer, User, Software, Equipment,
    Network, NetworkComputer, HostComputer
)
from datetime import date
import random


class DatabaseConnectionTest(TestCase):
    """Тест подключения к базе данных"""

    def test_connection_info(self):
        """Тест получения информации о подключении"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, version();")
            result = cursor.fetchone()

            print("\n" + "=" * 60)
            print("ТЕСТ ПОДКЛЮЧЕНИЯ К БАЗЕ ДАННЫХ")
            print("=" * 60)
            print(f"База данных: {result[0]}")
            print(f"Пользователь: {result[1]}")
            print(f"Версия PostgreSQL: {result[2][:50]}...")
            print("=" * 60)

            self.assertIsNotNone(result[0])
            self.assertIsNotNone(result[1])
            self.assertIsNotNone(result[2])


class DatabaseSchemaTest(TestCase):
    """Тест схемы базы данных"""

    def test_tables_exist(self):
        """Проверка существования всех таблиц"""
        expected_tables = [
            'Department', 'Computer', 'User', 'User_Computer',
            'Software', 'Software_Computer', 'Equipment',
            'Network', 'Network_Computer', 'Server',
            'Server_Network', 'Host_Computer'
        ]

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]

        print("\n" + "=" * 60)
        print("ТЕСТ СУЩЕСТВОВАНИЯ ТАБЛИЦ")
        print("=" * 60)

        for table in expected_tables:
            exists = table in existing_tables
            print(f"{'✓' if exists else '✗'} {table}")
            if exists:
                self.assertIn(table, existing_tables)

    def test_foreign_keys(self):
        """Проверка внешних ключей"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM
                    information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.table_name;
            """)
            foreign_keys = cursor.fetchall()

        print("\n" + "=" * 60)
        print("ТЕСТ ВНЕШНИХ КЛЮЧЕЙ")
        print("=" * 60)
        for fk in foreign_keys:
            print(f"{fk[0]}.{fk[1]} -> {fk[2]}.{fk[3]}")

        self.assertTrue(len(foreign_keys) > 0)


class DatabaseCRUDTest(TestCase):
    """Тест операций CRUD"""

    def setUp(self):
        """Подготовка тестовых данных"""
        self.department = Department.objects.create(
            room_number=999,
            internal_phone=9999,
            employee_count=0,
            employee_phones=[]
        )

    def test_create_department(self):
        """Тест создания записи"""
        dept = Department.objects.create(
            room_number=101,
            internal_phone=1234,
            employee_count=5,
            employee_phones=[1001, 1002]
        )

        self.assertIsNotNone(dept.id)
        self.assertEqual(dept.room_number, 101)

        print("\n" + "=" * 60)
        print("ТЕСТ СОЗДАНИЯ ЗАПИСИ")
        print("=" * 60)
        print(f"Создан отдел: {dept}")
        print("=" * 60)

    def test_read_department(self):
        """Тест чтения записи"""
        dept = Department.objects.get(id=self.department.id)

        self.assertEqual(dept.room_number, 999)

        print("\n" + "=" * 60)
        print("ТЕСТ ЧТЕНИЯ ЗАПИСИ")
        print("=" * 60)
        print(f"Прочитан отдел: {dept}")
        print("=" * 60)

    def test_update_department(self):
        """Тест обновления записи"""
        self.department.room_number = 1000
        self.department.save()

        updated_dept = Department.objects.get(id=self.department.id)
        self.assertEqual(updated_dept.room_number, 1000)

        print("\n" + "=" * 60)
        print("ТЕСТ ОБНОВЛЕНИЯ ЗАПИСИ")
        print("=" * 60)
        print(f"Обновлен отдел: {updated_dept}")
        print("=" * 60)

    def test_delete_department(self):
        """Тест удаления записи"""
        dept_id = self.department.id
        self.department.delete()

        with self.assertRaises(Department.DoesNotExist):
            Department.objects.get(id=dept_id)

        print("\n" + "=" * 60)
        print("ТЕСТ УДАЛЕНИЯ ЗАПИСИ")
        print("=" * 60)
        print(f"Удален отдел ID: {dept_id}")
        print("=" * 60)


class DatabaseQueryTest(TestCase):
    """Тест сложных запросов"""

    def setUp(self):
        """Подготовка тестовых данных"""
        # Отдел
        self.dept = Department.objects.create(
            room_number=101,
            internal_phone=1234,
            employee_count=3
        )

        # Компьютеры
        self.computers = []
        for i in range(3):
            comp = Computer.objects.create(
                serial_number=100000 + i,
                model=f"Test Model {i}",
                os="Windows 10 Pro" if i < 2 else "Ubuntu 22.04",
                inventory_number=9000 + i,
                department=self.dept
            )
            self.computers.append(comp)

        # Пользователи
        self.users = []
        for i in range(2):
            user = User.objects.create(
                full_name=f"Test User {i}",
                phone=f"+7999{i}",
                email=f"test{i}@test.ru",
                position_id=i + 1,
                department=self.dept
            )
            self.users.append(user)

    def test_join_query(self):
        """Тест JOIN запроса"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    d.room_number,
                    COUNT(DISTINCT c.id) as computers_count,
                    COUNT(DISTINCT u.id) as users_count
                FROM "LocalComputerNetwork"."Department" d
                LEFT JOIN "LocalComputerNetwork"."Computer" c ON c.department_id = d.id
                LEFT JOIN "LocalComputerNetwork"."User" u ON u.department_id = d.id
                WHERE d.id = %s
                GROUP BY d.id, d.room_number
            """, [self.dept.id])

            result = cursor.fetchone()

        print("\n" + "=" * 60)
        print("ТЕСТ JOIN ЗАПРОСА")
        print("=" * 60)
        print(f"Отдел {result[0]}:")
        print(f"  Компьютеров: {result[1]}")
        print(f"  Пользователей: {result[2]}")
        print("=" * 60)

        self.assertEqual(result[1], 3)
        self.assertEqual(result[2], 2)

    def test_aggregate_query(self):
        """Тест агрегатных функций"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    os,
                    COUNT(*) as count,
                    AVG(inventory_number) as avg_inventory
                FROM "LocalComputerNetwork"."Computer"
                GROUP BY os
                ORDER BY count DESC
            """)
            results = cursor.fetchall()

        print("\n" + "=" * 60)
        print("ТЕСТ АГРЕГАТНЫХ ФУНКЦИЙ")
        print("=" * 60)
        for row in results:
            print(f"ОС: {row[0]}, Кол-во: {row[1]}, Средний инв.номер: {row[2]:.0f}")
        print("=" * 60)

    def test_subquery(self):
        """Тест подзапроса"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    d.room_number,
                    d.employee_count,
                    (
                        SELECT COUNT(*) 
                        FROM "LocalComputerNetwork"."Computer" c 
                        WHERE c.department_id = d.id
                    ) as computer_count
                FROM "LocalComputerNetwork"."Department" d
                WHERE d.id = %s
            """, [self.dept.id])

            result = cursor.fetchone()

        print("\n" + "=" * 60)
        print("ТЕСТ ПОДЗАПРОСА")
        print("=" * 60)
        print(f"Отдел {result[0]}:")
        print(f"  Сотрудников: {result[1]}")
        print(f"  Компьютеров: {result[2]}")
        print("=" * 60)

# tests/test_db_operations.py

class DatabasePerformanceTest(TestCase):
    """Тест производительности"""

    def setUp(self):
        """Подготовка тестовых данных"""
        from django.core.management import call_command
        call_command('generate_test_data', '--computers=100', '--clear')

    def test_query_performance(self):
        """Тест производительности запросов"""
        queries = [
            'SELECT * FROM "LocalComputerNetwork"."Computer" LIMIT 10;',

            # ИСПРАВЛЕНО: правильный синтаксис для PostgreSQL
            """SELECT * FROM "LocalComputerNetwork"."Computer" 
               WHERE os LIKE 'Windows%%' 
               LIMIT 50;""",

            # ИСПРАВЛЕНО: добавлен экранирование для %
            """SELECT * FROM "LocalComputerNetwork"."Computer" 
               WHERE os LIKE '%%Windows%%' 
               LIMIT 50;""",

            # Запрос с JOIN
            """
            SELECT d.room_number, COUNT(c.id) 
            FROM "LocalComputerNetwork"."Department" d
            LEFT JOIN "LocalComputerNetwork"."Computer" c ON c.department_id = d.id
            GROUP BY d.id, d.room_number;
            """,

            # Запрос с агрегацией
            """
            SELECT s.name, COUNT(sc."Computer_id") as installations
            FROM "LocalComputerNetwork"."Software" s
            JOIN "LocalComputerNetwork"."Software_Computer" sc ON sc."Software_id" = s.id
            GROUP BY s.id, s.name
            ORDER BY installations DESC
            LIMIT 10;
            """,

            # Дополнительный запрос для проверки
            """
            SELECT n.vlan, COUNT(nc."Computer_id") as computers
            FROM "LocalComputerNetwork"."Network" n
            LEFT JOIN "LocalComputerNetwork"."Network_Computer" nc ON nc."Network_id" = n.id
            GROUP BY n.id, n.vlan
            ORDER BY computers DESC
            LIMIT 10;
            """
        ]

        print("\n" + "=" * 80)
        print("ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("=" * 80)
        print(f"База данных: {connection.settings_dict['NAME']}")
        print(f"Движок: {connection.settings_dict['ENGINE']}")
        print("=" * 80)

        for i, query in enumerate(queries, 1):
            try:
                with connection.cursor() as cursor:
                    # Очищаем запрос от лишних пробелов
                    clean_query = ' '.join(query.split())

                    cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {clean_query}")
                    result = cursor.fetchall()

                    # Извлекаем информацию
                    execution_time = None
                    planning_time = None
                    buffers = None

                    for line in result:
                        line_text = line[0]
                        if 'Execution Time:' in line_text:
                            execution_time = line_text.strip()
                        elif 'Planning Time:' in line_text:
                            planning_time = line_text.strip()
                        elif 'Buffers:' in line_text:
                            buffers = line_text.strip()

                    print(f"\n--- Запрос {i} ---")
                    print(f"SQL: {clean_query[:100]}...")
                    if planning_time:
                        print(f"  {planning_time}")
                    if execution_time:
                        print(f"  {execution_time}")
                    if buffers:
                        print(f"  {buffers}")

                    # Проверяем, что запрос выполняется
                    cursor.execute(clean_query)
                    row_count = len(cursor.fetchall())
                    print(f"  Найдено записей: {row_count}")

            except Exception as e:
                print(f"\n--- Запрос {i} ---")
                print(f"ОШИБКА: {e}")
                print(f"Запрос: {query}")

        print("\n" + "=" * 80)