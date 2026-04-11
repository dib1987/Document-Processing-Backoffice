"""
Pydantic extraction schemas for each document type.
All fields are Optional[str] — partial extraction is graceful (null = not found).
Claude also populates _confidence with "high" | "medium" | "low" | "not_found" per field.
"""
from typing import Optional

from pydantic import BaseModel, Field


class TaxReturnExtraction(BaseModel):
    taxpayer_name: Optional[str] = None
    spouse_name: Optional[str] = None
    ssn_primary: Optional[str] = Field(None, description="Last 4 digits only, format: XXX-XX-NNNN")
    ssn_spouse: Optional[str] = Field(None, description="Last 4 digits only, format: XXX-XX-NNNN")
    filing_status: Optional[str] = Field(None, description="Single | Married Filing Jointly | Married Filing Separately | Head of Household | Qualifying Widow(er)")
    tax_year: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    total_income: Optional[str] = Field(None, description="Adjusted Gross Income (AGI)")
    wages_salaries: Optional[str] = None
    interest_income: Optional[str] = None
    dividend_income: Optional[str] = None
    business_income: Optional[str] = None
    capital_gains: Optional[str] = None
    ira_distributions: Optional[str] = None
    social_security: Optional[str] = None
    total_tax: Optional[str] = None
    federal_tax_withheld: Optional[str] = None
    refund_amount: Optional[str] = None
    amount_owed: Optional[str] = None
    form_type: Optional[str] = Field(None, description="1040 | 1040-SR | 1040-NR")
    preparer_name: Optional[str] = None
    preparer_ptin: Optional[str] = None
    _confidence: dict = {}


class GovernmentIDExtraction(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    id_number: Optional[str] = Field(None, description="Masked — show only last 4 digits: XXXX-NNNN")
    id_type: Optional[str] = Field(None, description="Driver License | Passport | State ID | Military ID")
    issuing_state: Optional[str] = None
    issuing_country: Optional[str] = None
    issue_date: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    expiration_date: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    sex: Optional[str] = None
    eye_color: Optional[str] = None
    height: Optional[str] = None
    _confidence: dict = {}


class BankStatementExtraction(BaseModel):
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = Field(None, description="Masked — last 4 digits only: XXXX-NNNN")
    routing_number: Optional[str] = None
    bank_name: Optional[str] = None
    account_type: Optional[str] = Field(None, description="Checking | Savings | Money Market | CD")
    statement_period_start: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    statement_period_end: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    beginning_balance: Optional[str] = None
    ending_balance: Optional[str] = None
    total_deposits: Optional[str] = None
    total_withdrawals: Optional[str] = None
    average_daily_balance: Optional[str] = None
    address_on_file: Optional[str] = None
    num_transactions: Optional[str] = None
    _confidence: dict = {}


class GeneralDocumentExtraction(BaseModel):
    document_title: Optional[str] = None
    document_date: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    issuing_entity: Optional[str] = None
    primary_person_name: Optional[str] = None
    reference_number: Optional[str] = None
    dollar_amount: Optional[str] = None
    address_mentioned: Optional[str] = None
    key_dates: Optional[list[str]] = None
    summary: Optional[str] = Field(None, description="2-3 sentence plain English summary of this document")
    document_category: Optional[str] = Field(None, description="Claude's best guess: W-2 | 1099 | Letter | Contract | Invoice | Other")
    _confidence: dict = {}


class PatientIntakeExtraction(BaseModel):
    patient_full_name: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    sex: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    pcp_name: Optional[str] = None
    referring_provider_name: Optional[str] = None
    patient_signature_present: Optional[str] = Field(None, description="'true' ONLY if a patient signature (handwritten name, initials, or mark) is clearly visible. Return 'false' if the signature line is blank, shows only underscores or a printed line, or contains no actual signature content. Default to 'false' when uncertain.")
    signature_date: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    preferred_language: Optional[str] = None
    _confidence: dict = {}


class InsuranceAuthorizationExtraction(BaseModel):
    patient_full_name: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    payer_name: Optional[str] = None
    member_id: Optional[str] = None
    group_number: Optional[str] = None
    plan_name: Optional[str] = None
    policy_holder_name: Optional[str] = None
    policy_holder_relationship: Optional[str] = None
    referring_provider_name: Optional[str] = None
    servicing_provider_name: Optional[str] = None
    npi_number: Optional[str] = Field(None, description="10-digit NPI number")
    referral_number: Optional[str] = None
    prior_authorization_number: Optional[str] = None
    authorization_status: Optional[str] = Field(None, description="approved | pending | denied | not_required")
    authorization_start_date: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    authorization_end_date: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    requested_service: Optional[str] = None
    icd10_codes: Optional[str] = Field(None, description="Comma-separated ICD-10 diagnosis codes, e.g. 'M54.5, G89.29'")
    cpt_codes: Optional[str] = Field(None, description="Comma-separated CPT procedure codes, e.g. '99213, 20610'")
    _confidence: dict = {}


class ClinicalSupportExtraction(BaseModel):
    patient_full_name: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    document_date: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    document_type_label: Optional[str] = Field(None, description="e.g. Physician Note, Discharge Summary, Lab Report, Diagnosis Summary, Order Sheet, Medical Necessity Letter")
    provider_name: Optional[str] = None
    provider_npi: Optional[str] = Field(None, description="10-digit NPI number")
    facility_name: Optional[str] = None
    diagnosis_summary: Optional[str] = None
    icd10_codes: Optional[str] = Field(None, description="Comma-separated ICD-10 diagnosis codes")
    requested_service: Optional[str] = None
    cpt_codes: Optional[str] = Field(None, description="Comma-separated CPT procedure codes")
    date_of_service: Optional[str] = Field(None, description="ISO 8601 format: YYYY-MM-DD")
    medical_necessity_present: Optional[str] = Field(None, description="'true' ONLY if the document contains explicit medical necessity language (e.g. a medical necessity statement, letter of medical necessity, or physician attestation). Return 'false' if no such language is present. Default to 'false' when uncertain.")
    provider_signature_present: Optional[str] = Field(None, description="'true' ONLY if a provider/physician signature (handwritten name, stamp, or countersigned block with content) is clearly visible. Return 'false' if the signature area is blank or shows only a printed line. Default to 'false' when uncertain.")
    _confidence: dict = {}


DOC_TYPE_SCHEMA_MAP: dict[str, type] = {
    "tax_return": TaxReturnExtraction,
    "government_id": GovernmentIDExtraction,
    "bank_statement": BankStatementExtraction,
    "general": GeneralDocumentExtraction,
    "patient_intake": PatientIntakeExtraction,
    "insurance_authorization": InsuranceAuthorizationExtraction,
    "clinical_support": ClinicalSupportExtraction,
}

DOC_TYPE_LABELS: dict[str, str] = {
    "tax_return": "Federal Tax Return (Form 1040 / 1040-SR / 1040-NR)",
    "government_id": "Government-Issued Photo ID (Driver License / Passport / State ID)",
    "bank_statement": "Bank or Financial Account Statement",
    "general": "General Financial Document",
    "patient_intake": "Patient Intake Packet",
    "insurance_authorization": "Insurance / Referral / Prior Authorization Packet",
    "clinical_support": "Clinical Support Packet",
}
