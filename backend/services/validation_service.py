"""
Validation Service — DocFlow AI

Runs field validation rules against extracted data.
Returns ValidationResult(passed, flags).

If passed=True  → route to HubSpot CRM writer
If passed=False → route to Review Queue
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ──────────────────────────────────────────────
# Configuration — adjust thresholds here
# ──────────────────────────────────────────────

REQUIRED_FIELDS: dict[str, list[str]] = {
    "tax_return":    ["taxpayer_name", "ssn_primary", "tax_year"],
    "government_id": ["full_name", "date_of_birth", "id_number", "expiration_date"],
    "bank_statement": ["account_holder_name", "account_number", "bank_name", "ending_balance"],
    "general":       ["primary_person_name", "document_date"],
}

FORMAT_RULES: dict[str, re.Pattern] = {
    "ssn_primary":    re.compile(r"^XXX-XX-\d{4}$"),
    "ssn_spouse":     re.compile(r"^XXX-XX-\d{4}$"),
    "address_zip":    re.compile(r"^\d{5}(-\d{4})?$"),
    "tax_year":       re.compile(r"^(19|20)\d{2}$"),
    "date_of_birth":  re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "issue_date":     re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "expiration_date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "statement_period_start": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "statement_period_end":   re.compile(r"^\d{4}-\d{2}-\d{2}$"),
}

# Dollar amounts — strip $ and commas, then compare
RANGE_RULES: dict[str, tuple[float, float]] = {
    "total_income": (0, 10_000_000),
    "total_tax":    (0, 5_000_000),
    "refund_amount": (0, 1_000_000),
    "amount_owed":  (0, 1_000_000),
    "ending_balance": (-500_000, 10_000_000),
}

# (doc_type, field_a, field_b, plain_message)
CROSS_FIELD_RULES: list[tuple[str, str, str, str]] = [
    (
        "tax_return",
        "refund_amount",
        "amount_owed",
        "A tax return cannot have both a refund and an amount owed at the same time.",
    ),
    (
        "government_id",
        "expiration_date",
        "issue_date",
        "The expiration date must be after the issue date.",
    ),
]


# ──────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────

@dataclass
class ValidationFlag:
    flag_type: str    # MISSING_REQUIRED | OUT_OF_RANGE | FORMAT_MISMATCH | CROSS_FIELD
    field_name: str | None
    plain_message: str  # Shown directly to the non-technical reviewer


@dataclass
class ValidationResult:
    passed: bool
    flags: list[ValidationFlag] = field(default_factory=list)


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def validate(
    extracted_fields: dict[str, Any],
    doc_type: str,
) -> ValidationResult:
    """
    Run all validation rules against the extracted fields.
    Returns ValidationResult — caller routes to CRM or Review Queue.
    """
    flags: list[ValidationFlag] = []

    _check_required(extracted_fields, doc_type, flags)
    _check_formats(extracted_fields, flags)
    _check_ranges(extracted_fields, flags)
    _check_cross_fields(extracted_fields, doc_type, flags)

    return ValidationResult(passed=len(flags) == 0, flags=flags)


# ──────────────────────────────────────────────
# Rule implementations
# ──────────────────────────────────────────────

def _check_required(fields: dict, doc_type: str, flags: list[ValidationFlag]) -> None:
    required = REQUIRED_FIELDS.get(doc_type, [])
    for field_name in required:
        value = fields.get(field_name)
        if not value or str(value).strip() == "":
            flags.append(ValidationFlag(
                flag_type="MISSING_REQUIRED",
                field_name=field_name,
                plain_message=(
                    f'"{_label(field_name)}" is required but was not found in the document. '
                    "Please enter this value manually before approving."
                ),
            ))


def _check_formats(fields: dict, flags: list[ValidationFlag]) -> None:
    for field_name, pattern in FORMAT_RULES.items():
        value = fields.get(field_name)
        if value is None or str(value).strip() == "":
            continue  # Missing is caught by required check
        if not pattern.match(str(value).strip()):
            flags.append(ValidationFlag(
                flag_type="FORMAT_MISMATCH",
                field_name=field_name,
                plain_message=(
                    f'"{_label(field_name)}" has an unexpected format. '
                    f'Got: "{value}". Please verify and correct this field.'
                ),
            ))


def _check_ranges(fields: dict, flags: list[ValidationFlag]) -> None:
    for field_name, (min_val, max_val) in RANGE_RULES.items():
        value = fields.get(field_name)
        if value is None or str(value).strip() == "":
            continue
        numeric = _parse_dollar(str(value))
        if numeric is None:
            continue  # Can't parse — skip range check, format check will catch it
        if not (min_val <= numeric <= max_val):
            flags.append(ValidationFlag(
                flag_type="OUT_OF_RANGE",
                field_name=field_name,
                plain_message=(
                    f'"{_label(field_name)}" value of {value} is outside the expected range '
                    f"(${min_val:,.0f}–${max_val:,.0f}). Please verify this is correct."
                ),
            ))


def _check_cross_fields(fields: dict, doc_type: str, flags: list[ValidationFlag]) -> None:
    for rule_doc_type, field_a, field_b, message in CROSS_FIELD_RULES:
        if rule_doc_type != doc_type:
            continue
        val_a = fields.get(field_a)
        val_b = fields.get(field_b)

        if field_a == "refund_amount" and field_b == "amount_owed":
            # Both non-null and non-zero → inconsistent
            a_num = _parse_dollar(str(val_a)) if val_a else None
            b_num = _parse_dollar(str(val_b)) if val_b else None
            if a_num and a_num > 0 and b_num and b_num > 0:
                flags.append(ValidationFlag(
                    flag_type="CROSS_FIELD",
                    field_name=f"{field_a}+{field_b}",
                    plain_message=message,
                ))

        elif field_a == "expiration_date" and field_b == "issue_date":
            exp = _parse_date(str(val_a)) if val_a else None
            iss = _parse_date(str(val_b)) if val_b else None
            if exp and iss and exp <= iss:
                flags.append(ValidationFlag(
                    flag_type="CROSS_FIELD",
                    field_name=f"{field_a}+{field_b}",
                    plain_message=message,
                ))


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _label(field_name: str) -> str:
    """Convert snake_case field name to Title Case for display."""
    return field_name.replace("_", " ").title()


def _parse_dollar(value: str) -> float | None:
    """Parse dollar strings like '$124,500' or '124500.00' to float."""
    cleaned = re.sub(r"[$,\s]", "", value)
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_date(value: str) -> datetime | None:
    """Parse ISO 8601 date string to datetime."""
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        return None
