"""
Settings Router — HubSpot configuration and field mapping per org.

GET  /settings/hubspot          — get HubSpot connection status (key masked)
PUT  /settings/hubspot          — update HubSpot API key
GET  /settings/field-mapping    — get field mapping for a doc type
PUT  /settings/field-mapping    — update field mapping for a doc type

All endpoints require admin role.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from middleware.auth_middleware import require_role
from models.db_models import HubSpotFieldMapping, Organization, User
from services import hubspot_service

router = APIRouter()


# ──────────────────────────────────────────────
# Request / Response models
# ──────────────────────────────────────────────

class HubSpotKeyRequest(BaseModel):
    api_key: str


class FieldMappingRequest(BaseModel):
    doc_type: str   # tax_return | government_id | bank_statement | general
    mapping: dict   # {"extracted_field": "hubspot_property"}


# ──────────────────────────────────────────────
# HubSpot key endpoints
# ──────────────────────────────────────────────

@router.get("/hubspot")
async def get_hubspot_settings(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Returns HubSpot connection status.
    The API key is masked — only the last 4 chars are shown.
    """
    org = await session.get(Organization, request.state.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    has_key = bool(org.hubspot_api_key)
    masked_key = None
    if has_key and org.hubspot_api_key:
        masked_key = "•••••••••••••••••••••" + org.hubspot_api_key[-4:]

    return {
        "connected": has_key,
        "masked_key": masked_key,
        "hubspot_portal_url": "https://app.hubspot.com" if has_key else None,
    }


@router.put("/hubspot")
async def update_hubspot_key(
    body: HubSpotKeyRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Save or update the HubSpot private app API key for this org.
    The key is stored as-is — enforce HTTPS + encrypted DB at rest in production.
    """
    if not body.api_key or len(body.api_key.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="API key appears invalid — HubSpot private app tokens are typically 50+ characters",
        )

    org = await session.get(Organization, request.state.org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    org.hubspot_api_key = body.api_key.strip()
    await session.commit()

    return {"status": "saved", "masked_key": "•••••••••••••••••••••" + body.api_key.strip()[-4:]}


# ──────────────────────────────────────────────
# Field mapping endpoints
# ──────────────────────────────────────────────

VALID_DOC_TYPES = {"tax_return", "government_id", "bank_statement", "general"}


@router.get("/field-mapping")
async def get_field_mapping(
    request: Request,
    doc_type: str = "tax_return",
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Returns the current field mapping for a specific doc type.
    If no custom mapping exists, returns the seeded default.

    Each entry maps an extracted field name to a HubSpot property name.
    Example: {"taxpayer_name": "firstname + lastname", "total_income": "annual_income__c"}

    Special directives:
      "firstname + lastname"  — splits a full name into HubSpot firstname/lastname
    """
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"doc_type must be one of: {', '.join(sorted(VALID_DOC_TYPES))}",
        )

    org_id = request.state.org_id

    # Try to load the mapping for this specific doc_type
    mapping_row = await session.scalar(
        select(HubSpotFieldMapping).where(
            HubSpotFieldMapping.org_id == org_id,
            HubSpotFieldMapping.doc_type == doc_type,
        )
    )

    if mapping_row:
        return {
            "doc_type": doc_type,
            "mapping": mapping_row.mapping,
            "updated_at": mapping_row.updated_at.isoformat() if mapping_row.updated_at else None,
        }

    # Fall back to the built-in default (in case seeding was missed)
    default = hubspot_service.DEFAULT_MAPPINGS.get(doc_type, {})
    return {
        "doc_type": doc_type,
        "mapping": default,
        "updated_at": None,
        "note": "Using built-in default mapping — save to customise for your HubSpot account",
    }


@router.get("/field-mapping/all")
async def get_all_field_mappings(
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """Returns all 4 doc-type mappings in a single call (used by the Settings page)."""
    org_id = request.state.org_id

    rows = (await session.scalars(
        select(HubSpotFieldMapping).where(HubSpotFieldMapping.org_id == org_id)
    )).all()

    saved = {r.doc_type: {"mapping": r.mapping, "updated_at": r.updated_at.isoformat() if r.updated_at else None} for r in rows}

    result = {}
    for dt in VALID_DOC_TYPES:
        if dt in saved:
            result[dt] = saved[dt]
        else:
            result[dt] = {
                "mapping": hubspot_service.DEFAULT_MAPPINGS.get(dt, {}),
                "updated_at": None,
            }

    return result


@router.put("/field-mapping")
async def update_field_mapping(
    body: FieldMappingRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Save a custom field mapping for a doc type.
    Creates the row if it doesn't exist, updates it if it does.

    Mapping format:
      Key   = extracted field name (must match schema field names)
      Value = HubSpot property name OR special directive

    Special directives:
      "firstname + lastname"  — splits full_name / taxpayer_name into two HubSpot fields
    """
    if body.doc_type not in VALID_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"doc_type must be one of: {', '.join(sorted(VALID_DOC_TYPES))}",
        )

    if not body.mapping:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mapping cannot be empty",
        )

    org_id = request.state.org_id

    existing = await session.scalar(
        select(HubSpotFieldMapping).where(
            HubSpotFieldMapping.org_id == org_id,
            HubSpotFieldMapping.doc_type == body.doc_type,
        )
    )

    if existing:
        existing.mapping = body.mapping
        existing.updated_at = datetime.now(timezone.utc)
    else:
        new_row = HubSpotFieldMapping(
            org_id=org_id,
            doc_type=body.doc_type,
            mapping=body.mapping,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(new_row)

    await session.commit()
    return {"status": "saved", "doc_type": body.doc_type, "field_count": len(body.mapping)}


@router.post("/field-mapping/reset")
async def reset_field_mapping(
    request: Request,
    doc_type: str = "tax_return",
    session: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    """
    Resets a doc type's field mapping back to the built-in default.
    Useful if a custom mapping is broken or if HubSpot was reconfigured.
    """
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"doc_type must be one of: {', '.join(sorted(VALID_DOC_TYPES))}",
        )

    org_id = request.state.org_id
    default_mapping = hubspot_service.DEFAULT_MAPPINGS.get(doc_type, {})

    existing = await session.scalar(
        select(HubSpotFieldMapping).where(
            HubSpotFieldMapping.org_id == org_id,
            HubSpotFieldMapping.doc_type == doc_type,
        )
    )

    if existing:
        existing.mapping = default_mapping
        existing.updated_at = datetime.now(timezone.utc)
    else:
        session.add(HubSpotFieldMapping(
            org_id=org_id,
            doc_type=doc_type,
            mapping=default_mapping,
            updated_at=datetime.now(timezone.utc),
        ))

    await session.commit()
    return {"status": "reset", "doc_type": doc_type, "mapping": default_mapping}
