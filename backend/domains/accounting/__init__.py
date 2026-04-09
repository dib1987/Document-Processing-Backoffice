from .bank_statement import BANK_STATEMENT_DOMAIN
from .general import GENERAL_DOMAIN
from .government_id import GOVT_ID_DOMAIN
from .tax_return import TAX_RETURN_DOMAIN

ACCOUNTING_DOMAINS = [
    TAX_RETURN_DOMAIN,
    GOVT_ID_DOMAIN,
    BANK_STATEMENT_DOMAIN,
    GENERAL_DOMAIN,
]
