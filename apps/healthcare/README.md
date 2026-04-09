# DocFlow Healthcare

Frontend app for healthcare clients (clinics, hospitals, medical practices).

## Status

Not yet scaffolded. Use the domain-scaffolder skill with a healthcare discovery brief to generate:
- `backend/domains/healthcare/patient_intake.py`
- `backend/domains/healthcare/insurance_claim.py`

Then scaffold this frontend using the frontend-design skill with the client's branding brief.

## Domain Config Scaffold Prompt

```
Scaffold a DocFlow domain config for a medical clinic / healthcare provider.

Doc types:
- patient_intake: New patient intake form. Required: patient_name, date_of_birth, address,
  insurance_member_id, emergency_contact_name, emergency_contact_phone.
  Format: insurance_member_id matches [A-Z]{3}-\d{6}, date_of_birth ISO 8601.
  Push to: Salesforce Health Cloud (FirstName, LastName, Birthdate, MemberID__c, Address)

- insurance_claim: Insurance claim. Required: member_id, provider_name, claim_amount,
  diagnosis_code, service_date.
  Format: diagnosis_code matches ICD-10 [A-Z]\d{2}\.?\d{0,2}.
  Range: claim_amount 0–500K.
  Push to: Salesforce (ClaimAmount__c, DiagnosisCode__c, ServiceDate__c, ProviderName__c)

Note: HIPAA applies. Mask member IDs to last 4 digits.
```

## Setup Checklist

- [ ] Add healthcare domain configs to `backend/domains/healthcare/`
- [ ] Register in `backend/domains/__init__.py`
- [ ] Scaffold this Next.js app using the frontend-design skill
- [ ] Configure `.env.local` (API URL, Clerk keys, branding)
- [ ] Deploy to client subdomain
