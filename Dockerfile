# Imagen unica para api y worker: el mismo codigo, distinto comando (lo pone compose.yml).
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

# Primero las dependencias, que cambian poco: asi el cache de capas sirve de algo.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Sin root dentro del contenedor.
RUN useradd --create-home --uid 10001 veridica && chown -R veridica:veridica /srv
USER veridica

EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
