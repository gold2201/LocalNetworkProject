from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import datetime, timedelta

from network_api.models import Network, NetworkComputer, Equipment, Computer, Department
from network_api.views import NetworkReadOnlyViewSet, NetworkFilter, StandardResultsSetPagination


class StandardResultsSetPaginationTestCase(TestCase):
    """Тесты для StandardResultsSetPagination"""
    
    def test_pagination_settings(self):
        """Тест настроек пагинации"""
        pagination = StandardResultsSetPagination()
        
        self.assertEqual(pagination.page_size, 25)
        self.assertEqual(pagination.page_size_query_param, 'page_size')
        self.assertEqual(pagination.max_page_size, 100)


class NetworkFilterTestCase(TestCase):
    """Тесты для NetworkFilter"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем оборудование
        self.equipment1 = Equipment.objects.create(
            type='Router',
            port_count=4,
            bandwidth='1000 Mbps'
        )
        
        self.equipment2 = Equipment.objects.create(
            type='Switch',
            port_count=24,
            bandwidth='1000 Mbps'
        )
        
        self.equipment3 = Equipment.objects.create(
            type='Firewall',
            port_count=8,
            bandwidth='1 Gbps'
        )
        
        # Создаем сети
        self.network1 = Network.objects.create(
            vlan=100,
            ip_range='192.168.1.0/24',
            subnet_mask='255.255.255.0',
            gateway='192.168.1.1',
            equipment=self.equipment1
        )
        
        self.network2 = Network.objects.create(
            vlan=200,
            ip_range='10.0.0.0/16',
            subnet_mask='255.255.0.0',
            gateway='10.0.0.1',
            equipment=self.equipment2
        )
        
        self.network3 = Network.objects.create(
            vlan=300,
            ip_range='172.16.0.0/12',
            subnet_mask='255.240.0.0',
            gateway='172.16.0.1',
            equipment=self.equipment3
        )
        
        self.network4 = Network.objects.create(
            vlan=400,
            ip_range='192.168.100.0/24',
            subnet_mask='255.255.255.0',
            gateway='192.168.100.1',
            equipment=None
        )
        
        # Создаем компьютеры и подключения к сетям
        self.department = Department.objects.create(
            room_number='101',
            internal_phone=1234,
            employee_count=5
        )
        
        self.computer1 = Computer.objects.create(
            model='Dell Optiplex',
            os='Windows 10',
            serial_number='SN001',
            inventory_number='INV001',
            department=self.department
        )
        
        self.computer2 = Computer.objects.create(
            model='MacBook Pro',
            os='macOS',
            serial_number='SN002',
            inventory_number='INV002',
            department=self.department
        )
        
        # Подключаем компьютеры к сетям
        self.nc1 = NetworkComputer.objects.create(
            network=self.network1,
            computer=self.computer1,
            ip_address='192.168.1.10',
            mac_address='00:11:22:33:44:55',
            speed=1000
        )
        
        self.nc2 = NetworkComputer.objects.create(
            network=self.network1,
            computer=self.computer2,
            ip_address='192.168.1.20',
            mac_address='66:77:88:99:AA:BB',
            speed=100
        )
        
        self.nc3 = NetworkComputer.objects.create(
            network=self.network2,
            computer=self.computer1,
            ip_address='10.0.0.10',
            mac_address='00:11:22:33:44:55',  # Тот же компьютер в другой сети
            speed=1000
        )
    
    def test_filter_by_vlan(self):
        """Тест фильтрации по VLAN"""
        filterset = NetworkFilter(
            data={'vlan': 100},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().vlan, 100)
    
    def test_filter_by_ip_range_icontains(self):
        """Тест фильтрации по IP-диапазону"""
        filterset = NetworkFilter(
            data={'ip_range': '192.168'},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)  # network1 и network4
        self.assertTrue(all('192.168' in net.ip_range for net in queryset))
    
    def test_filter_by_equipment_type(self):
        """Тест фильтрации по типу оборудования"""
        filterset = NetworkFilter(
            data={'equipment_type': 'router'},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().equipment.type, 'Router')
    
    def test_filter_has_computers_true(self):
        """Тест фильтрации сетей с компьютерами"""
        filterset = NetworkFilter(
            data={'has_computers': True},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)  # network1 и network2
        self.assertTrue(all(net.networkcomputer_set.count() > 0 for net in queryset))
    
    def test_filter_has_computers_false(self):
        """Тест фильтрации сетей без компьютеров"""
        filterset = NetworkFilter(
            data={'has_computers': False},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)  # network3 и network4
        self.assertTrue(all(net.networkcomputer_set.count() == 0 for net in queryset))
    
    def test_filter_search_method(self):
        """Тест поискового метода filter_search"""
        # Поиск по VLAN
        filterset = NetworkFilter(
            data={'search': '100'},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        
        # Поиск по IP-диапазону
        filterset = NetworkFilter(
            data={'search': '10.0'},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        
        # Поиск по маске подсети
        filterset = NetworkFilter(
            data={'search': '255.255.255.0'},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)  # network1 и network4
        
        # Поиск по типу оборудования
        filterset = NetworkFilter(
            data={'search': 'switch'},
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
    
    def test_combined_filters(self):
        """Тест комбинации нескольких фильтров"""
        filterset = NetworkFilter(
            data={
                'has_computers': True,
                'search': '192.168'
            },
            queryset=Network.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)  # network1
        self.assertEqual(queryset.first().vlan, 100)


class NetworkReadOnlyViewSetTestCase(APITestCase):
    """Тесты для NetworkReadOnlyViewSet"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем тестового пользователя для аутентификации
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Создаем оборудование
        self.equipment1 = Equipment.objects.create(
            type='Router',
            port_count=4,
            bandwidth='1000 Mbps',
            setup_date=timezone.now().date() - timedelta(days=30)
        )
        
        self.equipment2 = Equipment.objects.create(
            type='Switch',
            port_count=24,
            bandwidth='1000 Mbps',
            setup_date=timezone.now().date() - timedelta(days=15)
        )
        
        # Создаем сети
        self.network1 = Network.objects.create(
            vlan=100,
            ip_range='192.168.1.0/24',
            subnet_mask='255.255.255.0',
            gateway='192.168.1.1',
            equipment=self.equipment1
        )
        
        self.network2 = Network.objects.create(
            vlan=200,
            ip_range='10.0.0.0/16',
            subnet_mask='255.255.0.0',
            gateway='10.0.0.1',
            equipment=self.equipment2
        )
        
        self.network3 = Network.objects.create(
            vlan=300,
            ip_range='172.16.0.0/12',
            subnet_mask='255.240.0.0',
            gateway='172.16.0.1',
            equipment=None
        )
        
        # Создаем отдел и компьютеры
        self.department = Department.objects.create(
            room_number='101',
            internal_phone=1234,
            employee_count=5
        )
        
        self.computer1 = Computer.objects.create(
            model='Dell Optiplex',
            os='Windows 10',
            serial_number='SN001',
            inventory_number='INV001',
            department=self.department
        )
        
        self.computer2 = Computer.objects.create(
            model='MacBook Pro',
            os='macOS',
            serial_number='SN002',
            inventory_number='INV002',
            department=self.department
        )
        
        self.computer3 = Computer.objects.create(
            model='HP EliteBook',
            os='Windows 11',
            serial_number='SN003',
            inventory_number='INV003',
            department=self.department
        )
        
        # Подключаем компьютеры к сетям
        self.nc1 = NetworkComputer.objects.create(
            network=self.network1,
            computer=self.computer1,
            ip_address='192.168.1.10',
            mac_address='00:11:22:33:44:55',
            speed=1000
        )
        
        self.nc2 = NetworkComputer.objects.create(
            network=self.network1,
            computer=self.computer2,
            ip_address='192.168.1.20',
            mac_address='66:77:88:99:AA:BB',
            speed=100
        )
        
        self.nc3 = NetworkComputer.objects.create(
            network=self.network2,
            computer=self.computer1,
            ip_address='10.0.0.10',
            mac_address='00:11:22:33:44:55',
            speed=1000
        )
        
        self.nc4 = NetworkComputer.objects.create(
            network=self.network2,
            computer=self.computer3,
            ip_address='10.0.0.20',
            mac_address='CC:DD:EE:FF:00:11',
            speed=1000
        )
        
        # URL для API
        self.networks_url = reverse('network-list')
        
    def authenticate(self):
        """Вспомогательный метод для аутентификации"""
        self.client.force_authenticate(user=self.user)
    
    # Тесты для базовых ReadOnly операций
    
    def test_list_networks_authenticated(self):
        """Тест получения списка сетей (аутентифицированный пользователь)"""
        self.authenticate()
        response = self.client.get(self.networks_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 3)
        
        # Проверяем аннотированное поле
        first_network = response.data['results'][0]
        self.assertIn('computers_count', first_network)
    
    def test_list_networks_unauthenticated(self):
        """Тест получения списка сетей без аутентификации"""
        response = self.client.get(self.networks_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_retrieve_network(self):
        """Тест получения конкретной сети"""
        self.authenticate()
        url = reverse('network-detail', args=[self.network1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['vlan'], 100)
        self.assertEqual(response.data['ip_range'], '192.168.1.0/24')
        self.assertEqual(response.data['computers_count'], 2)
    
    def test_retrieve_network_not_found(self):
        """Тест получения несуществующей сети"""
        self.authenticate()
        url = reverse('network-detail', args=[999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    # Тесты для фильтрации через ViewSet
    
    def test_filter_by_vlan(self):
        """Тест фильтрации по VLAN через ViewSet"""
        self.authenticate()
        response = self.client.get(self.networks_url, {'vlan': 100})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['vlan'], 100)
    
    def test_filter_by_ip_range(self):
        """Тест фильтрации по IP-диапазону"""
        self.authenticate()
        response = self.client.get(self.networks_url, {'ip_range': '192.168'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ip_range'], '192.168.1.0/24')
    
    def test_filter_by_equipment_type(self):
        """Тест фильтрации по типу оборудования"""
        self.authenticate()
        response = self.client.get(self.networks_url, {'equipment_type': 'router'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['equipment'], self.equipment1.id)
    
    def test_filter_has_computers_true(self):
        """Тест фильтрации сетей с компьютерами"""
        self.authenticate()
        response = self.client.get(self.networks_url, {'has_computers': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)  # network1 и network2
        for net in response.data['results']:
            self.assertGreater(net['computers_count'], 0)
    
    def test_filter_has_computers_false(self):
        """Тест фильтрации сетей без компьютеров"""
        self.authenticate()
        response = self.client.get(self.networks_url, {'has_computers': 'false'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # network3
        self.assertEqual(response.data['results'][0]['computers_count'], 0)
    
    def test_filter_by_search(self):
        """Тест поиска через фильтр"""
        self.authenticate()
        response = self.client.get(self.networks_url, {'search': '10.0'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ip_range'], '10.0.0.0/16')
    
    # Тесты для пагинации
    
    def test_pagination_default_page_size(self):
        """Тест пагинации с размером страницы по умолчанию"""
        self.authenticate()
        
        # Создаем дополнительные сети для проверки пагинации
        for i in range(30):
            Network.objects.create(
                vlan=1000 + i,
                ip_range=f'192.168.{i}.0/24',
                subnet_mask='255.255.255.0'
            )
        
        response = self.client.get(self.networks_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 25)  # page_size по умолчанию
        self.assertIsNotNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
    
    def test_pagination_custom_page_size(self):
        """Тест пагинации с пользовательским размером страницы"""
        self.authenticate()
        
        # Создаем дополнительные сети
        for i in range(30):
            Network.objects.create(
                vlan=1000 + i,
                ip_range=f'192.168.{i}.0/24',
                subnet_mask='255.255.255.0'
            )
        
        response = self.client.get(self.networks_url, {'page_size': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 10)
    
    def test_pagination_max_page_size(self):
        """Тест максимального размера страницы"""
        self.authenticate()
        
        response = self.client.get(self.networks_url, {'page_size': 200})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 100)  # max_page_size = 100
    
    # Тесты для кастомных action методов
    
    def test_statistics_action(self):
        """Тест получения статистики по сетям"""
        self.authenticate()
        url = reverse('network-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем общую статистику
        self.assertEqual(response.data['total_networks'], 3)
        self.assertEqual(response.data['average_vlan'], (100 + 200 + 300) / 3)
        self.assertEqual(response.data['max_vlan'], 300)
        self.assertEqual(response.data['min_vlan'], 100)
        self.assertEqual(response.data['networks_with_equipment'], 2)
        self.assertEqual(response.data['total_computers_connected'], 3)  # computer1, computer2, computer3
        
        # Проверяем распределение VLAN
        self.assertIn('vlan_distribution', response.data)
        self.assertEqual(len(response.data['vlan_distribution']), 3)
    
    def test_statistics_action_empty(self):
        """Тест статистики при отсутствии сетей"""
        self.authenticate()
        Network.objects.all().delete()
        
        url = reverse('network-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_networks'], 0)
        self.assertIsNone(response.data['average_vlan'])
        self.assertIsNone(response.data['max_vlan'])
        self.assertIsNone(response.data['min_vlan'])
        self.assertEqual(response.data['networks_with_equipment'], 0)
        self.assertEqual(response.data['total_computers_connected'], 0)
        self.assertEqual(len(response.data['vlan_distribution']), 0)
    
    def test_computers_action(self):
        """Тест получения компьютеров в сети"""
        self.authenticate()
        url = reverse('network-computers', args=[self.network1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Проверяем структуру данных
        computer_data = response.data[0]
        self.assertIn('computer', computer_data)
        self.assertIn('ip_address', computer_data)
        self.assertIn('mac_address', computer_data)
        self.assertIn('speed', computer_data)
    
    def test_computers_action_no_computers(self):
        """Тест получения компьютеров для сети без компьютеров"""
        self.authenticate()
        url = reverse('network-computers', args=[self.network3.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_details_action_with_equipment(self):
        """Тест получения детальной информации о сети с оборудованием"""
        self.authenticate()
        url = reverse('network-details', args=[self.network1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем основные поля
        self.assertEqual(response.data['vlan'], 100)
        
        # Проверяем информацию об оборудовании
        self.assertIn('equipment_info', response.data)
        self.assertEqual(response.data['equipment_info']['type'], 'Router')
        self.assertEqual(response.data['equipment_info']['bandwidth'], '1000 Mbps')
        
        # Проверяем количество подключенных компьютеров
        self.assertEqual(response.data['connected_computers_count'], 2)
        
        # Проверяем недавние компьютеры
        self.assertIn('recent_computers', response.data)
        self.assertEqual(len(response.data['recent_computers']), 2)  # Всего 2 в сети
        self.assertIn('model', response.data['recent_computers'][0])
        self.assertIn('ip_address', response.data['recent_computers'][0])
    
    def test_details_action_without_equipment(self):
        """Тест получения детальной информации о сети без оборудования"""
        self.authenticate()
        url = reverse('network-details', args=[self.network3.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем информацию об оборудовании
        self.assertIn('equipment_info', response.data)
        self.assertIsNone(response.data['equipment_info'])
        
        # Проверяем количество подключенных компьютеров
        self.assertEqual(response.data['connected_computers_count'], 0)
        
        # Проверяем недавние компьютеры (пустой список)
        self.assertEqual(len(response.data['recent_computers']), 0)
    
    def test_details_action_with_many_computers(self):
        """Тест получения детальной информации с ограничением недавних компьютеров"""
        self.authenticate()
        
        # Добавляем еще компьютеры в сеть
        for i in range(10):
            computer = Computer.objects.create(
                model=f'Test Model {i}',
                os='Windows',
                serial_number=f'SN-TEST-{i}',
                inventory_number=f'INV-TEST-{i}',
                department=self.department
            )
            NetworkComputer.objects.create(
                network=self.network1,
                computer=computer,
                ip_address=f'192.168.1.{100 + i}',
                mac_address=f'AA:BB:CC:DD:EE:{i:02x}',
                speed=1000
            )
        
        url = reverse('network-details', args=[self.network1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['connected_computers_count'], 12)  # 2 старых + 10 новых
        self.assertEqual(len(response.data['recent_computers']), 5)  # Ограничение 5
    
    def test_details_action_not_found(self):
        """Тест получения деталей несуществующей сети"""
        self.authenticate()
        url = reverse('network-details', args=[999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    # Тесты для проверки queryset
    
    def test_queryset_annotations_and_prefetch(self):
        """Тест аннотаций и оптимизации запросов в queryset"""
        self.authenticate()
        
        # Получаем данные через API
        response = self.client.get(self.networks_url)
        
        # Проверяем через прямой запрос к ViewSet
        viewset = NetworkReadOnlyViewSet()
        viewset.request = self.client.get('/').wsgi_request
        viewset.request.user = self.user
        viewset.action = 'list'
        
        queryset = viewset.get_queryset()
        
        # Проверяем аннотацию
        first_network = queryset.first()
        self.assertTrue(hasattr(first_network, 'computers_count'))
        
        # Проверяем, что используется select_related и prefetch_related
        # (не можем проверить напрямую, но можем проверить количество запросов)
        with self.assertNumQueries(2):  # Один для сетей, один для prefetch_related
            for network in queryset:
                # Доступ к связанным объектам не должен создавать новые запросы
                if network.equipment:
                    _ = network.equipment.type
                for nc in network.networkcomputer_set.all():
                    _ = nc.computer.model
    
    # Тесты для обработки ошибок
    
    @patch('network_api.models.Network.objects.all')
    def test_list_error_handling(self, mock_all):
        """Тест обработки ошибок при получении списка"""
        mock_all.side_effect = Exception("Database error")
        
        self.authenticate()
        response = self.client.get(self.networks_url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @patch('network_api.views.NetworkReadOnlyViewSet.get_object')
    def test_computers_action_error_handling(self, mock_get_object):
        """Тест обработки ошибок в computers action"""
        mock_get_object.side_effect = Exception("Database error")
        
        self.authenticate()
        url = reverse('network-computers', args=[self.network1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @patch('network_api.models.Network.objects.aggregate')
    def test_statistics_action_error_handling(self, mock_aggregate):
        """Тест обработки ошибок в statistics action"""
        mock_aggregate.side_effect = Exception("Database error")
        
        self.authenticate()
        url = reverse('network-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class NetworkReadOnlyViewSetUnitTests(TestCase):
    """Модульные тесты для отдельных методов NetworkReadOnlyViewSet"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = NetworkReadOnlyViewSet
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.equipment = Equipment.objects.create(
            type='Router',
            port_count=4,
            bandwidth='1000 Mbps',
            setup_date=timezone.now().date()
        )
        
        self.network = Network.objects.create(
            vlan=100,
            ip_range='192.168.1.0/24',
            subnet_mask='255.255.255.0',
            gateway='192.168.1.1',
            equipment=self.equipment
        )
    
    def test_statistics_method_structure(self):
        """Тест структуры метода statistics"""
        request = self.factory.get('/')
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.action = 'statistics'
        
        # Мокаем методы
        mock_aggregate = MagicMock(return_value={
            'total_networks': 5,
            'average_vlan': 150,
            'max_vlan': 300,
            'min_vlan': 50,
            'networks_with_equipment': 3,
            'total_computers_connected': 10
        })
        
        mock_values = MagicMock()
        mock_values.annotate.return_value.order_by.return_value = [
            {'vlan': 100, 'count': 2},
            {'vlan': 200, 'count': 1}
        ]
        
        with patch('network_api.models.Network.objects.aggregate', mock_aggregate):
            with patch('network_api.models.Network.objects.values', return_value=mock_values):
                response = view.statistics(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_networks'], 5)
        self.assertIn('vlan_distribution', response.data)
    
    def test_computers_method(self):
        """Тест метода computers"""
        request = self.factory.get('/')
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.action = 'computers'
        view.kwargs = {'pk': str(self.network.id)}
        
        # Мокаем get_object
        mock_network = MagicMock()
        mock_network.networkcomputer_set.all.return_value = []
        
        with patch.object(view, 'get_object', return_value=mock_network):
            with patch('network_api.serializers.NetworkComputerSerializer') as mock_serializer:
                mock_serializer.return_value.data = [{'id': 1}, {'id': 2}]
                response = view.computers(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_details_method_with_equipment(self):
        """Тест метода details с оборудованием"""
        request = self.factory.get('/')
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.action = 'details'
        view.kwargs = {'pk': str(self.network.id)}
        
        # Мокаем методы
        mock_serializer = MagicMock()
        mock_serializer.data = {'id': self.network.id, 'vlan': 100}
        
        mock_network = MagicMock()
        mock_network.equipment = self.equipment
        mock_network.networkcomputer_set.count.return_value = 5
        mock_network.networkcomputer_set.select_related.return_value.order_by.return_value[:5].return_value = []
        
        with patch.object(view, 'get_object', return_value=mock_network):
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                response = view.details(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['connected_computers_count'], 5)
        self.assertIsNotNone(response.data['equipment_info'])
        self.assertEqual(response.data['equipment_info']['type'], 'Router')


class NetworkReadOnlyViewSetIntegrationTests(TestCase):
    """Интеграционные тесты для NetworkReadOnlyViewSet"""
    
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)
        
        # Создаем оборудование
        self.equipment_types = ['Router', 'Switch', 'Firewall', 'Access Point']
        self.equipment_list = []
        for i, eq_type in enumerate(self.equipment_types):
            eq = Equipment.objects.create(
                type=eq_type,
                port_count=(i + 1) * 4,
                bandwidth=f'{1000 * (i + 1)} Mbps'
            )
            self.equipment_list.append(eq)
        
        # Создаем сети
        self.networks = []
        vlan_ranges = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for i, vlan in enumerate(vlan_ranges):
            equipment = self.equipment_list[i % len(self.equipment_list)]
            network = Network.objects.create(
                vlan=vlan,
                ip_range=f'192.168.{vlan}.0/24',
                subnet_mask='255.255.255.0',
                gateway=f'192.168.{vlan}.1',
                equipment=equipment if i % 2 == 0 else None
            )
            self.networks.append(network)
        
        # Создаем отдел и компьютеры
        department = Department.objects.create(
            room_number='101',
            internal_phone=1234,
            employee_count=5
        )
        
        self.computers = []
        for i in range(1, 11):
            computer = Computer.objects.create(
                model=f'Computer Model {i}',
                os='Windows' if i % 2 == 0 else 'Linux',
                serial_number=f'SN-COMP-{i:03d}',
                inventory_number=f'INV-COMP-{i:03d}',
                department=department
            )
            self.computers.append(computer)
        
        # Подключаем компьютеры к сетям
        for i, network in enumerate(self.networks[:5]):  # Первые 5 сетей имеют компьютеры
            for j, computer in enumerate(self.computers[:i+2]):  # Разное количество компьютеров
                NetworkComputer.objects.create(
                    network=network,
                    computer=computer,
                    ip_address=f'192.168.{network.vlan}.{10 + j}',
                    mac_address=f'AA:BB:CC:DD:{i:02x}:{j:02x}',
                    speed=1000 if j % 2 == 0 else 100
                )
    
    def test_complex_filtering_scenarios(self):
        """Тест сложных сценариев фильтрации"""
        # Фильтр по типу оборудования и наличию компьютеров
        response = self.client.get('/api/networks/', {
            'equipment_type': 'router',
            'has_computers': 'true'
        })
        
        self.assertEqual(response.status_code, 200)
        
        # Фильтр по VLAN и поиск
        response = self.client.get('/api/networks/', {
            'vlan': 30,
            'search': '192.168'
        })
        
        self.assertEqual(response.status_code, 200)
        if len(response.data['results']) > 0:
            self.assertEqual(response.data['results'][0]['vlan'], 30)
    
    def test_pagination_and_filtering(self):
        """Тест пагинации с фильтрацией"""
        response = self.client.get('/api/networks/', {
            'page_size': 5,
            'has_computers': 'true'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 5)
        self.assertIsNotNone(response.data['next'])
        
        # Проверяем, что все результаты имеют компьютеры
        for network in response.data['results']:
            self.assertGreater(network['computers_count'], 0)
    
    def test_details_with_complete_data(self):
        """Тест детальной информации с полными данными"""
        network_with_computers = self.networks[0]
        url = reverse('network-details', args=[network_with_computers.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['connected_computers_count'], 
                        network_with_computers.networkcomputer_set.count())
        self.assertIsNotNone(response.data['equipment_info'])
        self.assertEqual(len(response.data['recent_computers']), 
                        min(5, network_with_computers.networkcomputer_set.count()))
    
    def test_statistics_with_complex_data(self):
        """Тест статистики с полными данными"""
        url = reverse('network-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total_networks'], len(self.networks))
        self.assertEqual(response.data['total_computers_connected'], 
                        NetworkComputer.objects.values('computer').distinct().count())
        
        # Проверяем распределение VLAN
        self.assertLessEqual(len(response.data['vlan_distribution']), 10)