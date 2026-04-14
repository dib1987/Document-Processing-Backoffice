FROM python:3.13-slim

# Install system dependencies (Tesseract for OCR)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Create worker startup script inside the container (avoids Windows CRLF issues)
RUN printf '#!/bin/sh\nexec python3 -m celery -A celery_app worker --loglevel=info -Q documents\n' > /start_worker.sh \
    && chmod +x /start_worker.sh

EXPOSE $PORT

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
