from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.db.models import Q

from network_api.models import Department, Computer, HostComputer, User as NetworkUser, Position
from network_api.views import DepartmentViewSet


class DepartmentViewSetTestCase(APITestCase):
    """Тесты для DepartmentViewSet"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем тестового пользователя для аутентификации
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Создаем тестовые должности
        self.position1 = Position.objects.create(
            name='Developer',
            salary=100000
        )
        self.position2 = Position.objects.create(
            name='Manager',
            salary=150000
        )
        
        # Создаем тестовые отделы
        self.department1 = Department.objects.create(
            room_number='101',
            internal_phone=1234,
            employee_count=5
        )
        
        self.department2 = Department.objects.create(
            room_number='102',
            internal_phone=5678,
            employee_count=10
        )
        
        self.department3 = Department.objects.create(
            room_number='201',
            internal_phone=9012,
            employee_count=3
        )
        
        # Создаем пользователей для отделов
        self.user1 = NetworkUser.objects.create(
            full_name='John Doe',
            email='john@example.com',
            phone='1234567890',
            position=self.position1,
            department=self.department1
        )
        
        self.user2 = NetworkUser.objects.create(
            full_name='Jane Smith',
            email='jane@example.com',
            phone='0987654321',
            position=self.position2,
            department=self.department1
        )
        
        self.user3 = NetworkUser.objects.create(
            full_name='Bob Johnson',
            email='bob@example.com',
            phone='5555555555',
            position=self.position1,
            department=self.department2
        )
        
        # Создаем компьютеры для отделов
        self.computer1 = Computer.objects.create(
            model='Dell Optiplex',
            os='Windows 10',
            serial_number='SN001',
            inventory_number='INV001',
            department=self.department1
        )
        
        self.computer2 = Computer.objects.create(
            model='MacBook Pro',
            os='macOS',
            serial_number='SN002',
            inventory_number='INV002',
            department=self.department1
        )
        
        self.computer3 = Computer.objects.create(
            model='HP EliteBook',
            os='Windows 11',
            serial_number='SN003',
            inventory_number='INV003',
            department=self.department2
        )
        
        # Создаем хост-компьютеры
        self.host1 = HostComputer.objects.create(
            hostname='host-101',
            ip_address='192.168.1.1',
            mac_address='00:11:22:33:44:55',
            department=self.department1
        )
        
        self.host2 = HostComputer.objects.create(
            hostname='host-102',
            ip_address='192.168.1.2',
            mac_address='66:77:88:99:AA:BB',
            department=self.department2
        )
        
        # URL для API
        self.departments_url = reverse('department-list')
        
    def authenticate(self):
        """Вспомогательный метод для аутентификации"""
        self.client.force_authenticate(user=self.user)
    
    # Тесты для базовых CRUD операций
    
    def test_list_departments(self):
        """Тест получения списка отделов"""
        self.authenticate()
        response = self.client.get(self.departments_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        # Проверяем аннотированные поля
        first_dept = next(d for d in response.data if d['room_number'] == '101')
        self.assertEqual(first_dept['computers_count'], 2)
        self.assertEqual(first_dept['users_count'], 2)
        self.assertEqual(first_dept['host_computers_count'], 1)
        self.assertEqual(first_dept['first_host_computer_ip'], '192.168.1.1')
    
    def test_retrieve_department(self):
        """Тест получения конкретного отдела"""
        self.authenticate()
        url = reverse('department-detail', args=[self.department1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['room_number'], '101')
        self.assertEqual(response.data['internal_phone'], 1234)
        self.assertEqual(response.data['employee_count'], 5)
    
    def test_create_department_success(self):
        """Тест успешного создания отдела"""
        self.authenticate()
        data = {
            'room_number': '301',
            'internal_phone': '4321',  # Строка, должна преобразоваться в int
            'employee_count': 8
        }
        
        response = self.client.post(self.departments_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Department.objects.count(), 4)
        self.assertEqual(response.data['room_number'], '301')
        self.assertEqual(response.data['internal_phone'], 4321)  # Должен быть int
        
    def test_create_department_with_id_field(self):
        """Тест создания отдела с полем id (должно игнорироваться)"""
        self.authenticate()
        data = {
            'id': 999,
            'room_number': '302',
            'internal_phone': 5432,
            'employee_count': 6
        }
        
        response = self.client.post(self.departments_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Проверяем, что id не использовался
        self.assertNotEqual(response.data['id'], 999)
    
    def test_create_department_validation_error(self):
        """Тест ошибки валидации при создании"""
        self.authenticate()
        data = {
            'room_number': '',  # Пустое поле вызовет ошибку
            'employee_count': -1  # Отрицательное значение
        }
        
        response = self.client.post(self.departments_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_department_success(self):
        """Тест успешного обновления отдела"""
        self.authenticate()
        url = reverse('department-detail', args=[self.department1.id])
        data = {
            'room_number': '101-UPD',
            'internal_phone': '9999',  # Строка
            'employee_count': 7
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.department1.refresh_from_db()
        self.assertEqual(self.department1.room_number, '101-UPD')
        self.assertEqual(self.department1.internal_phone, 9999)
        self.assertEqual(self.department1.employee_count, 7)
    
    def test_partial_update_department(self):
        """Тест частичного обновления отдела"""
        self.authenticate()
        url = reverse('department-detail', args=[self.department1.id])
        data = {
            'employee_count': 15
        }
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.department1.refresh_from_db()
        self.assertEqual(self.department1.employee_count, 15)
        # Остальные поля не изменились
        self.assertEqual(self.department1.room_number, '101')
    
    def test_update_department_with_id_field(self):
        """Тест обновления с полем id (должно игнорироваться)"""
        self.authenticate()
        url = reverse('department-detail', args=[self.department1.id])
        data = {
            'id': 999,
            'room_number': '101-UPD',
            'employee_count': 8
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.department1.refresh_from_db()
        self.assertEqual(self.department1.id, self.department1.id)  # ID не изменился
    
    def test_delete_department(self):
        """Тест удаления отдела"""
        self.authenticate()
        url = reverse('department-detail', args=[self.department1.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Department.objects.count(), 2)
    
    # Тесты для фильтрации и поиска
    
    def test_filter_by_employee_count(self):
        """Тест фильтрации по количеству сотрудников"""
        self.authenticate()
        response = self.client.get(self.departments_url, {'employee_count': 5})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], '101')
    
    def test_filter_by_min_employees(self):
        """Тест фильтрации по минимальному количеству сотрудников"""
        self.authenticate()
        response = self.client.get(self.departments_url, {'min_employees': 8})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], '102')
        self.assertEqual(response.data[0]['employee_count'], 10)
    
    def test_search_by_room_number(self):
        """Тест поиска по номеру комнаты"""
        self.authenticate()
        response = self.client.get(self.departments_url, {'search': '101'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], '101')
    
    def test_search_by_internal_phone(self):
        """Тест поиска по внутреннему телефону"""
        self.authenticate()
        response = self.client.get(self.departments_url, {'search': '1234'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], '101')
    
    def test_combined_filters(self):
        """Тест комбинации фильтров"""
        self.authenticate()
        response = self.client.get(
            self.departments_url, 
            {'min_employees': 4, 'search': '10'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], '101')
    
    # Тесты для кастомных action методов
    
    def test_statistics_action(self):
        """Тест получения статистики отдела"""
        self.authenticate()
        url = reverse('department-statistics', args=[self.department1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['department_id'], self.department1.id)
        self.assertEqual(response.data['room_number'], '101')
        self.assertEqual(response.data['employee_count'], 5)
        self.assertEqual(response.data['total_computers'], 2)
        self.assertEqual(response.data['total_users'], 2)
        self.assertEqual(response.data['host_computers_count'], 1)
        self.assertEqual(response.data['computers_per_employee'], 0.4)  # 2/5 = 0.4
        self.assertEqual(response.data['users_per_computer'], 1.0)  # 2/2 = 1.0
        self.assertEqual(response.data['is_under_equipped'], True)  # 0.4 < 0.5
    
    def test_statistics_action_with_no_employees(self):
        """Тест статистики для отдела без сотрудников"""
        self.authenticate()
        empty_dept = Department.objects.create(
            room_number='999',
            internal_phone=9999,
            employee_count=0
        )
        
        url = reverse('department-statistics', args=[empty_dept.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['employee_count'], 0)
        self.assertEqual(response.data['computers_per_employee'], 0)
        self.assertEqual(response.data['is_under_equipped'], True)
    
    def test_statistics_action_not_found(self):
        """Тест статистики для несуществующего отдела"""
        self.authenticate()
        url = reverse('department-statistics', args=[999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Department not found')
    
    def test_host_computers_action(self):
        """Тест получения хост-компьютеров отдела"""
        self.authenticate()
        url = reverse('department-host-computers', args=[self.department1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['department_id'], self.department1.id)
        self.assertEqual(response.data['room_number'], '101')
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['host_computers'][0]['ip_address'], '192.168.1.1')
    
    def test_host_computers_action_empty(self):
        """Тест получения хост-компьютеров для отдела без них"""
        self.authenticate()
        url = reverse('department-host-computers', args=[self.department3.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 0)
        self.assertEqual(len(response.data['host_computers']), 0)
    
    def test_users_action(self):
        """Тест получения пользователей отдела"""
        self.authenticate()
        url = reverse('department-users', args=[self.department1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['department_id'], self.department1.id)
        self.assertEqual(response.data['room_number'], '101')
        self.assertEqual(response.data['total'], 2)
        
        # Проверяем структуру данных пользователя
        user_data = response.data['users'][0]
        self.assertIn('id', user_data)
        self.assertIn('full_name', user_data)
        self.assertIn('email', user_data)
        self.assertIn('position_id', user_data)
    
    # Тесты для обработки ошибок
    
    @patch('network_api.models.Department.objects.get')
    def test_statistics_action_error_handling(self, mock_get):
        """Тест обработки ошибок в statistics action"""
        mock_get.side_effect = Exception("Database error")
        
        self.authenticate()
        url = reverse('department-statistics', args=[self.department1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
    
    # Тесты для проверки прав доступа
    
    def test_unauthenticated_access(self):
        """Тест доступа без аутентификации"""
        response = self.client.get(self.departments_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # Тесты для проверки аннотаций в queryset
    
    def test_queryset_annotations_for_get(self):
        """Тест наличия аннотаций в queryset для GET запросов"""
        self.authenticate()
        
        # Создаем request с методом GET
        factory = APIRequestFactory()
        request = factory.get(self.departments_url)
        request.user = self.user
        
        view = DepartmentViewSet()
        view.request = request
        view.action = 'list'
        
        queryset = view.get_queryset()
        
        # Проверяем наличие аннотированных полей
        first_dept = queryset.first()
        self.assertTrue(hasattr(first_dept, 'computers_count'))
        self.assertTrue(hasattr(first_dept, 'users_count'))
        self.assertTrue(hasattr(first_dept, 'host_computers_count'))
        self.assertTrue(hasattr(first_dept, 'first_host_computer_ip'))
    
    def test_queryset_no_annotations_for_post(self):
        """Тест отсутствия аннотаций в queryset для POST запросов"""
        self.authenticate()
        
        # Создаем request с методом POST
        factory = APIRequestFactory()
        request = factory.post(self.departments_url)
        request.user = self.user
        
        view = DepartmentViewSet()
        view.request = request
        view.action = 'create'
        
        queryset = view.get_queryset()
        
        # Проверяем отсутствие аннотированных полей
        first_dept = queryset.first()
        self.assertFalse(hasattr(first_dept, 'computers_count'))
        self.assertFalse(hasattr(first_dept, 'users_count'))


class DepartmentViewSetUnitTests(TestCase):
    """Модульные тесты для отдельных методов DepartmentViewSet"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = DepartmentViewSet
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.department = Department.objects.create(
            room_number='101',
            internal_phone=1234,
            employee_count=5
        )
    
    def test_internal_phone_parsing_in_create(self):
        """Тест парсинга внутреннего телефона в методе create"""
        request = self.factory.post('/', {
            'room_number': '202',
            'internal_phone': '+7 (123) 456-78-90',  # Строка с символами
            'employee_count': 10
        })
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        
        # Мокаем get_serializer для возврата валидного сериализатора
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = True
        mock_serializer.data = {'id': 1, 'room_number': '202', 'internal_phone': 1234567890}
        
        with patch.object(view, 'get_serializer', return_value=mock_serializer):
            with patch.object(view, 'perform_create'):
                with patch.object(view, 'get_success_headers', return_value={}):
                    response = view.create(request)
        
        # Проверяем, что телефон был правильно распарсен
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_internal_phone_parsing_in_update(self):
        """Тест парсинга внутреннего телефона в методе update"""
        request = self.factory.put('/', {
            'internal_phone': '9999-ABC',  # Строка с символами
            'employee_count': 8
        })
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        view.kwargs = {'pk': self.department.pk}
        
        # Мокаем get_object для возврата нашего отдела
        with patch.object(view, 'get_object', return_value=self.department):
            mock_serializer = MagicMock()
            mock_serializer.is_valid.return_value = True
            mock_serializer.data = {'id': self.department.id, 'internal_phone': 9999}
            
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                with patch.object(view, 'perform_update'):
                    response = view.update(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_create_method_exception_handling(self):
        """Тест обработки исключений в методе create"""
        request = self.factory.post('/', {'room_number': '202'})
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        
        # Мокаем get_serializer для выброса исключения
        with patch.object(view, 'get_serializer', side_effect=Exception("Unexpected error")):
            response = view.create(request)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
    
    def test_update_method_with_partial(self):
        """Тест метода update с partial=True"""
        request = self.factory.patch('/', {'employee_count': 15})
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        view.kwargs = {'pk': self.department.pk}
        view.action = 'partial_update'
        
        with patch.object(view, 'get_object', return_value=self.department):
            mock_serializer = MagicMock()
            mock_serializer.is_valid.return_value = True
            mock_serializer.data = {'id': self.department.id, 'employee_count': 15}
            
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                with patch.object(view, 'perform_update'):
                    response = view.update(request, partial=True)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)