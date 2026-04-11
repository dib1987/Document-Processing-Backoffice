from domains.base import DomainConfig
from models.schemas import ClinicalSupportExtraction

# NOTE: "date_of_service should not be before document_date unless retrospective review
# is explicitly allowed" — the retrospective caveat makes this ambiguous to enforce
# automatically. Skipped as a cross_field_rule; reviewer will catch it if needed.

CLINICAL_SUPPORT_DOMAIN = DomainConfig(
    doc_type="clinical_support",
    label="Clinical Support Packet",
    schema_class=ClinicalSupportExtraction,
    required_fields=[
        "patient_full_name",
        "document_date",
        "provider_name",
        "diagnosis_summary",
    ],
    format_rules={
        "document_date":   r"^\d{4}-\d{2}-\d{2}$",
        "date_of_birth":   r"^\d{4}-\d{2}-\d{2}$",
        "provider_npi":    r"^\d{10}$",
        "date_of_service": r"^\d{4}-\d{2}-\d{2}$",
    },
    range_rules={},
    cross_field_rules=[],
    value_rules={
        "provider_signature_present": "true",
        "medical_necessity_present":  "true",
    },
    default_hubspot_mapping={
        # Only standard HubSpot properties mapped by default.
        # Add custom HubSpot properties (provider_name, diagnosis_summary, etc.) via
        # Settings → Field Mapping after creating them in HubSpot.
        "patient_full_name": "__split_name__",
        "date_of_birth":     "date_of_birth",
    },
)
