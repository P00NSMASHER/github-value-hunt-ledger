"""Generate a conservative buyer-visible Recovery Evidence Pack.

This module formats already-reviewed evidence. It does not discover findings,
authorize claims, or manufacture settlement truth.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

VALID_DISPOSITIONS = {"VALIDATED", "REJECTED", "REVIEW"}
VALID_AUTH = {"NOT_REQUESTED", "PENDING", "AUTHORIZED", "DECLINED"}
VALID_CLAIM = {"NOT_SUBMITTED", "SUBMITTED", "PENDING", "APPROVED", "DENIED", "CLOSED"}
VALID_CONFIDENCE = {"SUPPORTED", "REVIEW", "INSUFFICIENT"}
SUPPRESSION_FLAGS = ("incumbent_known", "automatic_credit", "preexisting_claim", "duplicate_opportunity")


def money(cents):
    return ("-" if cents < 0 else "") + "$" + f"{abs(cents) / 100:,.2f}"


def require_text(row, key):
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text")
    return value.strip()


def require_cents(row, key):
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be nonnegative integer cents")
    return value


def normalize_finding(row):
    clean = dict(row)
    for key in (
        "finding_id", "invoice_id", "shipment_id", "carrier", "invoice_date",
        "authority_type", "authority_reference", "authority_effective_date",
        "finding_category", "reviewer_disposition", "confidence",
        "customer_authorization_state", "claim_status"
    ):
        clean[key] = require_text(row, key)
    for key in ("billed_cents", "expected_cents", "settled_credit_cents", "reversal_cents"):
        clean[key] = require_cents(row, key)
    if clean["reviewer_disposition"] not in VALID_DISPOSITIONS:
        raise ValueError("invalid reviewer disposition")
    if clean["customer_authorization_state"] not in VALID_AUTH:
        raise ValueError("invalid authorization state")
    if clean["claim_status"] not in VALID_CLAIM:
        raise ValueError("invalid claim status")
    if clean["confidence"] not in VALID_CONFIDENCE:
        raise ValueError("invalid confidence")
    evidence = row.get("supporting_evidence") or []
    if not isinstance(evidence, list) or not all(isinstance(x, str) and x.strip() for x in evidence):
        raise ValueError("supporting_evidence must be a list of non-empty strings")
    clean["supporting_evidence"] = evidence
    for key in SUPPRESSION_FLAGS:
        clean[key] = bool(row.get(key, False))
    clean["second_look"] = bool(row.get("second_look", False))
    clean["carrier_response"] = str(row.get("carrier_response") or "").strip()
    clean["settlement_reference"] = str(row.get("settlement_reference") or "").strip()
    clean["unresolved_issues"] = str(row.get("unresolved_issues") or "").strip()
    clean["difference_cents"] = max(clean["billed_cents"] - clean["expected_cents"], 0)
    clean["net_realized_cents"] = max(clean["settled_credit_cents"] - clean["reversal_cents"], 0)
    suppressed = (
        clean["reviewer_disposition"] != "VALIDATED"
        or clean["confidence"] != "SUPPORTED"
        or any(clean[key] for key in SUPPRESSION_FLAGS)
    )
    clean["attribution_state"] = "SUPPRESSED" if suppressed else "FREIGHT_RECOVERY_ORIGIN"
    clean["fee_eligible_realized_cents"] = clean["net_realized_cents"] if (
        not suppressed
        and clean["customer_authorization_state"] == "AUTHORIZED"
        and clean["claim_status"] in {"APPROVED", "CLOSED"}
    ) else 0
    return clean


def build_pack(payload):
    customer = require_text(payload, "customer")
    population_id = require_text(payload, "population_id")
    period = require_text(payload, "period")
    rows = payload.get("findings")
    if not isinstance(rows, list) or not rows:
        raise ValueError("findings must be a non-empty list")
    findings = [normalize_finding(row) for row in rows]
    ids = [row["finding_id"] for row in findings]
    if len(ids) != len(set(ids)):
        raise ValueError("finding_id must be unique")
    totals = {
        "findings_count": len(findings),
        "validated_count": sum(row["reviewer_disposition"] == "VALIDATED" for row in findings),
        "review_count": sum(row["reviewer_disposition"] == "REVIEW" for row in findings),
        "rejected_count": sum(row["reviewer_disposition"] == "REJECTED" for row in findings),
        "candidate_difference_cents": sum(row["difference_cents"] for row in findings),
        "validated_difference_cents": sum(
            row["difference_cents"] for row in findings
            if row["reviewer_disposition"] == "VALIDATED" and row["confidence"] == "SUPPORTED"
        ),
        "net_realized_cents": sum(row["net_realized_cents"] for row in findings),
        "fee_eligible_realized_cents": sum(row["fee_eligible_realized_cents"] for row in findings),
        "suppressed_count": sum(row["attribution_state"] == "SUPPRESSED" for row in findings),
    }
    return {
        "schema_version": 1,
        "customer": customer,
        "population_id": population_id,
        "period": period,
        "synthetic": bool(payload.get("synthetic", False)),
        "claim_boundary": {
            "potential_is_not_recovered": True,
            "validated_is_not_settled": True,
            "preexisting_and_duplicate_value_excluded": True,
            "reversals_reduce_realized_value": True,
            "fee_eligibility_requires_authorized_supported_settlement": True,
        },
        "totals": totals,
        "findings": findings,
    }


def render_markdown(pack):
    t = pack["totals"]
    label = "SYNTHETIC / FICTIONAL EXAMPLE" if pack["synthetic"] else "CUSTOMER EVIDENCE PACK"
    lines = [
        "# Freight Recovery Evidence Pack", "",
        f"> **{label}.** Potential recovery, validated findings, and actual recovered funds are separate measures.", "",
        f"- **Customer:** {pack['customer']}",
        f"- **Population:** {pack['population_id']}",
        f"- **Period:** {pack['period']}", "",
        "## Executive recovery state", "",
        f"- Findings in pack: **{t['findings_count']}**",
        f"- Validated findings: **{t['validated_count']}**",
        f"- Review / rejected: **{t['review_count']} / {t['rejected_count']}**",
        f"- Candidate difference: **{money(t['candidate_difference_cents'])}** — not recovered cash",
        f"- Validated difference: **{money(t['validated_difference_cents'])}** — not necessarily recovered",
        f"- Net realized recovery: **{money(t['net_realized_cents'])}**",
        f"- Fee-eligible realized recovery: **{money(t['fee_eligible_realized_cents'])}**",
        f"- Suppressed from Freight Recovery attribution: **{t['suppressed_count']} finding(s)**", "",
        "## Finding evidence", ""
    ]
    for row in pack["findings"]:
        lines.extend([
            f"### {row['finding_id']} — {row['finding_category']}", "",
            f"- Invoice / shipment: `{row['invoice_id']}` / `{row['shipment_id']}`",
            f"- Carrier / invoice date: {row['carrier']} / {row['invoice_date']}",
            f"- Billed / expected / difference: **{money(row['billed_cents'])} / {money(row['expected_cents'])} / {money(row['difference_cents'])}**",
            f"- Authority: {row['authority_type']} `{row['authority_reference']}` effective {row['authority_effective_date']}",
            f"- Supporting evidence: {', '.join(row['supporting_evidence'])}",
            f"- Confidence / reviewer: **{row['confidence']} / {row['reviewer_disposition']}**",
            f"- Unresolved issues: {row['unresolved_issues'] or 'None'}",
            f"- Customer authorization: **{row['customer_authorization_state']}**",
            f"- Claim status / carrier response: **{row['claim_status']}** / {row['carrier_response'] or 'None recorded'}",
            f"- Settlement reference: {row['settlement_reference'] or 'None'}",
            f"- Credit / reversal / net realized: **{money(row['settled_credit_cents'])} / {money(row['reversal_cents'])} / {money(row['net_realized_cents'])}**",
            f"- Attribution: **{row['attribution_state']}**",
            f"- Fee-eligible realized: **{money(row['fee_eligible_realized_cents'])}**", ""
        ])
    lines.extend([
        "## Interpretation rules", "",
        "1. A calculated difference is not automatically a validated finding.",
        "2. A validated finding is not automatically an approved claim.",
        "3. An approved claim is not actual recovered funds.",
        "4. Existing, automatic, incumbent-known, duplicate, or unsupported value is suppressed from Freight Recovery attribution.",
        "5. Reversals reduce realized recovery.",
        "6. Fee-eligible recovery requires supported evidence, customer authorization, and an eligible settled outcome under the engagement.", ""
    ])
    return "\n".join(lines)


def write_pack(payload_path, output_dir):
    payload = json.loads(Path(payload_path).read_text(encoding="utf-8"))
    pack = build_pack(payload)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_bytes = (json.dumps(pack, indent=2, sort_keys=True) + "\n").encode()
    markdown_bytes = (render_markdown(pack) + "\n").encode()
    (output / "RECOVERY_EVIDENCE_PACK.json").write_bytes(json_bytes)
    (output / "RECOVERY_EVIDENCE_PACK.md").write_bytes(markdown_bytes)
    receipt = {
        "schema_version": 1,
        "population_id": pack["population_id"],
        "synthetic": pack["synthetic"],
        "json_sha256": hashlib.sha256(json_bytes).hexdigest(),
        "markdown_sha256": hashlib.sha256(markdown_bytes).hexdigest(),
    }
    (output / "EVIDENCE_PACK_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("payload")
    parser.add_argument("output")
    args = parser.parse_args()
    print(json.dumps(write_pack(args.payload, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
