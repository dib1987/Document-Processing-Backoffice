"""
HubSpot CRM Service — DocFlow AI

Creates or updates a HubSpot contact using the firm's API key and
their configured field mapping (stored in hubspot_field_mapping table).

HubSpot free tier:
  POST /crm/v3/objects/contacts   — create contact
  PATCH /crm/v3/objects/contacts/{id} — update contact

Field mapping is per-org, per-doc-type (configurable in Settings UI).
Default mappings are seeded on org creation.
"""
import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.db_models import HubSpotFieldMapping, Job, Organization

logger = logging.getLogger(__name__)

HUBSPOT_API_BASE = "https://api.hubapi.com"

# ──────────────────────────────────────────────
# Default field mappings (seeded on org creation)
# ──────────────────────────────────────────────

DEFAULT_MAPPINGS: dict[str, dict[str, str]] = {
    "tax_return": {
        "taxpayer_name":    "__split_name__",   # special: split into firstname/lastname
        "address_street":   "address",
        "address_city":     "city",
        "address_state":    "state",
        "address_zip":      "zip",
        "total_income":     "annual_revenue",
        "tax_year":         "tax_year__c",
        "ssn_primary":      "ssn_last4__c",
        "filing_status":    "filing_status__c",
        "form_type":        "tax_form_type__c",
    },
    "government_id": {
        "full_name":        "__split_name__",
        "date_of_birth":    "date_of_birth__c",
        "id_type":          "id_type__c",
        "id_number":        "id_number_last4__c",
        "expiration_date":  "id_expiration__c",
        "address_street":   "address",
        "address_city":     "city",
        "address_state":    "state",
        "address_zip":      "zip",
    },
    "bank_statement": {
        "account_holder_name": "__split_name__",
        "bank_name":           "bank_name__c",
        "account_type":        "account_type__c",
        "account_number":      "account_last4__c",
        "ending_balance":      "bank_balance__c",
    },
    "general": {
        "primary_person_name": "__split_name__",
        "issuing_entity":      "company",
        "document_category":   "document_type__c",
        "dollar_amount":       "document_amount__c",
    },
}


# ──────────────────────────────────────────────
# Main entry points
# ──────────────────────────────────────────────

async def create_contact(
    session: AsyncSession,
    job: Job,
    extracted_fields: dict[str, Any],
    reviewed_fields: dict[str, Any] | None = None,
    hubspot_api_key: str | None = None,
) -> str:
    """
    Map extracted (or reviewer-corrected) fields to HubSpot properties
    and create a contact. Returns the HubSpot contact ID.

    Pass hubspot_api_key explicitly to bypass SQLAlchemy identity map caching.
    If not provided, fetches fresh from DB via direct query.
    """
    # Use reviewed_fields if provided (post-approval); fall back to extracted
    fields = {**extracted_fields, **(reviewed_fields or {})}

    # Fetch API key fresh from DB if not passed in (avoids identity map stale reads)
    if hubspot_api_key is None:
        hubspot_api_key = await session.scalar(
            select(Organization.hubspot_api_key).where(Organization.id == job.org_id)
        )
    if not hubspot_api_key:
        raise ValueError(f"org={job.org_id} has no HubSpot API key configured")

    mapping = await _get_field_mapping(session, job.org_id, job.doc_type)
    hs_properties = _apply_mapping(fields, mapping)

    if not hs_properties:
        raise ValueError(f"job={job.id} No HubSpot properties after mapping — check field mapping config")

    logger.info("job=%s creating HubSpot contact with %d properties", job.id, len(hs_properties))

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts",
            headers={
                "Authorization": f"Bearer {org.hubspot_api_key}",
                "Content-Type": "application/json",
            },
            json={"properties": hs_properties},
        )

    if resp.status_code == 409:
        # Contact already exists — update instead
        existing_id = _extract_existing_id(resp.json())
        if existing_id:
            logger.info("job=%s contact exists (%s) — updating", job.id, existing_id)
            return await _update_contact(org.hubspot_api_key, existing_id, hs_properties, job.id)

    if resp.status_code not in (200, 201):
        error_body = resp.text[:500]
        logger.error("job=%s HubSpot API error %d: %s", job.id, resp.status_code, error_body)
        raise RuntimeError(f"HubSpot API returned {resp.status_code}: {error_body}")

    contact_id = resp.json().get("id", "")
    logger.info("job=%s HubSpot contact created: %s", job.id, contact_id)
    return contact_id


async def seed_default_mapping(session: AsyncSession, org_id: str) -> None:
    """
    Seed default field mappings for a new org.
    Called from the Clerk webhook handler when a new org is created.
    """
    for doc_type, mapping in DEFAULT_MAPPINGS.items():
        existing = await session.scalar(
            select(HubSpotFieldMapping).where(
                HubSpotFieldMapping.org_id == org_id,
                HubSpotFieldMapping.doc_type == doc_type,
            )
        )
        if not existing:
            session.add(HubSpotFieldMapping(
                org_id=org_id,
                doc_type=doc_type,
                mapping=mapping,
            ))
    await session.flush()


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

async def _get_field_mapping(session: AsyncSession, org_id: str, doc_type: str) -> dict[str, str]:
    """Fetch the org's field mapping, falling back to defaults."""
    row = await session.scalar(
        select(HubSpotFieldMapping).where(
            HubSpotFieldMapping.org_id == org_id,
            HubSpotFieldMapping.doc_type == doc_type,
        )
    )
    if row and row.mapping:
        return row.mapping
    return DEFAULT_MAPPINGS.get(doc_type, {})


def _apply_mapping(
    fields: dict[str, Any],
    mapping: dict[str, str],
) -> dict[str, str]:
    """
    Map extracted field names to HubSpot property names.
    Handles the special __split_name__ directive.
    """
    hs_props: dict[str, str] = {}

    for extracted_key, hs_key in mapping.items():
        value = fields.get(extracted_key)
        if value is None or str(value).strip() == "":
            continue

        if hs_key == "__split_name__":
            # Split "John Smith" → firstname="John", lastname="Smith"
            parts = str(value).strip().split(None, 1)
            hs_props["firstname"] = parts[0]
            if len(parts) > 1:
                hs_props["lastname"] = parts[1]
        else:
            hs_props[hs_key] = str(value).strip()

    return hs_props


async def _update_contact(api_key: str, contact_id: str, properties: dict, job_id: str) -> str:
    """PATCH an existing HubSpot contact."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.patch(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{contact_id}",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"properties": properties},
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"HubSpot update {resp.status_code}: {resp.text[:300]}")
    return contact_id


def _extract_existing_id(error_body: dict) -> str | None:
    """Extract the existing contact ID from a HubSpot 409 conflict response."""
    try:
        # HubSpot returns: {"message": "Contact already exists. ...", "error": "CONTACT_EXISTS"}
        # The existing ID is typically in the error context
        context = error_body.get("context", {})
        ids = context.get("ids", [])
        return ids[0] if ids else None
    except Exception:
        return None
