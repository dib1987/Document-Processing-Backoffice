"""
Domain base types — DocFlow AI

DomainConfig is the interface every domain must implement.
Each domain file creates one DomainConfig instance describing its doc types,
validation rules, and CRM field mappings.

To add a new domain:
  1. Create backend/domains/<industry>/<doc_type>.py with a DomainConfig instance
  2. Import it in backend/domains/<industry>/__init__.py
  3. Import that list in backend/domains/__init__.py and merge into DOMAIN_REGISTRY
"""
from dataclasses import dataclass, field
from typing import NamedTuple


class CrossFieldRule(NamedTuple):
    """
    Defines a validation constraint between two fields.

    rule_type options:
      "mutually_exclusive" — both fields cannot simultaneously have a positive dollar value
      "date_order"         — field_a must be chronologically after field_b
    """
    field_a: str
    field_b: str
    message: str        # Plain English message shown to human reviewers
    rule_type: str      # "mutually_exclusive" | "date_order"


@dataclass
class DomainConfig:
    """
    Complete configuration for one document type within a domain.

    Fields:
        doc_type               Unique string key (e.g. "tax_return", "patient_intake")
        label                  Human-readable name shown in the UI and Claude prompt
        schema_class           Pydantic BaseModel subclass — defines extractable fields
        required_fields        Fields that must be non-null for the job to auto-pass
        format_rules           dict[field_name, regex_pattern_string] — format validation
        range_rules            dict[field_name, (min, max)] — numeric bounds (dollar amounts)
        cross_field_rules      Constraints spanning two fields (optional)
        default_hubspot_mapping  dict[extracted_field, hubspot_property] for CRM push
                               Use "__split_name__" to split a full name into firstname/lastname
    """
    doc_type: str
    label: str
    schema_class: type                              # Pydantic BaseModel subclass
    required_fields: list[str]
    format_rules: dict[str, str]                   # field → raw regex string
    range_rules: dict[str, tuple[float, float]]    # field → (min, max)
    cross_field_rules: list[CrossFieldRule] = field(default_factory=list)
    default_hubspot_mapping: dict[str, str] = field(default_factory=dict)
