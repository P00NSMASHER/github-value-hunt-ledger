"""Mission 10: synthetic-only invoice evidence chain and blinded-label rehearsal.

This is a new capability inside EXISTING Lab 14, not an independent audit,
legal opinion, payment verification, customer-source importer or third-party
invoice corpus. Every case, authority, document, payment and reviewer is invented.
No network calls, secrets, live customer data, external claims or bank actions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re

from freight.research_evidence_gate import canon_hash
from freight.research_validation_protocols import build_protocol_report

SCOPE = "LAB14_SYNTHETIC_ONLY_GROUND_TRUTH_INSTRUMENT"
DATA_ORIGIN = "AUTHOR_WRITTEN_FICTITIOUS_INVOICES_NOT_CUSTOMER_OR_VENDOR_DATA"
CASE_IDS = tuple(f"SYN-GT-{n:02d}" for n in range(1, 11))
ROLES = {"INVOICE", "SHIPMENT", "RATE_AUTHORITY", "PAYMENT_LEDGER"}
VOTES = {"EXCESS_BILLING", "DUPLICATE_PAYMENT", "NO_DIFFERENCE",
         "INSUFFICIENT_EVIDENCE"}
EVENT_TYPES = {"PAYMENT", "REFUND", "CARRIER_CREDIT"}
PKG_FIELDS = {
    "case_id", "shipment_id", "invoice_id", "carrier_code", "currency", "shipment_on",
    "invoice_on", "invoice_cents", "expected_cents", "claim_category",
    "authority", "documents", "payment_events", "reviewers", "synthetic_only",
    "buyer_data_rights_verified", "external_claim_authorized",
}
DOC_FIELDS = {"id", "case_id", "role", "body", "body_sha256"}
PAYMENT_FIELDS = {"event_id", "invoice_id", "kind", "posted_on",
                  "amount_cents", "currency", "source_document_id"}
AUTHORITY_FIELDS = {"id", "source_document_id", "carrier_code", "effective_on",
                    "expires_on", "kind", "currency", "real_contract_applicability_established"}
REVIEWER_FIELDS = {"reviewer_id", "finding", "blinded", "real_person",
                   "saw_other_vote", "evidence_document_ids"}
ROOT = Path(__file__).resolve().parent


def _day(raw: object) -> date:
    if type(raw) is not str:
        raise ValueError("ISO date string required")
    parsed = date.fromisoformat(raw)
    if raw != parsed.isoformat():
        raise ValueError("noncanonical date")
    return parsed


def _digest(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _doc(cid: str, role: str, body: str, suffix: str) -> dict:
    return {"id": cid + "-" + suffix, "case_id": cid, "role": role,
            "body": body, "body_sha256": _digest(body)}


def _invoice_body(p: dict) -> str:
    return ("FICTITIOUS invoice=" + p["invoice_id"] +
            "; shipment=" + p["shipment_id"] +
            "; invoice_cents=" + str(p["invoice_cents"]) +
            "; currency=" + p["currency"])


def _shipment_body(p: dict) -> str:
    return ("FICTITIOUS shipment=" + p["shipment_id"] +
            "; carrier=" + p["carrier_code"] +
            "; shipped=" + p["shipment_on"])


def _authority_body(p: dict) -> str:
    a = p["authority"]
    return ("FICTITIOUS rate=" + a["id"] +
            "; carrier=" + a["carrier_code"] +
            "; starts=" + a["effective_on"] +
            "; ends=" + a["expires_on"] +
            "; expected_cents=" + str(p["expected_cents"]) +
            "; currency=" + a["currency"])


def _payment_body(event: dict) -> str:
    return ("FICTITIOUS event=" + event["event_id"] +
            "; invoice=" + event["invoice_id"] +
            "; kind=" + event["kind"] +
            "; amount_cents=" + str(event["amount_cents"]) +
            "; posted=" + event["posted_on"] +
            "; currency=" + event["currency"])


def _build_case(index: int, *, invoice: int, expected: int | None,
                paid: tuple[tuple[str, int], ...],
                label1: str, label2: str | None = None,
                effective: str = "2026-01-01",
                expires: str = "2026-12-31",
                authority_carrier: str = "SYN-CARRIER-A") -> dict:
    """Construct local mock documents with hashes, never external attestations."""
    cid = CASE_IDS[index - 1]
    pkt = {
        "case_id": cid, "shipment_id": f"SYN-SHIP-{index:02d}",
        "invoice_id": f"SYN-INV-{index:02d}",
        "carrier_code": "SYN-CARRIER-A", "currency": "USD",
        "shipment_on": "2026-02-01", "invoice_on": "2026-02-02",
        "invoice_cents": invoice, "expected_cents": expected,
        "claim_category": "DUPLICATE_PAYMENT" if index == 3 else "BILLING_REVIEW",
        "authority": None, "documents": [], "payment_events": [],
        "reviewers": [], "synthetic_only": True,
        "buyer_data_rights_verified": False, "external_claim_authorized": False,
    }
    docs = [
        _doc(cid, "INVOICE", _invoice_body(pkt), "DOC-INVOICE"),
        _doc(cid, "SHIPMENT", _shipment_body(pkt), "DOC-SHIPMENT"),
    ]
    if expected is not None:
        pkt["authority"] = {
            "id": cid + "-RATE", "source_document_id": cid + "-DOC-RATE",
            "carrier_code": authority_carrier,
            "effective_on": effective, "expires_on": expires,
            "kind": "INVENTED_RATE_NOTE", "currency": "USD",
            "real_contract_applicability_established": False,
        }
        docs.append(_doc(cid, "RATE_AUTHORITY", _authority_body(pkt), "DOC-RATE"))
    for n, (kind, amount) in enumerate(paid, 1):
        event = {
            "event_id": f"{cid}-EVENT-{n}", "invoice_id": pkt["invoice_id"],
            "kind": kind, "posted_on": f"2026-02-{10 + n:02d}",
            "amount_cents": amount, "currency": "USD",
            "source_document_id": f"{cid}-DOC-PAY-{n}",
        }
        pkt["payment_events"].append(event)
        docs.append(_doc(cid, "PAYMENT_LEDGER", _payment_body(event),
                         f"DOC-PAY-{n}"))
    pkt["documents"] = docs
    # Blind reviewers must receive the source payment/credit events too;
    # the simulated disagreement is independent of any engine alert.
    available_docs = [d["id"] for d in docs]
    for n, finding in enumerate((label1, label1 if label2 is None else label2), 1):
        pkt["reviewers"].append({
            "reviewer_id": f"FICTIONAL-REVIEWER-{n}", "finding": finding,
            "blinded": True, "real_person": False, "saw_other_vote": False,
            "evidence_document_ids": available_docs,
        })
    return pkt


def invented_fixture_book() -> dict:
    """Complete made-up fixtures: successes, legitimate negatives and hard holds."""
    cases = [
        _build_case(1, invoice=15000, expected=12000,
                    paid=(("PAYMENT", 15000),), label1="EXCESS_BILLING"),
        _build_case(2, invoice=12000, expected=12000,
                    paid=(("PAYMENT", 12000),), label1="NO_DIFFERENCE"),
        _build_case(3, invoice=10000, expected=10000,
                    paid=(("PAYMENT", 10000), ("PAYMENT", 10000)),
                    label1="DUPLICATE_PAYMENT"),
        _build_case(4, invoice=15000, expected=None,
                    paid=(("PAYMENT", 15000),), label1="INSUFFICIENT_EVIDENCE"),
        _build_case(5, invoice=16000, expected=12000,
                    paid=(("PAYMENT", 16000),), label1="EXCESS_BILLING",
                    effective="2026-03-01"),
        _build_case(6, invoice=15000, expected=12000,
                    paid=(("PAYMENT", 15000),), label1="EXCESS_BILLING",
                    label2="NO_DIFFERENCE"),
        _build_case(7, invoice=15000, expected=12000,
                    paid=(("PAYMENT", 15000), ("REFUND", 3000)),
                    label1="EXCESS_BILLING"),
        _build_case(8, invoice=15000, expected=12000,
                    paid=(), label1="EXCESS_BILLING"),
        _build_case(9, invoice=15000, expected=12000,
                    paid=(("PAYMENT", 15000),), label1="EXCESS_BILLING",
                    authority_carrier="SYN-CARRIER-OTHER"),
        _build_case(10, invoice=15000, expected=12000,
                    paid=(("PAYMENT", 15000), ("CARRIER_CREDIT", 3000)),
                    label1="EXCESS_BILLING"),
    ]
    return {
        "schema_version": 1,
        "scope": SCOPE,
        "source_kind": DATA_ORIGIN,
        "recorded_as_of": "2026-10-10",
        "synthetic_only": True,
        "actual_customer_records": 0,
        "real_invoice_ground_truth_verified": False,
        "external_data_acquisition_authorized": False,
        "claims_or_financial_actions_authorized": False,
        "cases": cases,
    }


def _issue(errors: list[str], cid: str, value: str) -> None:
    errors.append(f"{cid}: {value}")


def _is_cents(value: object) -> bool:
    return type(value) is int and 0 <= value <= 100_000_000


def validate_fixtures(book: dict, protocol: dict, *, as_of: date) -> list[str]:
    """Return integrity and admissibility failures; never authorize real use."""
    errors: list[str] = []
    if type(book) is not dict or book.get("schema_version") != 1:
        return ["invalid synthetic fixture format"]
    if set(book) != {
        "schema_version", "scope", "source_kind", "recorded_as_of",
        "synthetic_only", "actual_customer_records",
        "real_invoice_ground_truth_verified", "external_data_acquisition_authorized",
        "claims_or_financial_actions_authorized", "cases",
    }:
        errors.append("unexpected fixture fields: no real customer data allowed")
    if book.get("scope") != SCOPE or book.get("source_kind") != DATA_ORIGIN:
        errors.append("fixtures must have an invented-only provenance")
    if (book.get("synthetic_only") is not True or
        book.get("real_invoice_ground_truth_verified") is not False or
        book.get("external_data_acquisition_authorized") is not False or
        book.get("claims_or_financial_actions_authorized") is not False or
        type(book.get("actual_customer_records")) is not int or
        book["actual_customer_records"] != 0):
        errors.append("forbidden real-world authority or outcome promotion")
    try:
        if _day(book.get("recorded_as_of")) > as_of:
            errors.append("future fixture publication date")
    except ValueError:
        errors.append("invalid fixture date")
    if (type(protocol) is not dict or
        protocol.get("scope") != "LAB14_INTERNAL_STUDY_DESIGN_REVIEW_ONLY" or
        protocol.get("external_studies_executed") != 0 or
        protocol.get("observed_customer_outcomes") != 0 or
        protocol.get("approved_preregistrations") != 0 or
        protocol.get("external_actions_allowed") is not False or
        protocol.get("public_performance_claims_allowed") is not False or
        protocol.get("receipt_sha256") != canon_hash({
            k: v for k, v in protocol.items() if k != "receipt_sha256"
        })):
        return errors + ["held original protocol register required"]
    try:
        matched = {p["experiment_id"]: p for p in protocol["protocols"]}
        if len(matched) != 6 or matched["M7-01"]["study_type"] != "BLINDED_REFERENCE_ADJUDICATION" or matched["M7-06"]["study_type"] != "RECONCILED_COHORT_ACCOUNTING":
            errors.append("preregistered study method mismatch")
    except (KeyError, TypeError, ValueError):
        errors.append("malformed research study dependencies")
    cases = book.get("cases")
    if type(cases) is not list or len(cases) != 10:
        return errors + ["ten fixed invented cases required"]
    observed_cases: set[str] = set()
    observed_invoice: set[str] = set()
    observed_shipment: set[str] = set()
    doc_ids_global: set[str] = set()
    event_ids_global: set[str] = set()
    for index, p in enumerate(cases, 1):
        if type(p) is not dict or set(p) != PKG_FIELDS:
            _issue(errors, str(index), "unexpected/missing fields or non-object case")
            continue
        cid = p.get("case_id")
        if type(cid) is not str or cid not in CASE_IDS or cid in observed_cases:
            _issue(errors, str(index), "duplicate or non-synthetic case identifier")
            continue
        observed_cases.add(cid)
        if (p.get("shipment_id") != cid.replace("SYN-GT", "SYN-SHIP") or
            p.get("invoice_id") != cid.replace("SYN-GT", "SYN-INV")):
            _issue(errors, cid, "invoice and shipment identities must be fictional and bound")
        for field, seen in (("invoice_id", observed_invoice),
                            ("shipment_id", observed_shipment)):
            value = p.get(field)
            if type(value) is not str or value in seen:
                _issue(errors, cid, "duplicate or invalid " + field)
            else:
                seen.add(value)
        if p.get("synthetic_only") is not True or p.get("buyer_data_rights_verified") is not False or p.get("external_claim_authorized") is not False:
            _issue(errors, cid, "real-world authority flag forbidden")
        if p.get("currency") != "USD":
            _issue(errors, cid, "mixed/unsupported invoice currency")
        if p.get("carrier_code") != "SYN-CARRIER-A":
            _issue(errors, cid, "unexpected real/other carrier")
        if p.get("claim_category") not in {"BILLING_REVIEW", "DUPLICATE_PAYMENT"}:
            _issue(errors, cid, "cargo loss/damage or unsupported claim category")
        for key in ("invoice_cents",):
            if not _is_cents(p.get(key)):
                _issue(errors, cid, "invalid exact integer invoice cents")
        if p.get("expected_cents") is not None and not _is_cents(p["expected_cents"]):
            _issue(errors, cid, "invalid expected rate cents")
        try:
            ship = _day(p.get("shipment_on"))
            issued = _day(p.get("invoice_on"))
            if issued < ship or issued > as_of:
                _issue(errors, cid, "noncausal/future invoice chronology")
        except ValueError:
            _issue(errors, cid, "invalid shipment/invoice dates")
            ship = None
            issued = None
        authority = p.get("authority")
        if authority is None:
            if p.get("expected_cents") is not None:
                _issue(errors, cid, "numeric expected rate without authority document")
        elif type(authority) is not dict or set(authority) != AUTHORITY_FIELDS:
            _issue(errors, cid, "invalid rate authority contract schema")
            authority = None
        else:
            if (authority.get("id") != cid + "-RATE" or
                authority.get("source_document_id") != cid + "-DOC-RATE" or
                authority.get("kind") != "INVENTED_RATE_NOTE" or
                authority.get("currency") != "USD" or
                authority.get("real_contract_applicability_established") is not False):
                _issue(errors, cid, "fake external rate document authority")
            if authority.get("carrier_code") not in {
                "SYN-CARRIER-A", "SYN-CARRIER-OTHER"
            }:
                _issue(errors, cid, "invalid fictional rate carrier")
            if p.get("expected_cents") is None:
                _issue(errors, cid, "rate authority without expected amount")
            try:
                effective = _day(authority.get("effective_on"))
                expires = _day(authority.get("expires_on"))
                if expires < effective:
                    _issue(errors, cid, "inverted authority version interval")
            except ValueError:
                _issue(errors, cid, "invalid dated rate interval")
        docs = p.get("documents")
        if type(docs) is not list or not 2 <= len(docs) <= 10:
            _issue(errors, cid, "bounded document set required")
            continue
        by_doc = {}
        for d in docs:
            if type(d) is not dict or set(d) != DOC_FIELDS:
                _issue(errors, cid, "unknown or malformed document; no private fields")
                continue
            did = d.get("id")
            role = d.get("role")
            if (type(did) is not str or not did.startswith(cid + "-DOC-") or
                did in doc_ids_global or did in by_doc):
                _issue(errors, cid, "duplicate/cross-tenant document id")
                continue
            doc_ids_global.add(did)
            by_doc[did] = d
            if d.get("case_id") != cid or role not in ROLES:
                _issue(errors, cid, "document role/case provenance mismatch")
            body = d.get("body")
            if (type(body) is not str or len(body) > 350 or
                not body.startswith("FICTITIOUS ") or
                d.get("body_sha256") != _digest(body)):
                _issue(errors, cid, "document content not synthetic or hash mismatched")
        expected_bodies = {
            cid + "-DOC-INVOICE": ("INVOICE", _invoice_body(p)) if _is_cents(p.get("invoice_cents")) else None,
            cid + "-DOC-SHIPMENT": ("SHIPMENT", _shipment_body(p)) if type(p.get("shipment_on")) is str else None,
        }
        if authority and p.get("expected_cents") is not None and _is_cents(p["expected_cents"]):
            expected_bodies[cid + "-DOC-RATE"] = ("RATE_AUTHORITY", _authority_body(p))
        if authority is None and cid + "-DOC-RATE" in by_doc:
            _issue(errors, cid, "orphan future/unknown authority document")
        events = p.get("payment_events")
        if type(events) is not list or len(events) > 5:
            _issue(errors, cid, "bounded payment events list required")
            continue
        payment_cents = 0
        refund_cents = 0
        for n, e in enumerate(events, 1):
            if type(e) is not dict or set(e) != PAYMENT_FIELDS:
                _issue(errors, cid, "payment event schema invalid")
                continue
            eid = e.get("event_id")
            if (type(eid) is not str or eid != f"{cid}-EVENT-{n}" or
                eid in event_ids_global):
                _issue(errors, cid, "duplicated/misbound financial event")
            else:
                event_ids_global.add(eid)
            if e.get("currency") != "USD":
                _issue(errors, cid, "mixed/unsupported cash event currency")
            if e.get("invoice_id") != p.get("invoice_id") or e.get("source_document_id") != f"{cid}-DOC-PAY-{n}":
                _issue(errors, cid, "payment source/invoice link mismatch")
            if e.get("kind") not in EVENT_TYPES or not _is_cents(e.get("amount_cents")) or e.get("amount_cents") == 0:
                _issue(errors, cid, "unsupported money event; positive integer cents required")
            else:
                if e["kind"] == "PAYMENT":
                    payment_cents += e["amount_cents"]
                elif e["kind"] == "REFUND":
                    refund_cents += e["amount_cents"]
            try:
                posted = _day(e.get("posted_on"))
                if issued is not None and posted < issued or posted > as_of:
                    _issue(errors, cid, "financial event predates invoice/future")
            except ValueError:
                _issue(errors, cid, "invalid money event date")
            if _is_cents(e.get("amount_cents")) and type(e.get("kind")) is str and type(e.get("posted_on")) is str:
                expected_bodies[f"{cid}-DOC-PAY-{n}"] = ("PAYMENT_LEDGER", _payment_body(e))
        if refund_cents > payment_cents:
            _issue(errors, cid, "refund larger than cash receipts")
        for did, expectation in expected_bodies.items():
            d = by_doc.get(did)
            if expectation is None or not d or (d.get("role"), d.get("body")) != expectation:
                _issue(errors, cid, "missing/mismatched source-bound " + did)
        if set(by_doc) != set(expected_bodies):
            _issue(errors, cid, "orphan or extra document; no silently ignored evidence")
        reviews = p.get("reviewers")
        if type(reviews) is not list or len(reviews) != 2:
            _issue(errors, cid, "two blinded fictional reviewer votes required")
            continue
        referenced = set(expected_bodies)
        for n, review in enumerate(reviews, 1):
            if type(review) is not dict or set(review) != REVIEWER_FIELDS:
                _issue(errors, cid, "blind-review schema invalid")
                continue
            if review.get("reviewer_id") != f"FICTIONAL-REVIEWER-{n}":
                _issue(errors, cid, "reviewer identity duplicate or forged")
            if review.get("finding") not in VOTES:
                _issue(errors, cid, "unsupported independent vote")
            if review.get("blinded") is not True or review.get("real_person") is not False or review.get("saw_other_vote") is not False:
                _issue(errors, cid, "reviewer not blinded or fictitious")
            ids = review.get("evidence_document_ids")
            if (type(ids) is not list or len(ids) != len(set(map(str, ids))) or
                any(type(x) is not str or x not in referenced for x in ids) or
                not set(expected_bodies) <= set(ids)):
                _issue(errors, cid, "orphan or missing documented reviewer evidence")
    if observed_cases != set(CASE_IDS):
        errors.append("ten-case inventory missing or duplicated")
    # The frozen fixture generator, not a user-supplied license or untrusted
    # external row, is the only accepted source for this test-only cohort.
    if not errors and canon_hash(book) != canon_hash(invented_fixture_book()):
        errors.append("fixture drift from locked invented case definitions")
    return errors


# The public entry point catches malformed JSON field types; validation
# failures are reported as holds, never used for a successful calculation.
_validate_fixture_book_inner = validate_fixtures


def validate_fixtures(book: dict, protocol: dict, *, as_of: date) -> list[str]:
    try:
        return _validate_fixture_book_inner(book, protocol, as_of=as_of)
    except (TypeError, ValueError, AttributeError, KeyError, OverflowError):
        return ["malformed nested synthetic fixture rejected"]


def _assess_case(p: dict) -> dict:
    """Compute arithmetic separately from mock review; no legal determination."""
    invoice = p["invoice_cents"]
    expected = p["expected_cents"]
    payments = sum(e["amount_cents"] for e in p["payment_events"]
                   if e["kind"] == "PAYMENT")
    refunds = sum(e["amount_cents"] for e in p["payment_events"]
                  if e["kind"] == "REFUND")
    credits = sum(e["amount_cents"] for e in p["payment_events"]
                  if e["kind"] == "CARRIER_CREDIT")
    net_paid = payments - refunds
    outstanding_paid_excess = max(0, net_paid - expected) if expected is not None else None
    billed_difference = max(0, invoice - expected) if expected is not None else None
    votes = [x["finding"] for x in p["reviewers"]]
    reason = ""
    a = p["authority"]
    if a is None or expected is None:
        status, reason = "HOLD_NO_CONTROLLING_AUTHORITY", "Expected charge cannot be independently reconstructed."
    elif a["carrier_code"] != p["carrier_code"]:
        status, reason = "HOLD_CARRIER_SCOPE_MISMATCH", "Fictional rate record belongs to a different carrier."
    elif not _day(a["effective_on"]) <= _day(p["shipment_on"]) <= _day(a["expires_on"]):
        status, reason = "HOLD_RATE_EFFECTIVE_DATE", "Shipment falls outside asserted fictional authority interval."
    elif votes[0] != votes[1]:
        status, reason = "HOLD_BLIND_REVIEW_DISAGREEMENT", "Independent fictional reviewers disagree; no majority inference."
    elif votes[0] == "INSUFFICIENT_EVIDENCE":
        status, reason = "HOLD_REVIEWER_ABSTENTION", "Neither reviewer assigned a resolved label."
    elif p["claim_category"] == "DUPLICATE_PAYMENT":
        if (invoice == expected and payments > invoice and
            sum(e["kind"] == "PAYMENT" for e in p["payment_events"]) > 1 and
            votes[0] == "DUPLICATE_PAYMENT"):
            status, reason = "SYNTHETIC_DUPLICATE_PAYMENT_CANDIDATE", "Multiple fictional receipts exceed one billed charge."
        else:
            status, reason = "HOLD_DUPLICATE_PAYMENT_CONTRADICTION", "Payment events or reviewer vote do not support duplication."
    elif billed_difference is not None and billed_difference > 0:
        if votes[0] != "EXCESS_BILLING":
            status, reason = "HOLD_REVIEW_LABEL_ARITHMETIC_CONFLICT", "Blind mock label contradicts declared cents."
        elif not payments:
            status, reason = "SYNTHETIC_UNPAID_BILLING_DIFFERENCE", "Billed amount exceeds expected; zero simulated paid cash."
        elif credits:
            status, reason = "HOLD_CREDIT_NOT_CASH_RECONCILIATION", "Carrier credit is not documented as a cash refund."
        elif net_paid <= expected:
            status, reason = "SYNTHETIC_PRIOR_REFUND_NO_REMAINING_CASH_EXCESS", "Previously refunded fictional cash offsets price difference."
        else:
            status, reason = "SYNTHETIC_PAID_NUMERIC_DIFFERENCE_CANDIDATE", "Mock invoice and dated rate agree on excess paid amount."
    elif (billed_difference == 0 and net_paid == expected and
          votes[0] == "NO_DIFFERENCE"):
        status, reason = "SYNTHETIC_NO_DISCREPANCY_CONTROL", "Mock billed/rate/paid values agree."
    else:
        status, reason = "HOLD_UNSUPPORTED_ADJUDICATION", "Neither arithmetic nor fictional votes establish a consistent result."
    return {
        "case_id": p["case_id"], "status": status, "reason": reason,
        "claim_category": p["claim_category"],
        "invoice_cents_fictional": invoice,
        "expected_cents_fictional": expected,
        "billed_difference_cents_fictional": billed_difference,
        "gross_payment_cents_fictional": payments,
        "refund_cents_fictional": refunds,
        "carrier_credit_not_cash_cents_fictional": credits,
        "net_cash_paid_cents_fictional": net_paid,
        "cash_above_mock_expected_cents_not_a_refund_right": outstanding_paid_excess,
        "reviewer_votes": votes,
        "evidence_document_sha256": {d["id"]: d["body_sha256"]
                                      for d in p["documents"]},
        "independent_real_world_truth": False,
        "money_recovered_cents": 0,
        "customer_claim_authorized": False,
    }


def run_ground_truth(*, as_of: date, book: dict | None = None,
                     protocols: dict | None = None) -> dict:
    if book is None:
        book = invented_fixture_book()
    if protocols is None:
        protocols = build_protocol_report(as_of=as_of)
    issues = validate_fixtures(book, protocols, as_of=as_of)
    if issues:
        raise ValueError("INVALID_SYNTHETIC_GROUND_TRUTH: " + "; ".join(issues))
    results = [_assess_case(p) for p in book["cases"]]
    statuses = dict(sorted(Counter(x["status"] for x in results).items()))
    result = {
        "schema_version": 1, "scope": "LAB14_GROUND_TRUTH_INSTRUMENT_ONLY",
        "as_of": as_of.isoformat(), "case_count": len(results),
        "source_data_origin": DATA_ORIGIN,
        "fixture_sha256": canon_hash(book),
        "study_design_sha256": protocols["receipt_sha256"],
        "case_status_counts": statuses,
        "cases": results,
        "external_invoice_data_admitted": False,
        "real_customer_cases": 0,
        "verified_ground_truth_cases": 0,
        "actual_cash_recovered_cents": 0,
        "external_actions_allowed": False,
        "legal_applicability_established": False,
        "approved_public_performance_benchmark": False,
        "synthetic_only": True,
        "new_lab_created": False, "existing_lab_number": 14,
        "limits": ("Every evidence document, numeric rate, payment and reviewer is "
                   "invented. A SHA-256 digest checks local bytes only. No shipper "
                   "authorization, controlling contract, real bank settlement, "
                   "regulatory applicability or independent accuracy is verified."),
    }
    result["receipt_sha256"] = canon_hash(result)
    return result


def render_html(result: dict) -> str:
    cards = []
    for row in result["cases"]:
        cards.append(
            '<article><small>' + escape(row["case_id"]) + ' · FICTIONAL</small>'
            '<h2>' + escape(row["status"].replace("_", " ")) + '</h2><p>' +
            escape(row["reason"]) +
            '</p><p>Fictional invoice / expected (cents): ' +
            str(row["invoice_cents_fictional"]) + ' / ' +
            escape(str(row["expected_cents_fictional"])) +
            '</p><p>Mock paid / refunds / carrier credit (cents): ' +
            str(row["gross_payment_cents_fictional"]) + ' / ' +
            str(row["refund_cents_fictional"]) + ' / ' +
            str(row["carrier_credit_not_cash_cents_fictional"]) +
            '</p><p>Mock review votes: ' +
            escape(", ".join(row["reviewer_votes"])) + '</p></article>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Synthetic Invoice Truth</title><style>'
        '*{box-sizing:border-box}body{background:#f6f9f7;color:#18352c;'
        'font:15px/1.6 system-ui,-apple-system,sans-serif;margin:0}'
        'main{max-width:1050px;margin:auto;padding:30px 18px 68px}'
        'h1{font-size:clamp(31px,5vw,50px);letter-spacing:-.045em;line-height:1.1}'
        'article{background:white;border:1px solid #dbe8df;'
        'border-radius:15px;padding:22px;margin:18px 0}'
        'small{font-size:12px;letter-spacing:.09em;color:#557363}'
        'h2{font-size:19px;line-height:1.3}p{overflow-wrap:anywhere}'
        '</style></head><body><main><small>RETALLY / EXISTING LAB 14 / '
        'MISSION 10 / ALL DATA INVENTED</small><h1>Do not confuse an alert '
        'with a proven refund.</h1><p>Ten wholly fictional invoice evidence '
        'chains test date authority, gross vs net cash, duplicate payment, '
        'blind disagreements and already-paid refunds. <b>There are zero '
        'real invoice adjudications and zero verified recoveries.</b></p>' +
        "".join(cards) + '<footer><small>Local fixture checksum only: ' +
        escape(result["receipt_sha256"]) + '</small></footer></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", type=date.fromisoformat,
                        default=date.today())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run_ground_truth(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "invoice_ground_truth.json").write_text(
        json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.out / "invoice_ground_truth.html").write_text(
        render_html(result), encoding="utf-8")
    print(json.dumps({"cases": result["case_count"],
                      "real_adjudications": result["verified_ground_truth_cases"],
                      "customer_refunds_cents": result["actual_cash_recovered_cents"],
                      "receipt": result["receipt_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
