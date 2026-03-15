FROM python:3.13-slim AS build

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim

WORKDIR /app

COPY --from=build /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

