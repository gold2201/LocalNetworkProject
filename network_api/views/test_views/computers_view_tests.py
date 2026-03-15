from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.db.models import Q

from network_api.models import Computer, Department, NetworkComputer, Software
from network_api.views import ComputerViewSet


class ComputerViewSetTestCase(APITestCase):
    """Тесты для ComputerViewSet"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем тестового пользователя для аутентификации
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Создаем тестовый отдел
        self.department = Department.objects.create(
            room_number='101',
            name='IT Department'
        )
        
        # Создаем тестовые компьютеры
        self.computer1 = Computer.objects.create(
            model='Dell Optiplex',
            os='Windows 10',
            serial_number='SN12345',
            inventory_number='INV001',
            department=self.department
        )
        
        self.computer2 = Computer.objects.create(
            model='MacBook Pro',
            os='macOS',
            serial_number='SN67890',
            inventory_number='INV002',
            department=self.department
        )
        
        # Создаем сетевое подключение для computer1
        self.network_computer = NetworkComputer.objects.create(
            computer=self.computer1,
            ip_address='192.168.1.100',
            mac_address='00:11:22:33:44:55',
            speed=1000
        )
        
        # Создаем программное обеспечение
        self.software = Software.objects.create(
            name='Test Software',
            version='1.0',
            vendor='Test Vendor'
        )
        self.computer1.software.add(self.software)
        
        # URL для API
        self.computers_url = reverse('computer-list')
        
    def authenticate(self):
        """Вспомогательный метод для аутентификации"""
        self.client.force_authenticate(user=self.user)
    
    # Тесты для базовых CRUD операций
    
    def test_list_computers(self):
        """Тест получения списка компьютеров"""
        self.authenticate()
        response = self.client.get(self.computers_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_retrieve_computer(self):
        """Тест получения конкретного компьютера"""
        self.authenticate()
        url = reverse('computer-detail', args=[self.computer1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['model'], 'Dell Optiplex')
        self.assertEqual(response.data['serial_number'], 'SN12345')
    
    def test_create_computer_success(self):
        """Тест успешного создания компьютера"""
        self.authenticate()
        data = {
            'model': 'HP EliteBook',
            'os': 'Windows 11',
            'serial_number': 'SN99999',
            'inventory_number': 'INV003',
            'department': self.department.id
        }
        
        response = self.client.post(self.computers_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Computer.objects.count(), 3)
        
    def test_create_computer_duplicate_serial(self):
        """Тест создания компьютера с существующим серийным номером"""
        self.authenticate()
        data = {
            'model': 'HP EliteBook',
            'os': 'Windows 11',
            'serial_number': 'SN12345',  # Уже существует
            'inventory_number': 'INV003',
            'department': self.department.id
        }
        
        response = self.client.post(self.computers_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(
            response.data['error'], 
            'Компьютер с таким серийным номером уже существует'
        )
    
    def test_update_computer_success(self):
        """Тест успешного обновления компьютера"""
        self.authenticate()
        url = reverse('computer-detail', args=[self.computer1.id])
        data = {
            'model': 'Updated Model',
            'os': 'Windows 11',
            'serial_number': 'SN12345',  # Оставляем тот же
            'inventory_number': 'INV001-UPD',
            'department': self.department.id
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.computer1.refresh_from_db()
        self.assertEqual(self.computer1.model, 'Updated Model')
        self.assertEqual(self.computer1.inventory_number, 'INV001-UPD')
    
    def test_update_computer_duplicate_serial(self):
        """Тест обновления с серийным номером, который уже используется"""
        self.authenticate()
        url = reverse('computer-detail', args=[self.computer1.id])
        data = {
            'model': 'Updated Model',
            'os': 'Windows 11',
            'serial_number': 'SN67890',  # Серийный номер computer2
            'inventory_number': 'INV001',
            'department': self.department.id
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_delete_computer(self):
        """Тест удаления компьютера"""
        self.authenticate()
        url = reverse('computer-detail', args=[self.computer1.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Computer.objects.count(), 1)
    
    # Тесты для фильтрации и поиска
    
    def test_filter_by_os(self):
        """Тест фильтрации по операционной системе"""
        self.authenticate()
        response = self.client.get(self.computers_url, {'os': 'Windows 10'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['os'], 'Windows 10')
    
    def test_filter_by_department(self):
        """Тест фильтрации по отделу"""
        self.authenticate()
        response = self.client.get(self.computers_url, {'department': self.department.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_search_by_model(self):
        """Тест поиска по модели"""
        self.authenticate()
        response = self.client.get(self.computers_url, {'search': 'Dell'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['model'], 'Dell Optiplex')
    
    def test_search_by_serial(self):
        """Тест поиска по серийному номеру"""
        self.authenticate()
        response = self.client.get(self.computers_url, {'search': '12345'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['serial_number'], 'SN12345')
    
    def test_combined_filters(self):
        """Тест комбинации нескольких фильтров"""
        self.authenticate()
        response = self.client.get(
            self.computers_url, 
            {'os_filter': 'Windows', 'search': 'Dell'}
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    # Тесты для кастомных action методов
    
    def test_report_action(self):
        """Тест получения отчета"""
        self.authenticate()
        url = reverse('computer-report')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('by_os_and_department', response.data)
        self.assertIn('by_department', response.data)
        
        # Проверяем структуру отчета
        dept_report = response.data['by_department']
        self.assertEqual(len(dept_report), 1)
        self.assertEqual(dept_report[0]['department__room_number'], '101')
        self.assertEqual(dept_report[0]['total_computers'], 2)
    
    def test_network_stats_action(self):
        """Тест получения сетевой статистики"""
        self.authenticate()
        url = reverse('computer-network-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['ip_address'], '192.168.1.100')
        self.assertEqual(response.data[0]['network_speed'], 1000)
    
    def test_details_action(self):
        """Тест получения детальной информации о компьютере"""
        self.authenticate()
        url = reverse('computer-details', args=[self.computer1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.computer1.id)
        self.assertIn('users', response.data)
        self.assertIn('software', response.data)
        self.assertIn('network_connections', response.data)
        
        # Проверяем, что связанные данные загружены
        self.assertEqual(len(response.data['software']), 1)
        self.assertEqual(len(response.data['network_connections']), 1)
    
    def test_details_action_not_found(self):
        """Тест получения деталей несуществующего компьютера"""
        self.authenticate()
        url = reverse('computer-details', args=[999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Computer not found')
    
    # Тесты для ExportMixin
    
    def test_apply_export_filters(self):
        """Тест применения фильтров при экспорте"""
        viewset = ComputerViewSet()
        request = MagicMock()
        request.GET = {'os': 'Windows', 'department_id': str(self.department.id)}
        
        queryset = Computer.objects.all()
        filtered_queryset = viewset.apply_export_filters(queryset, request)
        
        self.assertEqual(filtered_queryset.count(), 1)
        self.assertEqual(filtered_queryset.first().os, 'Windows 10')
    
    # Тесты для проверки прав доступа и аутентификации
    
    def test_unauthenticated_access(self):
        """Тест доступа без аутентификации"""
        response = self.client.get(self.computers_url)
        # Предполагаем, что API требует аутентификации
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # Тесты для проверки производительности запросов
    
    def test_queryset_optimization(self):
        """Тест оптимизации запросов (select_related/prefetch_related)"""
        self.authenticate()
        viewset = ComputerViewSet()
        viewset.request = self.client.get('/').wsgi_request
        viewset.request.user = self.user
        viewset.action = 'list'
        
        queryset = viewset.get_queryset()
        
        # Проверяем, что queryset содержит правильные оптимизации
        self.assertTrue(hasattr(queryset, '_prefetch_related_lookups'))
        prefetch_lookups = [lookup.prefetch_through for lookup in queryset._prefetch_related_lookups]
        self.assertIn('users', prefetch_lookups)
        self.assertIn('software', prefetch_lookups)
    
    # Тесты для обработки ошибок
    
    @patch('network_api.models.Computer.objects.filter')
    def test_report_action_error_handling(self, mock_filter):
        """Тест обработки ошибок в report action"""
        mock_filter.side_effect = Exception("Database error")
        
        self.authenticate()
        url = reverse('computer-report')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)


class ComputerViewSetUnitTests(TestCase):
    """Модульные тесты для отдельных методов ComputerViewSet"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ComputerViewSet
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.department = Department.objects.create(
            room_number='101',
            name='IT Department'
        )
        
        self.computer = Computer.objects.create(
            model='Test Model',
            os='Windows',
            serial_number='SN-TEST',
            inventory_number='INV-TEST',
            department=self.department
        )
    
    def test_get_queryset_with_filters(self):
        """Тест метода get_queryset с разными фильтрами"""
        # Тест с поиском
        request = self.factory.get('/', {'search': 'Test'})
        request.user = self.user
        view = self.view()
        view.request = request
        view.action = 'list'
        
        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)
        
        # Тест с фильтром по отделу
        request = self.factory.get('/', {'department': self.department.id})
        request.user = self.user
        view.request = request
        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)
        
        # Тест с фильтром по ОС
        request = self.factory.get('/', {'os_filter': 'Windows'})
        request.user = self.user
        view.request = request
        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)
    
    def test_create_method_validation(self):
        """Тест валидации в методе create"""
        # Создаем компьютер с существующим серийным номером
        request = self.factory.post('/', {
            'model': 'New Model',
            'serial_number': 'SN-TEST'  # Уже существует
        })
        request.user = self.user
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        
        # Мокаем get_serializer для возврата данных
        with patch.object(view, 'get_serializer', return_value=MagicMock()):
            response = view.create(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_method_validation(self):
        """Тест валидации в методе update"""
        # Создаем еще один компьютер для проверки конфликта
        other_computer = Computer.objects.create(
            model='Other Model',
            os='Linux',
            serial_number='SN-OTHER',
            inventory_number='INV-OTHER'
        )
        
        request = self.factory.put('/', {
            'serial_number': 'SN-OTHER'  # Серийный номер другого компьютера
        })
        request.user = self.user
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        view.kwargs = {'pk': self.computer.pk}
        
        # Мокаем get_object для возврата нашего компьютера
        with patch.object(view, 'get_object', return_value=self.computer):
            response = view.update(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ComputerViewSetIntegrationTests(TestCase):
    """Интеграционные тесты для ComputerViewSet"""
    
    def setUp(self):
        self.client = APITestClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Создаем связанные объекты
        self.department1 = Department.objects.create(room_number='101', name='IT')
        self.department2 = Department.objects.create(room_number='102', name='HR')
        
        self.computers = []
        for i in range(5):
            computer = Computer.objects.create(
                model=f'Model {i}',
                os='Windows' if i % 2 == 0 else 'Linux',
                serial_number=f'SN{i:03d}',
                inventory_number=f'INV{i:03d}',
                department=self.department1 if i < 3 else self.department2
            )
            self.computers.append(computer)
    
    def test_complex_filtering_scenarios(self):
        """Тест сложных сценариев фильтрации"""
        # Фильтр по ОС и отделу
        response = self.client.get('/api/computers/', {
            'os_filter': 'Windows',
            'department': self.department1.id
        })
        
        self.assertEqual(response.status_code, 200)
        # Должны получить только Windows компьютеры из department1
        windows_count = sum(1 for c in self.computers[:3] if 'Windows' in c.os)
        self.assertEqual(len(response.data), windows_count)
    
    def test_report_with_multiple_departments(self):
        """Тест отчета с несколькими отделами"""
        response = self.client.get('/api/computers/report/')
        
        self.assertEqual(response.status_code, 200)
        by_department = response.data['by_department']
        self.assertEqual(len(by_department), 2)  # Два отдела
        
        # Проверяем статистику по отделам
        dept_101_report = next(
            (d for d in by_department if d['department__room_number'] == '101'), 
            None
        )
        self.assertIsNotNone(dept_101_report)
        self.assertEqual(dept_101_report['total_computers'], 3)