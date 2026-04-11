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

from domains import get_domain


# ──────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────

@dataclass
class ValidationFlag:
    flag_type: str    # MISSING_REQUIRED | OUT_OF_RANGE | FORMAT_MISMATCH | CROSS_FIELD | VALUE_MISMATCH
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
    _check_formats(extracted_fields, doc_type, flags)
    _check_ranges(extracted_fields, doc_type, flags)
    _check_cross_fields(extracted_fields, doc_type, flags)
    _check_values(extracted_fields, doc_type, flags)

    return ValidationResult(passed=len(flags) == 0, flags=flags)


# ──────────────────────────────────────────────
# Rule implementations
# ──────────────────────────────────────────────

def _check_required(fields: dict, doc_type: str, flags: list[ValidationFlag]) -> None:
    required = get_domain(doc_type).required_fields
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


def _check_formats(fields: dict, doc_type: str, flags: list[ValidationFlag]) -> None:
    for field_name, pattern_str in get_domain(doc_type).format_rules.items():
        value = fields.get(field_name)
        if value is None or str(value).strip() == "":
            continue  # Missing is caught by required check
        if not re.match(pattern_str, str(value).strip()):
            flags.append(ValidationFlag(
                flag_type="FORMAT_MISMATCH",
                field_name=field_name,
                plain_message=(
                    f'"{_label(field_name)}" has an unexpected format. '
                    f'Got: "{value}". Please verify and correct this field.'
                ),
            ))


def _check_ranges(fields: dict, doc_type: str, flags: list[ValidationFlag]) -> None:
    for field_name, (min_val, max_val) in get_domain(doc_type).range_rules.items():
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
    for rule in get_domain(doc_type).cross_field_rules:
        val_a = fields.get(rule.field_a)
        val_b = fields.get(rule.field_b)

        if rule.rule_type == "mutually_exclusive":
            a_num = _parse_dollar(str(val_a)) if val_a else None
            b_num = _parse_dollar(str(val_b)) if val_b else None
            if a_num is not None and b_num is not None and a_num > 0 and b_num > 0:
                flags.append(ValidationFlag(
                    flag_type="CROSS_FIELD",
                    field_name=f"{rule.field_a}+{rule.field_b}",
                    plain_message=rule.message,
                ))

        elif rule.rule_type == "date_order":
            # field_a must be chronologically after field_b
            a_date = _parse_date(str(val_a)) if val_a else None
            b_date = _parse_date(str(val_b)) if val_b else None
            if a_date is not None and b_date is not None and a_date <= b_date:
                flags.append(ValidationFlag(
                    flag_type="CROSS_FIELD",
                    field_name=f"{rule.field_a}+{rule.field_b}",
                    plain_message=rule.message,
                ))


def _check_values(fields: dict, doc_type: str, flags: list[ValidationFlag]) -> None:
    for field_name, expected in get_domain(doc_type).value_rules.items():
        value = fields.get(field_name)
        if value is None or str(value).strip() == "":
            continue  # null is handled by required_fields check
        if str(value).strip().lower() != expected.lower():
            flags.append(ValidationFlag(
                flag_type="VALUE_MISMATCH",
                field_name=field_name,
                plain_message=(
                    f'"{_label(field_name)}" must be "{expected}" for auto-approval. '
                    f'Got: "{value}". Please review and correct before approving.'
                ),
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
