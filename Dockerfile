FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SKILLPASSPORT_STORE_PATH=/app/runtime/skillpassport.json

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY data/demo/fixture.json /app/data/demo/fixture.json
COPY frontend /app/frontend

RUN useradd --create-home --uid 10001 skillpassport \
    && mkdir -p /app/runtime \
    && chown -R skillpassport:skillpassport /app/runtime

USER skillpassport

CMD ["python", "-m", "backend.start"]
