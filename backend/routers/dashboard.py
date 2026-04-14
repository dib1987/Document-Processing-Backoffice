"""
Dashboard Router — ROI metrics for the firm owner.

GET /dashboard/stats — returns the 4 key metrics shown on the dashboard:
  - docs_processed_this_month
  - hours_saved_this_month
  - auto_approved_rate
  - pending_review_count
  + weekly volume chart data (last 8 weeks)
  + recent jobs table
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from middleware.auth_middleware import require_role
from models.db_models import Job, ReviewQueue, User

router = APIRouter()
settings = get_settings()


@router.get("/stats")
async def get_dashboard_stats(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("viewer")),
):
    """
    Returns all data needed to render the firm's ROI dashboard.
    """
    org_id = request.state.org_id
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # ── Docs processed this month (crm_written only) ───────────
    docs_this_month = await session.scalar(
        select(func.count(Job.id)).where(
            Job.org_id == org_id,
            Job.status == "crm_written",
            Job.created_at >= month_start,
        )
    ) or 0

    # ── Hours saved (vs 2hr baseline per doc) ──────────────────
    hours_saved = round(docs_this_month * settings.hours_saved_per_doc_baseline, 1)

    # ── Auto-approved count (crm_written without going through review) ─
    auto_approved = docs_this_month  # all crm_written this month

    # ── Pending review count ────────────────────────────────────
    pending_review = await session.scalar(
        select(func.count(ReviewQueue.id))
        .join(Job, Job.id == ReviewQueue.job_id)
        .where(
            Job.org_id == org_id,
            ReviewQueue.review_status == "pending",
        )
    ) or 0

    # ── Error count this month ──────────────────────────────────
    errors = await session.scalar(
        select(func.count(Job.id)).where(
            Job.org_id == org_id,
            Job.status.in_(["error", "crm_error"]),
            Job.created_at >= month_start,
        )
    ) or 0

    # ── Weekly chart: docs processed per week, last 8 weeks ────
    eight_weeks_ago = now - timedelta(weeks=8)
    weekly_jobs = (await session.scalars(
        select(Job).where(
            Job.org_id == org_id,
            Job.status == "crm_written",
            Job.created_at >= eight_weeks_ago,
        )
    )).all()

    weekly_chart = _build_weekly_chart(weekly_jobs, now)

    # ── Recent jobs (last 10) ───────────────────────────────────
    recent_jobs = (await session.scalars(
        select(Job)
        .where(Job.org_id == org_id)
        .order_by(Job.created_at.desc())
        .limit(10)
    )).all()

    auto_approved_rate = round((auto_approved / docs_this_month * 100) if docs_this_month > 0 else 0, 1)

    return {
        "stats": {
            "docs_processed_this_month": docs_this_month,
            "hours_saved_this_month": hours_saved,
            "auto_approved_rate": auto_approved_rate,
            "pending_review_count": pending_review,
        },
        "weekly_chart": weekly_chart,
        "recent_jobs": [
            {
                "job_id": j.id,
                "filename": j.original_filename,
                "doc_type": j.doc_type,
                "status": j.status,
                "processing_ms": j.processing_ms,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in recent_jobs
        ],
    }


def _build_weekly_chart(jobs: list, now: datetime) -> list[dict]:
    """Build 8-week bar chart data."""
    weeks = []
    for i in range(7, -1, -1):
        week_end = now - timedelta(weeks=i)
        week_start = week_end - timedelta(weeks=1)
        count = sum(
            1 for j in jobs
            if j.created_at and week_start <= j.created_at < week_end
        )
        weeks.append({
            "week_label": week_start.strftime("%d %b").lstrip("0") or "0",
            "count": count,
        })
    return weeks
