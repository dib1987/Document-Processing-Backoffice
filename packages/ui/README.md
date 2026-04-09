# @docflow/ui

Shared UI component library — used by all domain frontend apps.

## Status

Not yet extracted. Components currently live in `apps/accounting/src/components/ui/`.

## When to extract here

When you have 2+ domain apps (`apps/accounting/`, `apps/healthcare/`, etc.) that both need
the same component and you feel the duplication. Extract then, not before.

## Components that belong here (future)

- `Button`, `Badge`, `Modal`, `Table`, `Card` — generic Radix UI + Tailwind wrappers
- `StatusBadge` — job status display (used by all domains)
- `FileDropzone` — upload component (same UX across domains)
- `ConfidenceIndicator` — field confidence display (shared review UI pattern)

## Components that stay per-app

- Page layouts (each domain has its own navigation structure)
- Domain-specific forms (tax return upload != patient intake form)
- Branding (logo, colors, typography — all per-client)
