from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from network_api.models import Department, Computer, User, HostComputer

class DepartmentViewSetTests(APITestCase):

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
            employee_count=15
        )
        cls.department3 = Department.objects.create(
            room_number=305,
            internal_phone=789,
            employee_count=25
        )
        cls.department4 = Department.objects.create(
            room_number=410,
            internal_phone=321,
            employee_count=8
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
            os="Windows 11",
            inventory_number=5002,
            department=cls.department1
        )

        cls.computer3 = Computer.objects.create(
            serial_number=1003,
            model="Apple MacBook",
            os="macOS",
            inventory_number=5003,
            department=cls.department2
        )

        cls.user1 = User.objects.create(
            full_name="Иван Петров",
            phone="1234567890",
            email="ivan@company.com",
            position_id=1,
            department=cls.department1
        )
        cls.user2 = User.objects.create(
            full_name="Мария Иванова",
            phone="0987654321",
            email="maria@company.com",
            position_id=2,
            department=cls.department1
        )

        cls.user3 = User.objects.create(
            full_name="Петр Сидоров",
            phone="5555555555",
            email="petr@company.com",
            position_id=3,
            department=cls.department2
        )

        cls.host1 = HostComputer.objects.create(
            hostname="host-101-1",
            ip_address="192.168.1.101",
            mac_address="00:11:22:33:44:55",
            department=cls.department1
        )
        cls.host2 = HostComputer.objects.create(
            hostname="host-101-2",
            ip_address="192.168.1.102",
            mac_address="00:11:22:33:44:66",
            department=cls.department1
        )

        cls.host3 = HostComputer.objects.create(
            hostname="host-202-1",
            ip_address="192.168.2.101",
            mac_address="00:11:22:33:44:77",
            department=cls.department2
        )

        cls.base_url = '/api/departments/'

    def setUp(self):
        self.client = APIClient()

    def test_list_departments(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 4)
        else:
            self.assertEqual(len(response.data), 4)

    def test_list_filter_by_employee_count(self):
        response = self.client.get(self.base_url, {'employee_count': 15})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['room_number'], 202)
        else:
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]['room_number'], 202)

    def test_list_filter_min_employees(self):
        response = self.client.get(self.base_url, {'min_employees': 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 2)
        else:
            self.assertEqual(len(response.data), 2)

    def test_list_search_by_room_number(self):
        response = self.client.get(self.base_url, {'search': '101'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['room_number'], 101)
        else:
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]['room_number'], 101)

    def test_list_search_by_internal_phone(self):
        response = self.client.get(self.base_url, {'search': '456'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['internal_phone'], 456)
        else:
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]['internal_phone'], 456)

    def test_create_department_success(self):
        data = {
            'room_number': 515,
            'internal_phone': 999,
            'employee_count': 12,
            'employee_phones': [111, 222, 333]
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Department.objects.count(), 5)
        self.assertEqual(response.data['room_number'], 515)
        self.assertEqual(response.data['internal_phone'], 999)
        self.assertEqual(response.data['employee_count'], 12)
        self.assertEqual(len(response.data['employee_phones']), 3)

    def test_create_department_with_string_phone(self):
        data = {
            'room_number': 525,
            'internal_phone': '777-777',
            'employee_count': 10,
            'employee_phones': []
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['internal_phone'], 777777)

    def test_create_department_invalid_room_number(self):
        data = {
            'room_number': 50,
            'internal_phone': 123,
            'employee_count': 5,
            'employee_phones': []
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('room_number', response.data)

    def test_create_department_invalid_employee_count(self):
        data = {
            'room_number': 200,
            'internal_phone': 123,
            'employee_count': 100,
            'employee_phones': []
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('employee_count', response.data)

    def test_create_department_invalid_employee_phones(self):
        data = {
            'room_number': 300,
            'internal_phone': 123,
            'employee_count': 5,
            'employee_phones': ['not a number']
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('employee_phones', response.data)

    def test_create_department_validation_large_department_room(self):
        data = {
            'room_number': 150,
            'internal_phone': 123,
            'employee_count': 35,
            'employee_phones': []
        }
        response = self.client.post(self.base_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('room_number', response.data)

    def test_retrieve_department(self):
        url = f'{self.base_url}{self.department1.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['room_number'], 101)
        self.assertEqual(response.data['internal_phone'], 123)
        self.assertEqual(response.data['employee_count'], 5)

        self.assertIn('computers_count', response.data)
        self.assertIn('users_count', response.data)
        self.assertIn('host_computers_count', response.data)
        self.assertIn('first_host_computer_ip', response.data)
        self.assertIn('avg_computers_per_employee', response.data)
        self.assertIn('is_large_department', response.data)

        self.assertEqual(response.data['computers_count'], 2)
        self.assertEqual(response.data['users_count'], 2)
        self.assertEqual(response.data['host_computers_count'], 2)
        self.assertEqual(response.data['first_host_computer_ip'], '192.168.1.101')
        self.assertEqual(response.data['avg_computers_per_employee'], 0.4)
        self.assertFalse(response.data['is_large_department'])

    def test_retrieve_department_not_found(self):
        url = f'{self.base_url}999/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_department_success(self):
        url = f'{self.base_url}{self.department1.id}/'
        data = {
            'room_number': 111,
            'internal_phone': 111,
            'employee_count': 8,
            'employee_phones': [111, 222]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.department1.refresh_from_db()
        self.assertEqual(self.department1.room_number, 111)
        self.assertEqual(self.department1.internal_phone, 111)
        self.assertEqual(self.department1.employee_count, 8)

    def test_update_department_with_string_phone(self):
        url = f'{self.base_url}{self.department1.id}/'
        data = {
            'room_number': 112,
            'internal_phone': '222-333',
            'employee_count': 9,
            'employee_phones': []
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.department1.refresh_from_db()
        self.assertEqual(self.department1.internal_phone, 222333)

    def test_update_department_partial(self):
        url = f'{self.base_url}{self.department1.id}/'
        data = {
            'employee_count': 10
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.department1.refresh_from_db()
        self.assertEqual(self.department1.employee_count, 10)
        self.assertEqual(self.department1.room_number, 101)

    def test_update_department_invalid_data(self):
        url = f'{self.base_url}{self.department1.id}/'
        data = {
            'room_number': 50,
            'internal_phone': 123,
            'employee_count': 100,
            'employee_phones': []
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_department(self):
        url = f'{self.base_url}{self.department4.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Department.objects.count(), 3)

    def test_delete_department_with_related_objects(self):
        url = f'{self.base_url}{self.department1.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        Computer.objects.get(id=self.computer1.id).department is None
        User.objects.get(id=self.user1.id).department is None
        HostComputer.objects.get(id=self.host1.id).department is None

    def test_statistics_action_under_equipped(self):
        url = f'{self.base_url}{self.department3.id}/statistics/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertTrue(response.data['is_under_equipped'])

    def test_statistics_action_not_found(self):
        url = f'{self.base_url}999/statistics/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_host_computers_action(self):
        url = f'{self.base_url}{self.department1.id}/host_computers/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['department_id'], self.department1.id)
        self.assertEqual(response.data['room_number'], 101)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(len(response.data['host_computers']), 2)

        host_data = response.data['host_computers'][0]
        self.assertIn('id', host_data)
        self.assertIn('hostname', host_data)
        self.assertIn('ip_address', host_data)
        self.assertIn('mac_address', host_data)

    def test_host_computers_action_empty(self):
        url = f'{self.base_url}{self.department3.id}/host_computers/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['total'], 0)
        self.assertEqual(len(response.data['host_computers']), 0)

    def test_users_action(self):
        url = f'{self.base_url}{self.department1.id}/users/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['department_id'], self.department1.id)
        self.assertEqual(response.data['room_number'], 101)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(len(response.data['users']), 2)

        user_data = response.data['users'][0]
        self.assertIn('id', user_data)
        self.assertIn('full_name', user_data)
        self.assertIn('email', user_data)
        self.assertIn('phone', user_data)
        self.assertIn('position_id', user_data)

    def test_users_action_empty(self):
        empty_dept = Department.objects.create(
            room_number=600,
            internal_phone=999,
            employee_count=1
        )
        url = f'{self.base_url}{empty_dept.id}/users/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(response.data['total'], 0)
        self.assertEqual(len(response.data['users']), 0)

    def test_annotated_fields_in_list(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'results' in response.data:
            dept_data = response.data['results'][0]
        else:
            dept_data = response.data[0]

        self.assertIn('computers_count', dept_data)
        self.assertIn('users_count', dept_data)
        self.assertIn('host_computers_count', dept_data)
        self.assertIn('first_host_computer_ip', dept_data)

    def test_multiple_filters_combined(self):
        response = self.client.get(self.base_url, {
            'min_employees': 10,
            'search': '202'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
            self.assertEqual(response.data['results'][0]['room_number'], 202)
        else:
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]['room_number'], 202)