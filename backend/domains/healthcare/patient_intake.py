from domains.base import CrossFieldRule, DomainConfig
from models.schemas import PatientIntakeExtraction

PATIENT_INTAKE_DOMAIN = DomainConfig(
    doc_type="patient_intake",
    label="Patient Intake Packet",
    schema_class=PatientIntakeExtraction,
    required_fields=[
        "patient_full_name",
        "date_of_birth",
        "phone",
        "address_line_1",
        "city",
        "state",
        "zip_code",
        "patient_signature_present",
        "signature_date",
    ],
    format_rules={
        "date_of_birth":  r"^\d{4}-\d{2}-\d{2}$",
        "signature_date": r"^\d{4}-\d{2}-\d{2}$",
        "zip_code":       r"^\d{5}(-\d{4})?$",
        "phone":          r"^(\+1[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}$",
        "email":          r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    },
    range_rules={},
    cross_field_rules=[
        CrossFieldRule(
            field_a="signature_date",
            field_b="date_of_birth",
            message="Signature date cannot be earlier than the patient's date of birth.",
            rule_type="date_order",
        ),
    ],
    value_rules={
        "patient_signature_present": "true",
    },
    default_hubspot_mapping={
        "patient_full_name": "__split_name__",
        "date_of_birth":     "date_of_birth",
        "phone":             "phone",
        "email":             "email",
        "address_line_1":    "address",
        "city":              "city",
        "state":             "state",
        "zip_code":          "zip",
    },
)
