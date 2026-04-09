# DocFlow Legal

Frontend app for legal clients (law firms, legal services providers).

## Status

Not yet scaffolded. Use the domain-scaffolder skill with a legal discovery brief to generate:
- `backend/domains/legal/contract.py`
- `backend/domains/legal/court_filing.py`
- `backend/domains/legal/client_id.py`

Then scaffold this frontend using the frontend-design skill with the client's branding brief.

## Domain Config Scaffold Prompt

```
Scaffold a DocFlow domain config for a law firm / legal services provider.

Doc types:
- contract: Legal contract or agreement. Required: party_name_1, party_name_2,
  contract_date, effective_date, contract_value, governing_law.
  Cross-field: effective_date must be on or after contract_date.
  Range: contract_value 0–100M.
  Push to: HubSpot (firstname, lastname, contract_value, governing_law, contract_date)

- court_filing: Court filing. Required: case_number, filing_party, court_name,
  filing_date, document_type.
  Format: case_number matches \d{2}-[A-Z]{2}-\d{4,6}.
  Push to: HubSpot (case_number, filing_party, court_name, filing_date)

- client_id: Client identity verification. Required: full_name, date_of_birth,
  id_number, expiration_date.
  Cross-field: expiration_date must be after issue_date.
  Push to: HubSpot (firstname, lastname, date_of_birth, id_expiration)
```

## Setup Checklist

- [ ] Add legal domain configs to `backend/domains/legal/`
- [ ] Register in `backend/domains/__init__.py`
- [ ] Scaffold this Next.js app using the frontend-design skill
- [ ] Configure `.env.local` (API URL, Clerk keys, branding)
- [ ] Deploy to client subdomain
