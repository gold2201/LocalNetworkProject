from django.test import TestCase
from django.contrib.auth.models import User as AuthUser
from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.db.models import Q

from network_api.models import User, Department, Position, Computer


class UserViewSetTestCase(APITestCase):
    """Тесты для UserViewSet"""
    
    def setUp(self):
        """Подготовка данных перед каждым тестом"""
        # Создаем тестового пользователя для аутентификации
        self.auth_user = AuthUser.objects.create_user(username='testuser', password='testpass')
        
        # Создаем тестовые должности
        self.position1 = Position.objects.create(
            name='Director',
            salary=200000
        )
        self.position2 = Position.objects.create(
            name='Manager',
            salary=150000
        )
        self.position3 = Position.objects.create(
            name='Developer',
            salary=120000
        )
        self.position4 = Position.objects.create(
            name='Tester',
            salary=100000
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
            room_number='103',
            internal_phone=9012,
            employee_count=3
        )
        
        # Создаем тестовых пользователей
        self.user1 = User.objects.create(
            full_name='John Doe',
            email='john@example.com',
            phone='1234567890',
            position=self.position1,
            department=self.department1
        )
        
        self.user2 = User.objects.create(
            full_name='Jane Smith',
            email='jane@example.com',
            phone='0987654321',
            position=self.position2,
            department=self.department1
        )
        
        self.user3 = User.objects.create(
            full_name='Bob Johnson',
            email='bob@example.com',
            phone='5551234567',
            position=self.position2,
            department=self.department2
        )
        
        self.user4 = User.objects.create(
            full_name='Alice Brown',
            email='alice@example.com',
            phone='7778889999',
            position=self.position3,
            department=self.department2
        )
        
        self.user5 = User.objects.create(
            full_name='Charlie Wilson',
            email='charlie@example.com',
            phone='3334445555',
            position=self.position4,
            department=self.department3
        )
        
        # Создаем компьютеры для пользователей
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
        
        # Назначаем компьютеры пользователям
        self.user1.computers.add(self.computer1, self.computer2)
        self.user2.computers.add(self.computer1)
        self.user4.computers.add(self.computer3)
        
        # URL для API
        self.users_url = reverse('user-list')
        
    def authenticate(self):
        """Вспомогательный метод для аутентификации"""
        self.client.force_authenticate(user=self.auth_user)
    
    # Тесты для базовых CRUD операций
    
    def test_list_users(self):
        """Тест получения списка пользователей"""
        self.authenticate()
        response = self.client.get(self.users_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)
    
    def test_retrieve_user(self):
        """Тест получения конкретного пользователя"""
        self.authenticate()
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], 'John Doe')
        self.assertEqual(response.data['email'], 'john@example.com')
        self.assertEqual(response.data['phone'], '1234567890')
        self.assertEqual(response.data['position_id'], self.position1.id)
        self.assertEqual(response.data['department'], self.department1.id)
    
    def test_create_user_success(self):
        """Тест успешного создания пользователя"""
        self.authenticate()
        data = {
            'full_name': 'New User',
            'email': 'newuser@example.com',
            'phone': '1112223333',
            'position_id': self.position3.id,
            'department': self.department2.id
        }
        
        response = self.client.post(self.users_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 6)
        self.assertEqual(response.data['full_name'], 'New User')
        self.assertEqual(response.data['email'], 'newuser@example.com')
    
    def test_create_user_missing_required_field(self):
        """Тест создания пользователя с отсутствующим обязательным полем"""
        self.authenticate()
        data = {
            'full_name': 'New User',
            'email': 'newuser@example.com',
            # Отсутствует phone
            'position_id': self.position3.id,
        }
        
        response = self.client.post(self.users_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertIn('Missing required field', response.data['error'])
    
    def test_create_user_duplicate_email(self):
        """Тест создания пользователя с существующим email"""
        self.authenticate()
        data = {
            'full_name': 'Another John',
            'email': 'john@example.com',  # Уже существует
            'phone': '9998887777',
            'position_id': self.position3.id,
            'department': self.department2.id
        }
        
        response = self.client.post(self.users_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
        self.assertEqual(
            response.data['error'],
            'Пользователь с таким email уже существует'
        )
    
    def test_update_user_success(self):
        """Тест успешного обновления пользователя"""
        self.authenticate()
        url = reverse('user-detail', args=[self.user1.id])
        data = {
            'full_name': 'John Doe Updated',
            'email': 'john@example.com',  # Тот же email
            'phone': '1112223333',
            'position_id': self.position2.id,  # Изменяем должность
            'department': self.department2.id  # Изменяем отдел
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.full_name, 'John Doe Updated')
        self.assertEqual(self.user1.phone, '1112223333')
        self.assertEqual(self.user1.position_id, self.position2.id)
        self.assertEqual(self.user1.department_id, self.department2.id)
    
    def test_update_user_duplicate_email(self):
        """Тест обновления с email, который уже используется другим пользователем"""
        self.authenticate()
        url = reverse('user-detail', args=[self.user1.id])
        data = {
            'full_name': 'John Doe',
            'email': 'jane@example.com',  # Email user2
            'phone': '1234567890',
            'position_id': self.position1.id,
            'department': self.department1.id
        }
        
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_partial_update_user(self):
        """Тест частичного обновления пользователя"""
        self.authenticate()
        url = reverse('user-detail', args=[self.user1.id])
        data = {
            'phone': '9998887777'
        }
        
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.phone, '9998887777')
        self.assertEqual(self.user1.full_name, 'John Doe')  # Не изменилось
    
    def test_delete_user(self):
        """Тест удаления пользователя"""
        self.authenticate()
        url = reverse('user-detail', args=[self.user1.id])
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(User.objects.count(), 4)
    
    # Тесты для фильтрации и поиска
    
    def test_filter_by_department(self):
        """Тест фильтрации по отделу"""
        self.authenticate()
        response = self.client.get(self.users_url, {'department': self.department1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # user1 и user2
        self.assertTrue(all(item['department'] == self.department1.id for item in response.data))
    
    def test_filter_by_position(self):
        """Тест фильтрации по должности"""
        self.authenticate()
        response = self.client.get(self.users_url, {'position_id': self.position2.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # user2 и user3
        self.assertTrue(all(item['position_id'] == self.position2.id for item in response.data))
    
    def test_search_by_full_name(self):
        """Тест поиска по полному имени"""
        self.authenticate()
        response = self.client.get(self.users_url, {'search': 'John'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['full_name'], 'John Doe')
    
    def test_search_by_email(self):
        """Тест поиска по email"""
        self.authenticate()
        response = self.client.get(self.users_url, {'search': 'jane@example.com'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['full_name'], 'Jane Smith')
    
    def test_search_by_phone(self):
        """Тест поиска по телефону"""
        self.authenticate()
        response = self.client.get(self.users_url, {'search': '5551234567'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['full_name'], 'Bob Johnson')
    
    def test_combined_filters(self):
        """Тест комбинации фильтров"""
        self.authenticate()
        response = self.client.get(
            self.users_url, 
            {
                'department': self.department1.id,
                'search': 'Jane'
            }
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['full_name'], 'Jane Smith')
    
    # Тесты для кастомных action методов
    
    def test_managers_action(self):
        """Тест получения менеджеров (position_id = 1 или 2)"""
        self.authenticate()
        url = reverse('user-managers')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('managers', response.data)
        
        # Должны получить пользователей с position_id 1 и 2
        self.assertEqual(response.data['count'], 3)  # user1 (pos1), user2 (pos2), user3 (pos2)
        self.assertEqual(len(response.data['managers']), 3)
        
        # Проверяем, что все пользователи имеют position_id 1 или 2
        for manager in response.data['managers']:
            self.assertIn(manager['position_id'], [self.position1.id, self.position2.id])
    
    def test_non_manager_action(self):
        """Тест получения не-менеджеров (position_id != 1 и != 2)"""
        self.authenticate()
        url = reverse('user-non-manager')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('non_managers', response.data)
        
        # Должны получить пользователей с position_id != 1 и != 2
        self.assertEqual(response.data['count'], 2)  # user4 (pos3), user5 (pos4)
        self.assertEqual(len(response.data['non_managers']), 2)
        
        # Проверяем, что все пользователи имеют position_id не 1 и не 2
        for non_manager in response.data['non_managers']:
            self.assertNotIn(non_manager['position_id'], [self.position1.id, self.position2.id])
    
    def test_computer_history_action(self):
        """Тест получения истории компьютеров пользователя"""
        self.authenticate()
        url = reverse('user-computer-history', args=[self.user1.id])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], 'John Doe')
        self.assertEqual(response.data['total_computers'], 2)
        self.assertEqual(len(response.data['computers']), 2)
        
        # Проверяем структуру данных компьютера
        computer_data = response.data['computers'][0]
        self.assertIn('id', computer_data)
        self.assertIn('model', computer_data)
        self.assertIn('os', computer_data)
        self.assertIn('serial_number', computer_data)
    
    def test_computer_history_action_no_computers(self):
        """Тест получения истории компьютеров для пользователя без компьютеров"""
        self.authenticate()
        url = reverse('user-computer-history', args=[self.user5.id])  # user5 без компьютеров
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], 'Charlie Wilson')
        self.assertEqual(response.data['total_computers'], 0)
        self.assertEqual(len(response.data['computers']), 0)
    
    def test_computer_history_action_not_found(self):
        """Тест получения истории для несуществующего пользователя"""
        self.authenticate()
        url = reverse('user-computer-history', args=[999])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_statistics_action(self):
        """Тест получения статистики по пользователям"""
        self.authenticate()
        url = reverse('user-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем общую статистику
        self.assertEqual(response.data['total'], 5)
        self.assertEqual(response.data['with_computers'], 3)  # user1, user2, user4
        self.assertEqual(response.data['without_computers'], 2)  # user3, user5
        
        # Проверяем статистику по должностям
        self.assertIn('by_position', response.data)
        self.assertEqual(len(response.data['by_position']), 4)  # 4 разные должности
        
        # Проверяем статистику по отделам
        self.assertIn('by_department', response.data)
        self.assertEqual(len(response.data['by_department']), 3)  # 3 отдела
    
    # Тесты для проверки get_queryset с фильтрами
    
    def test_get_queryset_with_search_filter(self):
        """Тест метода get_queryset с поисковым фильтром"""
        self.authenticate()
        
        response = self.client.get(self.users_url, {'search': 'John'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
    
    def test_get_queryset_with_department_filter(self):
        """Тест метода get_queryset с фильтром по отделу"""
        self.authenticate()
        
        response = self.client.get(self.users_url, {'department': self.department1.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_get_queryset_with_position_filter(self):
        """Тест метода get_queryset с фильтром по должности"""
        self.authenticate()
        
        response = self.client.get(self.users_url, {'position_id': self.position2.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
    
    def test_get_queryset_without_filters(self):
        """Тест метода get_queryset без фильтров"""
        self.authenticate()
        
        # Создаем ViewSet для прямого тестирования
        viewset = UserViewSet()
        viewset.request = self.client.get('/').wsgi_request
        viewset.request.user = self.auth_user
        viewset.action = 'list'
        
        queryset = viewset.get_queryset()
        self.assertEqual(queryset.count(), 5)
    
    # Тесты для обработки ошибок
    
    def test_create_user_exception_handling(self):
        """Тест обработки исключений при создании пользователя"""
        self.authenticate()
        
        # Создаем данные, которые вызовут исключение в сериализаторе
        data = {
            'full_name': 'Test User',
            'email': 'test@example.com',
            'phone': '1234567890' * 10,  # Слишком длинный телефон
            'position_id': self.position1.id,
        }
        
        response = self.client.post(self.users_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch('network_api.models.User.objects.filter')
    def test_computer_history_error_handling(self, mock_filter):
        """Тест обработки ошибок в computer_history action"""
        mock_filter.side_effect = Exception("Database error")
        
        self.authenticate()
        
        # Мокаем get_object для возврата пользователя, но фильтр вызовет исключение
        with patch('network_api.views.UserViewSet.get_object', return_value=self.user1):
            url = reverse('user-computer-history', args=[self.user1.id])
            response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)
    
    # Тесты для проверки select_related и prefetch_related
    
    def test_queryset_optimization(self):
        """Тест оптимизации запросов с select_related и prefetch_related"""
        self.authenticate()
        
        viewset = UserViewSet()
        viewset.request = self.client.get('/').wsgi_request
        viewset.request.user = self.auth_user
        viewset.action = 'list'
        
        queryset = viewset.get_queryset()
        
        # Проверяем, что используется select_related и prefetch_related
        # (не можем проверить напрямую, но можем проверить количество запросов)
        with self.assertNumQueries(2):  # Один для пользователей, один для prefetch_related computers
            for user in queryset:
                # Доступ к связанному отделу не должен создавать новый запрос
                if user.department:
                    _ = user.department.room_number
                # Доступ к компьютерам не должен создавать новые запросы
                count = user.computers.count()


class UserViewSetUnitTests(TestCase):
    """Модульные тесты для отдельных методов UserViewSet"""
    
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = UserViewSet
        self.auth_user = AuthUser.objects.create_user(username='testuser', password='testpass')
        
        self.position = Position.objects.create(
            name='Developer',
            salary=100000
        )
        
        self.department = Department.objects.create(
            room_number='101',
            internal_phone=1234,
            employee_count=5
        )
        
        self.user = User.objects.create(
            full_name='Test User',
            email='test@example.com',
            phone='1234567890',
            position=self.position,
            department=self.department
        )
    
    def test_create_method_with_missing_fields(self):
        """Тест метода create с отсутствующими полями"""
        request = self.factory.post('/', {
            'full_name': 'New User',
            'email': 'new@example.com',
            # Отсутствует phone
            'position_id': self.position.id,
        })
        request.user = self.auth_user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        
        response = view.create(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing required field', response.data['error'])
    
    def test_create_method_with_duplicate_email(self):
        """Тест метода create с дублирующимся email"""
        request = self.factory.post('/', {
            'full_name': 'Another User',
            'email': self.user.email,  # Уже существует
            'phone': '9998887777',
            'position_id': self.position.id,
            'department': self.department.id
        })
        request.user = self.auth_user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        
        response = view.create(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Пользователь с таким email уже существует')
    
    def test_update_method_with_duplicate_email(self):
        """Тест метода update с дублирующимся email"""
        # Создаем другого пользователя
        other_user = User.objects.create(
            full_name='Other User',
            email='other@example.com',
            phone='5555555555',
            position=self.position
        )
        
        request = self.factory.put('/', {
            'full_name': 'Test User Updated',
            'email': other_user.email,  # Email другого пользователя
            'phone': '1234567890',
            'position_id': self.position.id,
        })
        request.user = self.auth_user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        view.kwargs = {'pk': self.user.pk}
        
        # Мокаем get_object для возврата нашего пользователя
        with patch.object(view, 'get_object', return_value=self.user):
            response = view.update(request)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Пользователь с таким email уже существует')
    
    def test_update_method_with_same_email(self):
        """Тест метода update с тем же email (должно работать)"""
        request = self.factory.put('/', {
            'full_name': 'Test User Updated',
            'email': self.user.email,  # Тот же email
            'phone': '9998887777',
            'position_id': self.position.id,
        })
        request.user = self.auth_user
        
        view = self.view()
        view.request = request
        view.format_kwarg = {}
        view.kwargs = {'pk': self.user.pk}
        
        # Мокаем методы для успешного обновления
        mock_serializer = MagicMock()
        mock_serializer.is_valid.return_value = True
        mock_serializer.data = {'id': self.user.id, 'full_name': 'Test User Updated'}
        
        with patch.object(view, 'get_object', return_value=self.user):
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                with patch.object(view, 'perform_update'):
                    response = view.update(request)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_managers_method_with_custom_position_ids(self):
        """Тест метода managers с кастомными ID должностей"""
        request = self.factory.get('/')
        request.user = self.auth_user
        
        view = self.view()
        view.request = request
        view.action = 'managers'
        
        # Создаем мок для queryset
        mock_queryset = MagicMock()
        mock_filtered = MagicMock()
        mock_queryset.filter.return_value = mock_filtered
        mock_filtered.count.return_value = 2
        
        mock_serializer = MagicMock()
        mock_serializer.data = [{'id': 1}, {'id': 2}]
        
        with patch.object(view, 'get_queryset', return_value=mock_queryset):
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                response = view.managers(request)
        
        # Проверяем, что filter был вызван с правильными параметрами
        mock_queryset.filter.assert_called_once_with(position_id__in=[1, 2])
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['managers']), 2)
    
    def test_non_manager_method(self):
        """Тест метода non_manager"""
        request = self.factory.get('/')
        request.user = self.auth_user
        
        view = self.view()
        view.request = request
        view.action = 'non_manager'
        
        # Создаем мок для queryset
        mock_queryset = MagicMock()
        mock_excluded = MagicMock()
        mock_queryset.exclude.return_value = mock_excluded
        mock_excluded.count.return_value = 3
        
        mock_serializer = MagicMock()
        mock_serializer.data = [{'id': 3}, {'id': 4}, {'id': 5}]
        
        with patch.object(view, 'get_queryset', return_value=mock_queryset):
            with patch.object(view, 'get_serializer', return_value=mock_serializer):
                response = view.non_manager(request)
        
        # Проверяем, что exclude был вызван с правильными параметрами
        mock_queryset.exclude.assert_called_once_with(position_id__in=[1, 2])
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['non_managers']), 3)


class UserViewSetIntegrationTests(TestCase):
    """Интеграционные тесты для UserViewSet"""
    
    def setUp(self):
        from rest_framework.test import APIClient
        self.client = APIClient()
        self.auth_user = AuthUser.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.auth_user)
        
        # Создаем должности
        self.positions = []
        position_names = ['Director', 'Manager', 'Team Lead', 'Developer', 'Tester', 'Designer']
        for i, name in enumerate(position_names):
            position = Position.objects.create(
                name=name,
                salary=200000 - i * 20000
            )
            self.positions.append(position)
        
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
        
        # Создаем пользователей
        self.users = []
        for i in range(1, 16):
            position = self.positions[i % len(self.positions)]
            dept = self.departments[i % len(self.departments)]
            user = User.objects.create(
                full_name=f'User {i}',
                email=f'user{i}@example.com',
                phone=f'555{i:04d}',
                position=position,
                department=dept
            )
            self.users.append(user)
        
        # Назначаем компьютеры пользователям
        for i, user in enumerate(self.users):
            # Каждый пользователь имеет 1-3 компьютера
            for j in range(i % 3 + 1):
                computer_idx = (i + j) % len(self.computers)
                user.computers.add(self.computers[computer_idx])
    
    def test_complex_filtering_scenarios(self):
        """Тест сложных сценариев фильтрации"""
        # Фильтр по отделу и поиск
        dept_id = self.departments[0].id
        response = self.client.get('/api/users/', {
            'department': dept_id,
            'search': 'User'
        })
        
        self.assertEqual(response.status_code, 200)
        # Проверяем, что все результаты из указанного отдела
        for user in response.data:
            self.assertEqual(user['department'], dept_id)
        
        # Фильтр по должности и поиск
        pos_id = self.positions[2].id
        response = self.client.get('/api/users/', {
            'position_id': pos_id,
            'search': 'example.com'
        })
        
        self.assertEqual(response.status_code, 200)
        for user in response.data:
            self.assertEqual(user['position_id'], pos_id)
    
    def test_managers_and_non_managers(self):
        """Тест получения менеджеров и не-менеджеров"""
        # Получаем менеджеров
        response = self.client.get('/api/users/managers/')
        self.assertEqual(response.status_code, 200)
        managers_count = response.data['count']
        
        # Получаем не-менеджеров
        response = self.client.get('/api/users/non_manager/')
        self.assertEqual(response.status_code, 200)
        non_managers_count = response.data['count']
        
        # Проверяем, что сумма равна общему количеству пользователей
        total_users = User.objects.count()
        self.assertEqual(managers_count + non_managers_count, total_users)
    
    def test_computer_history_for_all_users(self):
        """Тест истории компьютеров для всех пользователей"""
        for user in self.users[:5]:  # Проверяем первых 5 пользователей
            url = reverse('user-computer-history', args=[user.id])
            response = self.client.get(url)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['user'], user.full_name)
            self.assertEqual(response.data['total_computers'], user.computers.count())
            self.assertEqual(len(response.data['computers']), user.computers.count())
    
    def test_statistics_consistency(self):
        """Тест согласованности статистики"""
        url = reverse('user-statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что with_computers + without_computers = total
        self.assertEqual(
            response.data['with_computers'] + response.data['without_computers'],
            response.data['total']
        )
        
        # Проверяем, что сумма по должностям равна общему количеству
        total_from_positions = sum(item['count'] for item in response.data['by_position'])
        self.assertEqual(total_from_positions, response.data['total'])
        
        # Проверяем, что сумма по отделам равна общему количеству
        total_from_departments = sum(item['count'] for item in response.data['by_department'])
        self.assertEqual(total_from_departments, response.data['total'])