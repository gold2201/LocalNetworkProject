from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class DashboardView(TemplateView):
    template_name = 'dashboard.html'

class DepartmentUIView(TemplateView):
    template_name = 'departments.html'

class ComputerUIView(TemplateView):
    template_name = 'computers.html'

class UserUIView(TemplateView):
    template_name = 'users.html'

class SoftwareUIView(TemplateView):
    template_name = 'software.html'

class NetworkUIView(TemplateView):
    template_name = 'networks.html'

class EquipmentUIView(TemplateView):
    template_name = 'equipment.html'

class HostComputerUIView(TemplateView):
    template_name = 'host_computers.html'

class ServerUIView(TemplateView):
    template_name = 'servers.html'

class AnalyticsUIView(TemplateView):
    template_name = 'analytics.html'

class ReportsUIView(TemplateView):
    template_name = 'reports.html'

class DatabaseBackupView(TemplateView):
    template_name = 'database_backup.html'

class SQLQueryView(TemplateView):
    template_name = 'sql_query.html'