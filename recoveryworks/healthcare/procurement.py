"""Deterministic source-to-authority purchasing audit; all findings remain REVIEW."""
from collections import defaultdict
from dataclasses import asdict
from decimal import Decimal
import hashlib

from .authority import resolve_authority
from .ingestion import canonical_bytes
from .models import (
    AuditResult, CanonicalBatch, InvoiceLine, ProductIdentity, ContractAuthority,
    PackConversion, ReceiptEvent, ReceiptAllocation, QuantityDecision,
    RuleSetVersion, SourceRef, Hold, Finding,
)
from .money import extend_price, parse_decimal
from .products import resolve_product, to_price_quantity


def _refs(*items: SourceRef) -> tuple[SourceRef, ...]:
    return tuple(sorted(set(items), key=lambda x: (x.sha256, x.locator, x.system)))


def loss_id(line: InvoiceLine) -> str:
    """One facility/account/invoice-line economic loss across *all* detectors."""
    identity = {'scope': asdict(line.scope), 'invoice_number': line.invoice_number,
                'invoice_date': line.invoice_date, 'line_number': line.line_number}
    return hashlib.sha256(canonical_bytes(identity)).hexdigest()


def audit_procurement(batch: CanonicalBatch, rules: RuleSetVersion) -> AuditResult:
    if type(batch) is not CanonicalBatch or type(rules) is not RuleSetVersion:
        raise ValueError('INVALID_AUDIT_INPUT')
    invoices = batch.of_type(InvoiceLine)
    holds = list(batch.holds)
    if holds or not batch.import_batch.complete:
        if not holds:
            holds.append(Hold('INCOMPLETE_POPULATION', 'batch'))
        return AuditResult((), tuple(holds), 0, len(invoices), 0, batch.scope.synthetic,
                           batch.import_batch.original_hash, batch.import_batch.normalized_hash)

    products = batch.of_type(ProductIdentity)
    contracts = batch.of_type(ContractAuthority)
    conversions = batch.of_type(PackConversion)
    receipts = {(x.scope, x.id): x for x in batch.of_type(ReceiptEvent)}
    invoice_index = {(x.scope, x.id): x for x in invoices}
    allocations = defaultdict(list)
    decisions = defaultdict(list)
    blocked = set()

    # Detect duplicate economic invoices even if source-local row IDs differ.
    by_economic = defaultdict(list)
    for line in invoices:
        if line.status == 'ACTIVE':
            # Same supplier invoice and line across different issue dates can
            # be a reissue, not an additional economic obligation.
            by_economic[(line.scope, line.invoice_number, line.line_number)].append(line)
    for cluster in by_economic.values():
        if len(cluster) > 1:
            for line in cluster:
                holds.append(Hold('DUPLICATE_ECONOMIC_INVOICE_LINE', line.id, _refs(*(x.source for x in cluster))))
                blocked.add((line.scope, line.id))

    for decision in batch.of_type(QuantityDecision):
        key = decision.scope, decision.invoice_line_id
        if key not in invoice_index:
            holds.append(Hold('ORPHAN_QUANTITY_DECISION', decision.id, (decision.source,)))
        else:
            decisions[key].append(decision)

    by_receipt = defaultdict(list)
    for alloc in batch.of_type(ReceiptAllocation):
        ik = (alloc.scope, alloc.invoice_line_id)
        rk = (alloc.scope, alloc.receipt_id)
        invoice, receipt = invoice_index.get(ik), receipts.get(rk)
        if invoice is None or receipt is None or receipt.scope != invoice.scope:
            holds.append(Hold('ORPHAN_RECEIPT_ALLOCATION', alloc.id, (alloc.source,)))
            if invoice:
                blocked.add(ik)
            continue
        if receipt.product_id != invoice.product_id or receipt.po_line_id != invoice.po_line_id:
            holds.append(Hold('RECEIPT_IDENTITY_MISMATCH', invoice.id, _refs(invoice.source, receipt.source, alloc.source)))
            blocked.add(ik)
            continue
        if not receipt.accepted or receipt.receipt_date > batch.scope.as_of:
            holds.append(Hold('RECEIPT_OUTSIDE_SNAPSHOT' if receipt.receipt_date > batch.scope.as_of else
                              'UNACCEPTED_RECEIPT', invoice.id, _refs(receipt.source, alloc.source)))
            blocked.add(ik)
            continue
        allocated = parse_decimal(alloc.quantity)
        if allocated <= 0:
            holds.append(Hold('NONPOSITIVE_RECEIPT_ALLOCATION', invoice.id, (alloc.source,)))
            blocked.add(ik)
            continue
        allocations[ik].append((alloc, receipt))
        by_receipt[rk].append((alloc, receipt, invoice))

    # Cumulative capacity conservation: one physical receipt cannot be consumed twice.
    for key, group in by_receipt.items():
        capacity = parse_decimal(group[0][1].quantity)
        if sum((parse_decimal(x.quantity) for x, _, _ in group), Decimal(0)) > capacity:
            for alloc, receipt, line in group:
                holds.append(Hold('OVERALLOCATED_RECEIPT', line.id, _refs(line.source, receipt.source, alloc.source)))
                blocked.add((line.scope, line.id))

    findings, unassessed, skipped = [], 0, 0
    for line in sorted(invoices, key=lambda x: (repr(x.scope), x.id)):
        ik = (line.scope, line.id)
        if line.status in ('CANCELLED', 'REPLACED'):
            skipped += 1
            continue
        if line.status != 'ACTIVE':
            holds.append(Hold('UNSUPPORTED_INVOICE_STATUS', line.id, (line.source,)))
            unassessed += 1
            continue
        if ik in blocked:
            unassessed += 1
            continue
        if line.supersedes_id:
            old = invoice_index.get((line.scope, line.supersedes_id))
            if old is None or old.status not in ('CANCELLED', 'REPLACED'):
                holds.append(Hold('UNVERIFIED_INVOICE_REPLACEMENT', line.id, (line.source,)))
                unassessed += 1
                continue
        if line.unsupported_components:
            holds.append(Hold('UNSUPPORTED_INVOICE_COMPONENTS', line.id, (line.source,)))
            unassessed += 1
            continue
        product = resolve_product(line, products)
        if isinstance(product, Hold):
            holds.append(product)
            unassessed += 1
            continue
        authority = resolve_authority(line, contracts)
        if isinstance(authority, Hold):
            holds.append(authority)
            unassessed += 1
            continue
        when = getattr(line, {'ORDER_DATE': 'order_date', 'INVOICE_DATE': 'invoice_date',
                              'SHIP_DATE': 'ship_date'}[authority.date_basis])
        inv = to_price_quantity(quantity=line.quantity, from_unit=line.unit, authority=authority,
                                when=when, conversions=conversions, record_id=line.id,
                                scope=line.scope, product_id=line.product_id)
        if isinstance(inv, Hold):
            holds.append(inv)
            unassessed += 1
            continue
        billed_qty, invoice_conversions = inv
        if billed_qty <= 0:
            holds.append(Hold('NONPOSITIVE_INVOICE_QUANTITY', line.id, (line.source,)))
            unassessed += 1
            continue
        group = allocations.get(ik, [])
        if not group:
            holds.append(Hold('MISSING_ACCEPTED_RECEIPT', line.id, (line.source,)))
            unassessed += 1
            continue
        receipt_qty = Decimal(0)
        receipt_evidence = []
        bad_receipt = None
        for alloc, receipt in group:
            converted = to_price_quantity(quantity=alloc.quantity, from_unit=receipt.unit,
                                          authority=authority, when=receipt.receipt_date,
                                          conversions=conversions, record_id=line.id,
                                          scope=line.scope, product_id=line.product_id)
            if isinstance(converted, Hold):
                bad_receipt = converted
                break
            quantity, refs = converted
            receipt_qty += quantity
            receipt_evidence.extend((alloc.source, receipt.source, *refs))
        if bad_receipt:
            holds.append(bad_receipt)
            unassessed += 1
            continue
        if receipt_qty <= 0:
            holds.append(Hold('ZERO_ACCEPTED_RECEIPT', line.id, (line.source,)))
            unassessed += 1
            continue
        line_decisions = decisions.get(ik, [])
        if len(line_decisions) > 1:
            holds.append(Hold('CONFLICTING_QUANTITY_DECISIONS', line.id,
                              _refs(*(x.source for x in line_decisions))))
            unassessed += 1
            continue
        approved_qty = billed_qty
        decision_evidence = []
        if billed_qty > receipt_qty and not line_decisions:
            holds.append(Hold('BILLING_EXCEEDS_RECEIPT_UNRESOLVED', line.id, (line.source,)))
            unassessed += 1
            continue
        if line_decisions:
            decision = line_decisions[0]
            if decision.decision_date > batch.scope.as_of:
                holds.append(Hold('QUANTITY_DECISION_OUTSIDE_SNAPSHOT', line.id, (decision.source,)))
                unassessed += 1
                continue
            decided = to_price_quantity(quantity=decision.quantity, from_unit=decision.unit,
                                        authority=authority, when=decision.decision_date,
                                        conversions=conversions, record_id=line.id,
                                        scope=line.scope, product_id=line.product_id)
            if isinstance(decided, Hold):
                holds.append(decided)
                unassessed += 1
                continue
            decided_qty, decision_conversion_refs = decided
            if decided_qty > receipt_qty:
                holds.append(Hold('QUANTITY_DECISION_EXCEEDS_RECEIPT', line.id, (decision.source,)))
                unassessed += 1
                continue
            approved_qty = min(billed_qty, decided_qty)
            decision_evidence.extend((decision.source, *decision_conversion_refs))
        expected = extend_price(parse_decimal(authority.unit_price), approved_qty, authority.rounding)
        if expected > line.amount_cents and not line.unsupported_components:
            # Underbilling is recorded as zero candidate, never a recovery amount.
            pass
        gross = max(0, line.amount_cents - expected)
        evidence = _refs(line.source, product.source, authority.source,
                         *invoice_conversions, *receipt_evidence, *decision_evidence)
        findings.append(Finding(
            economic_loss_id=loss_id(line), scope=line.scope, invoice_line_id=line.id,
            billed_cents=line.amount_cents, expected_cents=expected, paid_cents=0,
            return_entitlement_cents=0, gross_price_variance_cents=gross,
            payment_above_invoice_cents=0, funded_exposure_cents=0,
            net_issued_credit_cents=0, applied_credit_cents=0, refunded_credit_cents=0,
            remaining_candidate_cents=0, issued_unapplied_cents=0,
            unpaid_discrepancy_cents=gross, simulated_new_realized_cents=0,
            evidence=evidence,
            trace=(('source_invoice_amount_cents', str(line.amount_cents)),
                   ('contract_price', authority.unit_price), ('price_quantity', str(approved_qty)),
                   ('contract_id', authority.id), ('contract_date_basis', authority.date_basis),
                   ('expected_cents', str(expected)), ('gross_price_variance_cents', str(gross))),
        ))
    findings.sort(key=lambda x: x.economic_loss_id)
    holds.sort(key=lambda x: (x.code, x.record_id))
    return AuditResult(tuple(findings), tuple(holds), len(findings), unassessed,
                       skipped, batch.scope.synthetic, batch.import_batch.original_hash,
                       batch.import_batch.normalized_hash)
