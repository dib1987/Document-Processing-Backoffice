# Future: legal domain
#
# Add DomainConfig instances here for:
#   - contract      (legal contracts and agreements)
#   - court_filing  (court filings and legal documents)
#   - client_id     (client identity verification)
#
# Example scaffold prompt (paste into Claude Code with the domain-scaffolder skill):
#
#   "Scaffold a DocFlow domain config for a law firm.
#    Doc types: contract, court_filing, client_id.
#    Required fields for contract: party_name_1, party_name_2, contract_date, contract_value.
#    Format rules: case_number matches \d{2}-[A-Z]{2}-\d{4,6}.
#    Push to: HubSpot."
#
# Then:
#   from .contract import CONTRACT_DOMAIN
#   from .court_filing import COURT_FILING_DOMAIN
#   LEGAL_DOMAINS = [CONTRACT_DOMAIN, COURT_FILING_DOMAIN]
#
# And in domains/__init__.py uncomment:
#   from .legal import LEGAL_DOMAINS
#   _ALL_DOMAINS = [..., *LEGAL_DOMAINS]

LEGAL_DOMAINS: list = []
