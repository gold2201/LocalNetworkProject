from rest_framework import serializers
from network_api.mixins import ExportMixin
from network_api.models import Department
from network_api.serializers import DepartmentSerializer

from django.db.models import Count, F, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

class DepartmentViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['employee_count']
    search_fields = ['room_number', 'internal_phone']

    def get_queryset(self):
        queryset = Department.objects.all()

        # Для всех запросов добавляем префетчинг
        queryset = queryset.select_related('hostcomputer').prefetch_related('computers')

        # Применяем фильтрацию для GET запросов
        if self.request.method == 'GET':
            min_employees = self.request.query_params.get('min_employees')
            search = self.request.query_params.get('search')

            if min_employees:
                queryset = queryset.filter(employee_count__gte=int(min_employees))

            if search:
                queryset = queryset.filter(
                    Q(room_number__icontains=search) |
                    Q(internal_phone__icontains=search)
                )

            # Аннотируем всегда для списка и детального просмотра
            queryset = queryset.annotate(
                computers_count=Count('computers', distinct=True),
                host_computer_ip=F('hostcomputer__ip_address')
            )

        return queryset

    def retrieve(self, request, *args, **kwargs):
        # Используем get_queryset который уже содержит аннотации
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        print(f"Create request data: {request.data}")

        # Удаляем id из данных если он есть
        data = request.data.copy()
        if 'id' in data:
            del data['id']

        # Преобразуем internal_phone в число если это строка
        if 'internal_phone' in data and isinstance(data['internal_phone'], str):
            # Удаляем все нецифровые символы
            data['internal_phone'] = int(''.join(filter(str.isdigit, data['internal_phone'])))

        serializer = self.get_serializer(data=data)

        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except serializers.ValidationError as e:
            print(f"Validation error: {e.detail}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"Error: {str(e)}")
            return Response(
                {'error': f'Server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        print(f"Update request data: {request.data}")

        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        data = request.data.copy()
        if 'id' in data:
            del data['id']

        # Преобразуем internal_phone в число если нужно
        if 'internal_phone' in data and isinstance(data['internal_phone'], str):
            data['internal_phone'] = int(''.join(filter(str.isdigit, data['internal_phone'])))

        serializer = self.get_serializer(instance, data=data, partial=partial)

        try:
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}

            return Response(serializer.data)

        except serializers.ValidationError as e:
            print(f"Validation error: {e.detail}")
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        try:
            # Используем аннотированный queryset
            department = self.get_queryset().filter(pk=pk).first()

            if not department:
                return Response({'error': 'Department not found'}, status=404)

            # Получаем users через related_name
            total_users = department.users.count() if hasattr(department, 'users') else 0

            return Response({
                'department_id': department.id,
                'room_number': department.room_number,
                'total_computers': department.computers_count if hasattr(department,
                                                                         'computers_count') else department.computers.count(),
                'total_users': total_users,
                'computers_per_employee': round(department.computers_count / department.employee_count, 2)
                if hasattr(department, 'computers_count') and department.employee_count > 0
                else 0,
                'is_under_equipped': (department.computers_count / department.employee_count) < 0.5
                if hasattr(department, 'computers_count') and department.employee_count > 0
                else True,
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
