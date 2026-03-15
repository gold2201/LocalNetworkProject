from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.db.models import Q

from network_api.models import Equipment, Network
from network_api.views import EquipmentViewSet, EquipmentFilter


class EquipmentFilterTestCase(TestCase):
    """Тесты для EquipmentFilter"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем тестовое оборудование
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
        
        self.equipment3 = Equipment.objects.create(
            type='Switch',
            port_count=48,
            bandwidth='10 Gbps',
            setup_date=timezone.now().date()
        )
        
        self.equipment4 = Equipment.objects.create(
            type='Firewall',
            port_count=8,
            bandwidth='1 Gbps',
            setup_date=timezone.now().date() - timedelta(days=60)
        )
    
    def test_filter_by_type_icontains(self):
        """Тест фильтрации по типу (регистронезависимый поиск)"""
        filterset = EquipmentFilter(
            data={'type': 'switch'},
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)
        self.assertTrue(all('switch' in eq.type.lower() for eq in queryset))
    
    def test_filter_by_min_ports(self):
        """Тест фильтрации по минимальному количеству портов"""
        filterset = EquipmentFilter(
            data={'min_ports': 10},
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)  # Switch 24 и Switch 48
        self.assertTrue(all(eq.port_count >= 10 for eq in queryset))
    
    def test_filter_by_max_ports(self):
        """Тест фильтрации по максимальному количеству портов"""
        filterset = EquipmentFilter(
            data={'max_ports': 10},
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 2)  # Router (4) и Firewall (8)
        self.assertTrue(all(eq.port_count <= 10 for eq in queryset))
    
    def test_filter_by_ports_range(self):
        """Тест фильтрации по диапазону портов"""
        filterset = EquipmentFilter(
            data={'min_ports': 5, 'max_ports': 20},
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)  # Firewall (8)
    
    def test_filter_by_bandwidth_min(self):
        """Тест фильтрации по минимальной пропускной способности"""
        filterset = EquipmentFilter(
            data={'bandwidth_min': 1000},  # Ищет в строке, должно работать по-другому
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        # Обратите внимание: bandwidth_min ищет по числовому полю,
        # но у нас bandwidth - строковое поле. Возможно, нужно исправить фильтр
    
    def test_filter_by_setup_date_after(self):
        """Тест фильтрации по дате установки (после)"""
        date_threshold = timezone.now().date() - timedelta(days=20)
        filterset = EquipmentFilter(
            data={'setup_date_after': date_threshold.isoformat()},
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        # Должны получить оборудование с датой >= date_threshold
        self.assertTrue(all(eq.setup_date >= date_threshold for eq in queryset))
    
    def test_filter_by_setup_date_before(self):
        """Тест фильтрации по дате установки (до)"""
        date_threshold = timezone.now().date() - timedelta(days=20)
        filterset = EquipmentFilter(
            data={'setup_date_before': date_threshold.isoformat()},
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        # Должны получить оборудование с датой <= date_threshold
        self.assertTrue(all(eq.setup_date <= date_threshold for eq in queryset))
    
    def test_filter_by_date_range(self):
        """Тест фильтрации по диапазону дат"""
        start_date = timezone.now().date() - timedelta(days=40)
        end_date = timezone.now().date() - timedelta(days=10)
        
        filterset = EquipmentFilter(
            data={
                'setup_date_after': start_date.isoformat(),
                'setup_date_before': end_date.isoformat()
            },
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        # Должны получить оборудование с датой в диапазоне
        for eq in queryset:
            self.assertTrue(start_date <= eq.setup_date <= end_date)
    
    def test_filter_search_method(self):
        """Тест поискового метода filter_search"""
        filterset = EquipmentFilter(
            data={'search': 'router'},
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        # Метод filter_search вызывается автоматически через фильтр
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().type, 'Router')
    
    def test_filter_search_empty(self):
        """Тест поиска с пустым значением"""
        filterset = EquipmentFilter(
            data={'search': ''},
            queryset=Equipment.objects.all()
        )
        self.assertTrue(filterset.is_valid())
        
        queryset = filterset.qs
        self.assertEqual(queryset.count(), 4)  # Все записи


class EquipmentViewSetTestCase(APITestCase):
    """Тесты для EquipmentViewSet"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем тестового пользователя (хотя permissions.AllowAny)
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # Создаем тестовое оборудование
        self.router = Equipment.objects.create(
            type='Router',
            port_count=4,
            bandwidth='1000 Mbps',
            setup_date=timezone.now().date() - timedelta(days=30)
        )
        
        self.switch1 = Equipment.objects.create(
            type='Switch',
            port_count=24,
            bandwidth='1000 Mbps',
            setup_date=timezone.now().date() - timedelta(days=15)
        )
        
        self.switch2 = Equipment.objects.create(
            type='Switch',
            port_count=48,
            bandwidth='10 Gbps',
            setup_date=timezone.now().date()
        )
        
        # Создаем сети и связываем с оборудованием
        self.network1 = Network.objects.create(
            name='Main Network',
            ip_range='192.168.1.0/24'
        )
        
        self.network2 = Network.objects.create(
            name='Backup Network',
            ip_range='10.0.0.0/16'
        )
        
        self.network3 = Network.objects.create(
            name='DMZ',
            ip_range='172.16.0.0/12'
        )
        
        # Связываем оборудование с сетями
        self.router.networks.add(self.network1, self.network2)
        self.switch1.networks.add(self.network1)
        self.switch2.networks.add(self.network3)
        
        # URL для API
        self.equipment_url = reverse('equipment-list')
        
    def test_list_equipment(self):
        """Тест получения списка оборудования"""
        response = self.client.get(self.equipment_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('equipment', response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['equipment']), 3)
        
        # Проверяем, что данные отсортированы по типу
        types = [item['type'] for item in response.data['equipment']]
        self.assertEqual(types, sorted(types))
    
    def test_retrieve_equipment(self):
        """Тест получения конкретного оборудования"""
        url = reverse('equipment-detail', args=[self.router.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type'], 'Router')
        self.assertEqual(response.data['port_count'], 4)
        self.assertEqual(response.data['bandwidth'], '1000 Mbps')
        
        # Проверяем аннотированное поле
        self.assertIn('networks_count', response.data)
        self.assertEqual(response.data['networks_count'], 2)
    
    def test_retrieve_equipment_not_found(self):
        """Тест получения несуществующего оборудования"""
        url = reverse('equipment-detail', args=[999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    # Тесты для фильтрации через ViewSet
    
    def test_filter_by_type(self):
        """Тест фильтрации по типу через ViewSet"""
        response = self.client.get(self.equipment_url, {'type': 'Switch'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertTrue(all(
            item['type'] == 'Switch' for item in response.data['equipment']
        ))
    
    def test_filter_by_min_ports(self):
        """Тест фильтрации по минимальному количеству портов"""
        response = self.client.get(self.equipment_url, {'min_ports': 20})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # Switch 24 и Switch 48
        self.assertTrue(all(
            item['port_count'] >= 20 for item in response.data['equipment']
        ))
    
    def test_filter_by_max_ports(self):
        """Тест фильтрации по максимальному количеству портов"""
        response = self.client.get(self.equipment_url, {'max_ports': 10})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)  # Router (4)
        self.assertTrue(all(
            item['port_count'] <= 10 for item in response.data['equipment']
        ))
    
    def test_filter_by_date_range(self):
        """Тест фильтрации по диапазону дат"""
        today = timezone.now().date()
        start_date = today - timedelta(days=20)
        end_date = today - timedelta(days=10)
        
        response = self.client.get(self.equipment_url, {
            'setup_date_after': start_date.isoformat(),
            'setup_date_before': end_date.isoformat()
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)  # Switch1 (15 days ago)
    
    def test_filter_by_search(self):
        """Тест поиска через фильтр"""
        response = self.client.get(self.equipment_url, {'search': 'router'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['equipment'][0]['type'], 'Router')
    
    # Тесты для кастомных action методов
    
    def test_networks_action(self):
        """Тест получения сетей оборудования"""
        url = reverse('equipment-networks', args=[self.router.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Проверяем данные сетей
        network_names = [net['name'] for net in response.data]
        self.assertIn('Main Network', network_names)
        self.assertIn('Backup Network', network_names)
    
    def test_networks_action_no_networks(self):
        """Тест получения сетей для оборудования без сетей"""
        # Создаем оборудование без сетей
        empty_equipment = Equipment.objects.create(
            type='Test',
            port_count=1,
            bandwidth='100 Mbps'
        )
        
        url = reverse('equipment-networks', args=[empty_equipment.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
    
    def test_statistics_action(self):
        """Тест получения статистики по оборудованию"""
        url = reverse('equipment-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем общую статистику
        self.assertEqual(response.data['total_equipment'], 3)
        self.assertEqual(response.data['average_ports'], (4 + 24 + 48) / 3)
        self.assertEqual(response.data['max_ports'], 48)
        self.assertEqual(response.data['min_ports'], 4)
        self.assertEqual(response.data['types_count'], 2)  # Router и Switch
        self.assertEqual(response.data['total_networks'], 3)  # 3 уникальные сети
        
        # Проверяем распределение по типам
        self.assertIn('type_distribution', response.data)
        type_dist = response.data['type_distribution']
        self.assertEqual(len(type_dist), 2)
        
        # Switch должен быть первым (2 шт)
        self.assertEqual(type_dist[0]['type'], 'Switch')
        self.assertEqual(type_dist[0]['count'], 2)
        
        # Router вторым (1 шт)
        self.assertEqual(type_dist[1]['type'], 'Router')
        self.assertEqual(type_dist[1]['count'], 1)
    
    def test_statistics_action_empty(self):
        """Тест статистики при отсутствии оборудования"""
        # Удаляем все оборудование
        Equipment.objects.all().delete()
        
        url = reverse('equipment-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_equipment'], 0)
        self.assertIsNone(response.data['average_ports'])
        self.assertIsNone(response.data['max_ports'])
        self.assertIsNone(response.data['min_ports'])
        self.assertEqual(response.data['types_count'], 0)
        self.assertEqual(response.data['total_networks'], 0)
        self.assertEqual(len(response.data['type_distribution']), 0)
    
    # Тесты для проверки queryset
    
    def test_queryset_annotation(self):
        """Тест аннотации networks_count в queryset"""
        # Получаем данные через API
        url = reverse('equipment-detail', args=[self.router.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['networks_count'], 2)
        
        # Проверяем через прямой запрос к ViewSet
        viewset = EquipmentViewSet()
        viewset.request = self.client.get('/').wsgi_request
        viewset.action = 'retrieve'
        
        queryset = viewset.get_queryset()
        router_from_queryset = queryset.get(pk=self.router.id)
        self.assertTrue(hasattr(router_from_queryset, 'networks_count'))
        self.assertEqual(router_from_queryset.networks_count, 2)
    
    # Тесты для проверки прав доступа
    
    def test_public_access(self):
        """Тест публичного доступа (permissions.AllowAny)"""
        # Не аутентифицируем пользователя
        response = self.client.get(self.equipment_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    # Тесты для обработки ошибок
    
    @patch('network_api.models.Equipment.objects.all')
    def test_list_error_handling(self, mock_all):
        """Тест обработки ошибок при получении списка"""
        mock_all.side_effect = Exception("Database error")
        
        response = self.client.get(self.equipment_url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @patch('network_api.models.Equipment.objects.get')
    def test_retrieve_error_handling(self, mock_get):
        """Тест обработки ошибок при получении конкретной записи"""
        mock_get.side_effect = Exception("Database error")
        
        url = reverse('equipment-detail', args=[1])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @patch('network_api.models.Equipment.objects.filter')
    def test_networks_action_error_handling(self, mock_filter):
        """Тест обработки ошибок в networks action"""
        mock_filter.side_effect = Exception("Database error")
        
        url = reverse('equipment-networks', args=[self.router.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @patch('network_api.models.Equipment.objects.aggregate')
    def test_statistics_action_error_handling(self, mock_aggregate):
        """Тест обработки ошибок в statistics action"""
        mock_aggregate.side_effect = Exception("Database error")
        
        url = reverse('equipment-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class EquipmentViewSetIntegrationTests(TestCase):
    """Интеграционные тесты для EquipmentViewSet"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем несколько единиц оборудования
        self.equipment_data = [
            {'type': 'Router', 'port_count': 4, 'bandwidth': '1000 Mbps'},
            {'type': 'Switch', 'port_count': 24, 'bandwidth': '1000 Mbps'},
            {'type': 'Switch', 'port_count': 48, 'bandwidth': '10 Gbps'},
            {'type': 'Firewall', 'port_count': 8, 'bandwidth': '1 Gbps'},
            {'type': 'Access Point', 'port_count': 2, 'bandwidth': '1 Gbps'},
        ]
        
        self.equipment_objects = []
        for data in self.equipment_data:
            obj = Equipment.objects.create(**data)
            self.equipment_objects.append(obj)
        
        # Создаем сети
        self.networks = [
            Network.objects.create(name=f'Network {i}', ip_range=f'192.168.{i}.0/24')
            for i in range(1, 4)
        ]
        
        # Связываем оборудование с сетями
        self.equipment_objects[0].networks.add(self.networks[0], self.networks[1])
        self.equipment_objects[1].networks.add(self.networks[0])
        self.equipment_objects[2].networks.add(self.networks[2])
    
    def test_complex_filtering_scenarios(self):
        """Тест сложных сценариев фильтрации"""
        # Фильтр по типу и минимальному количеству портов
        response = self.client.get('/api/equipment/', {
            'type': 'switch',
            'min_ports': 30
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)  # Только Switch с 48 портами
        
        # Фильтр по нескольким параметрам
        response = self.client.get('/api/equipment/', {
            'min_ports': 5,
            'max_ports': 20,
            'search': 'firewall'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)  # Firewall
        self.assertEqual(response.data['equipment'][0]['type'], 'Firewall')
    
    def test_pagination_and_count(self):
        """Тест пагинации и подсчета"""
        response = self.client.get('/api/equipment/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 5)
        self.assertEqual(len(response.data['equipment']), 5)
    
    def test_ordering_by_type(self):
        """Тест сортировки по типу"""
        response = self.client.get('/api/equipment/')
        
        types = [item['type'] for item in response.data['equipment']]
        expected_types = ['Access Point', 'Firewall', 'Router', 'Switch', 'Switch']
        self.assertEqual(types, expected_types)