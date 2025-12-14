from io import BytesIO

import pandas as pd
from django.http import HttpResponse
from django.db import connection
from django.db.models.aggregates import Max
from django.db.models import Subquery, OuterRef
from network_api.mixins import ExportMixin
from network_api.models import Department, User, Network, Software, Server, SoftwareComputer, \
    UserComputer, ServerNetwork, NetworkComputer
from network_api.serializers import (
    ServerSerializer,
    SoftwareComputerSerializer,
    UserComputerSerializer,
    ServerNetworkSerializer
)
from network_api.services.export_utils import export_analytics_to_excel

from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

class ServerViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Server.objects.all()
    serializer_class = ServerSerializer

class SoftwareComputerViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = SoftwareComputer.objects.all()
    serializer_class = SoftwareComputerSerializer

class UserComputerViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = UserComputer.objects.all()
    serializer_class = UserComputerSerializer

class ServerNetworkViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = ServerNetwork.objects.all()
    serializer_class = ServerNetworkSerializer

class AnalyticsViewSet(viewsets.ViewSet):
    """ViewSet для аналитических запросов"""

    @action(detail=False, methods=['get'])
    def department_stats(self, request):
        """Статистика по отделам с GROUP BY и HAVING"""
        from django.db.models import Count, Avg, Q

        # Отделы с более чем 5 компьютерами
        departments = Department.objects.annotate(
            computer_count=Count('computers'),
            avg_inventory=Avg('computers__inventory_number')
        ).filter(
            computer_count__gt=5
        ).values(
            'room_number', 'employee_count', 'computer_count', 'avg_inventory'
        ).order_by('-computer_count')

        return Response(list(departments))

    @action(detail=False, methods=['get'])
    def network_usage(self, request):
        """Использование сетей с подзапросами"""
        from django.db.models import Subquery, OuterRef

        # Сети с количеством подключенных компьютеров
        networks = Network.objects.annotate(
            computer_count=Count('computers'),
            max_speed=Subquery(
                NetworkComputer.objects.filter(
                    network_id=OuterRef('id')
                ).values('network_id').annotate(
                    max_speed=Max('speed')
                ).values('max_speed')[:1]
            )
        ).filter(
            computer_count__gt=0
        ).values(
            'vlan', 'ip_range', 'computer_count', 'max_speed'
        ).order_by('-computer_count')

        return Response(list(networks))

    @action(detail=False, methods=['get'])
    def software_distribution(self, request):
        """Распределение ПО по отделам"""
        software_stats = Software.objects.annotate(
            installation_count=Count('computers'),
            department_count=Count('computers__department', distinct=True)
        ).filter(
            installation_count__gt=0
        ).values(
            'name', 'version', 'installation_count', 'department_count'
        ).order_by('-installation_count')

        return Response(list(software_stats))

    @action(detail=False, methods=['get'])
    def user_computer_relationships(self, request):
        """Связи пользователей с компьютерами"""
        from django.db.models import Count

        user_stats = User.objects.annotate(
            computer_count=Count('computers'),
            department_name=Subquery(
                Department.objects.filter(
                    id=OuterRef('department_id')
                ).values('room_number')[:1]
            )
        ).filter(
            computer_count__gt=0
        ).values(
            'full_name', 'position_id', 'department_name', 'computer_count'
        ).order_by('-computer_count')

        return Response(list(user_stats))

    @action(detail=False, methods=['get'])
    def advanced_queries(self, request):
        """Расширенные запросы с фильтрацией"""
        query_type = request.GET.get('type')

        if query_type == 'high_speed_networks':
            # Сети с высокой скоростью
            networks = NetworkComputer.objects.filter(
                speed__gte=1000
            ).select_related('computer', 'network').values(
                'computer__model',
                'network__vlan',
                'speed',
                'ip_address'
            ).order_by('-speed')

            return Response(list(networks))

        elif query_type == 'software_by_vendor':
            # ПО по вендору с группировкой
            vendor = request.GET.get('vendor', '')
            software = Software.objects.filter(
                vendor__icontains=vendor
            ).annotate(
                install_count=Count('computers')
            ).values(
                'name', 'version', 'vendor', 'install_count'
            ).order_by('-install_count')

            return Response(list(software))

    @action(detail=False, methods=['get'])
    def export_analytics(self, request):
        """Экспорт результатов аналитики"""
        query_type = request.GET.get('query', 'department_stats')

        try:
            if query_type == 'department_stats':
                data = self.department_stats(request).data
                return export_analytics_to_excel(data, 'department_stats')
            elif query_type == 'network_usage':
                data = self.network_usage(request).data
                return export_analytics_to_excel(data, 'network_usage')
            elif query_type == 'software_distribution':
                data = self.software_distribution(request).data
                return export_analytics_to_excel(data, 'software_distribution')
            elif query_type == 'user_computer_relationships':
                data = self.user_computer_relationships(request).data
                return export_analytics_to_excel(data, 'user_computer_relationships')
            else:
                return Response(
                    {'error': 'Invalid query type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {'error': f'Ошибка при экспорте: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export_department_stats(self, request):
        """Экспорт статистики по отделам"""
        try:
            data = self.department_stats(request).data
            return export_analytics_to_excel(data, 'department_stats')
        except Exception as e:
            return Response(
                {'error': f'Ошибка при экспорте: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export_network_usage(self, request):
        """Экспорт использования сетей"""
        try:
            data = self.network_usage(request).data
            return export_analytics_to_excel(data, 'network_usage')
        except Exception as e:
            return Response(
                {'error': f'Ошибка при экспорте: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export_software_distribution(self, request):
        """Экспорт распределения ПО"""
        try:
            data = self.software_distribution(request).data
            return export_analytics_to_excel(data, 'software_distribution')
        except Exception as e:
            return Response(
                {'error': f'Ошибка при экспорте: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def export_user_computer_relationships(self, request):
        """Экспорт связей пользователей с компьютерами"""
        try:
            data = self.user_computer_relationships(request).data
            return export_analytics_to_excel(data, 'user_computer_relationships')
        except Exception as e:
            return Response(
                {'error': f'Ошибка при экспорте: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def comprehensive_export(self, request):
        """
        Комплексный экспорт всех аналитических данных
        """
        try:
            analytics_data = {
                'department_stats': self.department_stats(request).data,
                'network_usage': self.network_usage(request).data,
                'software_distribution': self.software_distribution(request).data,
                'user_computer_relationships': self.user_computer_relationships(request).data,
            }

            return export_analytics_to_excel(analytics_data, 'comprehensive_analytics')
        except Exception as e:
            return Response(
                {'error': f'Ошибка при комплексном экспорте: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DatabaseViewSet(viewsets.ViewSet):
    """ViewSet для операций с базой данных"""

    @action(detail=False, methods=['post'])
    def execute_sql(self, request):
        """Выполнение SQL запроса"""
        try:
            sql_query = request.data.get('query', '').strip()

            if not sql_query:
                return Response({
                    'error': 'SQL запрос не может быть пустым'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Логируем запрос (для безопасности в продакшене нужно ограничить)
            print(f"Executing SQL: {sql_query}")

            with connection.cursor() as cursor:
                # Проверяем тип запроса
                sql_upper = sql_query.upper().strip()

                # Для SELECT и похожих запросов возвращаем данные
                if sql_upper.startswith(('SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN')):
                    cursor.execute(sql_query)

                    # Получаем названия колонок
                    if cursor.description:
                        columns = [col[0] for col in cursor.description]
                        results = []

                        # Преобразуем данные в словари
                        for row in cursor.fetchall():
                            row_dict = {}
                            for i, value in enumerate(row):
                                # Преобразуем специальные типы данных в строки
                                if hasattr(value, 'isoformat'):  # datetime/date
                                    row_dict[columns[i]] = value.isoformat()
                                else:
                                    row_dict[columns[i]] = str(value) if value is not None else None
                            results.append(row_dict)

                        return Response({
                            'status': 'success',
                            'type': 'query',
                            'columns': columns,
                            'results': results,
                            'row_count': len(results),
                            'query': sql_query
                        })
                    else:
                        return Response({
                            'status': 'success',
                            'type': 'query',
                            'message': 'Запрос выполнен, но нет данных для возврата',
                            'row_count': 0,
                            'query': sql_query
                        })

                # Для модифицирующих запросов (INSERT, UPDATE, DELETE)
                elif sql_upper.startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP')):
                    # Запрашиваем подтверждение для опасных операций
                    dangerous_keywords = ['DROP', 'DELETE', 'ALTER', 'TRUNCATE']
                    is_dangerous = any(keyword in sql_upper for keyword in dangerous_keywords)
                    confirmed = request.data.get('confirmed', False)

                    if is_dangerous and not confirmed:
                        return Response({
                            'status': 'warning',
                            'message': 'Этот запрос может изменить или удалить данные. Требуется подтверждение.',
                            'requires_confirmation': True,
                            'query': sql_query
                        }, status=status.HTTP_200_OK)

                    # Выполняем запрос
                    cursor.execute(sql_query)
                    affected_rows = cursor.rowcount

                    return Response({
                        'status': 'success',
                        'type': 'command',
                        'message': 'Команда выполнена успешно',
                        'affected_rows': affected_rows,
                        'query': sql_query
                    })

                else:
                    # Для других типов запросов
                    cursor.execute(sql_query)

                    # Пытаемся получить результаты, если есть
                    try:
                        if cursor.description:
                            columns = [col[0] for col in cursor.description]
                            results = []
                            for row in cursor.fetchall():
                                row_dict = {}
                                for i, value in enumerate(row):
                                    row_dict[columns[i]] = str(value) if value is not None else None
                                results.append(row_dict)

                            return Response({
                                'status': 'success',
                                'type': 'query',
                                'columns': columns,
                                'results': results,
                                'row_count': len(results),
                                'query': sql_query
                            })
                        else:
                            return Response({
                                'status': 'success',
                                'type': 'command',
                                'message': 'Запрос выполнен',
                                'query': sql_query
                            })
                    except:
                        return Response({
                            'status': 'success',
                            'type': 'command',
                            'message': 'Запрос выполнен',
                            'query': sql_query
                        })

        except Exception as e:
            error_msg = str(e)
            return Response({
                'status': 'error',
                'message': f'Ошибка выполнения запроса: {error_msg}',
                'query': sql_query
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def get_tables(self, request):
        """Получение списка всех таблиц в базе данных"""
        try:
            with connection.cursor() as cursor:
                # Для PostgreSQL
                cursor.execute("""
                    SELECT table_name, table_schema 
                    FROM information_schema.tables 
                    WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
                    ORDER BY table_schema, table_name
                """)

                tables = []
                for table_name, table_schema in cursor.fetchall():
                    tables.append({
                        'schema': table_schema,
                        'name': table_name,
                        'full_name': f'"{table_schema}"."{table_name}"'
                    })

                return Response({
                    'status': 'success',
                    'tables': tables
                })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Ошибка получения списка таблиц: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def get_table_info(self, request):
        """Получение информации о структуре таблицы"""
        table_name = request.GET.get('table')
        if not table_name:
            return Response({'error': 'Не указано имя таблицы'}, status=400)

        try:
            with connection.cursor() as cursor:
                # Получаем информацию о колонках
                cursor.execute("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = %s
                    ORDER BY ordinal_position
                """, [table_name])

                columns = []
                for col_name, data_type, is_nullable, column_default in cursor.fetchall():
                    columns.append({
                        'name': col_name,
                        'type': data_type,
                        'nullable': is_nullable == 'YES',
                        'default': column_default
                    })

                return Response({
                    'status': 'success',
                    'table': table_name,
                    'columns': columns
                })

        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Ошибка получения информации о таблице: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def export_sql_results(self, request):
        """Экспорт результатов SQL запроса в Excel"""
        try:
            sql_query = request.data.get('query', '').strip()
            if not sql_query:
                return Response({'error': 'SQL запрос не может быть пустым'}, status=400)

            # Выполняем запрос
            with connection.cursor() as cursor:
                cursor.execute(sql_query)

                if not cursor.description:
                    return Response({'error': 'Запрос не возвращает данные'}, status=400)

                columns = [col[0] for col in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = {}
                    for i, value in enumerate(row):
                        if hasattr(value, 'isoformat'):
                            row_dict[columns[i]] = value.isoformat()
                        else:
                            row_dict[columns[i]] = str(value) if value is not None else ''
                    results.append(row_dict)

            # Создаем Excel файл
            df = pd.DataFrame(results)
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Query Results', index=False)

            output.seek(0)

            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="sql_results.xlsx"'
            return response

        except Exception as e:
            return Response({
                'error': f'Ошибка при экспорте: {str(e)}'
            }, status=500)