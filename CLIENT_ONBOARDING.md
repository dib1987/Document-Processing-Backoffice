# DocFlow AI — New Client Onboarding Guide

> Use this guide each time you onboard a new client organization onto DocFlow AI.
> Applies to both Accounting and Healthcare verticals.

---

## Overview

Each client gets their own **isolated Clerk organization** (multi-tenant). Their data is 100% separated from other clients. You (Dibyendu) manage the platform as super-admin; the client's staff are added as `admin`, `reviewer`, or `viewer` roles inside their org.

---

## Part 1: Pre-Onboarding (Your Setup — 10 minutes)

### Step 1: Create the Client Organization in Clerk

1. Log in to [Clerk Dashboard](https://dashboard.clerk.com)
2. Go to **Organizations** → **Create Organization**
3. Name it after the client (e.g., `Smith & Associates CPA`)
4. Copy the **Organization ID** (`org_xxxxxxxx`) — you'll need it for debugging

### Step 2: Invite the Client's Admin User

1. In Clerk Dashboard → Organizations → select the client org
2. Go to **Members** → **Invite Member**
3. Enter the client's admin email address
4. Set role: **Admin**
5. Send invitation
6. The client receives an email → they click the link → they create their password

> **Note:** The Clerk webhook (`POST /auth/webhook`) automatically fires when the org and first user are created. This seeds the default HubSpot field mappings for that org in your database. No manual DB work needed.

### Step 3: Verify the Org Was Created in Your Database

```bash
# Quick check via the health + auth flow
# Or connect to your DB and run:
SELECT id, name, created_at FROM organizations ORDER BY created_at DESC LIMIT 5;
```

---

## Part 2: Client-Side Setup (Walk the Client Through This)

### Step 4: Client Logs In

- **Accounting clients** → `http://localhost:3000` (local) or your Vercel URL (live)
- **Healthcare clients** → `http://localhost:3001` (local) or your Vercel URL (live)
- Click **Sign In** → enter the email they received the invitation on → set password

### Step 5: Configure HubSpot Integration (if client uses HubSpot)

1. Client (admin) goes to **Settings** page
2. Scrolls to **HubSpot Integration**
3. Enters their HubSpot API Key
4. Clicks **Save**
5. The green "Connected" banner confirms it works

> If client doesn't use HubSpot yet: leave blank. Jobs will go to review queue and CRM push will be skipped. You can configure this later.

### Step 6: Review Default Field Mappings

1. In Settings → scroll to **HubSpot Field Mappings**
2. Shows default mappings (e.g., `full_name` → HubSpot `firstname`/`lastname`)
3. Client can update mappings to match their custom HubSpot property names
4. Click **Save Mappings**

---

## Part 3: Add the Client's Team Members

### Step 7: Invite Additional Staff

The client's **admin** can invite their own team, OR you do it for them:

1. Clerk Dashboard → Organizations → client org → Members → Invite
2. Role guide:
   - **Admin** — full access: settings, export, all reviews, user management
   - **Reviewer** — can review/approve/reject documents, view audit trail
   - **Viewer** — read-only dashboard + can upload documents (most staff are viewers)

---

## Part 4: First Document Upload (Training Run)

### Step 8: Upload a Test Document

1. Staff goes to **Upload** page
2. Selects **Document Type** from the dropdown:
   - Accounting: `Tax Return`, `Government ID`, `Bank Statement`, `General`
   - Healthcare: `Patient Intake`, `Insurance Claim`, `Medical Record`
3. Drags and drops a PDF (or clicks to browse)
4. Clicks **Upload**
5. Status shows: `Queued → OCR → Extracting → Validating → ...`

### Step 9: Review the Result

**If validation passes automatically:**
- Status → `CRM Pending` → `CRM Written`
- HubSpot contact created/updated automatically
- No action needed from staff

**If validation flags issues:**
- Status → `Review Queue`
- A reviewer goes to **Review** page
- Sees the extracted fields + which fields failed validation
- Can correct fields inline and **Approve** (pushes to HubSpot) or **Reject**

### Step 10: Confirm in HubSpot

1. Log into HubSpot
2. Go to Contacts
3. Search for the contact from the document
4. Confirm the fields were populated correctly

---

## Part 5: Ongoing Operations

### Daily Workflow for Reviewers

1. Log in → **Dashboard** shows counts: queued, in review, processed today
2. Go to **Review** → work through flagged documents
3. Approve (auto-pushes to HubSpot) or Reject (sends re-upload request email to uploader)

### Admin Tasks

- **Export data**: Admin → Export page → filter by date/status → download CSV or JSON
- **Audit trail**: Admin/Reviewer → Audit page → full history of every action on every document
- **Add/remove users**: Via Clerk Dashboard (no DocFlow UI for this yet)

### Re-Upload Request Flow

When a reviewer rejects a document:
1. Reviewer clicks **Request Re-upload** with a reason
2. The original uploader gets an automated email (via AWS SES) explaining what to fix
3. They re-upload → new job created → goes through pipeline again

---

## Part 6: Roles Quick Reference

| Action | Viewer | Reviewer | Admin |
|--------|--------|----------|-------|
| Upload documents | ✅ | ✅ | ✅ |
| View dashboard | ✅ | ✅ | ✅ |
| Review/approve/reject | ❌ | ✅ | ✅ |
| View audit trail | ❌ | ✅ | ✅ |
| Export CSV/JSON | ❌ | ❌ | ✅ |
| Manage HubSpot settings | ❌ | ❌ | ✅ |
| View/edit field mappings | ❌ | ❌ | ✅ |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Job stuck at `Queued` | Celery worker not running — start it: `celery -A celery_app worker --loglevel=info -Q documents` |
| HubSpot push failing | Check API key in Settings; check audit log for CRM error details |
| Email notifications not sending | Verify SES sender email in AWS console; check `SES_FROM_EMAIL` env var |
| User can't log in | Check Clerk Dashboard → verify their email, check org membership |
| Extraction fields empty | Check backend logs; may be OCR failure — ensure Tesseract installed at `TESSERACT_CMD` path |
| "Access Denied" on review page | User's role is `viewer` — upgrade to `reviewer` or `admin` in Clerk |

---

## Local Development URLs (for demo / testing)

| Service | URL |
|---------|-----|
| Accounting frontend | http://localhost:3000 |
| Healthcare frontend | http://localhost:3001 |
| Backend API | http://localhost:8080 |
| API health check | http://localhost:8080/health |
| API docs (Swagger) | http://localhost:8080/docs |

### Start everything locally:

```bash
# Terminal 1 — Backend
cd backend
python run.py

# Terminal 2 — Celery Worker (required for document processing)
cd backend
celery -A celery_app worker --loglevel=info -Q documents

# Terminal 3 — Accounting frontend
cd apps/accounting
npm run dev
# → http://localhost:3000

# Terminal 4 — Healthcare frontend
cd apps/healthcare
npm run dev
# → http://localhost:3001
```
