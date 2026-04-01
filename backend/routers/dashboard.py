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

    # ── Auto-approved rate (crm_written / total completed) ─────
    total_completed = await session.scalar(
        select(func.count(Job.id)).where(
            Job.org_id == org_id,
            Job.status.in_(["crm_written", "review_queue", "error"]),
            Job.created_at >= month_start,
        )
    ) or 0
    auto_approved_rate = (
        round((docs_this_month / total_completed) * 100, 1)
        if total_completed > 0 else 0.0
    )

    # ── Pending review count ────────────────────────────────────
    pending_review = await session.scalar(
        select(func.count(ReviewQueue.id))
        .join(Job, Job.id == ReviewQueue.job_id)
        .where(
            Job.org_id == org_id,
            ReviewQueue.review_status == "pending",
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
            "week_label": week_start.strftime("%-d %b") if hasattr(week_start, 'strftime') else str(week_start.date()),
            "count": count,
        })
    return weeks
