"""
Review Router — Human review queue for flagged documents.

GET  /review            — list pending items in this org's review queue
GET  /review/{job_id}   — review detail (fields, flags, presigned PDF URL)
POST /review/{job_id}/approve — save corrections, send to HubSpot, log changes
POST /review/{job_id}/reject  — reject and close the review item
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_middleware import get_current_user, require_role
from models.db_models import Extraction, Job, ReviewQueue, User, ValidationFlag
from services import audit_service, email_service, hubspot_service, storage_service

router = APIRouter()


class ApproveRequest(BaseModel):
    corrected_fields: dict  # {field_name: corrected_value}


class RejectRequest(BaseModel):
    reason: str


class ReuploadRequest(BaseModel):
    message: str = ""  # Optional note from back office to the uploader


@router.get("")
async def list_review_queue(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("reviewer")),
):
    """List all pending review items for this org, oldest first."""
    items = (await session.scalars(
        select(ReviewQueue)
        .join(Job, Job.id == ReviewQueue.job_id)
        .where(
            Job.org_id == request.state.org_id,
            ReviewQueue.review_status == "pending",
        )
        .order_by(ReviewQueue.created_at.asc())
    )).all()

    result = []
    for item in items:
        job = await session.get(Job, item.job_id)
        flags = (await session.scalars(
            select(ValidationFlag).where(ValidationFlag.job_id == item.job_id)
        )).all()
        result.append({
            "review_id": item.id,
            "job_id": item.job_id,
            "filename": job.original_filename if job else "",
            "doc_type": job.doc_type if job else "",
            "flag_count": len(flags),
            "flags": [f.plain_message for f in flags],
            "created_at": item.created_at.isoformat() if item.created_at else None,
        })
    return result


@router.get("/{job_id}")
async def get_review_detail(
    job_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("reviewer")),
):
    """
    Full review detail:
    - Extracted fields (with confidence scores)
    - Validation flags (with plain-language explanations)
    - Presigned S3 URL for the PDF preview
    """
    job = await _get_reviewable_job(session, job_id, request.state.org_id)

    extraction = await session.scalar(
        select(Extraction).where(Extraction.job_id == job_id)
    )
    flags = (await session.scalars(
        select(ValidationFlag).where(ValidationFlag.job_id == job_id)
    )).all()

    presigned_url = None
    try:
        presigned_url = storage_service.get_presigned_url(job.s3_key, expiry_seconds=7200)
    except Exception:
        pass

    await audit_service.log(
        session, request.state.org_id, "REVIEWED",
        job_id=job_id, user_id=request.state.user_id,
        actor=current_user.email,
    )
    await session.commit()

    return {
        "job_id": job.id,
        "filename": job.original_filename,
        "doc_type": job.doc_type,
        "presigned_url": presigned_url,
        "fields": extraction.raw_fields if extraction else {},
        "confidence": extraction.confidence if extraction else {},
        "flags": [
            {
                "flag_type": f.flag_type,
                "field_name": f.field_name,
                "plain_message": f.plain_message,
            }
            for f in flags
        ],
    }


@router.post("/{job_id}/approve")
async def approve_review(
    job_id: str,
    body: ApproveRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("reviewer")),
):
    """
    Reviewer approves the document:
    1. Save corrected fields (log each change individually)
    2. Send to HubSpot using merged fields
    3. Update job status → crm_written
    """
    job = await _get_reviewable_job(session, job_id, request.state.org_id)
    review = await session.scalar(
        select(ReviewQueue).where(ReviewQueue.job_id == job_id)
    )
    extraction = await session.scalar(
        select(Extraction).where(Extraction.job_id == job_id)
    )

    original_fields = extraction.raw_fields if extraction else {}
    corrected = body.corrected_fields

    # Log each field change individually (audit trail requirement)
    for field_name, new_value in corrected.items():
        old_value = original_fields.get(field_name)
        if old_value != new_value:
            # Mask SSNs in audit log detail
            display_old = "***" if _is_sensitive(field_name) else old_value
            display_new = "***" if _is_sensitive(field_name) else new_value
            await audit_service.log(
                session, request.state.org_id, "FIELD_CHANGED",
                job_id=job_id, user_id=request.state.user_id,
                actor=current_user.email,
                detail={"field": field_name, "before": display_old, "after": display_new},
            )

    # Update review record
    review.reviewed_fields = corrected
    review.review_status = "approved"
    review.reviewed_by = request.state.user_id
    review.reviewed_at = datetime.now(timezone.utc)

    await audit_service.log(
        session, request.state.org_id, "APPROVED",
        job_id=job_id, user_id=request.state.user_id,
        actor=current_user.email,
    )
    # Check if org has HubSpot configured — use direct query to avoid identity map cache
    from models.db_models import Organization
    hubspot_key = await session.scalar(
        select(Organization.hubspot_api_key).where(Organization.id == job.org_id)
    )

    # Always mark approved — HubSpot push is best-effort and never blocks approval
    job.status = "crm_written"
    contact_id = None

    if hubspot_key:
        try:
            contact_id = await hubspot_service.create_contact(
                session=session,
                job=job,
                extracted_fields=original_fields,
                reviewed_fields=corrected,
            )
            job.crm_contact_id = contact_id
            await audit_service.log(
                session, request.state.org_id, "CRM_WRITTEN",
                job_id=job_id, user_id=request.state.user_id,
                actor=current_user.email,
                detail={"hubspot_contact_id": contact_id},
            )
        except Exception as exc:
            # HubSpot failed — log it but don't block the approval
            job.error_message = str(exc)[:500]
            await audit_service.log(
                session, request.state.org_id, "CRM_PUSH_FAILED",
                job_id=job_id, actor="System",
                detail={"error": str(exc)[:300]},
            )

    await session.commit()
    return {"status": "approved", "contact_id": contact_id}


@router.post("/{job_id}/reject")
async def reject_review(
    job_id: str,
    body: RejectRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("reviewer")),
):
    """Reject the document. Records the reason in the audit log."""
    job = await _get_reviewable_job(session, job_id, request.state.org_id)
    review = await session.scalar(
        select(ReviewQueue).where(ReviewQueue.job_id == job_id)
    )

    review.review_status = "rejected"
    review.reviewed_by = request.state.user_id
    review.reviewed_at = datetime.now(timezone.utc)
    review.reject_reason = body.reason

    job.status = "error"
    job.error_message = f"Rejected by reviewer: {body.reason}"

    await audit_service.log(
        session, request.state.org_id, "REJECTED",
        job_id=job_id, user_id=request.state.user_id,
        actor=current_user.email,
        detail={"reason": body.reason},
    )
    await session.commit()
    return {"status": "rejected"}


@router.post("/{job_id}/request-reupload")
async def request_reupload(
    job_id: str,
    body: ReuploadRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("reviewer")),
):
    """
    Back office requests the uploader to re-upload a corrected document.
    Sends an email to the uploader with the validation flags listed.
    Job status → reupload_requested. Does not block on email failure.
    """
    job = await _get_reviewable_job(session, job_id, request.state.org_id)
    review = await session.scalar(
        select(ReviewQueue).where(ReviewQueue.job_id == job_id)
    )
    flags = (await session.scalars(
        select(ValidationFlag).where(ValidationFlag.job_id == job_id)
    )).all()

    # Get the uploader's email
    uploader = await session.get(User, job.uploaded_by) if job.uploaded_by else None
    to_email = uploader.email if uploader else None

    # Send email best-effort
    email_sent = False
    if to_email:
        email_sent = email_service.send_reupload_request(
            to_email=to_email,
            filename=job.original_filename,
            doc_type=job.doc_type,
            flags=[f.plain_message for f in flags],
            message=body.message,
        )

    # Update job and review record regardless of email outcome
    job.status = "reupload_requested"
    review.review_status = "reupload_requested"
    review.reviewed_by = request.state.user_id
    review.reviewed_at = datetime.now(timezone.utc)
    review.reject_reason = body.message or "Re-upload requested"

    await audit_service.log(
        session, request.state.org_id, "REUPLOAD_REQUESTED",
        job_id=job_id, user_id=request.state.user_id,
        actor=current_user.email,
        detail={"email_sent": email_sent, "to": to_email, "message": body.message},
    )
    await session.commit()

    return {
        "status": "reupload_requested",
        "email_sent": email_sent,
        "notified": to_email,
    }


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def _get_reviewable_job(session, job_id: str, org_id: str) -> Job:
    job = await session.get(Job, job_id)
    if not job or job.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in ("review_queue", "crm_error", "reupload_requested"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is not in review queue (current status: {job.status})",
        )
    return job


def _is_sensitive(field_name: str) -> bool:
    keywords = ("ssn", "account_number", "routing_number", "id_number")
    return any(kw in field_name.lower() for kw in keywords)
