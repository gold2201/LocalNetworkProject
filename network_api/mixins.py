from .services.export_utils import export_queryset_to_excel
from rest_framework.response import Response
from rest_framework.decorators import action


class ExportMixin:

    @action(detail=False, methods=['get'])
    def export(self, request):
        try:
            queryset = self.filter_queryset(self.get_queryset())

            queryset = self.apply_export_filters(queryset, request)

            model_name = self.queryset.model._meta.model_name
            filename = f"{model_name}_export"

            return export_queryset_to_excel(queryset, filename)

        except Exception as e:
            return Response(
                {'error': f'Ошибка при экспорте: {str(e)}'},
                status=500
            )

    @action(detail=False, methods=['get'])
    def export_filtered(self, request):
        try:
            queryset = self.filter_queryset(self.get_queryset())
            queryset = self.apply_export_filters(queryset, request)

            model_name = self.queryset.model._meta.model_name
            filter_info = self.get_filter_info(request)
            filename = f"{model_name}_export_{filter_info}"

            return export_queryset_to_excel(queryset, filename)

        except Exception as e:
            return Response(
                {'error': f'Ошибка при экспорте: {str(e)}'},
                status=500
            )

    def apply_export_filters(self, queryset, request):
        export_filters = {}

        date_field = self.get_date_field()
        if date_field:
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')
            if start_date:
                queryset = queryset.filter(**{f"{date_field}__gte": start_date})
            if end_date:
                queryset = queryset.filter(**{f"{date_field}__lte": end_date})

        return queryset

    def get_date_field(self):
        date_fields = ['created_at', 'updated_at', 'setup_date', 'connection_date', 'install_date']
        for field in date_fields:
            if hasattr(self.queryset.model, field):
                return field
        return None

    def get_filter_info(self, request):
        filters = []
        for key, value in request.GET.items():
            if key not in ['format', 'page', 'page_size'] and value:
                filters.append(f"{key}_{value}")

        return "_".join(filters) if filters else "all"