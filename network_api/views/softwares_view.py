from network_api.mixins import ExportMixin
from network_api.models import Software
from network_api.serializers import SoftwareSerializer

from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

class SoftwareViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = Software.objects.all()
    serializer_class = SoftwareSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['vendor', 'license']
    search_fields = ['name', 'version', 'vendor', 'license']

    def get_queryset(self):
        queryset = Software.objects.prefetch_related('computers')

        # Применяем кастомные фильтры
        search = self.request.query_params.get('search')
        license_type = self.request.query_params.get('license_type')

        filters = Q()
        has_filters = False

        if search:
            filters |= Q(name__icontains=search) | Q(vendor__icontains=search) | Q(license__icontains=search)
            has_filters = True

        if license_type:
            if license_type == 'trial':
                filters &= Q(license__icontains='trial')
            elif license_type == 'commercial':
                filters &= Q(license__icontains='commercial') | Q(license__icontains='paid')
            elif license_type == 'free':
                filters &= Q(license__icontains='free') | Q(license__icontains='open source')
            has_filters = True

        if has_filters:
            queryset = queryset.filter(filters)

        return queryset

    def create(self, request, *args, **kwargs):
        print(f"Software create request: {request.data}")

        # Проверка обязательных полей
        required_fields = ['name', 'version', 'vendor', 'license']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Проверка уникальности name+version
        name = request.data.get('name')
        version = request.data.get('version')
        if name and version:
            if Software.objects.filter(name=name, version=version).exists():
                return Response(
                    {'error': 'ПО с таким названием и версией уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            print(f"Error creating software: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        name = request.data.get('name')
        version = request.data.get('version')

        # Проверка уникальности name+version при обновлении
        if name and version:
            if name != instance.name or version != instance.version:
                if Software.objects.filter(name=name, version=version).exists():
                    return Response(
                        {'error': 'ПО с таким названием и версией уже существует'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def popularity_report(self, request):
        try:
            popular_software = Software.objects.annotate(
                installation_count=Count('computers'),
                unique_departments=Count('computers__department', distinct=True),
            ).order_by('-installation_count')

            serializer = self.get_serializer(popular_software, many=True)

            return Response({
                'count': popular_software.count(),
                'software': serializer.data,
                'total_installations': sum(item['installed_count'] for item in serializer.data)
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def compatible_computers(self, request, pk=None):
        try:
            software = self.get_object()

            comp_computers = software.computers.select_related('department').values(
                'id', 'model', 'os', 'department__room_number'
            )

            return Response({
                'software': f"{software.name} {software.version}",
                'vendor': software.vendor,
                'license': software.license,
                'compatible_computers_count': comp_computers.count(),
                'compatible_computers': list(comp_computers)
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def license_summary(self, request):
        """Сводка по лицензиям"""
        try:
            license_stats = Software.objects.values('license').annotate(
                count=Count('id'),
                total_installations=Count('computers')
            ).order_by('-count')

            return Response({
                'license_summary': list(license_stats),
                'total_software': Software.objects.count(),
                'total_installations': Software.objects.aggregate(total=Count('computers'))['total']
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)