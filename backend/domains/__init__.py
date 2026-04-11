"""
Domain Registry — DocFlow AI

Central registry of all supported doc types across all domains.

To add a new domain (e.g. healthcare):
  1. Create backend/domains/healthcare/<doc_type>.py with DomainConfig instances
  2. Add them to backend/domains/healthcare/__init__.py as a list
  3. Import the list here and merge it into DOMAIN_REGISTRY (two lines)

Core services (validation, extraction, HubSpot) never need to change —
they call get_domain(doc_type) and read properties from the config.
"""
from .accounting import ACCOUNTING_DOMAINS
from .base import DomainConfig
from .healthcare import HEALTHCARE_DOMAINS

# ── Register all active domains ──────────────────────────────────────────────
# To add a new domain uncomment/add the import and extend the list below:
#
#   from .legal import LEGAL_DOMAINS

_ALL_DOMAINS: list[DomainConfig] = [
    *ACCOUNTING_DOMAINS,
    *HEALTHCARE_DOMAINS,
    # *LEGAL_DOMAINS,
]

DOMAIN_REGISTRY: dict[str, DomainConfig] = {
    d.doc_type: d for d in _ALL_DOMAINS
}


def get_domain(doc_type: str) -> DomainConfig:
    """
    Retrieve the DomainConfig for a doc_type.
    Raises ValueError if the doc_type is not registered.
    """
    domain = DOMAIN_REGISTRY.get(doc_type)
    if not domain:
        raise ValueError(
            f"Unknown doc_type: {doc_type!r}. "
            f"Registered types: {sorted(DOMAIN_REGISTRY)}"
        )
    return domain


def allowed_types() -> set[str]:
    """Return the set of all registered doc_type strings."""
    return set(DOMAIN_REGISTRY)
