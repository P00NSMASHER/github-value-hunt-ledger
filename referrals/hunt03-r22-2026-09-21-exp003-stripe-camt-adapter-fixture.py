"""Synthetic Stripe-payout -> CAMT.053 bank-observation adapter for EXP-003.

This is a format-level acceptance fixture, not a live Stripe or bank test.  A
provider payout is money-final only when one unique, booked credit in a
scope-complete independent statement window matches the provider reference,
amount, currency, account, and bounded value-date contract.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
import hashlib
import json
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class ProviderPayout:
    payout_id: str = "po_fixture_001"
    status: str = "paid"
    amount_minor: int = 10_000
    currency: str = "USD"
    arrival_date: str = "2026-09-18"
    destination_account: str = "acct-bank-001"
    trace_status: str = "AVAILABLE"
    trace_value: str | None = "TRACE-000001"
    reversed_by: str | None = None


@dataclass(frozen=True)
class BankEntry:
    account_id: str = "acct-bank-001"
    reference: str = "TRACE-000001"
    amount: str = "100.00"
    currency: str = "USD"
    value_date: str = "2026-09-18"
    direction: str = "CRDT"
    status: str = "BOOK"


@dataclass(frozen=True)
class CoverageReceipt:
    state: str = "VERIFIED_WINDOW"
    account_ids: tuple[str, ...] = ("acct-bank-001",)
    all_pages_complete: bool = True
    durable_commit_ok: bool = True


def camt_document(entries: tuple[BankEntry, ...]) -> str:
    body = []
    for entry in entries:
        body.append(
            f"""<Ntry>
  <Amt Ccy="{entry.currency}">{entry.amount}</Amt>
  <CdtDbtInd>{entry.direction}</CdtDbtInd>
  <Sts>{entry.status}</Sts>
  <ValDt><Dt>{entry.value_date}</Dt></ValDt>
  <Acct><Id><Othr><Id>{entry.account_id}</Id></Othr></Id></Acct>
  <NtryDtls><TxDtls><Refs><AcctSvcrRef>{entry.reference}</AcctSvcrRef></Refs></TxDtls></NtryDtls>
</Ntry>"""
        )
    return "<Document><BkToCstmrStmt><Stmt>" + "".join(body) + "</Stmt></BkToCstmrStmt></Document>"


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _desc_text(node: ET.Element, name: str) -> str:
    for child in node.iter():
        if _local(child.tag) == name and child.text:
            return child.text.strip()
    return ""


def parse_camt(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    rows = []
    for entry in root.iter():
        if _local(entry.tag) != "Ntry":
            continue
        amount_node = next(
            (child for child in entry.iter() if _local(child.tag) == "Amt"), None
        )
        rows.append(
            {
                "account_id": _desc_text(entry, "Id"),
                "reference": _desc_text(entry, "AcctSvcrRef"),
                "amount": Decimal(amount_node.text.strip()) if amount_node is not None else None,
                "currency": amount_node.attrib.get("Ccy", "").upper() if amount_node is not None else "",
                "value_date": _desc_text(entry, "Dt"),
                "direction": _desc_text(entry, "CdtDbtInd"),
                "status": _desc_text(entry, "Sts"),
            }
        )
    return rows


def _coverage_authoritative(coverage: CoverageReceipt, payout: ProviderPayout) -> bool:
    return (
        coverage.state == "VERIFIED_WINDOW"
        and coverage.all_pages_complete
        and coverage.durable_commit_ok
        and payout.destination_account in coverage.account_ids
    )


def reconcile(
    payout: ProviderPayout,
    camt_xml: str,
    coverage: CoverageReceipt = CoverageReceipt(),
    date_tolerance_days: int = 5,
) -> dict:
    rows = parse_camt(camt_xml)
    base = {
        "payout_id": payout.payout_id,
        "provider_status": payout.status,
        "trace_value": payout.trace_value,
        "observed_entry_count": len(rows),
        "matched_entry_count": 0,
        "settlement_current": False,
    }

    if payout.status in {"failed", "canceled"} or payout.reversed_by:
        return base | {"state": "REVOKED_PROVIDER", "reason": "provider_counter_event"}
    if payout.status != "paid":
        return base | {"state": "PENDING_PROVIDER", "reason": "provider_not_paid"}
    if payout.trace_status != "AVAILABLE" or not payout.trace_value:
        return base | {"state": "PENDING_REFERENCE", "reason": "trace_not_available"}
    if not _coverage_authoritative(coverage, payout):
        return base | {"state": "UNKNOWN_SOURCE", "reason": "bank_coverage_not_authoritative"}

    expected_amount = Decimal(payout.amount_minor) / Decimal(100)
    arrival = date.fromisoformat(payout.arrival_date)
    candidates = []
    for row in rows:
        if row["reference"] != payout.trace_value:
            continue
        if row["account_id"] != payout.destination_account:
            continue
        if row["amount"] != expected_amount or row["currency"] != payout.currency.upper():
            continue
        if row["direction"] != "CRDT" or row["status"] != "BOOK":
            continue
        try:
            distance = abs((date.fromisoformat(row["value_date"]) - arrival).days)
        except ValueError:
            continue
        if distance <= date_tolerance_days:
            candidates.append(row)

    base["matched_entry_count"] = len(candidates)
    if not candidates:
        return base | {"state": "NOT_FOUND", "reason": "no_exact_bank_observation"}
    if len(candidates) > 1:
        return base | {"state": "AMBIGUOUS", "reason": "multiple_exact_bank_observations"}
    return base | {
        "state": "SETTLED_BANK_OBSERVED",
        "reason": "unique_exact_independent_observation",
        "settlement_current": True,
    }


BASE_ENTRY = BankEntry()
WRONG_REFERENCE_ENTRY = replace(BASE_ENTRY, reference="TRACE-OTHER")


CASES = (
    ("unique_exact", ProviderPayout(), (BASE_ENTRY,), CoverageReceipt(), "SETTLED_BANK_OBSERVED", True),
    ("provider_pending", replace(ProviderPayout(), status="pending"), (BASE_ENTRY,), CoverageReceipt(), "PENDING_PROVIDER", False),
    ("trace_pending", replace(ProviderPayout(), trace_status="PENDING", trace_value=None), (BASE_ENTRY,), CoverageReceipt(), "PENDING_REFERENCE", False),
    ("trace_unsupported", replace(ProviderPayout(), trace_status="UNSUPPORTED", trace_value=None), (BASE_ENTRY,), CoverageReceipt(), "PENDING_REFERENCE", False),
    ("provider_paid_no_bank_entry", ProviderPayout(), (), CoverageReceipt(), "NOT_FOUND", False),
    ("wrong_reference", ProviderPayout(), (WRONG_REFERENCE_ENTRY,), CoverageReceipt(), "NOT_FOUND", False),
    ("substring_collision", ProviderPayout(), (replace(BASE_ENTRY, reference="PREFIX-TRACE-000001-SUFFIX"),), CoverageReceipt(), "NOT_FOUND", False),
    ("wrong_amount", ProviderPayout(), (replace(BASE_ENTRY, amount="99.99"),), CoverageReceipt(), "NOT_FOUND", False),
    ("wrong_currency", ProviderPayout(), (replace(BASE_ENTRY, currency="EUR"),), CoverageReceipt(), "NOT_FOUND", False),
    ("wrong_account", ProviderPayout(), (replace(BASE_ENTRY, account_id="acct-bank-999"),), CoverageReceipt(), "NOT_FOUND", False),
    ("out_of_window", ProviderPayout(), (replace(BASE_ENTRY, value_date="2026-09-30"),), CoverageReceipt(), "NOT_FOUND", False),
    ("debit_not_credit", ProviderPayout(), (replace(BASE_ENTRY, direction="DBIT"),), CoverageReceipt(), "NOT_FOUND", False),
    ("pending_not_booked", ProviderPayout(), (replace(BASE_ENTRY, status="PDNG"),), CoverageReceipt(), "NOT_FOUND", False),
    ("duplicate_exact", ProviderPayout(), (BASE_ENTRY, BASE_ENTRY), CoverageReceipt(), "AMBIGUOUS", False),
    ("bank_source_stale", ProviderPayout(), (BASE_ENTRY,), replace(CoverageReceipt(), state="STALE"), "UNKNOWN_SOURCE", False),
    ("bank_scope_partial", ProviderPayout(), (BASE_ENTRY,), replace(CoverageReceipt(), account_ids=("acct-bank-999",)), "UNKNOWN_SOURCE", False),
    ("bank_pages_incomplete", ProviderPayout(), (BASE_ENTRY,), replace(CoverageReceipt(), all_pages_complete=False), "UNKNOWN_SOURCE", False),
    ("provider_late_failed", replace(ProviderPayout(), status="failed"), (BASE_ENTRY,), CoverageReceipt(), "REVOKED_PROVIDER", False),
    ("provider_reversed", replace(ProviderPayout(), reversed_by="po_reversal_001"), (BASE_ENTRY,), CoverageReceipt(), "REVOKED_PROVIDER", False),
    ("aggregate_equal_wrong_identity", ProviderPayout(), (WRONG_REFERENCE_ENTRY,), CoverageReceipt(), "NOT_FOUND", False),
)


def unsafe_provider_paid_is_final(payout, xml, coverage):
    if payout.status == "paid":
        return {"state": "SETTLED_BANK_OBSERVED", "settlement_current": True}
    return reconcile(payout, xml, coverage)


def unsafe_trace_substring(payout, xml, coverage):
    rows = parse_camt(xml)
    if payout.trace_value and any(payout.trace_value in row["reference"] for row in rows):
        return {"state": "SETTLED_BANK_OBSERVED", "settlement_current": True}
    return reconcile(payout, xml, coverage)


def unsafe_trace_only_first_match(payout, xml, coverage):
    rows = parse_camt(xml)
    if payout.trace_value and any(row["reference"] == payout.trace_value for row in rows):
        return {"state": "SETTLED_BANK_OBSERVED", "settlement_current": True}
    return reconcile(payout, xml, coverage)


def unsafe_amount_only(payout, xml, coverage):
    target = Decimal(payout.amount_minor) / Decimal(100)
    if any(row["amount"] == target and row["currency"] == payout.currency for row in parse_camt(xml)):
        return {"state": "SETTLED_BANK_OBSERVED", "settlement_current": True}
    return reconcile(payout, xml, coverage)


def mismatches(fn) -> list[str]:
    failures = []
    for name, payout, entries, coverage, expected_state, expected_final in CASES:
        result = fn(payout, camt_document(entries), coverage)
        if (result["state"], result["settlement_current"]) != (expected_state, expected_final):
            failures.append(name)
    return failures


def run_fixture() -> dict:
    assert not mismatches(reconcile)
    killed = {
        "provider_paid_equals_bank_finality": mismatches(unsafe_provider_paid_is_final),
        "substring_reference_match": mismatches(unsafe_trace_substring),
        "trace_only_first_match": mismatches(unsafe_trace_only_first_match),
        "amount_currency_only_match": mismatches(unsafe_amount_only),
    }
    assert all(killed.values())

    initial = reconcile(ProviderPayout(), camt_document((BASE_ENTRY,)))
    late_failure = reconcile(
        replace(ProviderPayout(), status="failed"), camt_document((BASE_ENTRY,))
    )
    assert initial["settlement_current"] is True
    assert late_failure["settlement_current"] is False
    assert initial["state"] == "SETTLED_BANK_OBSERVED"
    assert late_failure["state"] == "REVOKED_PROVIDER"

    results = []
    for name, payout, entries, coverage, _, _ in CASES:
        result = reconcile(payout, camt_document(entries), coverage)
        results.append({"case": name, "state": result["state"], "settlement_current": result["settlement_current"]})
    body = {
        "case_count": len(CASES),
        "case_failures": 0,
        "mutants_killed": {name: cases for name, cases in killed.items()},
        "late_provider_failure_revokes_current_finality": "PASS",
        "results": results,
    }
    body["result_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return body


if __name__ == "__main__":
    print(json.dumps(run_fixture(), sort_keys=True))
