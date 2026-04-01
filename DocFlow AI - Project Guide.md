# DocFlow AI — Complete Project Guide
### What We Are Building, How It Works, and Why Each Piece Exists

---

## What Is DocFlow AI?

DocFlow AI is an intelligent document processing platform built for **accounting firms**. Instead of a staff member manually opening a client's tax return or bank statement and typing out the data, DocFlow AI:

1. Accepts uploaded documents (PDFs, images)
2. Reads and extracts key information automatically using AI
3. Validates the extracted data
4. Either sends it directly to the firm's CRM (HubSpot) or flags it for a human to review

**The business value:** A task that takes a human 2+ hours per document can be done in seconds, with an audit trail and zero manual data entry.

---

## The Big Picture — How All Pieces Connect

```
USER (Browser)
    ↓ uploads document
FRONTEND (Next.js) — the website the user sees
    ↓ sends file to
BACKEND API (FastAPI) — the brain that receives requests
    ↓ stores file in
AWS S3 — cloud file storage (like a hard drive in the cloud)
    ↓ queues a background job in
REDIS — a fast message queue ("do this task next")
    ↓ picked up by
CELERY WORKER — a background process that does the heavy lifting
    ↓ reads text from the file using
OCR (Tesseract) — reads text from scanned/image PDFs
    ↓ sends text to
CLAUDE AI (Anthropic) — extracts structured data using AI
    ↓ validates the data, then either
HUBSPOT CRM ← auto-approved data sent here
    OR
REVIEW QUEUE ← flagged data goes here for human review
    ↓ everything is stored in
POSTGRESQL (Supabase) — the main database
    ↓ everything is logged in
AUDIT LOG — full history of every action
```

---

## Technology Deep Dive — What Each Tool Is and Why We Use It

---

### 1. Python + FastAPI — The Backend

**What it is:**
Python is the programming language. FastAPI is a web framework — it lets us define API endpoints (URLs that the frontend calls to do things).

**Why FastAPI specifically:**
- Very fast (one of the fastest Python frameworks)
- Built-in support for `async` (handles many requests at the same time without slowing down)
- Automatically generates API documentation at `http://localhost:8000/docs`

**What it does in our project:**
- Receives file uploads from the frontend
- Authenticates users (checks their login token)
- Returns job status, review queue, dashboard statistics
- Handles approve/reject actions on reviewed documents

**Key files:**
- `backend/main.py` — starts the FastAPI app
- `backend/routers/` — each file handles one area (jobs, review, dashboard, etc.)

---

### 2. PostgreSQL — The Main Database

**What it is:**
PostgreSQL (often called "Postgres") is a relational database — think of it as a very powerful, structured spreadsheet system where data is stored in tables with rows and columns.

**Why we need it:**
Every document uploaded, every extraction result, every user action needs to be stored permanently. Without a database, everything would disappear when the server restarts.

**What it stores in our project:**
| Table | What it holds |
|-------|--------------|
| `Organization` | Accounting firm accounts |
| `User` | Staff members and their roles |
| `Job` | Every uploaded document and its status |
| `Extraction` | The AI-extracted data from each document |
| `ValidationFlag` | Any errors found during validation |
| `ReviewQueue` | Documents waiting for human review |
| `AuditLog` | Complete history of every action |
| `HubSpotFieldMapping` | Which extracted fields map to which HubSpot fields |

---

### 3. Supabase — Where Our PostgreSQL Lives

**What it is:**
Supabase is a cloud platform that hosts PostgreSQL databases. Instead of installing and managing a database on your own computer or server, Supabase handles that for you.

**Why Supabase:**
- Free tier available (great for development)
- Managed — they handle backups, security, uptime
- Gives you a web UI to browse your data
- Your project: **"Document Processing"** (Project ID: `itrsetorevhlvkikqymz`)

**How we connect to it:**
Through the `DATABASE_URL` in your `.env` file:
```
DATABASE_URL=postgresql+asyncpg://postgres:PASSWORD@db.itrsetorevhlvkikqymz.supabase.co:5432/postgres
```
The `+asyncpg` part tells Python to use an async driver — this is what lets FastAPI handle many requests at once without waiting.

---

### 4. Redis — The Message Queue

**What it is:**
Redis is an extremely fast in-memory data store. Think of it as a to-do list that lives in RAM — things can be added to it and read from it in microseconds.

**Why we need it:**
Processing a document takes time (OCR + AI extraction can take 10-30 seconds). We can't make the user wait for the HTTP request to complete. Instead:
1. The API instantly says "OK, your document is queued" (fast response)
2. The actual work is put into Redis as a "task"
3. A separate Celery worker picks it up and does the heavy lifting in the background

This pattern is called a **message queue** or **task queue**.

**Why Redis specifically:**
- Blazing fast (stores data in RAM, not on disk)
- Perfect for temporary task queuing
- Works natively with Celery

---

### 5. Upstash — Where Our Redis Lives

**What it is:**
Upstash is a cloud platform for serverless Redis — just like Supabase hosts our Postgres, Upstash hosts our Redis.

**Why Upstash:**
- Free tier with generous limits
- No server to manage
- Works from anywhere (your laptop, cloud server, etc.)
- Your instance: `charming-lacewing-89786.upstash.io`

**The `rediss://` vs `redis://` difference:**
The double-s (`rediss://`) means the connection is **encrypted with TLS**. Upstash requires this for security. Without it, your Redis password would travel over the internet unencrypted.

---

### 6. Celery — The Background Worker

**What it is:**
Celery is a Python library that runs tasks in the background, separate from the main web server. It watches Redis for new tasks and executes them.

**Why we need it:**
If FastAPI tried to do the OCR + AI processing during the HTTP request, the user would wait 30+ seconds for a response. That's terrible UX. Celery handles it asynchronously:

```
Request comes in → FastAPI queues task in Redis → FastAPI responds instantly
                                                 ↓
                                    Celery picks up task from Redis
                                    Celery does all the heavy work
                                    Celery updates database with result
```

**Key file:** `backend/tasks/processing_pipeline.py` — this is the full pipeline Celery runs for each document.

**How to run it** (separate terminal):
```bash
celery -A celery_app worker --loglevel=info -Q documents
```

---

### 7. AWS S3 — File Storage

**What it is:**
Amazon S3 (Simple Storage Service) is cloud file storage. Think of it as a Google Drive/Dropbox but for your application — you can store and retrieve files programmatically.

**Why we need it:**
When a user uploads a PDF, we can't store it in the database (databases aren't designed for large files) or on the server's hard drive (servers can restart and lose files). S3 stores files permanently and reliably.

**How it works in our project:**
1. User uploads PDF → FastAPI sends it to S3
2. S3 stores it and gives back a "key" (like a file path)
3. Celery downloads it from S3 to process it
4. Frontend gets a "presigned URL" (a temporary link) to show the PDF preview

**Presigned URLs:** Instead of making files public, S3 generates a temporary URL (valid for 1 hour) that lets the frontend display the PDF securely.

---

### 8. Claude AI (Anthropic) — The Intelligence

**What it is:**
Claude is Anthropic's AI model — the same AI powering this conversation. Via API, we can send it text and ask it to extract structured information.

**Why Claude specifically:**
- Excellent at understanding documents in context
- Can extract specific fields (name, SSN, income, dates) from unstructured text
- Handles different document layouts and formats
- Returns structured JSON that our system can process

**How it works in our project:**
1. OCR extracts raw text from the PDF
2. **Before sending to Claude:** SSNs are masked (`XXX-XX-1234`) and account numbers are masked (`XXXX-5678`) — so sensitive data never leaves your system
3. We send Claude a prompt like: *"Extract the following fields from this tax return: name, filing status, total income..."*
4. Claude returns a JSON object with all the fields and confidence scores

**Key file:** `backend/services/extraction_service.py`

---

### 9. OCR — Reading Scanned Documents

**What it is:**
OCR stands for **Optical Character Recognition** — it's technology that reads text from images. When a PDF is a scanned image (rather than a digital PDF with selectable text), OCR converts the image into readable text.

**Two-step process in our project:**
1. **PyMuPDF** first — tries to extract digital text directly from the PDF (fast, accurate)
2. **Tesseract** fallback — if the page has less than 100 characters of digital text, it assumes it's a scanned image and runs OCR on it

**Key file:** `backend/services/ocr_service.py`

---

### 10. Clerk — Authentication

**What it is:**
Clerk is a complete authentication service — it handles user sign-up, sign-in, organizations (multiple firms), and roles (admin, reviewer, viewer).

**Why not build our own login system:**
Authentication is complex and security-critical. Building it from scratch is risky. Clerk handles:
- Secure password storage
- JWT tokens (digital proof that a user is logged in)
- Organization management (each accounting firm is an "org")
- Role-based access (admins can do everything, viewers can only see)

**How JWT works (simplified):**
When you log in, Clerk gives your browser a token (a long encrypted string). Every API request sends this token. Our backend verifies it with Clerk's public keys — if valid, it knows who you are and what org you belong to.

**Key file:** `backend/middleware/auth_middleware.py`

---

### 11. HubSpot — The CRM Destination

**What it is:**
HubSpot is a Customer Relationship Management (CRM) platform — it stores client contacts, deals, and interactions.

**Why it's in our project:**
Accounting firms already use HubSpot to manage their clients. Once DocFlow AI extracts data from a document, it automatically creates or updates the client's record in HubSpot — no manual data entry needed.

**How it works:**
Each firm can configure which extracted fields map to which HubSpot fields (e.g., "Total Income" → HubSpot field "annual_revenue"). This mapping is stored per-org in the database.

**Key file:** `backend/services/hubspot_service.py`

---

### 12. Next.js — The Frontend (Website)

**What it is:**
Next.js is a React framework for building websites. React is a JavaScript library for building user interfaces — Next.js adds routing, server-side rendering, and other production features on top of it.

**Why Next.js:**
- Industry standard for modern web apps
- Server-side rendering (pages load fast, good for SEO)
- Built-in routing (each folder in `src/app/` becomes a URL)
- Works seamlessly with Clerk and TypeScript

**What it does:**
- Shows the document upload interface
- Displays the review queue (documents needing human attention)
- Shows the dashboard with ROI metrics
- Handles the settings page for HubSpot configuration

---

### 13. Alembic — Database Migrations

**What it is:**
Alembic is a database migration tool for Python. Migrations are version-controlled changes to your database schema.

**Why we need it:**
When you first set up the project, the Supabase database is empty — it has no tables. Alembic creates all the tables by running migration scripts. Later, if we add a new column or table, Alembic handles updating the database safely without losing existing data.

**Where migrations live:** `backend/migrations/`

**This is still pending** — we'll run it next session:
```bash
cd backend && alembic upgrade head
```

---

## What's Been Set Up So Far

| Component | Status | Details |
|-----------|--------|---------|
| Python packages | ✅ Done | All backend dependencies installed |
| Node packages | ✅ Done | All frontend dependencies installed |
| `.env` file | ✅ Done | Created with credentials |
| PostgreSQL | ✅ Done | Supabase "Document Processing" project |
| Redis | ✅ Done | Upstash cloud Redis (TLS encrypted) |
| Anthropic API | ✅ Done | Claude API key configured |
| Clerk Auth | ✅ Partial | Keys added, webhook secret pending |
| AWS S3 | ⏳ Tomorrow | Need bucket + IAM credentials |
| DB Migrations | ⏳ Tomorrow | Run Alembic to create tables |
| Backend startup | ⏳ Tomorrow | FastAPI + Celery |
| Frontend startup | ⏳ Tomorrow | Next.js dev server |

---

## What Happens Tomorrow (Next Session)

1. **AWS S3 setup** — Create bucket, create IAM user, get access key + secret
2. **Clerk webhook** — Get the webhook signing secret
3. **Run database migrations** — This creates all the tables in Supabase
4. **Start the backend** — FastAPI server + Celery worker
5. **Start the frontend** — Next.js dev server
6. **Test the full pipeline** — Upload a document and watch it process end-to-end

---

## Your `.env` File Explained

```env
# Where your PostgreSQL database lives (Supabase cloud)
DATABASE_URL=postgresql+asyncpg://...supabase.co.../postgres

# Redis for background task queuing (Upstash cloud, encrypted)
REDIS_URL=rediss://...upstash.io:6379
CELERY_BROKER_URL=rediss://...         # Celery sends tasks here
CELERY_RESULT_BACKEND=rediss://...     # Celery stores results here

# AWS file storage credentials
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
S3_BUCKET_NAME=docflow-ai-uploads

# Claude AI — the brain that reads documents
ANTHROPIC_API_KEY=sk-ant-...

# Clerk — handles all user login and authentication
CLERK_SECRET_KEY=sk_test_...
CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_WEBHOOK_SECRET=...               # Verifies Clerk events are genuine
CLERK_JWKS_URL=...                     # Where to get Clerk's public keys

# App behaviour
MAX_UPLOAD_BYTES=20971520              # Max file size: 20 MB
HOURS_SAVED_PER_DOC_BASELINE=2.0      # Used for ROI calculation on dashboard
TESSERACT_CMD=C:\Program Files\...    # Path to OCR software

# Frontend knows where the backend API is
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

*Document created: 2026-03-31 | Project: DocFlow AI | Author: Claude Code*
