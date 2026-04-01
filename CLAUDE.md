# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DocFlow AI** is a full-stack document intelligence platform for accounting firms. It automates processing of client documents (tax returns, government IDs, bank statements) by extracting structured data via Claude AI, validating it, and either auto-pushing to HubSpot CRM or routing to a human review queue.

## Commands

### Backend

```bash
# Install dependencies (from repo root)
pip install -r backend/requirements.txt

# Run dev server (auto-reload, port 8000)
python backend/run.py

# Start Celery worker (separate terminal — required for document processing)
celery -A celery_app worker --loglevel=info -Q documents

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Frontend

```bash
# From frontend/ directory
npm install
npm run dev      # port 3000
npm run build
npm run lint
npm start        # production
```

### Environment Setup

Copy `backend/.env.example` to `backend/.env`. Required variables:
- `DATABASE_URL` — PostgreSQL async URL (`postgresql+asyncpg://...`)
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — Redis
- `ANTHROPIC_API_KEY` — Claude API
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` — S3
- `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `CLERK_WEBHOOK_SECRET` — Auth
- `TESSERACT_CMD` — path to Tesseract binary (OCR fallback)

## Architecture

### Document Processing Pipeline

The core flow is orchestrated by `backend/tasks/processing_pipeline.py` (Celery task):

```
Upload (POST /jobs/upload)
  → validate file → S3 upload → create Job (status: queued) → queue Celery task

Celery: process_document(job_id)
  → download from S3
  → OCR: PyMuPDF text extraction → Tesseract fallback (scanned docs)
  → Claude API: extract structured fields (SSN/account numbers masked before sending)
  → validate extracted fields (required fields, formats, range checks, cross-field logic)
  → PASS: push to HubSpot, mark crm_written
  → FAIL: add to ReviewQueue, mark review_queue

Review (manual): GET /review → approve (corrections → HubSpot) or reject
```

### Key Modules

| Path | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app factory, router registration |
| `backend/config.py` | Pydantic settings (reads `.env`) |
| `backend/database.py` | Async SQLAlchemy engine + session |
| `backend/celery_app.py` | Celery configuration |
| `backend/tasks/processing_pipeline.py` | Full pipeline Celery task |
| `backend/services/extraction_service.py` | Claude API calls; masks PII before sending |
| `backend/services/validation_service.py` | Configurable field validation rules |
| `backend/services/hubspot_service.py` | CRM contact create/update with per-org field mappings |
| `backend/services/ocr_service.py` | PDF text extraction with OCR fallback |
| `backend/models/db_models.py` | SQLAlchemy ORM (all tables) |
| `backend/models/schemas.py` | Pydantic extraction schemas per document type |
| `backend/middleware/auth_middleware.py` | Clerk JWT verification → injects org_id, user_id, role |
| `frontend/src/lib/api.ts` | Centralized Axios client + all API functions |
| `frontend/src/lib/hooks/` | React Query hooks (useJobs, useReviewQueue, useDashboard) |

### Multi-Tenancy & Auth

- Clerk handles auth; JWT verified in `auth_middleware.py`
- Every DB query is scoped by `org_id` (from `request.state`)
- Role-based access (`admin`, `reviewer`, `viewer`) enforced via `require_role()` FastAPI dependency
- Per-org HubSpot field mappings stored in `HubSpotFieldMapping` table

### Database Models (key relationships)

- `Organization` → `User`, `Job`, `HubSpotFieldMapping`
- `Job` → `Extraction` (JSONB fields + confidence scores), `ValidationFlag`, `ReviewQueue`, `CRMLog`
- `AuditLog` — append-only audit trail for all actions

### Frontend

- Next.js 14 App Router with Clerk integration
- `frontend/src/app/(dashboard)/` — all protected pages (upload, review, audit, settings)
- React Query for server state; `useJobStatus` polls every 3s while a job is processing
- Radix UI + Tailwind CSS for components
- `frontend/src/middleware.ts` — Next.js auth middleware (protects dashboard routes)

### PII Handling

SSNs are masked to `XXX-XX-NNNN` and account numbers to `XXXX-NNNN` in `extraction_service.py` **before** sending text to the Claude API. Presigned S3 URLs (1-hour expiry) are used for document preview to avoid proxying files through the server.
## Skills Reference
When modifying extraction or validation logic, 
follow these skill guidelines:

- C:\Users\dibye\.claude\skills\extract-structured-data\SKILL.md
- C:\Users\dibye\.claude\skills\document-intelligence\SKILL.md
- C:\Users\dibye\.claude\skills\normalize-text\SKILL.md
