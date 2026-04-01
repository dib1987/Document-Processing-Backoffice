---
name: DocFlow AI Setup Progress
description: Current setup state and pending tasks for DocFlow AI project
type: project
---

Setup progress as of 2026-03-31:

**Completed:**
- Backend Python dependencies installed (pip install -r requirements.txt)
- Frontend Node dependencies installed (npm install via PowerShell)
- .env file created from .env.example
- PostgreSQL: Supabase project "Document Processing" (project ID: itrsetorevhlvkikqymz), DATABASE_URL set with asyncpg driver
- Redis: Upstash instance at charming-lacewing-89786.upstash.io:6379 (TLS/rediss://), all 3 Celery vars updated
- Anthropic API Key: configured in .env
- Clerk: CLERK_SECRET_KEY and CLERK_PUBLISHABLE_KEY configured; CLERK_WEBHOOK_SECRET still REPLACE_ME

**Pending (resuming tomorrow):**
- AWS S3: user has AWS account, needs to create bucket + IAM user with AmazonS3FullAccess, get access key + secret
- Clerk webhook secret: needs to be set up
- Run database migrations (Alembic)
- Start FastAPI backend + Celery worker
- Start Next.js frontend

**Why:** Removed @radix-ui/react-badge from package.json (package doesn't exist in Radix UI).
