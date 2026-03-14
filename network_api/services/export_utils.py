import pandas as pd
from django.http import HttpResponse
from io import BytesIO
import datetime

def export_to_excel(data, filename, sheet_name='Data'):
    try:
        if isinstance(data, list) and data:
            df = pd.DataFrame(data)
        else:
            df = pd.DataFrame()

        return create_excel_response(df, filename, sheet_name)
    except ImportError:
        return export_to_csv(data, filename)


def export_queryset_to_excel(queryset, filename, fields=None):
    try:
        if fields:
            data = list(queryset.values(*fields))
        else:
            data = list(queryset.values())

        if data and hasattr(queryset, 'model'):
            model = queryset.model
            readable_data = []
            for item in data:
                readable_item = {}
                for key, value in item.items():
                    if key.endswith('_id') and value:
                        field_name = key[:-3]
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
    try:
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

            worksheet = writer.sheets[sheet_name]
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).str.len().max(),
                    len(str(col))
                )
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)

        output.seek(0)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename}_{timestamp}.xlsx"

        response = HttpResponse(
            output.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except ImportError:
        return create_csv_response(df, filename)


def export_analytics_to_excel(analytics_data, filename, description=""):
    try:
        if isinstance(analytics_data, dict):
            output = BytesIO()

            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                for sheet_name, data in analytics_data.items():
                    if isinstance(data, list) and data:
                        df = pd.DataFrame(data)
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
            return export_to_excel(analytics_data, filename)
    except ImportError:
        return export_analytics_to_csv(analytics_data, filename)

def export_to_csv(data, filename):
    if isinstance(data, list) and data:
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame()

    return create_csv_response(df, filename)


def export_queryset_to_csv(queryset, filename, fields=None):
    if fields:
        data = list(queryset.values(*fields))
    else:
        data = list(queryset.values())

    df = pd.DataFrame(data)
    return create_csv_response(df, filename)


def create_csv_response(df, filename):
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
    if isinstance(analytics_data, dict):
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