from django.db.models import Avg
from network_api.mixins import ExportMixin
from network_api.models import Computer
from network_api.serializers import ComputerSerializer

from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

class ComputerViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Computer.objects.all()
    serializer_class = ComputerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'os']
    search_fields = ['model', 'serial_number', 'inventory_number']

    def get_queryset(self):
        queryset = Computer.objects.select_related('department').prefetch_related(
            'users', 'software', 'networkcomputer_set'
        )

        # Применяем кастомные фильтры
        search = self.request.query_params.get('search')
        department_id = self.request.query_params.get('department')
        os_filter = self.request.query_params.get('os_filter')

        filters = Q()
        has_filters = False

        if search:
            filters |= Q(model__icontains=search) | Q(serial_number__icontains=search)
            has_filters = True

        if department_id:
            filters &= Q(department_id=department_id)
            has_filters = True

        if os_filter:
            filters &= Q(os__icontains=os_filter)
            has_filters = True

        if has_filters:
            queryset = queryset.filter(filters)

        return queryset

    def create(self, request, *args, **kwargs):
        # Проверка уникальности serial_number
        serial_number = request.data.get('serial_number')
        if serial_number and Computer.objects.filter(serial_number=serial_number).exists():
            return Response(
                {'error': 'Компьютер с таким серийным номером уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serial_number = request.data.get('serial_number')

        if serial_number and serial_number != instance.serial_number:
            if Computer.objects.filter(serial_number=serial_number).exists():
                return Response(
                    {'error': 'Компьютер с таким серийным номером уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def report(self, request):
        try:
            os_report = Computer.objects.values(
                'os',
                'department__room_number'
            ).annotate(
                computer_count=Count('id'),
                avg_inventory=Avg('inventory_number')
            ).order_by('os', 'department__room_number')

            department_report = Computer.objects.values(
                'department__room_number',
            ).annotate(
                total_computers=Count('id'),
                windows_count=Count('id', filter=Q(os__icontains='windows')),
                linux_count=Count('id', filter=Q(os__icontains='linux')),
            ).order_by('department__room_number')

            return Response({
                'by_os_and_department': list(os_report),
                'by_department': list(department_report),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def network_stats(self, request):
        try:
            computers = Computer.objects.filter(
                networkcomputer_set__isnull=False
            ).select_related('department').prefetch_related('networkcomputer_set')

            result = []
            for computer in computers:
                network_conn = computer.networkcomputer_set.first()
                if network_conn:
                    result.append({
                        'id': computer.id,
                        'model': computer.model,
                        'os': computer.os,
                        'department_room': computer.department.room_number if computer.department else None,
                        'network_speed': network_conn.speed,
                        'ip_address': network_conn.ip_address
                    })

            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def apply_export_filters(self, queryset, request):
        """Применяем специфичные для Computer фильтры"""
        queryset = super().apply_export_filters(queryset, request)

        # Добавляем фильтры из параметров запроса
        os_filter = request.GET.get('os')
        department_id = request.GET.get('department_id')

        if os_filter:
            queryset = queryset.filter(os__icontains=os_filter)
        if department_id:
            queryset = queryset.filter(department_id=department_id)

        return queryset

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Детальная информация о компьютере"""
        try:
            computer = self.get_queryset().get(pk=pk)

            data = {
                'id': computer.id,
                'model': computer.model,
                'os': computer.os,
                'serial_number': computer.serial_number,
                'inventory_number': computer.inventory_number,
                'department': {
                    'id': computer.department.id if computer.department else None,
                    'room_number': computer.department.room_number if computer.department else None
                },
                'users': list(computer.users.values('id', 'full_name', 'email')),
                'software': list(computer.software.values('id', 'name', 'version')),
                'network_connections': list(computer.networkcomputer_set.values(
                    'id', 'ip_address', 'mac_address', 'speed'
                ))
            }

            return Response(data)
        except Computer.DoesNotExist:
            return Response({'error': 'Computer not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
