from domains.base import CrossFieldRule, DomainConfig
from models.schemas import GovernmentIDExtraction

GOVT_ID_DOMAIN = DomainConfig(
    doc_type="government_id",
    label="Government-Issued Photo ID (Driver License / Passport / State ID)",
    schema_class=GovernmentIDExtraction,
    required_fields=["full_name", "date_of_birth", "id_number", "expiration_date"],
    format_rules={
        "date_of_birth":   r"^\d{4}-\d{2}-\d{2}$",
        "issue_date":      r"^\d{4}-\d{2}-\d{2}$",
        "expiration_date": r"^\d{4}-\d{2}-\d{2}$",
        "address_zip":     r"^\d{5}(-\d{4})?$",
    },
    range_rules={},
    cross_field_rules=[
        CrossFieldRule(
            field_a="expiration_date",
            field_b="issue_date",
            message="The expiration date must be after the issue date.",
            rule_type="date_order",
        ),
    ],
    default_hubspot_mapping={
        "full_name":       "__split_name__",
        "date_of_birth":   "date_of_birth",
        "id_type":         "id_type",
        "id_number":       "id_number_last4",
        "expiration_date": "id_expiration",
        "address_street":  "address",
        "address_city":    "city",
        "address_state":   "state",
        "address_zip":     "zip",
    },
)
