from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.db.models import Q

from network_api.models import Software, Computer, Department
from network_api.views import SoftwareViewSet


class SoftwareViewSetTestCase(APITestCase):
    """Тесты для SoftwareViewSet"""
    
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
        
        # Создаем тестовые компьютеры
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
        
        self.computer4 = Computer.objects.create(
            model='ThinkPad',
            os='Windows 10',
            serial_number='SN004',
            inventory_number='INV004',
            department=self.department2
        )
        
        # Создаем тестовое ПО
        self.software1 = Software.objects.create(
            name='Microsoft Office',
            version='2021',
            vendor='Microsoft',
            license='Commercial'
        )
        
        self.software2 = Software.objects.create(
            name='Google Chrome',
            version='120.0',
            vendor='Google',
            license='Free'
        )
        
        self.software3 = Software.objects.create(
            name='Adobe Photoshop',
            version='2023',
            vendor='Adobe',
            license='Commercial'
        )
        
        self.software4 = Software.objects.create(
            name='VLC Media Player',
            version='3.0',
            vendor='VideoLAN',
            license='Open Source'
        )
        
        self.software5 = Software.objects.create(
            name='Microsoft Office',
            version='2019',
            vendor='Microsoft',
            license='Commercial'
        )
        
        # Устанавливаем связи ПО с компьютерами
        self.software1.computers.add(self.computer1, self.computer2, self.computer3)
        self.software2.computers.add(self.computer1, self.computer4)
        self.software3.computers.add(self.computer2)
        self.software4.computers.add(self.computer3, self.computer4)
        
        # URL для API
        self.software_url = reverse('software-list')
        
    def authenticate(self):
        """Вспомогательный метод для аутентификации"""
        self.client.force_authenticate(user=self.user)
    
    # Тесты для базовых CRUD операций
    
    def test_list_software(self):
        """Тест получения списка ПО"""
        self.authenticate()
        response = self.client.get(self.software_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
    
    def test_retrieve_software(self):
        """Тест получения конкретного ПО"""
        self.authenticate()
        url = reverse('software-detail', args=[self.software1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Microsoft Office')
        self.assertEqual(response.data['version'], '2021')
        self.assertEqual(response.data['vendor'], 'Microsoft')
    
    def test_create_software_success(self):
        """Тест успешного создания ПО"""
        self.authenticate()
        data = {
            'name': 'Visual Studio Code',
            'version': '1.85',
            'vendor': 'Microsoft',
            'license': 'Free'
        }
        
        response = self.client.post(self.software_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Software.objects.count(), 6)
        self.assertEqual(response.data['name'], 'Visual Studio Code')
    
    def test_create_software_missing_required_field(self):
        """Тест создания ПО с отсутствующим обязательным полем"""
        self.authenticate()
        data = {
            'name': 'Test Software',
            'version': '1.0',
            # Отсутствует vendor
            'license': 'Free'
        }
        
        response = self.client.post(self.software_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Missing required field', response.data['error'])
    
    def test_create_software_duplicate_name_version(self):
        """Тест создания ПО с дублирующимся названием и версией"""
        self.authenticate()
        data = {
            'name': 'Microsoft Office',
            'version': '2021',  # Уже существует
            'vendor': 'Microsoft',
            'license': 'Commercial'
        }
        
        response = self.client.post(self.software_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(
            response.data['error'],
            'ПО с таким названием и версией уже существует'
        )
    
    def test_update_software_success(self):
        """Тест успешного обновления ПО"""
        self.authenticate()
        url = reverse('software-detail', args=[self.software1.id])
        data = {
            'name': 'Microsoft Office',
            'version': '2021',
            'vendor': 'Microsoft Corporation',  # Изменяем
            'license': 'Commercial'
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.software1.refresh_from_db()
        self.assertEqual(self.software1.vendor, 'Microsoft Corporation')
    
    def test_update_software_duplicate_name_version(self):
        """Тест обновления с названием и версией, которые уже используются"""
        self.authenticate()
        url = reverse('software-detail', args=[self.software1.id])
        data = {
            'name': 'Microsoft Office',
            'version': '2019',  # Версия software5
            'vendor': 'Microsoft',
            'license': 'Commercial'
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_partial_update_software(self):
        """Тест частичного обновления ПО"""
        self.authenticate()
        url = reverse('software-detail', args=[self.software1.id])
        data = {
            'license': 'Enterprise'
        }
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.software1.refresh_from_db()
        self.assertEqual(self.software1.license, 'Enterprise')
        self.assertEqual(self.software1.name, 'Microsoft Office')  # Не изменилось
    
    def test_delete_software(self):
        """Тест удаления ПО"""
        self.authenticate()
        url = reverse('software-detail', args=[self.software1.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Software.objects.count(), 4)
    
    # Тесты для фильтрации и поиска
    
    def test_filter_by_vendor(self):
        """Тест фильтрации по производителю"""
        self.authenticate()
        response = self.client.get(self.software_url, {'vendor': 'Microsoft'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Office 2021 и Office 2019
        self.assertTrue(all(item['vendor'] == 'Microsoft' for item in response.data))
    
    def test_filter_by_license(self):
        """Тест фильтрации по лицензии"""
        self.authenticate()
        response = self.client.get(self.software_url, {'license': 'Commercial'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # Office 2021, Photoshop, Office 2019
        self.assertTrue(all('Commercial' in item['license'] for item in response.data))
    
    def test_search_by_name(self):
        """Тест поиска по названию"""
        self.authenticate()
        response = self.client.get(self.software_url, {'search': 'Office'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all('Office' in item['name'] for item in response.data))
    
    def test_search_by_version(self):
        """Тест поиска по версии"""
        self.authenticate()
        response = self.client.get(self.software_url, {'search': '2021'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Microsoft Office')
        self.assertEqual(response.data[0]['version'], '2021')
    
    def test_search_by_vendor(self):
        """Тест поиска по производителю"""
        self.authenticate()
        response = self.client.get(self.software_url, {'search': 'Adobe'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Adobe Photoshop')
    
    def test_search_by_license(self):
        """Тест поиска по лицензии"""
        self.authenticate()
        response = self.client.get(self.software_url, {'search': 'Open Source'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'VLC Media Player')
    
    # Тесты для фильтрации по типу лицензии через параметр license_type
    
    def test_filter_by_license_type_trial(self):
        """Тест фильтрации по типу лицензии 'trial'"""
        self.authenticate()
        
        # Создаем ПО с trial лицензией
        trial_software = Software.objects.create(
            name='Trial Software',
            version='1.0',
            vendor='Test',
            license='trial version'
        )
        
        response = self.client.get(self.software_url, {'license_type': 'trial'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(item['license'] == 'trial version' for item in response.data))
    
    def test_filter_by_license_type_commercial(self):
        """Тест фильтрации по типу лицензии 'commercial'"""
        self.authenticate()
        response = self.client.get(self.software_url, {'license_type': 'commercial'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Должны получить Commercial и paid лицензии
        for item in response.data:
            self.assertTrue(
                'commercial' in item['license'].lower() or 
                'paid' in item['license'].lower()
            )
    
    def test_filter_by_license_type_free(self):
        """Тест фильтрации по типу лицензии 'free'"""
        self.authenticate()
        response = self.client.get(self.software_url, {'license_type': 'free'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Должны получить Free и Open Source
        for item in response.data:
            self.assertTrue(
                'free' in item['license'].lower() or 
                'open source' in item['license'].lower()
            )
    
    def test_combined_filters(self):
        """Тест комбинации фильтров"""
        self.authenticate()
        response = self.client.get(
            self.software_url, 
            {
                'search': 'Microsoft',
                'license_type': 'commercial'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Только Microsoft с commercial
    
    # Тесты для кастомных action методов
    
    def test_popularity_report_action(self):
        """Тест получения отчета о популярности ПО"""
        self.authenticate()
        url = reverse('software-popularity-report')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('software', response.data)
        self.assertIn('total_installations', response.data)
        
        # Проверяем сортировку по убыванию количества установок
        software_list = response.data['software']
        self.assertEqual(software_list[0]['name'], 'Microsoft Office')  # 3 установки
        self.assertEqual(software_list[1]['name'], 'Google Chrome')  # 2 установки
        self.assertEqual(software_list[2]['name'], 'VLC Media Player')  # 2 установки
        
        # Проверяем общее количество установок
        self.assertEqual(response.data['total_installations'], 3 + 2 + 1 + 2)  # 8 установок
    
    def test_compatible_computers_action(self):
        """Тест получения совместимых компьютеров для ПО"""
        self.authenticate()
        url = reverse('software-compatible-computers', args=[self.software1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['software'], 'Microsoft Office 2021')
        self.assertEqual(response.data['vendor'], 'Microsoft')
        self.assertEqual(response.data['license'], 'Commercial')
        self.assertEqual(response.data['compatible_computers_count'], 3)
        self.assertEqual(len(response.data['compatible_computers']), 3)
        
        # Проверяем структуру данных компьютера
        computer_data = response.data['compatible_computers'][0]
        self.assertIn('id', computer_data)
        self.assertIn('model', computer_data)
        self.assertIn('os', computer_data)
        self.assertIn('department__room_number', computer_data)
    
    def test_compatible_computers_action_no_computers(self):
        """Тест получения совместимых компьютеров для ПО без установок"""
        self.authenticate()
        
        # Создаем ПО без компьютеров
        new_software = Software.objects.create(
            name='New Software',
            version='1.0',
            vendor='Test',
            license='Free'
        )
        
        url = reverse('software-compatible-computers', args=[new_software.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['compatible_computers_count'], 0)
        self.assertEqual(len(response.data['compatible_computers']), 0)
    
    def test_license_summary_action(self):
        """Тест получения сводки по лицензиям"""
        self.authenticate()
        url = reverse('software-license-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('license_summary', response.data)
        self.assertIn('total_software', response.data)
        self.assertIn('total_installations', response.data)
        
        self.assertEqual(response.data['total_software'], 5)
        self.assertEqual(response.data['total_installations'], 8)
        
        # Проверяем структуру сводки по лицензиям
        license_summary = response.data['license_summary']
        self.assertEqual(len(license_summary), 3)  # Commercial, Free, Open Source
        
        # Находим Commercial
        commercial = next((item for item in license_summary if item['license'] == 'Commercial'), None)
        self.assertIsNotNone(commercial)
        self.assertEqual(commercial['count'], 3)  # 3 ПО с Commercial
        self.assertEqual(commercial['total_installations'], 3 + 1 + 0)  # Office2021(3) + Photoshop(1) + Office2019(0)
    
    # Тесты для проверки get_queryset с фильтрами
    
    def test_get_queryset_with_search_filter(self):
        """Тест метода get_queryset с поисковым фильтром"""
        self.authenticate()
        
        # Создаем request с поиском
        response = self.client.get(self.software_url, {'search': 'Microsoft'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_get_queryset_with_license_type_filter(self):
        """Тест метода get_queryset с фильтром по типу лицензии"""
        self.authenticate()
        
        response = self.client.get(self.software_url, {'license_type': 'free'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Должны получить Free и Open Source
        licenses = [item['license'] for item in response.data]
        self.assertTrue(any('Free' in lic or 'Open Source' in lic for lic in licenses))
    
    def test_get_queryset_without_filters(self):
        """Тест метода get_queryset без фильтров"""
        self.authenticate()
        
        # Создаем ViewSet для прямого тестирования
        viewset = SoftwareViewSet()
        viewset.request = self.client.get('/').wsgi_request
        viewset.request.user = self.user
        viewset.action = 'list'
        
        queryset = viewset.get_queryset()
        self.assertEqual(queryset.count(), 5)
    
    # Тесты для обработки ошибок
    
    def test_create_software_exception_handling(self):
        """Тест обработки исключений при создании"""
        self.authenticate()
        
        # Создаем данные, которые вызовут исключение в сериализаторе
        data = {
            'name': 'Test',
            'version': '1.0',
            'vendor': 'Test',
            'license': 'A' * 1000  # Слишком длинная строка
        }
        
        response = self.client.post(self.software_url, data)
        
        # Должна быть ошибка 400
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('network_api.models.Software.objects.annotate')
    def test_popularity_report_error_handling(self, mock_annotate):
        """Тест обработки ошибок в popularity_report action"""
        mock_annotate.side_effect = Exception("Database error")
        
        self.authenticate()
        url = reverse('software-popularity-report')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
    
    @patch('network_api.views.SoftwareViewSet.get_object')
    def test_compatible_computers_error_handling(self, mock_get_object):
        """Тест обработки ошибок в compatible_computers action"""
        mock_get_object.side_effect = Exception("Database error")
        
        self.authenticate()
        url = reverse('software-compatible-computers', args=[self.software1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @patch('network_api.models.Software.objects.values')
    def test_license_summary_error_handling(self, mock_values):
        """Тест обработки ошибок в license_summary action"""
        mock_values.side_effect = Exception("Database error")
        
        self.authenticate()
        url = reverse('software-license-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # Тесты для проверки prefetch_related
    
    def test_queryset_prefetch_related(self):
        """Тест оптимизации запросов с prefetch_related"""
        self.authenticate()
        
        viewset = SoftwareViewSet()
        viewset.request = self.client.get('/').wsgi_request
        viewset.request.user = self.user
        viewset.action = 'list'
        
        queryset = viewset.get_queryset()
        
        # Проверяем, что используется prefetch_related
        # (не можем проверить напрямую, но можем проверить количество запросов)
        with self.assertNumQueries(2):  # Один для ПО, один для prefetch_related computers
            for software in queryset:
                # Доступ к связанным компьютерам не должен создавать новые запросы
                count = software.computers.count()


class SoftwareViewSetUnitTests(TestCase):
    """Модульные тесты для отдельных методов SoftwareViewSet"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = SoftwareViewSet
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        self.software = Software.objects.create(
            name='Test Software',
            version='1.0',
            vendor='Test Vendor',
            license='Commercial'
        )
    
    def test_create_method_with_missing_fields(self):
        """Тест метода create с отсутствующими полями"""
        request = self.factory.post('/', {
            'name': 'Test',
            # Отсутствует version
            'vendor': 'Test',
            'license': 'Free'
        })
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        
        response = view.create(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing required field', response.data['error'])
    
    def test_create_method_with_duplicate_name_version(self):
        """Тест метода create с дублирующимся названием и версией"""
        request = self.factory.post('/', {
            'name': self.software.name,
            'version': self.software.version,
            'vendor': 'New Vendor',
            'license': 'Free'
        })
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        
        response = view.create(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'ПО с таким названием и версией уже существует')
    
    def test_update_method_with_duplicate_name_version(self):
        """Тест метода update с дублирующимся названием и версией"""
        # Создаем другое ПО
        other_software = Software.objects.create(
            name='Other Software',
            version='2.0',
            vendor='Other Vendor',
            license='Free'
        )
        
        request = self.factory.put('/', {
            'name': other_software.name,
            'version': other_software.version,
            'vendor': 'Updated Vendor',
            'license': 'Commercial'
        })
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        view.kwargs = {'pk': self.software.pk}
        
        # Мокаем get_object для возврата нашего ПО
        with patch.object(view, 'get_object', return_value=self.software):
            response = view.update(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'ПО с таким названием и версией уже существует')
    
    def test_update_method_with_same_name_version(self):
        """Тест метода update с тем же названием и версией (должно работать)"""
        request = self.factory.put('/', {
            'name': self.software.name,
            'version': self.software.version,
            'vendor': 'Updated Vendor',
            'license': 'Commercial'
        })
        request.user = self.user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        view.kwargs = {'pk': self.software.pk}
        
        # Мокаем методы для успешного обновления
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = True
        mock_serializer.data = {'id': self.software.id, 'vendor': 'Updated Vendor'}
        
        with patch.object(view, 'get_object', return_value=self.software):
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                with patch.object(view, 'perform_update'):
                    response = view.update(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class SoftwareViewSetIntegrationTests(TestCase):
    """Интеграционные тесты для SoftwareViewSet"""
    
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
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
        
        # Создаем компьютеры
        self.computers = []
        for i in range(1, 11):
            dept = self.departments[i % 3]
            computer = Computer.objects.create(
                model=f'Computer Model {i}',
                os='Windows' if i % 2 == 0 else 'Linux',
                serial_number=f'SN-COMP-{i:03d}',
                inventory_number=f'INV-COMP-{i:03d}',
                department=dept
            )
            self.computers.append(computer)
        
        # Создаем ПО
        self.software_list = []
        software_data = [
            {'name': 'Windows 10', 'version': '10.0', 'vendor': 'Microsoft', 'license': 'Commercial'},
            {'name': 'Windows 11', 'version': '11.0', 'vendor': 'Microsoft', 'license': 'Commercial'},
            {'name': 'Ubuntu', 'version': '22.04', 'vendor': 'Canonical', 'license': 'Open Source'},
            {'name': 'Firefox', 'version': '120.0', 'vendor': 'Mozilla', 'license': 'Open Source'},
            {'name': 'Chrome', 'version': '120.0', 'vendor': 'Google', 'license': 'Free'},
            {'name': 'Photoshop', 'version': '2023', 'vendor': 'Adobe', 'license': 'Commercial'},
            {'name': 'VS Code', 'version': '1.85', 'vendor': 'Microsoft', 'license': 'Free'},
        ]
        
        for data in software_data:
            software = Software.objects.create(**data)
            self.software_list.append(software)
        
        # Устанавливаем связи (каждый компьютер имеет несколько ПО)
        for i, computer in enumerate(self.computers):
            # Каждый компьютер имеет 3-5 программ
            for j in range(i % 3 + 3):
                software_idx = (i + j) % len(self.software_list)
                computer.software.add(self.software_list[software_idx])
    
    def test_complex_filtering_scenarios(self):
        """Тест сложных сценариев фильтрации"""
        # Фильтр по производителю и типу лицензии
        response = self.client.get('/api/software/', {
            'vendor': 'Microsoft',
            'license_type': 'commercial'
        })
        
        self.assertEqual(response.status_code, 200)
        # Проверяем, что все результаты от Microsoft с commercial лицензией
        for item in response.data:
            self.assertEqual(item['vendor'], 'Microsoft')
            self.assertTrue(
                'commercial' in item['license'].lower() or 
                'paid' in item['license'].lower()
            )
        
        # Поиск и фильтр по типу лицензии
        response = self.client.get('/api/software/', {
            'search': 'windows',
            'license_type': 'commercial'
        })
        
        self.assertEqual(response.status_code, 200)
        for item in response.data:
            self.assertTrue('windows' in item['name'].lower())
    
    def test_popularity_report_with_complex_data(self):
        """Тест отчета о популярности с полными данными"""
        url = reverse('software-popularity-report')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], len(self.software_list))
        
        # Проверяем, что данные отсортированы по убыванию популярности
        software_list = response.data['software']
        prev_count = float('inf')
        for software in software_list:
            current_count = software.get('installation_count', 0)
            self.assertLessEqual(current_count, prev_count)
            prev_count = current_count
    
    def test_license_summary_with_complex_data(self):
        """Тест сводки по лицензиям с полными данными"""
        url = reverse('software-license-summary')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Проверяем общее количество ПО
        self.assertEqual(response.data['total_software'], len(self.software_list))
        
        # Проверяем, что все типы лицензий представлены
        license_types = [item['license'] for item in response.data['license_summary']]
        self.assertIn('Commercial', license_types)
        self.assertIn('Open Source', license_types)
        self.assertIn('Free', license_types)
        
        # Проверяем, что сумма count равна общему количеству ПО
        total_count = sum(item['count'] for item in response.data['license_summary'])
        self.assertEqual(total_count, len(self.software_list))