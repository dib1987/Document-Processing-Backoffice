"""
Audit Router — Full audit trail for all org actions.

GET /audit — returns the audit log filterable by job, user, date range, and action type.
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_middleware import require_role
from models.db_models import AuditLog, User

router = APIRouter()


@router.get("")
async def get_audit_log(
    request: Request,
    job_id: str | None = None,
    user_id: str | None = None,
    action: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Return the audit log for this org with optional filters.
    Only admins can access the full audit trail.
    """
    org_id = request.state.org_id

    query = (
        select(AuditLog)
        .where(AuditLog.org_id == org_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    if job_id:
        query = query.where(AuditLog.job_id == job_id)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if date_from:
        try:
            dt = datetime.fromisoformat(date_from)
            query = query.where(AuditLog.created_at >= dt)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            query = query.where(AuditLog.created_at <= dt)
        except ValueError:
            pass

    entries = (await session.scalars(query)).all()

    return [
        {
            "id": e.id,
            "job_id": e.job_id,
            "user_id": e.user_id,
            "actor": e.actor,
            "action": e.action,
            "detail": e.detail,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]
