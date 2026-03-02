from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from network_api.models import HostComputer
from network_api.serializers import HostComputerSerializer
from network_api.mixins import ExportMixin

class HostComputerFilter(django_filters.FilterSet):
    """Фильтры для хост-компьютеров"""
    hostname = django_filters.CharFilter(field_name='hostname', lookup_expr='icontains')
    ip_address = django_filters.CharFilter(field_name='ip_address', lookup_expr='icontains')
    mac_address = django_filters.CharFilter(field_name='mac_address', lookup_expr='icontains')
    department = django_filters.NumberFilter(field_name='department__id')
    department_room = django_filters.NumberFilter(field_name='department__room_number')
    has_department = django_filters.BooleanFilter(field_name='department', lookup_expr='isnull', exclude=True)
    search = django_filters.CharFilter(method='filter_search', required=False)

    class Meta:
        model = HostComputer
        fields = ['hostname', 'ip_address', 'mac_address', 'department']

    def filter_search(self, queryset, name, value):
        """Универсальный поиск"""
        if value:
            return queryset.filter(
                Q(hostname__icontains=value) |
                Q(ip_address__icontains=value) |
                Q(mac_address__icontains=value) |
                Q(department__room_number__icontains=value)
            )
        return queryset


class HostComputerViewSet(ExportMixin, viewsets.ModelViewSet):
    """ViewSet для хост-компьютеров"""
    queryset = HostComputer.objects.select_related('department').order_by('hostname')
    serializer_class = HostComputerSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = HostComputerFilter

    def list(self, request, *args, **kwargs):
        """Список хост-компьютеров (без пагинации для UI)"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Детальная информация о хост-компьютере"""
        host = self.get_object()
        serializer = self.get_serializer(host)

        data = serializer.data

        # Добавляем дополнительную информацию
        if host.department:
            data['department_details'] = {
                'room_number': host.department.room_number,
                'internal_phone': host.department.internal_phone,
                'employee_count': host.department.employee_count
            }

        return Response(data)

    @action(detail=False, methods=['get'])
    def unassigned(self, request):
        """Хост-компьютеры без привязки к отделу"""
        queryset = self.get_queryset().filter(department__isnull=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)