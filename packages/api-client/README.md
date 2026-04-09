# @docflow/api-client

Shared API client and React Query hooks — used by all domain frontend apps.

## Status

Not yet extracted. Currently lives in `apps/accounting/src/lib/api.ts` and
`apps/accounting/src/lib/hooks/`.

## When to extract here

When you have 2+ domain apps and you're copying `api.ts` between them. Extract then.

## What belongs here (future)

- `api.ts` — Axios client + all API functions (upload, jobs, review, settings, export)
- `hooks/useJobs.ts` — React Query job list + polling
- `hooks/useReviewQueue.ts` — review queue with optimistic updates
- `hooks/useDashboard.ts` — dashboard stats
- `hooks/useCurrentUser.ts` — Clerk user + role
- TypeScript types for all API responses

## What stays per-app

- Any domain-specific API calls (e.g. healthcare app calling a patient-specific endpoint)
- App-level React Query config (QueryClient setup, stale times)
