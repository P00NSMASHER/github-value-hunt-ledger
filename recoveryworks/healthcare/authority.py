"""Contract authority is exact-scoped and selected by *its own* controlling date."""
from .models import ContractAuthority, InvoiceLine, Hold

_BASES = {'ORDER_DATE': 'order_date', 'SHIP_DATE': 'ship_date', 'INVOICE_DATE': 'invoice_date'}


def resolve_authority(line: InvoiceLine, authorities: tuple[ContractAuthority, ...]) -> ContractAuthority | Hold:
    eligible = []
    missing_date = False
    for contract in authorities:
        if contract.scope != line.scope or contract.product_id != line.product_id:
            continue
        field = _BASES.get(contract.date_basis)
        if field is None or contract.quantity_basis != 'ACCEPTED_RECEIPTS' or contract.rounding not in {'HALF_UP', 'HALF_EVEN'}:
            return Hold('UNSUPPORTED_CONTRACT_TERMS', line.id, (contract.source,))
        on_date = getattr(line, field)
        if on_date is None:
            missing_date = True
            continue
        if contract.effective_from <= on_date and (contract.effective_to is None or on_date <= contract.effective_to):
            eligible.append(contract)
    if missing_date:
        # Do not silently select a different authority when another candidate
        # has a controlling date missing from the supplied invoice.
        return Hold('MISSING_CONTROLLING_DATE', line.id, (line.source,))
    if len(eligible) != 1:
        return Hold('NO_CONTROLLING_AUTHORITY' if not eligible else 'OVERLAPPING_AUTHORITIES',
                    line.id, (line.source,) + tuple(x.source for x in eligible))
    return eligible[0]
