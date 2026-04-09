# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DocFlow AI** is a full-stack document intelligence platform. It automates processing of client documents by extracting structured data via Claude AI, validating it, and either auto-pushing to a CRM or routing to a human review queue.

The platform is multi-domain: one shared backend, one frontend app per industry vertical.

```
apps/
  accounting/    ← accounting firm UI (active)
  healthcare/    ← clinic/hospital UI (stub — scaffold when first healthcare client onboards)
  legal/         ← law firm UI (stub — scaffold when first legal client onboards)
packages/
  ui/            ← shared UI components (extract here when 2+ apps share components)
  api-client/    ← shared API hooks (extract here when 2+ apps share API calls)
backend/
  domains/
    accounting/  ← doc types: tax_return, government_id, bank_statement, general
    healthcare/  ← stub
    legal/       ← stub
```

## Commands

### Backend

```bash
# Install dependencies (from repo root)
pip install -r backend/requirements.txt

# Run dev server (auto-reload, port 8080)
python backend/run.py

# Start Celery worker (separate terminal — required for document processing)
celery -A celery_app worker --loglevel=info -Q documents

# Re-dispatch any stuck jobs with status=queued (Windows utility)
python backend/redispatch.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Database migrations (from backend/ directory)
alembic upgrade head        # apply all migrations
alembic revision --autogenerate -m "description"  # create new migration
```

### Frontend (per domain app)

```bash
# From the domain app directory, e.g. apps/accounting/
npm install
npm run dev      # port 3000
npm run build
npm run lint
npm start        # production

# Or from workspace root:
npm run accounting   # starts apps/accounting dev server
npm run healthcare   # starts apps/healthcare dev server (once scaffolded)
npm run legal        # starts apps/legal dev server (once scaffolded)
```

### Environment Setup

Copy `backend/.env.example` to `backend/.env`. Required variables:
- `DATABASE_URL` — PostgreSQL async URL (`postgresql+asyncpg://...`)
- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — Redis
- `ANTHROPIC_API_KEY` — Claude API (model: `claude-sonnet-4-6`, configurable via `CLAUDE_MODEL`)
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` — S3
- `SES_FROM_EMAIL` — AWS SES verified identity for email notifications
- `CLERK_SECRET_KEY`, `CLERK_PUBLISHABLE_KEY`, `CLERK_WEBHOOK_SECRET` — Auth
- `TESSERACT_CMD` — path to Tesseract binary (OCR fallback; e.g. `C:/Program Files/Tesseract-OCR/tesseract.exe`)
- `ALLOWED_ORIGINS` — comma-separated CORS origins (default: `http://localhost:3000`)

Health check: `GET /health` returns key configuration status without credentials.

## Architecture

### Document Processing Pipeline

The core flow is orchestrated by `backend/tasks/processing_pipeline.py` (Celery task):

```
Upload (POST /jobs/upload)
  → validate file type + doc_type → S3 upload → create Job (status: queued) → queue Celery task

Celery: process_document(job_id)
  → download from S3
  → OCR: PyMuPDF text extraction → Tesseract fallback if text density < 100 chars/page
  → truncate to 90,000 chars → mask SSNs (XXX-XX-NNNN) + account numbers (XXXX-NNNN)
  → Claude API (temp=0): extract structured fields + per-field confidence scores
  → validate: required fields, format patterns, numeric ranges, cross-field logic
  → PASS: push to HubSpot, mark crm_written
  → FAIL: add to ReviewQueue, mark review_queue

Review (manual): GET /review → approve (corrections → HubSpot) or reject → optional re-upload request
```

Every status transition is written to `audit_log`. Job status lifecycle:
`pending → queued → ocr → extracting → validating → review_queue | crm_pending → crm_written | error`

### Key Modules

| Path | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app factory, router registration |
| `backend/config.py` | Pydantic settings (reads `.env`); `get_settings()` is `@lru_cache` |
| `backend/database.py` | Async SQLAlchemy engine + session |
| `backend/celery_app.py` | Celery configuration; `task_acks_late=True`, `worker_prefetch_multiplier=1` |
| `backend/tasks/processing_pipeline.py` | Full pipeline Celery task; uses `NullPool` + new event loop per task to avoid asyncpg/Windows conflicts |
| `backend/services/extraction_service.py` | Claude API calls; masks PII before sending; `MAX_TEXT_CHARS=90_000` |
| `backend/services/validation_service.py` | Configurable `REQUIRED_FIELDS`, `FORMAT_RULES`, `RANGE_RULES`, `CROSS_FIELD_RULES` constants at module top |
| `backend/services/hubspot_service.py` | CRM contact create/update; `__split_name__` special mapping splits full name → firstname/lastname |
| `backend/services/ocr_service.py` | PDF text extraction with Tesseract fallback |
| `backend/services/audit_service.py` | Append-only audit log writes |
| `backend/services/email_service.py` | AWS SES email notifications (re-upload requests, reviewer alerts) |
| `backend/services/storage_service.py` | S3 upload/download; presigned URL generation (1-hour expiry) |
| `backend/models/db_models.py` | SQLAlchemy ORM (all tables) |
| `backend/models/schemas.py` | Pydantic extraction schemas per doc type; all fields `Optional[str]` |
| `backend/middleware/auth_middleware.py` | Clerk JWT verification → injects `org_id`, `user_id`, `role` into `request.state` |
| `backend/routers/export.py` | `GET /export/csv` and `/export/json`; admin-only; org-scoped |
| `apps/accounting/src/lib/api.ts` | Centralized Axios client + all API functions + TypeScript types |
| `apps/accounting/src/lib/hooks/` | React Query hooks (useJobs, useReviewQueue, useDashboard, useCurrentUser) |

### Multi-Tenancy & Auth

- Clerk handles auth; JWT verified in `auth_middleware.py` via Clerk JWKS endpoint
- Every DB query is scoped by `org_id` (from `request.state`)
- Role hierarchy: `admin` > `reviewer` > `viewer` — enforced via `require_role()` FastAPI dependency
  - `viewer` — read-only (dashboard, audit trail); can also upload
  - `reviewer` — can review, approve/reject
  - `admin` — full access including settings, export, user management
- Clerk webhook (`POST /auth/webhook`, verified via svix) creates `Organization` + seeds default HubSpot field mappings on org creation, creates `User` on member join

### Database Models (key relationships)

- `Organization` → `User`, `Job`, `HubSpotFieldMapping`
- `Job` → `Extraction` (JSONB `raw_fields` + `confidence` scores), `ValidationFlag`, `ReviewQueue`, `CRMLog`, `AuditLog`
- `AuditLog` — append-only; never update or delete rows

### Domain Plug-in Architecture

All domain knowledge lives in `backend/domains/` — services are domain-agnostic.

- `backend/domains/base.py` — `DomainConfig` dataclass + `CrossFieldRule` NamedTuple
- `backend/domains/__init__.py` — `DOMAIN_REGISTRY`, `get_domain(doc_type)`, `allowed_types()`
- `backend/domains/accounting/` — 4 accounting doc types (active)
- `backend/domains/healthcare/` — stub (add `patient_intake.py`, `insurance_claim.py` here)
- `backend/domains/legal/` — stub (add `contract.py`, `court_filing.py` here)

To add a new doc type: create a `DomainConfig` in the appropriate domain package and add it to that package's domain list. Zero changes to any service required.

### Validation Configuration

Validation rules are defined per-domain in `DomainConfig`:
- `required_fields` — fields that must be non-null
- `format_rules` — dict of field → regex pattern string
- `range_rules` — dict of field → (min, max) tuple
- `cross_field_rules` — list of `CrossFieldRule` (mutually_exclusive | date_order)

### Frontend (apps/accounting — reference implementation)

- Next.js 14 App Router with Clerk integration
- `apps/accounting/src/app/(dashboard)/` — all protected pages (upload, review, audit, settings)
- `apps/accounting/src/middleware.ts` — Next.js auth middleware (protects all dashboard routes)
- React Query for server state; `useJobStatus` polls every 3s while a job is processing
- Radix UI + Tailwind CSS for components; `apps/accounting/src/lib/utils.ts` has `cn()` helper
- Each domain app (`apps/healthcare/`, `apps/legal/`) follows the same structure with domain-specific branding, copy, and doc type UX

### PII Handling

SSNs are masked to `XXX-XX-NNNN` and account numbers to `XXXX-NNNN` in `extraction_service.py` **before** sending text to the Claude API. Presigned S3 URLs (1-hour expiry) are used for document preview to avoid proxying files through the server.

### Windows-Specific Notes

- `asyncpg` is incompatible with Windows `ProactorEventLoop`; the Celery task uses `WindowsSelectorEventLoopPolicy` + a fresh event loop per task
- `redispatch.py` is a one-off utility to re-queue stuck jobs on Windows

## Skills Reference

When modifying extraction or validation logic, follow these skill guidelines:

- C:\Users\dibye\.claude\skills\extract-structured-data\SKILL.md
- C:\Users\dibye\.claude\skills\document-intelligence\SKILL.md
- C:\Users\dibye\.claude\skills\normalize-text\SKILL.md
