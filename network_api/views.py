from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F, Q, Avg, Count
from .models import Department, Computer, User, Network, Software, Equipment
from .serializers import (
    DepartmentSerializer,
    UserSerializer,
    ComputerSerializer,
    SoftwareSerializer,
    NetworkSerializer, EquipmentSerializer
)

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    def get_queryset(self):
        return Department.objects.select_related('host_computer').prefetch_related('computers')

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        department = self.get_object()
        departments_with_stats = Department.objects.filter(id=pk).annotate(
            total_computers=Count('computers'),
            total_users=Count('users'),
            computers_per_employee=Count('computers') / F('employee_count')
        )

        stats = departments_with_stats.first()

        return Response({
            'department_id': department.id,
            'room_number': department.room_number,
            'total_computers': stats.total_computers,
            'total_users': stats.total_users,
            'computers_per_employee': round(stats.computers_per_employee, 2),
            'is_under_equipped': stats.computers_per_employee < 0.5,
        })

class ComputerViewSet(viewsets.ModelViewSet):
    queryset = Computer.objects.all()
    serializer_class = ComputerSerializer

    def get_queryset(self):
        queryset = Computer.objects.select_related('department').prefetch_related('users', 'software')

        search = self.request.query_params.get('search')
        department_id = self.request.query_params.get('department')
        os_filter = self.request.query_params.get('os_filter')
        min_speed = self.request.query_params.get('min_speed')

        filters = Q()

        if search:
            filters |= Q(model__icontains=search) | Q(serial_number__icontains=search)

        if department_id:
            filters &= Q(department_id=department_id)

        if os_filter:
            filters &= Q(os__icontains=os_filter)

        if filters:
            queryset = queryset.filter(filters)

        return queryset

    @action(detail=False, methods=['get'])
    def report(self, request):
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

    @action(detail=False, methods=['get'])
    def network_stats(self, request):
        computers = Computer.objects.filter(
            network_computer_set__isnull=False
        ).select_related('department').prefetch_related('network_computer_set')

        result = []
        for computer in computers:
            network_conn = computer.network_computer_set.first()
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

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        return User.objects.select_related('department').prefetch_related('computers')

    @action(detail=False, methods=['get'])
    def managers(self, request):
        managers = self.get_queryset().filter(position_id__in=[1,2])
        serializer = self.get_serializer(managers, many=True)
        return Response({
            'count': managers.count(),
            'managers': serializer.data
        })

    @action(detail=False, methods=['get'])
    def non_manager(self, request):
        non_managers = self.get_queryset().exclude(position_id__in=[1,2])
        serializer = self.get_serializer(non_managers, many=True)
        return Response({
            'count': non_managers.count(),
            'non_managers': serializer.data
        })

    @action(detail=True, methods=['get'])
    def computer_history(self, request, pk=None):
        user = self.get_object()

        user_computers = user.computers.all().values(
            'id', 'model', 'os', 'serial_number'
        )
        return Response({
            'user': user.full_name,
            'total_computers': user_computers.count(),
            'computers': list(user_computers),
        })

class SoftwareViewSet(viewsets.ModelViewSet):
    queryset = Software.objects.all()
    serializer_class = SoftwareSerializer

    def get_queryset(self):
        return Software.objects.prefetch_related('computers')

    @action(detail=False, methods=['get'])
    def popularity_report(self, request):
        popular_software = Software.objects.annotate(
            installation_count=Count('computers'),
            unique_departments=Count('computers__department', distinct=True),
        ).order_by('-installation_count')

        serializer = self.get_serializer(popular_software, many=True)

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def compatible_computers(self, request, pk=None):
        software = self.get_object()

        comp_computers = software.computers.select_related('department').values(
        'id', 'model', 'os', 'department__room_number'
        )

        return Response({
            'software': f"{software.name} {software.version}",
            'compatible_computers_count': comp_computers.count(),
            'compatible_computers': list(comp_computers)
        })

class NetworkReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Network.objects.select_related('equipment').prefetch_related('networkcomputer_set__computer')
    serializer_class = NetworkSerializer

class EquipmentViewSet(viewsets.ViewSet):
    def list(self, request):
        equipment = Equipment.objects.all()
        serializer = EquipmentSerializer(equipment, many=True)
        return Response({
            'count': len(serializer.data),
            'equipment': serializer.data,
        })

    def retrieve(self, request, pk=None):
        try:
            equipment = Equipment.objects.get(pk=pk)
            serializer = EquipmentSerializer(equipment)
            return Response(serializer.data)
        except Equipment.DoesNotExist:
            return Response(
            {'error': 'Оборудование не найдено'},
            status=status.HTTP_404_NOT_FOUND
            )