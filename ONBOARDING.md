# DocFlow AI — New Client Onboarding Guide

This guide is for the **system administrator** setting up a new client firm on DocFlow AI.
Follow every step in order. Each section has a checklist so nothing is missed.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Pre-Onboarding Checklist](#2-pre-onboarding-checklist)
3. [Start the System](#3-start-the-system)
4. [Configure the Clerk Webhook](#4-configure-the-clerk-webhook)
5. [Create the Organisation in Clerk](#5-create-the-organisation-in-clerk)
6. [Add Users in Clerk](#6-add-users-in-clerk)
7. [Seed Users into the Database](#7-seed-users-into-the-database)
8. [Configure HubSpot CRM](#8-configure-hubspot-crm)
9. [Verify Email Notifications (AWS SES)](#9-verify-email-notifications-aws-ses)
10. [End-to-End Test](#10-end-to-end-test)
11. [Share Access with the Client](#11-share-access-with-the-client)
12. [Ongoing Maintenance](#12-ongoing-maintenance)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Prerequisites

Before onboarding any client, confirm the following are in place.

### Accounts and credentials
- [ ] Clerk account with the DocFlow AI application created
- [ ] AWS account with S3 bucket (`docflow-ai-uploads`) and SES configured
- [ ] Supabase (or PostgreSQL) database running and migrations applied
- [ ] `backend/.env` fully populated — see `.env.example` for all required keys

### Software running on your machine
- [ ] Docker Desktop installed and running
- [ ] Python 3.13 installed with all backend dependencies (`pip install -r backend/requirements.txt`)
- [ ] Node.js installed with frontend dependencies (`npm install` in `frontend/`)
- [ ] ngrok installed (for webhook delivery during development)

### Access you will need
- [ ] Admin login to [Clerk Dashboard](https://dashboard.clerk.com)
- [ ] AWS Console access (SES)
- [ ] The client's HubSpot Private App token (if they use HubSpot)
- [ ] The client's email addresses for all users

---

## 2. Pre-Onboarding Checklist

Collect the following from the client before you start:

| Item | Example | Notes |
|---|---|---|
| Firm name | Acme Accounting Ltd | Used as the organisation name in Clerk and DB |
| Uploader name(s) + email(s) | jane@acme.com | These users get `viewer` role |
| Back office name(s) + email(s) | admin@acme.com | These users get `reviewer` role |
| HubSpot Private App token | `pat-na2-...` | Optional — only if they use HubSpot |
| Document types they will use | Tax Return, Bank Statement | Determines validation rules applied |
| Preferred language for emails | English | For future multi-language support |

---

## 3. Start the System

The backend must be running throughout the onboarding process. Open **4 separate terminals**:

```bash
# Terminal 1 — Redis
docker start docflow-redis
# If container doesn't exist yet:
# docker run -d --name docflow-redis -p 6379:6379 redis:alpine

# Terminal 2 — Backend API
cd "c:/Agentic Workflow/Document Processing System/backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 3 — Celery Worker (required for document processing)
cd "c:/Agentic Workflow/Document Processing System/backend"
python -m celery -A celery_app worker --loglevel=info -Q documents --pool=solo

# Terminal 4 — Frontend
cd "c:/Agentic Workflow/Document Processing System/frontend"
npm run dev
```

**Verify everything is up:**
- Backend: `http://localhost:8080/health` — should return `{"status": "ok"}`
- Frontend: `http://localhost:3000` — should show the login page

---

## 4. Configure the Clerk Webhook

The Clerk webhook automatically creates the organisation and users in the DocFlow database
when they are added in Clerk. Without it, you must seed them manually (Step 7).

### 4a. Start ngrok

```bash
ngrok http 8080
```

Copy the **Forwarding URL** (e.g. `https://abc123.ngrok-free.app`).

> The ngrok URL changes every time you restart it. Update the webhook URL in Clerk each session.

### 4b. Register the webhook in Clerk

1. Go to [Clerk Dashboard](https://dashboard.clerk.com) → your app
2. Go to **Webhooks** → **Add Endpoint**
3. Set the URL to: `https://YOUR-NGROK-URL.ngrok-free.app/auth/webhook`
4. Subscribe to these events:
   - `organization.created`
   - `organizationMembership.created`
5. Copy the **Signing Secret** → paste it into `backend/.env` as `CLERK_WEBHOOK_SECRET`
6. Restart the backend (Terminal 2) so it picks up the new secret

> **If ngrok is not running:** Skip this step and use the manual seed scripts in Step 7 instead.

---

## 5. Create the Organisation in Clerk

1. Log into [Clerk Dashboard](https://dashboard.clerk.com)
2. Go to **Organizations** → **Create Organization**
3. Enter the firm name exactly as agreed (e.g. `Acme Accounting Ltd`)
4. Copy the **Organization ID** (starts with `org_...`) — save it, you will need it in Step 7

**If webhook is active:** The organisation is automatically created in the DocFlow database.
Check your backend Terminal 2 logs for:
```
Clerk webhook received: organization.created
Created org: Acme Accounting Ltd
```

---

## 6. Add Users in Clerk

Repeat for each user at the firm.

### 6a. Create the user account

1. Go to **Users** → **Create User**
2. Enter their **email address** and a **temporary password**
   - Use a strong temporary password (e.g. `DocFlow@2024!`)
   - The client will be asked to change it on first login
3. Copy the **User ID** (starts with `user_...`) — save it for Step 7

> **Where to find the User ID:** Clerk Dashboard → Users → click the user → the ID is shown at the top of the profile page.

### 6b. Add the user to the organisation

1. Go to **Organizations** → select the firm → **Members** → **Add Member**
2. Search for the user by email
3. Assign role:
   - `org:member` → for both uploaders (viewer) and back office (reviewer)
   - `org:admin` → for admin users

> **Note:** Clerk roles do not map directly to DocFlow roles. The `viewer` role (for client uploaders)
> is set in the DocFlow database in Step 7 — not in Clerk.

**If webhook is active:** Check backend logs for:
```
Clerk webhook received: organizationMembership.created
Created user: jane@acme.com (reviewer) in org ...
```

---

## 7. Seed Users into the Database

### When to use this step

- If ngrok was **not running** when the org/users were created in Clerk (webhook didn't fire)
- If a user needs the `viewer` role (Clerk webhooks always create users as `reviewer`)
- If you need to verify what's already in the database

### 7a. Check what already exists

Run from `backend/` directory:

```bash
cd "c:/Agentic Workflow/Document Processing System/backend"
python -c "
import asyncio, sys; sys.path.insert(0, '.')
from database import AsyncSessionLocal
from models.db_models import Organization, User
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as s:
        orgs = (await s.scalars(select(Organization))).all()
        users = (await s.scalars(select(User))).all()
        print('=== ORGANISATIONS ===')
        for o in orgs:
            print(f'  {o.name}  |  id={o.id}  |  clerk_org_id={o.clerk_org_id}')
        print('=== USERS ===')
        for u in users:
            print(f'  {u.email}  |  role={u.role}  |  org={u.org_id}  |  clerk_id={u.clerk_user_id}')

asyncio.run(check())
"
```

### 7b. Create the organisation (only if not auto-created by webhook)

```bash
python -c "
import asyncio, sys; sys.path.insert(0, '.')
from database import AsyncSessionLocal
from models.db_models import Organization
from services import hubspot_service

async def create_org():
    async with AsyncSessionLocal() as s:
        org = Organization(
            name='Acme Accounting Ltd',        # ← firm name from Step 5
            clerk_org_id='org_XXXXXXXXXXXX',   # ← Clerk org ID from Step 5
            plan='free',
        )
        s.add(org)
        await s.flush()
        await hubspot_service.seed_default_mapping(s, org.id)
        await s.commit()
        print(f'Created org: {org.id}')

asyncio.run(create_org())
"
```

### 7c. Create each user

Run once per user. Change `clerk_user_id`, `email`, and `role` each time.

```bash
python -c "
import asyncio, sys; sys.path.insert(0, '.')
from database import AsyncSessionLocal
from models.db_models import User, Organization
from sqlalchemy import select

async def create_user():
    async with AsyncSessionLocal() as s:
        org = await s.scalar(
            select(Organization).where(Organization.clerk_org_id == 'org_XXXXXXXXXXXX')
        )
        if not org:
            print('ERROR: Organisation not found — run Step 7b first')
            return

        existing = await s.scalar(select(User).where(User.email == 'jane@acme.com'))
        if existing:
            print(f'User already exists: {existing.email} | role={existing.role}')
            return

        user = User(
            org_id=org.id,
            clerk_user_id='user_XXXXXXXXXXXX',  # ← Clerk User ID from Step 6a
            email='jane@acme.com',              # ← their email
            role='viewer',                      # ← viewer | reviewer | admin
        )
        s.add(user)
        await s.commit()
        print(f'Created: {user.email} | role={user.role} | id={user.id}')

asyncio.run(create_user())
"
```

**Role guide:**
| Person | Role to set |
|---|---|
| Client document uploaders | `viewer` |
| Back office / reviewers | `reviewer` |
| System administrators | `admin` |

### 7d. Fix org setup (if user gets FK errors on first upload)

If a user was created without a matching organisation, call this endpoint while logged in as that user:

```
POST http://localhost:8080/auth/setup-org
Authorization: Bearer <their Clerk JWT token>
```

This creates a personal organisation and links it to the user automatically.

---

## 8. Configure HubSpot CRM

Skip this step if the client does not use HubSpot.

### 8a. Client creates a HubSpot Private App

Ask the client to:

1. Log into their HubSpot account
2. Go to **Settings → Integrations → Private Apps**
3. Click **Create a Private App**
4. Set a name (e.g. `DocFlow AI Integration`)
5. Under **Scopes**, enable:
   - `crm.objects.contacts.write`
   - `crm.objects.contacts.read`
6. Click **Create App** → **Continue Creating**
7. Copy the **Access Token** (starts with `pat-...`) and send it to you securely

### 8b. Enter the token in DocFlow AI

1. Log into DocFlow AI as an `admin` user for that firm
2. Go to **Settings → HubSpot Integration**
3. Paste the Private App token
4. Click **Save**

### 8c. Verify field mappings

1. Go to **Settings → Field Mappings**
2. Confirm the mappings for each document type match the client's HubSpot property names
3. Update any that differ from the defaults

> **HubSpot free tier limit:** Maximum 10 custom properties. All 10 are used by the default mapping.
> If the client needs more, they must upgrade their HubSpot plan.

---

## 9. Verify Email Notifications (AWS SES)

DocFlow AI sends emails to uploaders when:
- Their document is **approved** (auto or manual)
- A **re-upload** is requested by back office

### While in SES sandbox mode (development)

Every recipient email must be individually verified in AWS SES:

1. Go to **AWS Console → SES → Verified Identities**
2. Click **Create Identity → Email address**
3. Enter the client's email address
4. Client receives a verification email — they **must click the link**
5. Status shows **Verified** ✓

Repeat for every email address that will receive notifications from DocFlow AI.

### For production

Request SES production access to send to any email without pre-verification:

1. AWS Console → **SES → Account dashboard**
2. Click **Request production access**
3. Fill in the use case form (transactional notifications, low volume)
4. Approval typically takes 1–2 business days

> Until production access is approved, clients must verify their email in SES or they will
> not receive any notifications.

---

## 10. End-to-End Test

Before handing over to the client, run this full test yourself:

### Test A — Auto-approval flow (document passes validation)

1. Log in as the **viewer** user
2. Go to **Upload** → upload this test document as **Tax Return**:

```
FORM 1040 - U.S. Individual Income Tax Return
Tax Year: 2024
Taxpayer Name: John Michael Smith
SSN: XXX-XX-4521
Filing Status: Single
Address: 142 Maple Street, Austin, TX 78701
Total Income: $82,500
Total Tax: $14,200
Refund Amount: $1,850
Amount Owed: $0
```

3. Confirm:
   - [ ] Status shows "Upload successful — you will be notified by email"
   - [ ] Approval email arrives at the viewer's inbox
   - [ ] HubSpot contact created (if configured)
   - [ ] Document appears on Dashboard with "In HubSpot" status

### Test B — Review queue flow (document fails validation)

1. Log in as the **viewer** user
2. Upload this test document as **Tax Return**:

```
FORM 1040
Tax Year: 2024
Filing Status: Married
Total Income: $82,500
Refund Amount: $1,200
Amount Owed: $400
```
*(Missing taxpayer name and SSN — will fail validation)*

3. Log in as the **reviewer/admin** user
4. Go to **Review Queue** — the document should appear
5. Click the document → review the flags
6. Click **Request Re-upload** → add a note → Send
7. Confirm:
   - [ ] Re-upload email arrives at the viewer's inbox
   - [ ] Document disappears from the review queue

### Test C — Manual approval

1. Upload another failing document (same as Test B)
2. In the Review Queue, correct the missing fields manually
3. Click **Approve & Push to CRM**
4. Confirm:
   - [ ] Approval email arrives at the viewer's inbox
   - [ ] HubSpot contact created/updated (if configured)
   - [ ] Audit Trail shows the approval event

---

## 11. Share Access with the Client

### 11a. Send login details

```
Subject: Your DocFlow AI Access Is Ready

Hi [Name],

Your DocFlow AI account has been set up. Here are your login details:

  Login URL:  http://localhost:3000   (replace with your production URL)
  Email:      [their email]
  Password:   [temporary password]

Please change your password after your first login.

WHAT YOU CAN DO
---------------
• Upload documents from the Upload page (PDF, JPG, PNG, TIFF — max 50 MB)
• Supported document types: Tax Return, Bank Statement, Government ID, General Document
• You will receive an email confirmation once your document has been processed
• If we need anything from you, you will receive an email with instructions

WHAT TO EXPECT
--------------
• Most documents are processed within 1–2 minutes
• If your document has issues, you will receive an email asking you to re-upload
• You do not need to check the system — all updates come via email

If you have any questions, reply to this email or contact [your contact details].

Best regards,
[Your name]
```

### 11b. Share the User Manual

Send the client a copy of `USER_MANUAL.md` (or a PDF export of it). It covers:
- How to upload a document
- What each status means
- What to do when a re-upload is requested
- How to reach support

---

## 12. Ongoing Maintenance

### Adding more users to an existing firm

Repeat Steps 6 and 7 for each new user. The firm's organisation already exists — skip Step 5 and 7b.

### Changing a user's role

```bash
cd "c:/Agentic Workflow/Document Processing System/backend"
python -c "
import asyncio, sys; sys.path.insert(0, '.')
from database import AsyncSessionLocal
from models.db_models import User
from sqlalchemy import select

async def update_role():
    async with AsyncSessionLocal() as s:
        user = await s.scalar(select(User).where(User.email == 'jane@acme.com'))
        if user:
            user.role = 'reviewer'   # ← viewer | reviewer | admin
            await s.commit()
            print(f'Updated {user.email} → {user.role}')
        else:
            print('User not found')

asyncio.run(update_role())
"
```

### Removing a user

Remove them from the organisation in Clerk Dashboard → Organizations → Members → Remove.
Their database record is kept for audit trail integrity but they can no longer log in.

### Rotating the HubSpot API key

1. Client creates a new Private App token in HubSpot
2. Admin logs in to DocFlow AI → Settings → HubSpot Integration → paste new token → Save

### Re-dispatching stuck jobs

If documents are stuck in `queued` status after a Redis/Celery restart:

```bash
cd "c:/Agentic Workflow/Document Processing System/backend"
python redispatch.py
```

---

## 13. Troubleshooting

| Problem | Most Likely Cause | Fix |
|---|---|---|
| User logs in but gets 401 / blank screen | User not in DocFlow DB | Run Step 7c seed script |
| User can't see Review Queue | Role is `viewer`, needs `reviewer` | Update role (Step 12) |
| Document stuck at "Queued" forever | Celery worker or Redis not running | Start Terminal 1 + 3 from Step 3 |
| "Processing queue unavailable" on upload | Redis down or Celery crashed | Restart Redis + Celery |
| No approval email received | Recipient email not verified in SES | Complete Step 9 |
| Approval email goes to spam | Sender is personal Gmail without SPF/DKIM | Ask client to mark as "Not spam"; fix properly in production |
| Nothing pushed to HubSpot | No API key configured, or key expired | Check Settings → HubSpot Integration |
| HubSpot push fails (crm_error status) | Invalid token or scope missing | Re-create the Private App in HubSpot |
| Webhook not firing | ngrok not running or URL changed | Restart ngrok, update webhook URL in Clerk (Step 4) |
| "Organization not found" on user creation | Org not in DB yet | Run Step 7b first |
| Celery won't start | Wrong terminal / wrong directory | Must `cd backend` first, use `python -m celery` not `celery` |

---

## Production Readiness Checklist

Complete these before going live with real clients:

| Item | Action Required |
|---|---|
| AWS SES sandbox restriction | Request production access in AWS Console → SES → Account dashboard |
| Domain email sender | Verify a domain (e.g. `yourfirm.com`) in SES instead of personal Gmail |
| SPF / DKIM DNS records | Add DNS records from SES to prevent spam classification |
| HTTPS + custom domain | Deploy frontend + backend with SSL certificate |
| Clerk production instance | Create a separate Clerk production app (keep dev separate) |
| Stable webhook URL | Replace ngrok with your production domain for Clerk webhook |
| HubSpot custom properties | Upgrade HubSpot plan if more than 10 custom properties needed |
| Database backups | Enable automated backups on Supabase (or your PostgreSQL provider) |
| Environment secrets | Move all `.env` secrets to a secrets manager (AWS Secrets Manager, etc.) |
