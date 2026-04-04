# DocFlow AI — User Manual

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Roles and Permissions](#2-roles-and-permissions)
3. [Adding a New Client](#3-adding-a-new-client)
4. [Client Guide — How to Upload a Document](#4-client-guide--how-to-upload-a-document)
5. [Back Office Guide — Processing the Review Queue](#5-back-office-guide--processing-the-review-queue)
6. [Document Status Reference](#6-document-status-reference)
7. [Day-to-Day Operations](#7-day-to-day-operations)
8. [Session Startup Checklist](#8-session-startup-checklist)
9. [Troubleshooting](#9-troubleshooting)
10. [Production Readiness Notes](#10-production-readiness-notes)

---

## 1. System Overview

DocFlow AI automates the processing of client documents for accounting firms. The workflow is:

```
Client uploads document
       ↓
AI extracts data (OCR + Claude)
       ↓
Validation checks run automatically
       ↓
PASS → Contact created in HubSpot CRM automatically
FAIL → Sent to Back Office Review Queue
       ↓
Back Office reviews and either:
  • Approve & Push to CRM
  • Request Re-upload (email sent to client)
  • Reject (document closed)
```

**Supported document types:**
- Tax Returns (W-2, 1040, etc.)
- Government IDs
- Bank Statements
- General Documents

**Tech stack:**
- Frontend: Next.js on `http://localhost:3000`
- Backend: FastAPI on `http://localhost:8080`
- Queue: Celery + Redis
- Storage: AWS S3
- CRM: HubSpot
- Email: AWS SES
- Auth: Clerk
- Database: Supabase (PostgreSQL)

---

## 2. Roles and Permissions

| Feature | Viewer (Client) | Reviewer (Back Office) | Admin |
|---|---|---|---|
| Upload documents | ✓ | ✓ | ✓ |
| View dashboard | ✓ | ✓ | ✓ |
| Review Queue | ✗ | ✓ | ✓ |
| Audit Trail | ✗ | ✓ | ✓ |
| Settings (HubSpot, Field Mappings) | ✗ | ✓ | ✓ |
| Approve / Reject / Notify | ✗ | ✓ | ✓ |

- **Clients** are assigned `viewer` role — they can only upload and see their dashboard.
- **Back office staff** are assigned `reviewer` role.
- **Admins** have full access including settings.

---

## 3. Adding a New Client

Follow these steps every time a new client needs to be onboarded:

### Step 1 — Verify client email in AWS SES (sandbox only)

> Skip this step once SES production access is approved.

1. Go to AWS Console → **SES** → **Verified Identities**
2. Click **Create Identity** → select **Email address**
3. Enter the client's email → **Create Identity**
4. Client receives a verification email — they must click the link
5. Status shows **Verified** ✓

### Step 2 — Create client account in Clerk

1. Go to [Clerk Dashboard](https://dashboard.clerk.com) → your app → **Users**
2. Click **Invite user** → enter client email → send invite
3. Client receives an invite email and sets up their password
4. Go to **Organizations** → **DocFlow AI - Dev** → **Members** → **Add user**
5. Select the client → set role to **Member**

### Step 3 — Seed client into the database

The Clerk webhook only fires if your backend + ngrok tunnel are running when the user joins the org. If not, run this script manually:

```bash
cd "c:\Agentic Workflow\Document Processing System\backend"
python
```

```python
import asyncio, sys
sys.path.insert(0, '.')
from database import AsyncSessionLocal
from models.db_models import User
from sqlalchemy import select

async def add_client(clerk_user_id: str, client_email: str):
    async with AsyncSessionLocal() as session:
        admin = await session.scalar(select(User).where(User.email == "dibyendumondal87@gmail.com"))
        existing = await session.scalar(select(User).where(User.email == client_email))
        if existing:
            print("Already exists:", existing.id)
            return
        client = User(
            org_id=admin.org_id,
            clerk_user_id=clerk_user_id,   # from Clerk Dashboard → Users → click user → User ID
            email=client_email,
            role="viewer"
        )
        session.add(client)
        await session.commit()
        print("Created:", client.id)

asyncio.run(add_client("user_XXXX", "client@example.com"))
```

**Where to find the Clerk User ID:**
Clerk Dashboard → **Users** → click the client → copy the **User ID** field (starts with `user_...`)

### Step 4 — Confirm access

Ask the client to log in at `http://localhost:3000` (or your production URL) and verify they can see the Dashboard and Upload page only.

---

## 4. Client Guide — How to Upload a Document

1. Go to the app URL and sign in with your email and password
2. Click **Upload** in the left sidebar
3. Click **Choose File** and select your document (PDF, JPG, PNG, TIFF supported — max 10 MB)
4. Select the **Document Type** from the dropdown:
   - Tax Return
   - Government ID
   - Bank Statement
   - General
5. Click **Upload**
6. The status will update automatically:
   - **Processing** — AI is reading and extracting data
   - **In HubSpot** — document processed successfully, no action needed
   - **Needs Review** — our team is reviewing your document
   - **Re-upload Requested** — check your email for instructions

**If you receive a re-upload request email:**
- Read the listed issues carefully
- Prepare a corrected or clearer version of the document
- Upload the new document using the same Upload page

---

## 5. Back Office Guide — Processing the Review Queue

### Accessing the Review Queue

1. Log in as a back office user (reviewer or admin)
2. Click **Review Queue** in the left sidebar
3. The badge number shows how many documents need attention

### Reviewing a Document

1. Click a document in the list (left panel)
2. The right panel shows:
   - **Validation Issues** — what the AI flagged
   - **Extracted Fields** — what data was found (click any value to edit/correct it)
   - **Preview** — presigned PDF link (if available)

### Actions

#### Request Re-upload (primary action)
Use when the document is unclear, incomplete, or incorrect.

1. Click **Request Re-upload** (indigo button)
2. Optionally type a message to the client explaining what to fix
3. Click **Send Re-upload Request**
4. An email is sent to the client automatically
5. The document is removed from the queue (status: `reupload_requested`)

#### Approve & Push to CRM
Use when the document is valid (with or without manual corrections).

1. Optionally edit any extracted fields by clicking on them
2. Click **Approve & Push to CRM** (green button)
3. A HubSpot contact is created/updated with the extracted data
4. Document is removed from the queue (status: `crm_written`)

#### Reject
Use when the document is completely unusable and no re-upload is needed.

1. Click **Reject** (red button)
2. Optionally enter a rejection reason
3. Click **Confirm Reject**
4. Document is closed (status: `error`)

### Audit Trail

All actions (uploads, approvals, rejections, field edits, emails sent) are logged in the **Audit Trail** page. Use this to track who did what and when.

---

## 6. Document Status Reference

| Status | Meaning |
|---|---|
| `queued` | Uploaded, waiting for Celery worker |
| `ocr` | AI is reading the document text |
| `extracting` | Claude is extracting structured fields |
| `validating` | Running validation rules |
| `review_queue` / Needs Review | Failed validation — awaiting back office action |
| `crm_written` / In HubSpot | Approved and pushed to HubSpot CRM |
| `reupload_requested` | Back office requested client to re-upload |
| `error` | Rejected or pipeline error |
| `crm_error` | Approved but HubSpot push failed (still approved) |

---

## 7. Day-to-Day Operations

### Monitoring
- Check **Review Queue** badge daily — documents accumulate here when AI flags issues
- Check **Audit Trail** for a full history of all activity

### HubSpot Field Mappings
If extracted field names need to map to different HubSpot properties:
1. Go to **Settings** → **Field Mappings**
2. Select document type
3. Update the mapping (extracted field → HubSpot property name)
4. Click **Save**

### HubSpot API Key
If the HubSpot connection needs updating:
1. Go to **Settings** → **HubSpot Integration**
2. Paste the new Private App token
3. Click **Save**

---

## 8. Session Startup Checklist

Every time you start a new development session, run these in **separate terminals**:

```bash
# Terminal 1 — Redis (required for Celery)
docker start docflow-redis

# Terminal 2 — Backend API
cd "c:\Agentic Workflow\Document Processing System\backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 3 — Celery worker (required for document processing)
cd "c:\Agentic Workflow\Document Processing System\backend"
python -m celery -A celery_app worker --loglevel=info -Q documents --pool=solo

# Terminal 4 — Frontend
cd "c:\Agentic Workflow\Document Processing System\frontend"
npm run dev
```

**Health check:** Visit `http://localhost:8080/docs` — you should see the FastAPI Swagger UI.

> Note: Port 8080 is required. Port 8000 is blocked by `sgibiosrv.exe` (Samsung service).

---

## 9. Troubleshooting

### Upload fails with "reviewer role required"
- The user's role in the DB may be incorrect. Run:
```bash
cd backend && python -c "
import asyncio, sys; sys.path.insert(0, '.')
from database import AsyncSessionLocal
from models.db_models import User
from sqlalchemy import select
async def fix():
    async with AsyncSessionLocal() as s:
        u = await s.scalar(select(User).where(User.email == 'client@example.com'))
        print('Role:', u.role)
asyncio.run(fix())
"
```

### Document stuck in "queued" status
- Celery worker is not running. Start Terminal 3 from the startup checklist.
- Check Redis is running: `docker ps | grep docflow-redis`

### "User not found" error on login
- The client was added to Clerk but not seeded into the database.
- Follow Step 3 of [Adding a New Client](#3-adding-a-new-client).

### Email goes to spam
- Expected in development when sending from a personal Gmail via SES.
- In production: use a domain email (e.g. `noreply@yourfirm.com`) with SPF/DKIM records.
- For now: ask the client to mark the email as "Not spam" once — future emails will reach inbox.

### HubSpot push fails but document shows "approved"
- This is by design — approval never blocks on HubSpot.
- Check the Audit Trail for a `CRM_PUSH_FAILED` entry with the error detail.
- Verify the HubSpot API key in Settings is valid.

### Celery fails to start on Windows
```bash
# Always use python -m celery, not the celery binary
python -m celery -A celery_app worker --loglevel=info -Q documents --pool=solo
```

---

## 10. Production Readiness Notes

These steps are needed before going live with real clients:

| Item | Status | Action Required |
|---|---|---|
| AWS SES sandbox | Dev only | Request production access in AWS Console → SES → Account dashboard → Request production access |
| Domain email sender | Pending | Verify a domain (e.g. `yourfirm.com`) in SES instead of a personal Gmail |
| SPF / DKIM records | Pending | Add DNS records provided by SES for your domain |
| HTTPS / custom domain | Pending | Deploy frontend + backend behind a real domain with SSL |
| HubSpot custom properties | 10/10 used | Upgrade HubSpot plan to add more custom properties |
| Clerk production instance | Dev only | Create a Clerk production instance (separate from development) |
| ngrok dependency | Dev only | Remove ngrok — use a stable public URL for the Clerk webhook endpoint |
