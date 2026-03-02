# networks_view.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg, Max, Min
from network_api.models import Network, NetworkComputer
from network_api.serializers import NetworkSerializer, NetworkComputerSerializer
from network_api.mixins import ExportMixin


class NetworkFilter(django_filters.FilterSet):
    """Фильтры для сетей"""
    vlan = django_filters.NumberFilter(field_name='vlan')
    ip_range = django_filters.CharFilter(field_name='ip_range', lookup_expr='icontains')
    equipment_type = django_filters.CharFilter(field_name='equipment__type', lookup_expr='icontains')
    has_computers = django_filters.BooleanFilter(method='filter_has_computers')
    search = django_filters.CharFilter(method='filter_search', required=False)

    class Meta:
        model = Network
        fields = ['vlan', 'ip_range', 'equipment']

    def filter_has_computers(self, queryset, name, value):
        """Фильтр по наличию подключенных компьютеров"""
        if value is True:
            return queryset.filter(networkcomputer_set__isnull=False).distinct()
        elif value is False:
            return queryset.filter(networkcomputer_set__isnull=True).distinct()
        return queryset

    def filter_search(self, queryset, name, value):
        """Универсальный поиск по нескольким полям"""
        if value:
            return queryset.filter(
                Q(vlan__icontains=value) |
                Q(ip_range__icontains=value) |
                Q(subnet_mask__icontains=value) |
                Q(equipment__type__icontains=value)
            )
        return queryset


class NetworkReadOnlyViewSet(ExportMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для чтения сетевых подключений.
    Пагинация реализована на стороне UI.
    """
    queryset = Network.objects.select_related('equipment').prefetch_related(
        'networkcomputer_set__computer'
    ).order_by('vlan')

    serializer_class = NetworkSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = NetworkFilter

    def list(self, request, *args, **kwargs):
        """
        Переопределяем list, чтобы отключить пагинацию по умолчанию
        и возвращать все данные для клиентской пагинации.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Отключаем пагинацию - возвращаем все данные
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получение статистики по сетям"""
        stats = Network.objects.aggregate(
            total_networks=Count('id'),
            average_vlan=Avg('vlan'),
            max_vlan=Max('vlan'),
            min_vlan=Min('vlan'),
            networks_with_equipment=Count('equipment', distinct=True),
            total_computers_connected=Count('networkcomputer_set', distinct=True)
        )

        # Распределение по VLAN для статистики
        vlan_distribution = list(
            Network.objects.values('vlan')
            .annotate(count=Count('id'))
            .order_by('vlan')[:10]
        )
        stats['vlan_distribution'] = vlan_distribution

        return Response(stats)

    @action(detail=True, methods=['get'])
    def computers(self, request, pk=None):
        """Получить все компьютеры в сети (без пагинации)"""
        network = self.get_object()
        network_computers = NetworkComputer.objects.filter(
            network=network
        ).select_related('computer')

        serializer = NetworkComputerSerializer(network_computers, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Детальная информация о сети"""
        network = self.get_object()
        serializer = self.get_serializer(network)

        data = serializer.data
        data['connected_computers_count'] = network.networkcomputer_set.count()

        # Информация об оборудовании
        if network.equipment:
            data['equipment_info'] = {
                'type': network.equipment.type,
                'bandwidth': network.equipment.bandwidth,
                'port_count': network.equipment.port_count,
                'setup_date': network.equipment.setup_date.strftime('%d.%m.%Y')
            }
        else:
            data['equipment_info'] = None

        # Последние 5 компьютеров
        recent_computers = network.networkcomputer_set.select_related(
            'computer'
        ).order_by('-id')[:5]

        data['recent_computers'] = [
            {
                'id': nc.computer.id,
                'model': nc.computer.model,
                'serial_number': nc.computer.serial_number,
                'ip_address': nc.ip_address,
                'speed': nc.speed
            }
            for nc in recent_computers
        ]

        return Response(data)