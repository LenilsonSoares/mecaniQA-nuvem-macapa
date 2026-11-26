FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Um único worker garante consistência dos contadores Prometheus em memória
CMD ["gunicorn", "mecaniqa_api.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4"]
