"""
Auth Router — Clerk Webhook Handler

Clerk calls POST /auth/webhook when:
  - An organization is created → we create the org in our DB + seed HubSpot field mappings
  - A user joins an org → we create the user in our DB with default role

The webhook payload is verified using the Clerk webhook secret (via svix).
"""
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError

from config import get_settings
from database import get_db
from models.db_models import Organization, User
from services import hubspot_service

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/webhook", status_code=status.HTTP_204_NO_CONTENT)
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(None, alias="svix-id"),
    svix_timestamp: str = Header(None, alias="svix-timestamp"),
    svix_signature: str = Header(None, alias="svix-signature"),
    session: AsyncSession = Depends(get_db),
):
    """
    Handles Clerk webhook events to sync users and organizations into our DB.
    """
    body = await request.body()

    # Verify signature
    if not settings.clerk_webhook_secret:
        logger.warning("CLERK_WEBHOOK_SECRET not set — skipping signature verification in dev")
    else:
        try:
            wh = Webhook(settings.clerk_webhook_secret)
            wh.verify(
                body,
                {
                    "svix-id": svix_id or "",
                    "svix-timestamp": svix_timestamp or "",
                    "svix-signature": svix_signature or "",
                },
            )
        except WebhookVerificationError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")

    payload = await request.json()
    event_type = payload.get("type")
    data = payload.get("data", {})

    logger.info("Clerk webhook received: %s", event_type)

    if event_type == "organization.created":
        await _handle_org_created(session, data)

    elif event_type == "organizationMembership.created":
        await _handle_membership_created(session, data)

    elif event_type == "user.created":
        # user.created fires before org membership — handled in membership event
        pass

    await session.commit()


async def _handle_org_created(session: AsyncSession, data: dict) -> None:
    clerk_org_id = data.get("id")
    org_name = data.get("name", "Unnamed Firm")

    existing = await session.scalar(
        select(Organization).where(Organization.clerk_org_id == clerk_org_id)
    )
    if existing:
        return  # Idempotent

    org = Organization(
        name=org_name,
        clerk_org_id=clerk_org_id,
        plan="free",
    )
    session.add(org)
    await session.flush()

    # Seed default HubSpot field mappings
    await hubspot_service.seed_default_mapping(session, org.id)
    logger.info("Created org: %s (%s)", org_name, org.id)


async def _handle_membership_created(session: AsyncSession, data: dict) -> None:
    clerk_org_id = data.get("organization", {}).get("id")
    clerk_user_id = data.get("public_user_data", {}).get("user_id")
    user_email = data.get("public_user_data", {}).get("identifier", "")
    role_str = data.get("role", "org:member")

    # Map Clerk roles to our roles
    role = "admin" if "admin" in role_str else "reviewer"

    org = await session.scalar(
        select(Organization).where(Organization.clerk_org_id == clerk_org_id)
    )
    if not org:
        logger.warning("Membership created for unknown org: %s", clerk_org_id)
        return

    existing_user = await session.scalar(
        select(User).where(User.clerk_user_id == clerk_user_id)
    )
    if existing_user:
        return  # Idempotent

    user = User(
        org_id=org.id,
        clerk_user_id=clerk_user_id,
        email=user_email,
        role=role,
    )
    session.add(user)
    logger.info("Created user: %s (%s) in org %s", user_email, role, org.id)
