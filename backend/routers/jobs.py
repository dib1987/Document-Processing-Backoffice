"""
Jobs Router — Upload and job status tracking.

POST /jobs/upload  — receive file, create job, queue Celery task
GET  /jobs         — list all jobs for this org (with optional status filter)
GET  /jobs/{id}    — job detail including extracted fields
GET  /jobs/{id}/status — lightweight status poll (used by frontend progress tracker)
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from middleware.auth_middleware import get_current_user, require_role
from models.db_models import Extraction, Job, User, ValidationFlag
from services import audit_service, storage_service
from tasks.processing_pipeline import process_document

router = APIRouter()
settings = get_settings()

ALLOWED_DOC_TYPES = {"tax_return", "government_id", "bank_statement", "general"}
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}


import traceback

@router.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    file: UploadFile,
    doc_type: Annotated[str, Form()],
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("reviewer")),
):
    """
    Upload a document and start the processing pipeline.
    Returns job_id for polling.
    """
    try:
        return await _upload_document_inner(request, file, doc_type, session, current_user)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def _upload_document_inner(request, file, doc_type, session, current_user):
    if doc_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"doc_type must be one of: {', '.join(ALLOWED_DOC_TYPES)}",
        )

    filename = file.filename or "upload"
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_upload_bytes // 1_048_576} MB limit",
        )

    job_id = str(uuid.uuid4())
    s3_key = storage_service.build_s3_key(request.state.org_id, job_id, filename)

    # Upload to S3
    content_type = file.content_type or "application/octet-stream"
    storage_service.upload_file(file_bytes, s3_key, content_type)

    # Create job record
    job = Job(
        id=job_id,
        org_id=request.state.org_id,
        uploaded_by=request.state.user_id,
        original_filename=filename,
        s3_key=s3_key,
        doc_type=doc_type,
        status="queued",
    )
    session.add(job)

    await audit_service.log(
        session,
        org_id=request.state.org_id,
        action="UPLOADED",
        job_id=job_id,
        user_id=request.state.user_id,
        actor=current_user.email,
        detail={"filename": filename, "doc_type": doc_type, "size_bytes": len(file_bytes)},
    )
    await session.commit()

    # Queue Celery task
    try:
        task = process_document.delay(job_id)
        job.celery_task_id = task.id
        await session.commit()
        celery_task_id = task.id
    except Exception as e:
        # Celery/Redis not available — job saved, processing deferred
        await session.commit()
        celery_task_id = None

    return {"job_id": job_id, "status": "queued", "celery_task_id": celery_task_id}


@router.get("")
async def list_jobs(
    request: Request,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("viewer")),
):
    """List all jobs for this org, newest first."""
    query = (
        select(Job)
        .where(Job.org_id == request.state.org_id)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if status_filter:
        query = query.where(Job.status == status_filter)

    jobs = (await session.scalars(query)).all()
    return [_job_summary(j) for j in jobs]


@router.get("/{job_id}/status")
async def get_job_status(
    job_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("viewer")),
):
    """Lightweight status endpoint for frontend polling."""
    job = await _get_job(session, job_id, request.state.org_id)
    return {
        "job_id": job.id,
        "status": job.status,
        "error_message": job.error_message,
    }


@router.get("/{job_id}")
async def get_job_detail(
    job_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("viewer")),
):
    """Full job detail including extracted fields, confidence, and flags."""
    job = await _get_job(session, job_id, request.state.org_id)

    extraction = await session.scalar(
        select(Extraction).where(Extraction.job_id == job_id)
    )
    flags = (await session.scalars(
        select(ValidationFlag).where(ValidationFlag.job_id == job_id)
    )).all()

    # Generate presigned URL for PDF preview in review UI
    presigned_url = None
    try:
        presigned_url = storage_service.get_presigned_url(job.s3_key)
    except Exception:
        pass

    return {
        **_job_summary(job),
        "presigned_url": presigned_url,
        "extraction": {
            "fields": extraction.raw_fields if extraction else {},
            "confidence": extraction.confidence if extraction else {},
        } if extraction else None,
        "flags": [
            {
                "flag_type": f.flag_type,
                "field_name": f.field_name,
                "plain_message": f.plain_message,
            }
            for f in flags
        ],
    }


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def _get_job(session, job_id: str, org_id: str) -> Job:
    job = await session.get(Job, job_id)
    if not job or job.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


def _job_summary(job: Job) -> dict:
    return {
        "job_id": job.id,
        "original_filename": job.original_filename,
        "doc_type": job.doc_type,
        "status": job.status,
        "page_count": job.page_count,
        "crm_contact_id": job.crm_contact_id,
        "processing_ms": job.processing_ms,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
