from domains.base import DomainConfig
from models.schemas import GeneralDocumentExtraction

GENERAL_DOMAIN = DomainConfig(
    doc_type="general",
    label="General Financial Document",
    schema_class=GeneralDocumentExtraction,
    required_fields=["primary_person_name", "document_date"],
    format_rules={
        "document_date": r"^\d{4}-\d{2}-\d{2}$",
    },
    range_rules={},
    cross_field_rules=[],
    default_hubspot_mapping={
        "primary_person_name": "__split_name__",
        "issuing_entity":      "company",
        "document_category":   "jobtitle",
        "dollar_amount":       "annualrevenue",
    },
)
