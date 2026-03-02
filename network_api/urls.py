from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import views, views_ui, computers_view, users_view, departments_view, softwares_view, networks_view, hostcomputers_view, equipments_view
from network_api.views.views import DatabaseViewSet

router = DefaultRouter()

# API endpoints
router.register(r'users', users_view.UserViewSet, basename='users')
router.register(r'computers', computers_view.ComputerViewSet, basename='computers')
router.register(r'departments', departments_view.DepartmentViewSet, basename='departments')
router.register(r'software', softwares_view.SoftwareViewSet, basename='software')
router.register(r'networks', networks_view.NetworkReadOnlyViewSet, basename='networks')
router.register(r'host-computers', hostcomputers_view.HostComputerViewSet)
router.register(r'servers', views.ServerViewSet)
router.register(r'software-computers', views.SoftwareComputerViewSet)
router.register(r'user-computers', views.UserComputerViewSet)
router.register(r'server-networks', views.ServerNetworkViewSet)
router.register(r'analytics', views.AnalyticsViewSet, basename='analytics')
router.register(r'database', DatabaseViewSet, basename='database')

urlpatterns = [
    # UI Pages - регистрируем ПЕРЕД API
    path('', views_ui.DashboardView.as_view(), name='dashboard'),  # Корень на дашборд
    path('departments/', views_ui.DepartmentUIView.as_view(), name='departments-ui'),
    path('computers/', views_ui.ComputerUIView.as_view(), name='computers-ui'),
    path('users/', views_ui.UserUIView.as_view(), name='users-ui'),
    path('software/', views_ui.SoftwareUIView.as_view(), name='software-ui'),
    path('networks/', views_ui.NetworkUIView.as_view(), name='networks-ui'),
    path('equipment/', views_ui.EquipmentUIView.as_view(), name='equipment-ui'),
    path('host-computers/', views_ui.HostComputerUIView.as_view(), name='host-computers-ui'),
    path('servers/', views_ui.ServerUIView.as_view(), name='servers-ui'),
    path('analytics/', views_ui.AnalyticsUIView.as_view(), name='analytics-ui'),
    path('reports/', views_ui.ReportsUIView.as_view(), name='reports-ui'),
    path('database-backup/', views_ui.DatabaseBackupView.as_view(), name='database-backup-ui'),
    path('sql-query/', views_ui.SQLQueryView.as_view(), name='sql-query-ui'),

    # API routes
    path('api/', include(router.urls)),

    # Equipment API endpoints
    path('api/equipment/', equipments_view.EquipmentViewSet.as_view({'get': 'list'}), name='equipment-list'),
    path('api/equipment/<int:pk>/', equipments_view.EquipmentViewSet.as_view({'get': 'retrieve'}), name='equipment-detail'),
    path('api/equipment/export/', equipments_view .EquipmentViewSet.as_view({'get': 'export'}), name='equipment-export'),
]