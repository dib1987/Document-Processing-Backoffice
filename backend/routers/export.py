"""
Export Router — Download job data for reporting and compliance.

GET /export/csv   — All jobs for this org as a CSV file
GET /export/json  — All jobs with full extraction data as JSON

Both endpoints require admin role.
The exported data is scoped to the requesting org — no cross-tenant data.
"""
import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_middleware import require_role
from models.db_models import AuditLog, Extraction, Job, User, ValidationFlag

router = APIRouter()


@router.get("/csv")
async def export_csv(
    request: Request,
    status_filter: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Export all jobs as a CSV file.
    Includes job metadata + top-level extracted fields (no raw JSON).
    Safe to open in Excel — no sensitive fields (SSNs are already masked).

    Query params:
      status_filter  — filter by job status (e.g. crm_written, review_queue)
      date_from      — ISO 8601 date (e.g. 2024-01-01)
      date_to        — ISO 8601 date (e.g. 2024-03-31)
    """
    org_id = request.state.org_id
    jobs = await _fetch_jobs(session, org_id, status_filter, date_from, date_to)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        "job_id",
        "filename",
        "doc_type",
        "status",
        "page_count",
        "processing_ms",
        "crm_contact_id",
        "error_message",
        "uploaded_at",
        # Extracted fields (flat — most useful for accountants)
        "taxpayer_name",
        "full_name",
        "account_holder_name",
        "document_title",
        "tax_year",
        "total_income",
        "ending_balance",
        "bank_name",
        "issuing_state",
        "expiration_date",
        "document_date",
    ])

    for job in jobs:
        # Load extraction if available
        extraction = await session.scalar(
            select(Extraction).where(Extraction.job_id == job.id)
        )
        fields = extraction.raw_fields if extraction else {}

        writer.writerow([
            job.id,
            job.original_filename,
            job.doc_type,
            job.status,
            job.page_count or "",
            job.processing_ms or "",
            job.crm_contact_id or "",
            job.error_message or "",
            job.created_at.isoformat() if job.created_at else "",
            # Extracted fields — whichever are present
            fields.get("taxpayer_name", ""),
            fields.get("full_name", ""),
            fields.get("account_holder_name", ""),
            fields.get("document_title", ""),
            fields.get("tax_year", ""),
            fields.get("total_income", ""),
            fields.get("ending_balance", ""),
            fields.get("bank_name", ""),
            fields.get("issuing_state", ""),
            fields.get("expiration_date", ""),
            fields.get("document_date", ""),
        ])

    output.seek(0)
    filename = _export_filename(org_id, "csv")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/json")
async def export_json(
    request: Request,
    status_filter: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    include_audit: bool = False,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Export all jobs as a structured JSON file.
    Includes full extraction data and (optionally) per-job audit log entries.

    Query params:
      status_filter   — filter by job status
      date_from       — ISO 8601 date
      date_to         — ISO 8601 date
      include_audit   — include audit log entries per job (default: false)
    """
    org_id = request.state.org_id
    jobs = await _fetch_jobs(session, org_id, status_filter, date_from, date_to)

    records = []
    for job in jobs:
        extraction = await session.scalar(
            select(Extraction).where(Extraction.job_id == job.id)
        )
        flags = (await session.scalars(
            select(ValidationFlag).where(ValidationFlag.job_id == job.id)
        )).all()

        record = {
            "job_id": job.id,
            "filename": job.original_filename,
            "doc_type": job.doc_type,
            "status": job.status,
            "page_count": job.page_count,
            "processing_ms": job.processing_ms,
            "crm_contact_id": job.crm_contact_id,
            "error_message": job.error_message,
            "uploaded_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
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

        if include_audit:
            audit_entries = (await session.scalars(
                select(AuditLog)
                .where(AuditLog.job_id == job.id)
                .order_by(AuditLog.created_at.asc())
            )).all()
            record["audit_trail"] = [
                {
                    "action": e.action,
                    "actor": e.actor,
                    "detail": e.detail,
                    "timestamp": e.created_at.isoformat() if e.created_at else None,
                }
                for e in audit_entries
            ]

        records.append(record)

    export_payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "org_id": org_id,
        "total_records": len(records),
        "filters": {
            "status_filter": status_filter,
            "date_from": date_from,
            "date_to": date_to,
        },
        "jobs": records,
    }

    filename = _export_filename(org_id, "json")

    return Response(
        content=json.dumps(export_payload, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def _fetch_jobs(
    session,
    org_id: str,
    status_filter: str | None,
    date_from: str | None,
    date_to: str | None,
) -> list:
    query = (
        select(Job)
        .where(Job.org_id == org_id)
        .order_by(Job.created_at.desc())
    )
    if status_filter:
        query = query.where(Job.status == status_filter)
    if date_from:
        try:
            query = query.where(Job.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.where(Job.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass
    return (await session.scalars(query)).all()


def _export_filename(org_id: str, ext: str) -> str:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    short_org = org_id[:8]
    return f"docflow_export_{short_org}_{date_str}.{ext}"
