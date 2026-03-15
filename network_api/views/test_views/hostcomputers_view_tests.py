from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.db.models import Q

from network_api.models import HostComputer, Department
from network_api.views import HostComputerViewSet, HostComputerFilter


class HostComputerFilterTestCase(TestCase):
    """Тесты для HostComputerFilter"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
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
        
        # Создаем тестовые хост-компьютеры
        self.host1 = HostComputer.objects.create(
            hostname='server-01',
            ip_address='192.168.1.10',
            mac_address='00:11:22:33:44:55',
            department=self.department1
        )
        
        self.host2 = HostComputer.objects.create(
            hostname='server-02',
            ip_address='192.168.1.20',
            mac_address='66:77:88:99:AA:BB',
            department=self.department1
        )
        
        self.host3 = HostComputer.objects.create(
            hostname='database-01',
            ip_address='10.0.0.50',
            mac_address='AA:BB:CC:DD:EE:FF',
            department=self.department2
        )
        
        self.host4 = HostComputer.objects.create(
            hostname='unassigned-host',
            ip_address='172.16.0.100',
            mac_address='11:22:33:44:55:66',
            department=None
        )
    
    def test_filter_by_hostname_icontains(self):
        """Тест фильтрации по имени хоста (регистронезависимый поиск)"""
        filterset = HostComputerFilter(
            data={'hostname': 'server'},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)
        self.assertTrue(all('server' in host.hostname for host in queryset))
    
    def test_filter_by_ip_address_icontains(self):
        """Тест фильтрации по IP-адресу"""
        filterset = HostComputerFilter(
            data={'ip_address': '192.168'},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)
        self.assertTrue(all('192.168' in host.ip_address for host in queryset))
    
    def test_filter_by_mac_address_icontains(self):
        """Тест фильтрации по MAC-адресу"""
        filterset = HostComputerFilter(
            data={'mac_address': 'AA:BB'},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().mac_address, 'AA:BB:CC:DD:EE:FF')
    
    def test_filter_by_department_id(self):
        """Тест фильтрации по ID отдела"""
        filterset = HostComputerFilter(
            data={'department': self.department1.id},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)
        self.assertTrue(all(host.department_id == self.department1.id for host in queryset))
    
    def test_filter_by_department_room(self):
        """Тест фильтрации по номеру комнаты отдела"""
        filterset = HostComputerFilter(
            data={'department_room': 101},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)
        self.assertTrue(all(host.department.room_number == 101 for host in queryset))
    
    def test_filter_has_department_true(self):
        """Тест фильтрации хостов с отделом"""
        filterset = HostComputerFilter(
            data={'has_department': True},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 3)
        self.assertTrue(all(host.department is not None for host in queryset))
    
    def test_filter_has_department_false(self):
        """Тест фильтрации хостов без отдела"""
        filterset = HostComputerFilter(
            data={'has_department': False},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        self.assertTrue(all(host.department is None for host in queryset))
    
    def test_filter_search_method(self):
        """Тест поискового метода filter_search"""
        # Поиск по hostname
        filterset = HostComputerFilter(
            data={'search': 'database'},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().hostname, 'database-01')
        
        # Поиск по IP
        filterset = HostComputerFilter(
            data={'search': '10.0'},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        
        # Поиск по MAC
        filterset = HostComputerFilter(
            data={'search': '66:77'},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        
        # Поиск по номеру комнаты отдела
        filterset = HostComputerFilter(
            data={'search': '102'},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
    
    def test_filter_search_empty(self):
        """Тест поиска с пустым значением"""
        filterset = HostComputerFilter(
            data={'search': ''},
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 4)  # Все записи
    
    def test_combined_filters(self):
        """Тест комбинации нескольких фильтров"""
        filterset = HostComputerFilter(
            data={
                'department': self.department1.id,
                'search': 'server'
            },
            queryset=HostComputer.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)
        self.assertTrue(all(host.department_id == self.department1.id for host in queryset))
        self.assertTrue(all('server' in host.hostname for host in queryset))


class HostComputerViewSetTestCase(APITestCase):
    """Тесты для HostComputerViewSet"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем тестового пользователя для аутентификации
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
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
        
        # Создаем тестовые хост-компьютеры
        self.host1 = HostComputer.objects.create(
            hostname='server-01',
            ip_address='192.168.1.10',
            mac_address='00:11:22:33:44:55',
            department=self.department1
        )
        
        self.host2 = HostComputer.objects.create(
            hostname='server-02',
            ip_address='192.168.1.20',
            mac_address='66:77:88:99:AA:BB',
            department=self.department1
        )
        
        self.host3 = HostComputer.objects.create(
            hostname='database-01',
            ip_address='10.0.0.50',
            mac_address='AA:BB:CC:DD:EE:FF',
            department=self.department2
        )
        
        self.host4 = HostComputer.objects.create(
            hostname='unassigned-host',
            ip_address='172.16.0.100',
            mac_address='11:22:33:44:55:66',
            department=None
        )
        
        # URL для API
        self.hosts_url = reverse('hostcomputer-list')
        
    def authenticate(self):
        """Вспомогательный метод для аутентификации"""
        self.client.force_authenticate(user=self.user)
    
    # Тесты для базовых CRUD операций
    
    def test_list_hosts_authenticated(self):
        """Тест получения списка хостов (аутентифицированный пользователь)"""
        self.authenticate()
        response = self.client.get(self.hosts_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        
        # Проверяем сортировку по hostname
        hostnames = [item['hostname'] for item in response.data]
        self.assertEqual(hostnames, sorted(hostnames))
    
    def test_list_hosts_unauthenticated(self):
        """Тест получения списка хостов без аутентификации"""
        response = self.client.get(self.hosts_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_host(self):
        """Тест получения конкретного хоста"""
        self.authenticate()
        url = reverse('hostcomputer-detail', args=[self.host1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['hostname'], 'server-01')
        self.assertEqual(response.data['ip_address'], '192.168.1.10')
        self.assertEqual(response.data['mac_address'], '00:11:22:33:44:55')
        self.assertEqual(response.data['department'], self.department1.id)
    
    def test_create_host_success(self):
        """Тест успешного создания хоста"""
        self.authenticate()
        data = {
            'hostname': 'new-server',
            'ip_address': '192.168.1.30',
            'mac_address': '11:22:33:44:55:66',
            'department': self.department1.id
        }
        
        response = self.client.post(self.hosts_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(HostComputer.objects.count(), 5)
        self.assertEqual(response.data['hostname'], 'new-server')
    
    def test_create_host_without_department(self):
        """Тест создания хоста без отдела"""
        self.authenticate()
        data = {
            'hostname': 'standalone-server',
            'ip_address': '192.168.1.40',
            'mac_address': 'AA:BB:CC:DD:EE:FF'
        }
        
        response = self.client.post(self.hosts_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['department'])
    
    def test_create_host_validation_error(self):
        """Тест ошибки валидации при создании"""
        self.authenticate()
        data = {
            'hostname': '',  # Пустое имя хоста
            'ip_address': 'invalid-ip',  # Неверный IP
            'mac_address': 'invalid-mac'  # Неверный MAC
        }
        
        response = self.client.post(self.hosts_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_update_host_success(self):
        """Тест успешного обновления хоста"""
        self.authenticate()
        url = reverse('hostcomputer-detail', args=[self.host1.id])
        data = {
            'hostname': 'updated-server',
            'ip_address': '192.168.1.15',
            'mac_address': '00:11:22:33:44:55',  # Оставляем тот же MAC
            'department': self.department2.id
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.host1.refresh_from_db()
        self.assertEqual(self.host1.hostname, 'updated-server')
        self.assertEqual(self.host1.ip_address, '192.168.1.15')
        self.assertEqual(self.host1.department_id, self.department2.id)
    
    def test_partial_update_host(self):
        """Тест частичного обновления хоста"""
        self.authenticate()
        url = reverse('hostcomputer-detail', args=[self.host1.id])
        data = {
            'ip_address': '192.168.1.99'
        }
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.host1.refresh_from_db()
        self.assertEqual(self.host1.ip_address, '192.168.1.99')
        self.assertEqual(self.host1.hostname, 'server-01')  # Не изменилось
    
    def test_delete_host(self):
        """Тест удаления хоста"""
        self.authenticate()
        url = reverse('hostcomputer-detail', args=[self.host1.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(HostComputer.objects.count(), 3)
    
    # Тесты для фильтрации через ViewSet
    
    def test_filter_by_hostname(self):
        """Тест фильтрации по имени хоста через ViewSet"""
        self.authenticate()
        response = self.client.get(self.hosts_url, {'hostname': 'server'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all('server' in item['hostname'] for item in response.data))
    
    def test_filter_by_ip_address(self):
        """Тест фильтрации по IP-адресу"""
        self.authenticate()
        response = self.client.get(self.hosts_url, {'ip_address': '192.168'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_filter_by_department(self):
        """Тест фильтрации по отделу"""
        self.authenticate()
        response = self.client.get(self.hosts_url, {'department': self.department1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(item['department'] == self.department1.id for item in response.data))
    
    def test_filter_has_department_true(self):
        """Тест фильтрации хостов с отделом"""
        self.authenticate()
        response = self.client.get(self.hosts_url, {'has_department': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertTrue(all(item['department'] is not None for item in response.data))
    
    def test_filter_has_department_false(self):
        """Тест фильтрации хостов без отдела"""
        self.authenticate()
        response = self.client.get(self.hosts_url, {'has_department': 'false'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertIsNone(response.data[0]['department'])
    
    def test_filter_by_search(self):
        """Тест поиска через фильтр"""
        self.authenticate()
        response = self.client.get(self.hosts_url, {'search': 'database'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['hostname'], 'database-01')
    
    # Тесты для кастомных action методов
    
    def test_details_action_with_department(self):
        """Тест получения детальной информации о хосте с отделом"""
        self.authenticate()
        url = reverse('hostcomputer-details', args=[self.host1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем основные поля
        self.assertEqual(response.data['hostname'], 'server-01')
        
        # Проверяем детали отдела
        self.assertIn('department_details', response.data)
        self.assertEqual(response.data['department_details']['room_number'], 101)
        self.assertEqual(response.data['department_details']['internal_phone'], 1234)
        self.assertEqual(response.data['department_details']['employee_count'], 5)
    
    def test_details_action_without_department(self):
        """Тест получения детальной информации о хосте без отдела"""
        self.authenticate()
        url = reverse('hostcomputer-details', args=[self.host4.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем основные поля
        self.assertEqual(response.data['hostname'], 'unassigned-host')
        
        # Проверяем, что department_details отсутствует
        self.assertNotIn('department_details', response.data)
    
    def test_details_action_not_found(self):
        """Тест получения деталей несуществующего хоста"""
        self.authenticate()
        url = reverse('hostcomputer-details', args=[999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_unassigned_action(self):
        """Тест получения хостов без отдела"""
        self.authenticate()
        url = reverse('hostcomputer-unassigned')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['hostname'], 'unassigned-host')
        self.assertIsNone(response.data[0]['department'])
    
    def test_unassigned_action_authenticated_only(self):
        """Тест доступа к unassigned action без аутентификации"""
        url = reverse('hostcomputer-unassigned')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    # Тесты для проверки queryset
    
    def test_queryset_select_related(self):
        """Тест оптимизации запросов с select_related"""
        self.authenticate()
        
        # Получаем данные через API
        response = self.client.get(self.hosts_url)
        
        # Проверяем через прямой запрос к ViewSet
        viewset = HostComputerViewSet()
        viewset.request = self.client.get('/').wsgi_request
        viewset.request.user = self.user
        viewset.action = 'list'
        
        queryset = viewset.get_queryset()
        
        # Проверяем, что используется select_related
        self.assertTrue(queryset.query.select_related)
        
        # Проверяем, что можно получить доступ к department без дополнительного запроса
        with self.assertNumQueries(1):  # Только один запрос
            for host in queryset:
                if host.department:
                    _ = host.department.room_number
    
    # Тесты для обработки ошибок
    
    @patch('network_api.models.HostComputer.objects.all')
    def test_list_error_handling(self, mock_all):
        """Тест обработки ошибок при получении списка"""
        mock_all.side_effect = Exception("Database error")
        
        self.authenticate()
        response = self.client.get(self.hosts_url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @patch('network_api.views.HostComputerViewSet.get_object')
    def test_details_action_error_handling(self, mock_get_object):
        """Тест обработки ошибок в details action"""
        mock_get_object.side_effect = Exception("Database error")
        
        self.authenticate()
        url = reverse('hostcomputer-details', args=[self.host1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class HostComputerViewSetUnitTests(TestCase):
    """Модульные тесты для отдельных методов HostComputerViewSet"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = HostComputerViewSet
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.department = Department.objects.create(
            room_number='101',
            internal_phone=1234,
            employee_count=5
        )
        
        self.host = HostComputer.objects.create(
            hostname='test-host',
            ip_address='192.168.1.100',
            mac_address='00:11:22:33:44:55',
            department=self.department
        )
    
    def test_list_method_structure(self):
        """Тест структуры метода list"""
        request = self.factory.get('/')
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.action = 'list'
        
        # Мокаем методы
        mock_queryset = MagicMock()
        mock_serializer = MagicMock()
        mock_serializer.data = [{'id': 1}, {'id': 2}]
        
        with patch.object(view, 'filter_queryset', return_value=mock_queryset):
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                response = view.list(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{'id': 1}, {'id': 2}])
    
    def test_unassigned_method(self):
        """Тест метода unassigned"""
        request = self.factory.get('/')
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.action = 'unassigned'
        
        # Создаем мок для queryset
        mock_queryset = MagicMock()
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered
        
        mock_serializer = MagicMock()
        mock_serializer.data = [{'hostname': 'unassigned1'}, {'hostname': 'unassigned2'}]
        
        with patch.object(view, 'get_queryset', return_value=mock_queryset):
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                response = view.unassigned(request)
        
        # Проверяем, что filter был вызван с правильными параметрами
        mock_queryset.filter.assert_called_once_with(department__isnull=True)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class HostComputerViewSetIntegrationTests(TestCase):
    """Интеграционные тесты для HostComputerViewSet"""
    
    def setUp(self):
        self.client = APITestClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Создаем отделы
        self.departments = []
        for i in range(1, 4):
            dept = Department.objects.create(
                room_number=f'{i}0{i}',
                internal_phone=1000 + i,
                employee_count=i * 5
            )
            self.departments.append(dept)
        
        # Создаем хосты
        self.hosts = []
        for i in range(1, 11):
            dept = self.departments[i % 3] if i % 3 != 0 else None
            host = HostComputer.objects.create(
                hostname=f'host-{i:02d}',
                ip_address=f'192.168.1.{i}',
                mac_address=f'00:11:22:33:44:{i:02x}',
                department=dept
            )
            self.hosts.append(host)
    
    def test_complex_filtering_scenarios(self):
        """Тест сложных сценариев фильтрации"""
        # Фильтр по отделу и поиск
        response = self.client.get('/api/host-computers/', {
            'department': self.departments[0].id,
            'search': 'host-0'
        })
        
        self.assertEqual(response.status_code, 200)
        # Проверяем, что результаты соответствуют фильтрам
        
        # Фильтр хостов без отдела
        response = self.client.get('/api/host-computers/', {
            'has_department': 'false'
        })
        
        self.assertEqual(response.status_code, 200)
        unassigned_count = sum(1 for h in self.hosts if h.department is None)
        self.assertEqual(len(response.data), unassigned_count)
        
        # Комбинация нескольких фильтров
        response = self.client.get('/api/host-computers/', {
            'ip_address': '192.168',
            'has_department': 'true',
            'search': 'host-1'
        })
        
        self.assertEqual(response.status_code, 200)
    
    def test_pagination_and_ordering(self):
        """Тест пагинации и сортировки"""
        response = self.client.get('/api/host-computers/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 10)
        
        # Проверяем сортировку по hostname
        hostnames = [item['hostname'] for item in response.data]
        self.assertEqual(hostnames, sorted(hostnames))


class APITestClient:
    """Вспомогательный класс для тестов"""
    
    def __init__(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.user = None
    
    def force_authenticate(self, user=None):
        self.user = user
        self.client.force_authenticate(user=user)
    
    def get(self, url, data=None):
        return self.client.get(url, data)
    
    def post(self, url, data=None):
        return self.client.post(url, data)
    
    def put(self, url, data=None):
        return self.client.put(url, data)
    
    def patch(self, url, data=None):
        return self.client.patch(url, data)
    
    def delete(self, url):
        return self.client.delete(url)