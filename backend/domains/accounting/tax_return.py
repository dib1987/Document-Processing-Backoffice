from domains.base import CrossFieldRule, DomainConfig
from models.schemas import TaxReturnExtraction

TAX_RETURN_DOMAIN = DomainConfig(
    doc_type="tax_return",
    label="Federal Tax Return (Form 1040 / 1040-SR / 1040-NR)",
    schema_class=TaxReturnExtraction,
    required_fields=["taxpayer_name", "ssn_primary", "tax_year"],
    format_rules={
        "ssn_primary":  r"^XXX-XX-\d{4}$",
        "ssn_spouse":   r"^XXX-XX-\d{4}$",
        "tax_year":     r"^(19|20)\d{2}$",
        "address_zip":  r"^\d{5}(-\d{4})?$",
    },
    range_rules={
        "total_income":  (0, 10_000_000),
        "total_tax":     (0, 5_000_000),
        "refund_amount": (0, 1_000_000),
        "amount_owed":   (0, 1_000_000),
    },
    cross_field_rules=[
        CrossFieldRule(
            field_a="refund_amount",
            field_b="amount_owed",
            message="A tax return cannot have both a refund and an amount owed at the same time.",
            rule_type="mutually_exclusive",
        ),
    ],
    default_hubspot_mapping={
        "taxpayer_name":  "__split_name__",
        "address_street": "address",
        "address_city":   "city",
        "address_state":  "state",
        "address_zip":    "zip",
        "total_income":   "annualrevenue",
        "tax_year":       "tax_year",
        "ssn_primary":    "ssn_last4",
        "filing_status":  "filing_status",
        "form_type":      "tax_form_type",
    },
)
