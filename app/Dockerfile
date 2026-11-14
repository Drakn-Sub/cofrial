# Django + django-oscar servido por Gunicorn. Usuario sin privilegios y sistema de archivos de solo lectura (compose).
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN SECRET_KEY=solo-para-construir DEBUG=1 python manage.py collectstatic --noinput -v 0 \
    && useradd --system --uid 10001 app && chown -R app /app
USER app
EXPOSE 8000
CMD ["gunicorn", "cofrial.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", \
     "--worker-tmp-dir", "/tmp", "--access-logfile", "-", "--forwarded-allow-ips", "*"]
