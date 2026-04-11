"""
Claude Extraction Service — DocFlow AI

Calls Claude claude-sonnet-4-6 to extract structured fields from document text.
Returns (extracted_dict, confidence_dict) per field.

SDK patterns per anthropic Python SDK docs:
- anthropic.Anthropic() with max_retries=3 (SDK auto-retries 429 + 5xx)
- temperature=0 for deterministic extraction
- Typed exception handling
- JSON parsing from response content
"""
import json
import logging
import re
from typing import Any

import anthropic

from config import get_settings
from domains import get_domain

logger = logging.getLogger(__name__)
settings = get_settings()

# SDK client — max_retries handles 429 + 5xx automatically with exponential backoff
_client = anthropic.Anthropic(
    api_key=settings.anthropic_api_key,
    max_retries=3,
)

MAX_TEXT_CHARS = 90_000  # ~22K tokens — leaves headroom for prompt + JSON response

# Patterns for masking sensitive data before any DB write
_SSN_PATTERN = re.compile(r"\b(\d{3})-(\d{2})-(\d{4})\b")
_ACCOUNT_PATTERN = re.compile(r"\b\d{4,}(\d{4})\b")  # 5+ digit numbers → keep last 4


_SYSTEM_PROMPT_TEMPLATE = """You are a professional data extraction assistant specializing in {domain_label} documents.
Your job is to extract specific fields from these documents with precision.

Rules you MUST follow:
1. Return ONLY valid JSON — no explanation, no markdown, no extra text.
2. Use null for any field you cannot find or are not confident about.
3. NEVER fabricate, guess, or infer values not explicitly in the document.
4. For every field, include a matching entry in "_confidence" with one of:
   "high"      — clearly visible and unambiguous in the document
   "medium"    — readable but partially obscured or inferred from context
   "low"       — barely readable or uncertain
   "not_found" — field not present in the document at all
5. SSNs: return ONLY the last 4 digits in format "XXX-XX-NNNN". Never return a full SSN.
6. Account numbers: return ONLY the last 4 digits in format "XXXX-NNNN".
7. Dates: use ISO 8601 format (YYYY-MM-DD) where possible.
8. Dollar amounts: include the $ sign and use comma separators (e.g., "$124,500").
9. For boolean presence fields (e.g. signature_present, medical_necessity_present):
   Return "true" ONLY if you see clear, positive evidence (e.g. a name written, an ink mark,
   explicit text such as "signed", "authorized", or a dated signature block with content).
   Return "false" if the field is blank, shows only underscores/lines, or has no content.
   Never default to "true" when uncertain — default to "false".
"""


def _build_system_prompt(domain_label: str) -> str:
    return _SYSTEM_PROMPT_TEMPLATE.format(domain_label=domain_label)


def extract_fields(
    full_text: str,
    doc_type: str,
    job_id: str,
) -> tuple[dict[str, Any], dict[str, str]]:
    """
    Extract structured fields from document text using Claude.

    Args:
        full_text: OCR-extracted text from the document.
        doc_type: One of "tax_return", "government_id", "bank_statement", "general".
        job_id: Job UUID for logging.

    Returns:
        (extracted_fields, confidence_scores)
        Both are dicts keyed by field name.
        All values are strings or None. Confidence values are
        "high" | "medium" | "low" | "not_found".
    """
    domain = get_domain(doc_type)   # raises ValueError if unknown
    schema_json = json.dumps(domain.schema_class.model_json_schema(), indent=2)
    doc_label = domain.label

    # Truncate text to stay within context budget
    truncated_text = full_text[:MAX_TEXT_CHARS]
    if len(full_text) > MAX_TEXT_CHARS:
        logger.warning("job=%s text truncated from %d to %d chars", job_id, len(full_text), MAX_TEXT_CHARS)
        truncated_text += "\n\n[Document truncated — additional pages not shown]"

    user_prompt = f"""DOCUMENT TYPE: {doc_label}

DOCUMENT TEXT:
---
{truncated_text}
---

Extract all fields below and return them as a JSON object.
Include a "_confidence" object with confidence ratings for every field.

Target schema:
{schema_json}

Return JSON only. No other text."""

    logger.info("job=%s doc_type=%s invoking Claude extraction", job_id, doc_type)

    try:
        response = _client.messages.create(
            model=settings.claude_model,
            max_tokens=2048,
            temperature=0,
            system=_build_system_prompt(doc_label),
            messages=[{"role": "user", "content": user_prompt}],
        )
    except anthropic.AuthenticationError:
        logger.error("job=%s Anthropic authentication failed — check ANTHROPIC_API_KEY", job_id)
        raise
    except anthropic.BadRequestError as exc:
        logger.error("job=%s Claude bad request: %s", job_id, exc.message)
        raise
    except anthropic.RateLimitError:
        # SDK already retried 3 times — surface to Celery for task-level retry
        logger.error("job=%s Claude rate limit exhausted after retries", job_id)
        raise
    except anthropic.APIStatusError as exc:
        logger.error("job=%s Claude API error %d: %s", job_id, exc.status_code, exc.message)
        raise

    # Extract the text content block
    raw_json = ""
    for block in response.content:
        if block.type == "text":
            raw_json = block.text.strip()
            break

    if not raw_json:
        raise ValueError(f"job={job_id} Claude returned no text content")

    # Strip markdown code fences if present (defensive — prompt says JSON only)
    raw_json = _strip_code_fences(raw_json)

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        logger.error("job=%s JSON parse error: %s | raw=%s", job_id, exc, raw_json[:500])
        raise ValueError(f"Claude returned invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"job={job_id} Expected JSON object, got {type(parsed)}")

    # Split out confidence scores
    confidence: dict[str, str] = parsed.pop("_confidence", {})

    # Ensure all values are strings or None (normalize numbers, booleans, etc.)
    extracted: dict[str, Any] = {
        k: (str(v) if v is not None else None)
        for k, v in parsed.items()
        if not k.startswith("_")
    }

    # Mask any sensitive data Claude may have returned despite instructions
    extracted = _mask_sensitive_fields(extracted)

    logger.info(
        "job=%s extraction complete: %d fields, stop_reason=%s, tokens=%d",
        job_id,
        len(extracted),
        response.stop_reason,
        response.usage.input_tokens + response.usage.output_tokens,
    )

    return extracted, confidence


def _strip_code_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line (```json or ```) and last line (```)
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()
    return text


def _mask_sensitive_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """
    Second-pass masking after Claude's response.
    Catches any full SSNs or account numbers that slipped through the prompt instructions.
    """
    masked = {}
    for key, value in fields.items():
        if value is None:
            masked[key] = None
            continue
        val_str = str(value)

        # Mask full SSNs: 123-45-6789 → XXX-XX-6789
        val_str = _SSN_PATTERN.sub(lambda m: f"XXX-XX-{m.group(3)}", val_str)

        # For fields explicitly about account/routing/SSN numbers, enforce last-4-only format
        key_lower = key.lower()
        if any(kw in key_lower for kw in ("ssn", "account_number")):
            # If it still contains digits beyond last 4, mask
            digits = re.sub(r"\D", "", val_str)
            if len(digits) > 4:
                val_str = f"XXXX-{digits[-4:]}"

        masked[key] = val_str
    return masked
