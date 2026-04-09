from domains.base import DomainConfig
from models.schemas import BankStatementExtraction

BANK_STATEMENT_DOMAIN = DomainConfig(
    doc_type="bank_statement",
    label="Bank or Financial Account Statement",
    schema_class=BankStatementExtraction,
    required_fields=["account_holder_name", "account_number", "bank_name", "ending_balance"],
    format_rules={
        "statement_period_start": r"^\d{4}-\d{2}-\d{2}$",
        "statement_period_end":   r"^\d{4}-\d{2}-\d{2}$",
    },
    range_rules={
        "ending_balance": (-500_000, 10_000_000),
    },
    cross_field_rules=[],
    default_hubspot_mapping={
        "account_holder_name": "__split_name__",
        "bank_name":           "bank_name",
        "account_type":        "account_type",
        "account_number":      "description",
        "ending_balance":      "annualrevenue",
    },
)
