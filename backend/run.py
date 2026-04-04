"""
Entry point for the DocFlow AI backend.

Development:
    python run.py

Production (via Docker/Railway):
    uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

Celery worker (separate terminal):
    celery -A celery_app worker --loglevel=info -Q documents
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )
