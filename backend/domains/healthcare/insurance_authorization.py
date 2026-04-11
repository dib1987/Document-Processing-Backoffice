from domains.base import CrossFieldRule, DomainConfig
from models.schemas import InsuranceAuthorizationExtraction

# NOTE: The rule "prior_authorization_number must not be blank when authorization_status
# = approved" is a conditional required rule the current engine cannot enforce.
# It is left to the human reviewer — any document with authorization_status = approved
# and a missing prior_authorization_number will surface in the review queue if any
# other flag triggers, but is otherwise a manual check.

INSURANCE_AUTHORIZATION_DOMAIN = DomainConfig(
    doc_type="insurance_authorization",
    label="Insurance / Referral / Prior Authorization Packet",
    schema_class=InsuranceAuthorizationExtraction,
    required_fields=[
        "patient_full_name",
        "payer_name",
        "member_id",
        "servicing_provider_name",
        "requested_service",
    ],
    format_rules={
        "npi_number":               r"^\d{10}$",
        "member_id":                r"^[A-Za-z0-9][A-Za-z0-9\-]{3,24}$",
        "authorization_start_date": r"^\d{4}-\d{2}-\d{2}$",
        "authorization_end_date":   r"^\d{4}-\d{2}-\d{2}$",
        "date_of_birth":            r"^\d{4}-\d{2}-\d{2}$",
    },
    range_rules={},
    cross_field_rules=[
        CrossFieldRule(
            field_a="authorization_end_date",
            field_b="authorization_start_date",
            message="Authorization end date must be after the authorization start date.",
            rule_type="date_order",
        ),
    ],
    value_rules={},
    default_hubspot_mapping={
        # Only standard HubSpot properties mapped by default.
        # Add custom HubSpot properties (payer_name, member_id, etc.) via
        # Settings → Field Mapping after creating them in HubSpot.
        "patient_full_name": "__split_name__",
        "date_of_birth":     "date_of_birth",
    },
)
