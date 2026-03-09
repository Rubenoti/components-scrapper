FROM python:3.12-slim

# Evita bytecode y buffers — mejor para logs en Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema para psycopg2-binary y lxml
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ejecutar setup y luego la app web
CMD python setup_products.py && uvicorn app:app --host 0.0.0.0 --port $PORT
# Sobreescribir con CMD o entrypoint en compose para el modo summary.
CMD ["python", "tracker.py"]