# Simulador IoT: imagen mínima, usuario sin privilegios, sin puertos publicados.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /sim
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --system --uid 10001 sim
COPY simulador.py .
USER sim
CMD ["python", "simulador.py"]
