from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from routers import audit, auth, dashboard, export, jobs, review, settings as settings_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="DocFlow AI",
    description="AI-powered document processing for accounting firms",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
app.include_router(review.router, prefix="/review", tags=["Review"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(audit.router, prefix="/audit", tags=["Audit"])
app.include_router(settings_router.router, prefix="/settings", tags=["Settings"])
app.include_router(export.router, prefix="/export", tags=["Export"])


@app.get("/health", tags=["Health"])
async def health():
    checks = {
        "status": "ok",
        "anthropic_key": "set" if settings.anthropic_api_key else "missing",
        "s3_key": "set" if settings.aws_access_key_id else "missing",
        "clerk_key": "set" if settings.clerk_secret_key else "missing",
    }
    return checks
