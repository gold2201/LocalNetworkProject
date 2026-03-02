# network_api/services/export_utils.py
import pandas as pd
from django.http import HttpResponse
from io import BytesIO
import datetime
import json


def export_to_excel(data, filename, sheet_name='Data'):
    """
    Экспорт данных в Excel
    """
    try:
        if isinstance(data, list) and data:
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()

        return create_excel_response(df, filename, sheet_name)
    except ImportError:
        # Если openpyxl не установлен, используем CSV
        return export_to_csv(data, filename)


def export_queryset_to_excel(queryset, filename, fields=None):
    """
    Экспорт QuerySet в Excel
    """
    try:
        if fields:
            data = list(queryset.values(*fields))
        else:
            data = list(queryset.values())

        # Добавляем человеко-читаемые названия полей
        if data and hasattr(queryset, 'model'):
            model = queryset.model
            readable_data = []
            for item in data:
                readable_item = {}
                for key, value in item.items():
                    # Пытаемся получить человеко-читаемое значение для ForeignKey полей
                    if key.endswith('_id') and value:
                        field_name = key[:-3]  # Убираем _id
                        if hasattr(model, field_name):
                            try:
                                related_obj = getattr(model, field_name).field.related_model.objects.filter(
                                    id=value).first()
                                if related_obj:
                                    readable_item[field_name] = str(related_obj)
                                    continue
                            except:
                                pass
                    readable_item[key] = value
                readable_data.append(readable_item)
            data = readable_data

        df = pd.DataFrame(data)
        return create_excel_response(df, filename)
    except ImportError:
        return export_queryset_to_csv(queryset, filename, fields)


def create_excel_response(df, filename, sheet_name='Data'):
    """
    Создает HttpResponse с Excel файлом
    """
    try:
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Автонастройка ширины колонок
            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).str.len().max(),
                    len(str(col))
                )
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)

        output.seek(0)

        # Добавляем timestamp к имени файла
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename}_{timestamp}.xlsx"

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except ImportError:
        # Fallback to CSV if openpyxl is not available
        return create_csv_response(df, filename)


def export_analytics_to_excel(analytics_data, filename, description=""):
    """
    Специальная функция для экспорта аналитических данных
    """
    try:
        if isinstance(analytics_data, dict):
            # Если данные в формате словаря, создаем несколько листов
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, data in analytics_data.items():
                    if isinstance(data, list) and data:
                        df = pd.DataFrame(data)
                        # Обрезаем имя листа до 31 символа (ограничение Excel)
                        sheet_name_short = sheet_name[:31]
                        df.to_excel(writer, sheet_name=sheet_name_short, index=False)

            output.seek(0)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{timestamp}.xlsx"

            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        else:
            # Стандартный экспорт
            return export_to_excel(analytics_data, filename)
    except ImportError:
        return export_analytics_to_csv(analytics_data, filename)


# CSV fallback functions
def export_to_csv(data, filename):
    """Экспорт данных в CSV"""
    if isinstance(data, list) and data:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame()

    return create_csv_response(df, filename)


def export_queryset_to_csv(queryset, filename, fields=None):
    """Экспорт QuerySet в CSV"""
    if fields:
        data = list(queryset.values(*fields))
    else:
        data = list(queryset.values())

    df = pd.DataFrame(data)
    return create_csv_response(df, filename)


def create_csv_response(df, filename):
    """Создает HttpResponse с CSV файлом"""
    output = BytesIO()
    df.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename}_{timestamp}.csv"

    response = HttpResponse(
        output.getvalue(),
        content_type='text/csv; charset=utf-8'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def export_analytics_to_csv(analytics_data, filename):
    """Экспорт аналитических данных в CSV"""
    if isinstance(analytics_data, dict):
        # Для словарных данных создаем ZIP с несколькими CSV
        import zipfile
        output = BytesIO()

        with zipfile.ZipFile(output, 'w') as zip_file:
            for sheet_name, data in analytics_data.items():
                if isinstance(data, list) and data:
                    df = pd.DataFrame(data)
                    csv_data = df.to_csv(index=False, encoding='utf-8')
                    zip_file.writestr(f"{sheet_name}.csv", csv_data)

        output.seek(0)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename}_{timestamp}.zip"

        response = HttpResponse(
            output.getvalue(),
            content_type='application/zip'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    else:
        return export_to_csv(analytics_data, filename)