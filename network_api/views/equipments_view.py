from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from network_api.models import Equipment
from network_api.serializers import (
    EquipmentSerializer, NetworkSerializer
)
from network_api.mixins import ExportMixin

class EquipmentFilter(django_filters.FilterSet):
    """Фильтры для оборудования"""
    type = django_filters.CharFilter(field_name='type', lookup_expr='icontains')
    min_ports = django_filters.NumberFilter(field_name='port_count', lookup_expr='gte')
    max_ports = django_filters.NumberFilter(field_name='port_count', lookup_expr='lte')
    bandwidth_min = django_filters.NumberFilter(field_name='bandwidth', lookup_expr='gte')
    bandwidth_max = django_filters.NumberFilter(field_name='bandwidth', lookup_expr='lte')
    setup_date_after = django_filters.DateFilter(field_name='setup_date', lookup_expr='gte')
    setup_date_before = django_filters.DateFilter(field_name='setup_date', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search', required=False)

    class Meta:
        model = Equipment
        fields = ['type', 'port_count', 'bandwidth', 'setup_date']

    def filter_search(self, queryset, name, value):
        """Универсальный поиск"""
        if value:
            return queryset.filter(
                Q(type__icontains=value) |
                Q(bandwidth__icontains=value)
            )
        return queryset


class EquipmentViewSet(ExportMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet для оборудования"""
    queryset = Equipment.objects.prefetch_related('networks').order_by('type')
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EquipmentFilter

    def get_queryset(self):
        """Добавляем количество сетей"""
        return super().get_queryset().annotate(
            networks_count=Count('networks', distinct=True)
        )

    def list(self, request, *args, **kwargs):
        """Список оборудования (без пагинации для UI)"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'equipment': serializer.data,
        })

    @action(detail=True, methods=['get'])
    def networks(self, request, pk=None):
        """Получить все сети для оборудования"""
        equipment = self.get_object()
        networks = equipment.networks.all()
        serializer = NetworkSerializer(networks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по оборудованию"""
        stats = Equipment.objects.aggregate(
            total_equipment=Count('id'),
            average_ports=Count('port_count'),
            max_ports=Count('port_count'),
            min_ports=Count('port_count'),
            types_count=Count('type', distinct=True)
        )

        # Распределение по типам
        type_distribution = list(
            Equipment.objects.values('type')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        stats['type_distribution'] = type_distribution

        return Response(stats)