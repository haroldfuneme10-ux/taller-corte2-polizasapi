# syntax=docker/dockerfile:1

# --- Etapa 1: construcción. Instala las dependencias en un entorno virtual aislado. ---
FROM python:3.11.9-slim-bookworm AS builder

ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# --- Etapa 2: ejecución. Solo el entorno ya instalado y el código; sin pip cache ni compiladores. ---
FROM python:3.11.9-slim-bookworm

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////app/datos/polizas.db

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
# .dockerignore deja fuera .env, *.db, .git, entornos virtuales y tests.
COPY --chown=appuser:appuser . .
RUN mkdir -p /app/datos && chown appuser:appuser /app/datos && chmod +x docker-entrypoint.sh

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"

# El entrypoint aplica las migraciones (alembic upgrade head) y luego ejecuta el CMD.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
