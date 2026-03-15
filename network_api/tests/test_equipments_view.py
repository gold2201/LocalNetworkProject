from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from datetime import date, timedelta
from network_api.models import Equipment, Network


class EquipmentViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.equipment1 = Equipment.objects.create(
            type="Switch",
            bandwidth=1000,
            port_count=24,
            setup_date="2023-01-15"
        )
        cls.equipment2 = Equipment.objects.create(
            type="Router",
            bandwidth=100,
            port_count=4,
            setup_date="2023-02-20"
        )
        cls.equipment3 = Equipment.objects.create(
            type="Switch",
            bandwidth=100,
            port_count=48,
            setup_date="2023-03-10"
        )
        cls.equipment4 = Equipment.objects.create(
            type="Firewall",
            bandwidth=1000,
            port_count=8,
            setup_date="2023-04-05"
        )
        cls.equipment5 = Equipment.objects.create(
            type="Access Point",
            bandwidth=100,
            port_count=2,
            setup_date="2023-05-12"
        )
        cls.equipment6 = Equipment.objects.create(
            type="Switch",
            bandwidth=1000,
            port_count=48,
            setup_date="2023-06-18"
        )

        cls.network1 = Network.objects.create(
            subnet_mask="255.255.255.0",
            vlan=100,
            ip_range="192.168.1.0/24",
            equipment=cls.equipment1
        )
        cls.network2 = Network.objects.create(
            subnet_mask="255.255.255.0",
            vlan=200,
            ip_range="192.168.2.0/24",
            equipment=cls.equipment1
        )
        cls.network3 = Network.objects.create(
            subnet_mask="255.255.255.0",
            vlan=300,
            ip_range="192.168.3.0/24",
            equipment=cls.equipment2
        )
        cls.network4 = Network.objects.create(
            subnet_mask="255.255.255.0",
            vlan=400,
            ip_range="192.168.4.0/24",
            equipment=cls.equipment3
        )

        cls.base_url = '/api/equipment/'

    def setUp(self):
        self.client = APIClient()

    def test_list_equipment(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn('count', response.data)
        self.assertIn('equipment', response.data)

        self.assertEqual(response.data['count'], 6)
        self.assertEqual(len(response.data['equipment']), 6)

    def test_list_equipment_ordered_by_type(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        types = [item['type'] for item in response.data['equipment']]
        self.assertEqual(types, sorted(types))

    def test_filter_by_type_exact(self):
        response = self.client.get(self.base_url, {'type': 'Switch'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)
        for item in response.data['equipment']:
            self.assertEqual(item['type'], 'Switch')

    def test_filter_by_type_icontains(self):
        response = self.client.get(self.base_url, {'type': 'sw'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)

    def test_filter_min_ports(self):
        response = self.client.get(self.base_url, {'min_ports': 24})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)
        for item in response.data['equipment']:
            self.assertGreaterEqual(item['port_count'], 24)

    def test_filter_max_ports(self):
        response = self.client.get(self.base_url, {'max_ports': 8})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)
        for item in response.data['equipment']:
            self.assertLessEqual(item['port_count'], 8)

    def test_filter_ports_range(self):
        response = self.client.get(self.base_url, {
            'min_ports': 8,
            'max_ports': 24
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 2)

    def test_filter_bandwidth_min(self):
        response = self.client.get(self.base_url, {'bandwidth_min': 1000})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)
        for item in response.data['equipment']:
            self.assertEqual(item['bandwidth'], 1000)

    def test_filter_bandwidth_max(self):
        response = self.client.get(self.base_url, {'bandwidth_max': 100})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)
        for item in response.data['equipment']:
            self.assertEqual(item['bandwidth'], 100)

    def test_filter_setup_date_after(self):
        response = self.client.get(self.base_url, {'setup_date_after': '2023-04-01'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)

    def test_filter_setup_date_range(self):
        response = self.client.get(self.base_url, {
            'setup_date_after': '2023-02-01',
            'setup_date_before': '2023-05-01'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)

    def test_filter_search_by_type(self):
        response = self.client.get(self.base_url, {'search': 'switch'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)

    def test_filter_search_by_bandwidth(self):
        response = self.client.get(self.base_url, {'search': '1000'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 3)

    def test_filter_combined(self):
        response = self.client.get(self.base_url, {
            'type': 'Switch',
            'min_ports': 24,
            'bandwidth_min': 1000
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['count'], 2)

    def test_retrieve_equipment(self):
        url = f'{self.base_url}{self.equipment1.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['id'], self.equipment1.id)
        self.assertEqual(response.data['type'], 'Switch')
        self.assertEqual(response.data['bandwidth'], 1000)
        self.assertEqual(response.data['port_count'], 24)
        self.assertEqual(response.data['setup_date'], '2023-01-15')

        self.assertIn('type_of_bandwidth', response.data)
        self.assertEqual(response.data['type_of_bandwidth'], 'Онлайн-игры')

    def test_retrieve_equipment_type_of_bandwidth(self):
        url = f'{self.base_url}{self.equipment2.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type_of_bandwidth'], 'Базовый интернет')

        url = f'{self.base_url}{self.equipment1.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type_of_bandwidth'], 'Онлайн-игры')

        equipment = Equipment.objects.create(
            type="Test",
            bandwidth=500,
            port_count=10,
            setup_date="2023-01-01"
        )
        url = f'{self.base_url}{equipment.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['type_of_bandwidth'], 'Видеозвонки')

    def test_retrieve_equipment_not_found(self):
        url = f'{self.base_url}999/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_networks_action(self):
        url = f'{self.base_url}{self.equipment1.id}/networks/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 2)

        vlans = [network['vlan'] for network in response.data]
        self.assertIn(100, vlans)
        self.assertIn(200, vlans)

    def test_networks_action_empty(self):
        url = f'{self.base_url}{self.equipment5.id}/networks/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 0)

    def test_statistics_action_empty_database(self):
        Equipment.objects.all().delete()

        url = f'{self.base_url}statistics/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['total_equipment'], 0)
        self.assertIsNone(response.data['average_ports'])
        self.assertIsNone(response.data['max_ports'])
        self.assertIsNone(response.data['min_ports'])
        self.assertEqual(response.data['types_count'], 0)
        self.assertEqual(response.data['total_networks'], 0)
        self.assertEqual(response.data['type_distribution'], [])

    def test_create_not_allowed(self):
        data = {
            'type': 'Test',
            'bandwidth': 100,
            'port_count': 10,
            'setup_date': '2023-01-01'
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_not_allowed(self):
        url = f'{self.base_url}{self.equipment1.id}/'
        data = {
            'type': 'Updated',
            'bandwidth': 200,
            'port_count': 20,
            'setup_date': '2023-01-01'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_not_allowed(self):
        url = f'{self.base_url}{self.equipment1.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_patch_not_allowed(self):
        url = f'{self.base_url}{self.equipment1.id}/'
        data = {'type': 'Updated'}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_pagination_if_implemented(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn('count', response.data)
        self.assertIn('equipment', response.data)
