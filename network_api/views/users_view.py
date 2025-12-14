from network_api.mixins import ExportMixin
from network_api.models import User
from network_api.serializers import UserSerializer


from django.db.models import Count, F, Q, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

class UserViewSet(ExportMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'position_id']
    search_fields = ['full_name', 'email', 'phone']

    def get_queryset(self):
        queryset = User.objects.select_related('department').prefetch_related('computers')

        # Применяем кастомные фильтры из параметров запроса
        search = self.request.query_params.get('search')
        department_id = self.request.query_params.get('department')
        position_id = self.request.query_params.get('position_id')

        filters = Q()
        has_filters = False

        if search:
            filters |= Q(full_name__icontains=search) | Q(email__icontains=search) | Q(phone__icontains=search)
            has_filters = True

        if department_id:
            filters &= Q(department_id=department_id)
            has_filters = True

        if position_id:
            filters &= Q(position_id=position_id)
            has_filters = True

        if has_filters:
            queryset = queryset.filter(filters)

        return queryset

    def create(self, request, *args, **kwargs):
        print(f"User create request: {request.data}")

        # Проверка обязательных полей
        required_fields = ['full_name', 'email', 'phone', 'position_id']
        for field in required_fields:
            if field not in request.data:
                return Response(
                    {'error': f'Missing required field: {field}'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Проверка уникальности email
        email = request.data.get('email')
        if email and User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Пользователь с таким email уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except Exception as e:
            print(f"Error creating user: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        email = request.data.get('email')

        # Проверка уникальности email при обновлении
        if email and email != instance.email:
            if User.objects.filter(email=email).exists():
                return Response(
                    {'error': 'Пользователь с таким email уже существует'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return super().update(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def managers(self, request):
        managers = self.get_queryset().filter(position_id__in=[1, 2])
        serializer = self.get_serializer(managers, many=True)
        return Response({
            'count': managers.count(),
            'managers': serializer.data
        })

    @action(detail=False, methods=['get'])
    def non_manager(self, request):
        non_managers = self.get_queryset().exclude(position_id__in=[1, 2])
        serializer = self.get_serializer(non_managers, many=True)
        return Response({
            'count': non_managers.count(),
            'non_managers': serializer.data
        })

    @action(detail=True, methods=['get'])
    def computer_history(self, request, pk=None):
        try:
            user = self.get_object()

            user_computers = user.computers.all().values(
                'id', 'model', 'os', 'serial_number'
            )
            return Response({
                'user': user.full_name,
                'total_computers': user_computers.count(),
                'computers': list(user_computers),
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика по пользователям"""
        stats = {
            'total': User.objects.count(),
            'by_position': list(User.objects.values('position_id').annotate(count=Count('id'))),
            'by_department': list(User.objects.values('department__room_number').annotate(count=Count('id'))),
            'with_computers': User.objects.filter(computers__isnull=False).count(),
            'without_computers': User.objects.filter(computers__isnull=True).count(),
        }
        return Response(stats)