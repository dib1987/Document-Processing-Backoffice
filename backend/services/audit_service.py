"""
Audit service — writes a row to audit_log for every significant action.
Called throughout the processing pipeline and routers.
Every action is permanent and immutable — no deletes allowed on audit_log.
"""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import AuditLog


async def log(
    session: AsyncSession,
    org_id: str,
    action: str,
    job_id: str | None = None,
    user_id: str | None = None,
    actor: str = "System",
    detail: dict | None = None,
) -> None:
    """
    Write an audit log entry.

    Actions:
        UPLOADED         — file received and job created
        OCR_COMPLETE     — text extracted from document
        EXTRACTED        — Claude returned structured fields
        VALIDATION_PASSED — all fields passed validation, routed to HubSpot
        FLAGGED          — validation failed, routed to review queue
        REVIEWED         — reviewer opened the review item
        FIELD_CHANGED    — reviewer edited a field (detail: {field, before, after})
        APPROVED         — reviewer approved, sending to HubSpot
        REJECTED         — reviewer rejected
        CRM_WRITTEN      — HubSpot contact created/updated
        ERROR            — pipeline error (detail: {error})
    """
    entry = AuditLog(
        org_id=org_id,
        job_id=job_id,
        user_id=user_id,
        actor=actor,
        action=action,
        detail=detail,
        created_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.flush()  # persist without committing — caller commits
