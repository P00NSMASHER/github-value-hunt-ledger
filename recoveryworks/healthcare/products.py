"""Fixed-pack identity and *documented*, effective-dated quantity conversion."""
from datetime import date
from decimal import Decimal
from .models import (ScopeKey, ProductIdentity, InvoiceLine, PackConversion,
                     ContractAuthority, Hold)
from .money import parse_decimal, multiply


def resolve_product(line: InvoiceLine, products: tuple[ProductIdentity, ...]) -> ProductIdentity | Hold:
    matches = [p for p in products if p.scope == line.scope and p.id == line.product_id
               and p.effective_from <= line.invoice_date
               and (p.effective_to is None or line.invoice_date <= p.effective_to)]
    if len(matches) != 1:
        return Hold('MISSING_PRODUCT' if not matches else 'AMBIGUOUS_PRODUCT', line.id, (line.source,))
    product = matches[0]
    if product.category != 'FIXED_PACK_NONPHARMA':
        return Hold('UNSUPPORTED_PRODUCT_CATEGORY', line.id, (product.source,))
    return product


def convert_quantity(quantity: Decimal, conversion: PackConversion, on_date: date) -> Decimal | Hold:
    if not isinstance(on_date, date):
        raise ValueError('INVALID_CONVERSION_DATE')
    when = on_date.isoformat()
    if when < conversion.effective_from or (conversion.effective_to and when > conversion.effective_to):
        return Hold('EXPIRED_PACK_CONVERSION', conversion.id, (conversion.source,))
    factor = parse_decimal(conversion.factor)
    if factor <= 0:
        return Hold('INVALID_PACK_CONVERSION', conversion.id, (conversion.source,))
    return multiply(quantity, factor)


def to_price_quantity(*, quantity: str, from_unit: str,
                      authority: ContractAuthority, when: str,
                      conversions: tuple[PackConversion, ...], record_id: str,
                      scope: ScopeKey, product_id: str) -> tuple[Decimal, tuple] | Hold:
    qty = parse_decimal(quantity)
    if from_unit == authority.unit:
        return (qty, ())
    matches = [x for x in conversions if x.scope == scope and x.product_id == product_id
               and x.from_unit == from_unit and x.to_unit == authority.unit
               and x.effective_from <= when and (x.effective_to is None or when <= x.effective_to)]
    if len(matches) != 1:
        return Hold('MISSING_PACK_CONVERSION' if not matches else 'AMBIGUOUS_PACK_CONVERSION',
                    record_id, (authority.source,))
    conversion = matches[0]
    result = convert_quantity(qty, conversion, date.fromisoformat(when))
    if isinstance(result, Hold):
        return result
    return (result, (conversion.source,))
