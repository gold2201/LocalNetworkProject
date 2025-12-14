# network_project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('network_api.urls')),  # Включаем ВСЕ пути из приложения
]
