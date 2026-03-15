from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from network_api.models import (
    Department, Computer, NetworkComputer, User, Software,
    Network, Equipment
)


class ComputerViewSetTests(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.department1 = Department.objects.create(
            room_number=101,
            internal_phone=123,
            employee_count=5
        )
        cls.department2 = Department.objects.create(
            room_number=202,
            internal_phone=456,
            employee_count=10
        )

        cls.computer1 = Computer.objects.create(
            serial_number=1001,
            model="Dell OptiPlex",
            os="Windows 10",
            inventory_number=5001,
            department=cls.department1
        )
        cls.computer2 = Computer.objects.create(
            serial_number=1002,
            model="HP EliteBook",
            os="Linux Ubuntu",
            inventory_number=5002,
            department=cls.department2
        )
        cls.computer3 = Computer.objects.create(
            serial_number=1003,
            model="Apple MacBook",
            os="macOS",
            inventory_number=5003,
            department=cls.department1
        )

        cls.user = User.objects.create(
            full_name="Иван Петров",
            phone="123456",
            email="ivan@company.com",
            position_id=1,
            department=cls.department1
        )
        cls.user.computers.add(cls.computer1)

        cls.software = Software.objects.create(
            name="PyCharm",
            version="2023.1",
            license="Commercial",
            vendor="JetBrains"
        )
        cls.software.computers.add(cls.computer1)

        cls.equipment = Equipment.objects.create(
            type="Switch",
            bandwidth=1000,
            port_count=24,
            setup_date="2023-01-01"
        )

        cls.network = Network.objects.create(
            subnet_mask="255.255.255.0",
            vlan=100,
            ip_range="192.168.1.0/24",
            equipment=cls.equipment
        )

        cls.network_connection = NetworkComputer.objects.create(
            computer=cls.computer1,
            network=cls.network,
            ip_address="192.168.1.10",
            mac_address="00:11:22:33:44:55",
            speed=1000
        )

        cls.base_url = '/api/computers/'

    def setUp(self):
        self.client = APIClient()

    def test_list_computers(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 3)
        else:
            self.assertEqual(len(response.data), 3)

    def test_list_filter_by_department(self):
        response = self.client.get(self.base_url, {'department': self.department1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 2)
        else:
            self.assertEqual(len(response.data), 2)

    def test_list_search(self):
        response = self.client.get(self.base_url, {'search': 'Dell'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['model'], 'Dell OptiPlex')
        else:
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]['model'], 'Dell OptiPlex')

    def test_create_computer_success(self):
        data = {
            'serial_number': 2001,
            'model': 'Lenovo ThinkPad',
            'os': 'Windows 11',
            'inventory_number': 6001,
            'department': self.department1.id
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Computer.objects.count(), 4)
        self.assertEqual(Computer.objects.get(serial_number=2001).model, 'Lenovo ThinkPad')

    def test_create_computer_duplicate_serial(self):
        data = {
            'serial_number': 1001,
            'model': 'Duplicate',
            'os': 'Windows',
            'inventory_number': 9999,
            'department': self.department1.id
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_retrieve_computer(self):
        url = f'{self.base_url}{self.computer1.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['serial_number'], self.computer1.serial_number)
        self.assertIn('department_info', response.data)
        self.assertIn('users_count', response.data)
        self.assertIn('software_list', response.data)

    def test_update_computer_success(self):
        url = f'{self.base_url}{self.computer2.id}/'
        data = {
            'serial_number': 1002,
            'model': 'HP EliteBook Updated',
            'os': 'Windows 10',
            'inventory_number': 5002,
            'department': self.department2.id
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.computer2.refresh_from_db()
        self.assertEqual(self.computer2.model, 'HP EliteBook Updated')
        self.assertEqual(self.computer2.os, 'Windows 10')

    def test_update_computer_duplicate_serial(self):
        url = f'{self.base_url}{self.computer2.id}/'
        data = {
            'serial_number': 1001,
            'model': 'HP EliteBook',
            'os': 'Linux',
            'inventory_number': 5002,
            'department': self.department2.id
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_delete_computer(self):
        url = f'{self.base_url}{self.computer3.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Computer.objects.count(), 2)

    def test_report_action(self):
        url = f'{self.base_url}report/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('by_os_and_department', response.data)
        self.assertIn('by_department', response.data)
        self.assertTrue(len(response.data['by_os_and_department']) > 0)

    def test_details_action(self):
        url = f'{self.base_url}{self.computer1.id}/details/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('users', response.data)
        self.assertIn('software', response.data)
        self.assertIn('network_connections', response.data)
        self.assertEqual(len(response.data['users']), 1)
        self.assertEqual(len(response.data['software']), 1)
        self.assertEqual(len(response.data['network_connections']), 1)

    def test_details_action_not_found(self):
        url = f'{self.base_url}999/details/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)