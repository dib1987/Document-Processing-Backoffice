# Future: healthcare domain
#
# Add DomainConfig instances here for:
#   - patient_intake  (patient intake forms)
#   - insurance_claim (insurance claim documents)
#   - government_id   (patient ID verification)
#
# Example scaffold prompt (paste into Claude Code with the domain-scaffolder skill):
#
#   "Scaffold a DocFlow domain config for a medical clinic / healthcare provider.
#    Doc types: patient_intake, insurance_claim, government_id.
#    Required fields for patient_intake: patient_name, date_of_birth, insurance_member_id.
#    Format rules: member ID matches [A-Z]{3}-\d{6}.
#    Push to: Salesforce Health Cloud."
#
# Then:
#   from .patient_intake import PATIENT_INTAKE_DOMAIN
#   from .insurance_claim import INSURANCE_CLAIM_DOMAIN
#   HEALTHCARE_DOMAINS = [PATIENT_INTAKE_DOMAIN, INSURANCE_CLAIM_DOMAIN]
#
# And in domains/__init__.py uncomment:
#   from .healthcare import HEALTHCARE_DOMAINS
#   _ALL_DOMAINS = [..., *HEALTHCARE_DOMAINS]

HEALTHCARE_DOMAINS: list = []
