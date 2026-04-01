"""
Document Processing Pipeline — Celery Task

Orchestrates the full pipeline for a single uploaded document:
  1. Download file from S3
  2. OCR (PyMuPDF → pytesseract fallback)
  3. Claude extraction + confidence scoring
  4. Pydantic validation + flag rules
  5a. PASS → HubSpot contact creation  (status: crm_written)
  5b. FAIL → Review Queue              (status: review_queue)

Every status transition and action is written to the audit_log.

Celery config:
  max_retries=3, default_retry_delay=30s
  task_acks_late=True  — re-queued if worker crashes mid-task
"""
import asyncio
import logging
import time

import anthropic
from celery import Task

from celery_app import celery_app
from database import AsyncSessionLocal
from models.db_models import CRMLog, Extraction, Job, ReviewQueue, ValidationFlag
from services import audit_service, extraction_service, hubspot_service, ocr_service, storage_service
from services.validation_service import validate

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="tasks.processing_pipeline.process_document",
)
def process_document(self: Task, job_id: str) -> dict:
    """
    Main document processing task. Called after file upload.

    Args:
        job_id: UUID of the Job record.

    Returns:
        dict with final status and any relevant IDs.
    """
    logger.info("pipeline start: job=%s attempt=%d", job_id, self.request.retries + 1)
    start_ms = int(time.time() * 1000)

    try:
        return _run_async(_pipeline(job_id, start_ms))
    except anthropic.RateLimitError as exc:
        logger.warning("job=%s Claude rate limit — retrying in 60s", job_id)
        raise self.retry(exc=exc, countdown=60)
    except anthropic.APIStatusError as exc:
        if exc.status_code >= 500:
            logger.warning("job=%s Claude server error %d — retrying", job_id, exc.status_code)
            raise self.retry(exc=exc)
        raise
    except Exception as exc:
        logger.exception("job=%s unhandled error: %s", job_id, exc)
        _run_async(_mark_error(job_id, str(exc)))
        raise


async def _pipeline(job_id: str, start_ms: int) -> dict:
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        org_id = job.org_id

        # ── Step 1: Download from S3 ───────────────────────────
        await _set_status(session, job, "ocr")
        await audit_service.log(session, org_id, "OCR_STARTED", job_id=job_id)
        await session.commit()

        file_bytes = storage_service.download_file(job.s3_key)

        # ── Step 2: OCR ───────────────────────────────────────
        full_text, page_count = ocr_service.extract_text(file_bytes, job.original_filename)

        job.ocr_text = full_text
        job.page_count = page_count
        await audit_service.log(
            session, org_id, "OCR_COMPLETE", job_id=job_id,
            detail={"page_count": page_count, "char_count": len(full_text)},
        )
        await session.commit()

        # ── Step 3: Claude Extraction ─────────────────────────
        await _set_status(session, job, "extracting")
        await session.commit()

        extracted_fields, confidence = extraction_service.extract_fields(
            full_text=full_text,
            doc_type=job.doc_type,
            job_id=job_id,
        )

        # Persist extraction result
        extraction = Extraction(
            job_id=job_id,
            doc_type=job.doc_type,
            raw_fields=extracted_fields,
            confidence=confidence,
        )
        session.add(extraction)

        await audit_service.log(
            session, org_id, "EXTRACTED", job_id=job_id,
            detail={"field_count": len(extracted_fields)},
        )
        await session.commit()

        # ── Step 4: Validation ────────────────────────────────
        await _set_status(session, job, "validating")
        await session.commit()

        result = validate(extracted_fields, job.doc_type)

        # Persist validation flags
        for flag in result.flags:
            session.add(ValidationFlag(
                job_id=job_id,
                flag_type=flag.flag_type,
                field_name=flag.field_name,
                plain_message=flag.plain_message,
            ))

        # ── Step 5a: PASS → HubSpot ───────────────────────────
        if result.passed:
            await _set_status(session, job, "crm_pending")
            await audit_service.log(session, org_id, "VALIDATION_PASSED", job_id=job_id)
            await session.commit()

            contact_id = await hubspot_service.create_contact(
                session=session,
                job=job,
                extracted_fields=extracted_fields,
            )

            job.crm_contact_id = contact_id
            job.processing_ms = int(time.time() * 1000) - start_ms
            await _set_status(session, job, "crm_written")

            session.add(CRMLog(
                job_id=job_id,
                crm_contact_id=contact_id,
                crm_response={"contact_id": contact_id},
            ))
            await audit_service.log(
                session, org_id, "CRM_WRITTEN", job_id=job_id,
                detail={"hubspot_contact_id": contact_id},
            )
            await session.commit()

            logger.info("job=%s complete → HubSpot contact=%s in %dms",
                        job_id, contact_id, job.processing_ms)
            return {"status": "crm_written", "contact_id": contact_id}

        # ── Step 5b: FAIL → Review Queue ──────────────────────
        else:
            flag_summaries = [f.plain_message for f in result.flags]
            await _set_status(session, job, "review_queue")

            session.add(ReviewQueue(job_id=job_id, review_status="pending"))

            await audit_service.log(
                session, org_id, "FLAGGED", job_id=job_id,
                detail={"flag_count": len(result.flags), "flags": flag_summaries},
            )
            await session.commit()

            logger.info("job=%s → review queue (%d flags)", job_id, len(result.flags))
            return {"status": "review_queue", "flag_count": len(result.flags)}


async def _set_status(session, job: Job, status: str) -> None:
    job.status = status


async def _mark_error(job_id: str, error_message: str) -> None:
    async with AsyncSessionLocal() as session:
        job = await session.get(Job, job_id)
        if job:
            job.status = "error"
            job.error_message = error_message[:1000]
            await audit_service.log(
                session, job.org_id, "ERROR", job_id=job_id,
                detail={"error": error_message[:500]},
            )
            await session.commit()
