"""Offline, draft-only buyer review UI and strict decision import.

Browser exports are untrusted decision proposals, not signatures or authority.
The approved caller supplies current proof objects and the authenticated reviewer
role. Only the existing buyer-review workflow can issue bound FindingReviews.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from freight.buyer_review_workflow import BuyerReviewBatch
    from freight.contracts import TruthManifest
    from freight.review_packet import ReviewPacket
    from freight.review_routing import ReviewRouting

MAX_DECISION_BYTES = 1_048_576
MAX_DECISIONS = 2_000
ROOT_KEYS = frozenset({
    "schema_version", "review_packet_hash", "review_routing_hash", "truth_hash", "decisions",
})
DECISION_KEYS = frozenset({"case_hash", "disposition", "reviewer_minutes", "reviewed_at"})
TEMPLATE_PATH = Path(__file__).with_suffix(".html")


def _render_payload(payload: dict[str, Any]) -> str:
    """Render only inert JSON; evidence is never interpolated as HTML or code."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    style = re.search(r"<style>(.*?)</style>", template, re.DOTALL)
    script = re.search(r'<script id="workbench-code">(.*?)</script>', template, re.DOTALL)
    if style is None or script is None:
        raise ValueError("reviewer workbench template is incomplete")

    def digest(text: str) -> str:
        return base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii")

    # Escape HTML delimiters even inside the non-executable JSON script element.
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False)
    data = data.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
    return (template.replace("__STYLE_HASH__", digest(style.group(1)))
            .replace("__SCRIPT_HASH__", digest(script.group(1)))
            .replace("__FREIGHT_DATA__", data))


def render_reviewer_workbench(
    *,
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    truth: TruthManifest,
) -> str:
    from freight.buyer_review_workflow import build_buyer_review_batch

    # Validate the same proof boundary used by actual decision ingestion. No
    # decisions are made and this validation-only role is never exported.
    build_buyer_review_batch(
        review_packet=review_packet, review_routing=review_routing, truth=truth,
        reviewer_role="WORKBENCH_VALIDATION_ONLY", decisions=(),
    )
    eligible = set(review_routing.buyer_review_case_hashes)
    cases = []
    for case in review_packet.cases:
        row = asdict(case)
        row["buyer_review_ready"] = case.case_hash in eligible
        # JSON numbers lose integer precision in JavaScript beyond 2**53-1.
        # All economic values/units cross this boundary as decimal strings.
        for name in ("billed_cents", "expected_cents", "variance_cents", "quantity_units"):
            row[name] = None if row[name] is None else str(row[name])
        for rule in row["rule_evidence"]:
            for name in ("fixed_cents", "unit_rate_cents"):
                rule[name] = None if rule[name] is None else str(rule[name])
        cases.append(row)
    return _render_payload({
        "schema_version": 1,
        "max_decisions": MAX_DECISIONS,
        "buyer_id": review_packet.buyer_id,
        "business_unit": review_packet.business_unit,
        "review_packet_hash": review_packet.packet_hash,
        "review_routing_hash": review_routing.routing_hash,
        "truth_hash": truth.truth_hash,
        "buyer_review_case_count": review_routing.buyer_review_case_count,
        "evidence_remediation_case_count": review_routing.evidence_remediation_case_count,
        "cases": cases,
    })


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON property")
        out[key] = value
    return out


def _invalid_constant(_: str) -> None:
    raise ValueError("non-finite JSON numbers are not accepted")


def import_reviewer_decisions(
    *,
    data: bytes,
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    truth: TruthManifest,
    reviewer_role: str,
) -> BuyerReviewBatch:
    """Convert untrusted proposals into the existing proof-bound review batch.

    The caller must enforce authentication/authorization; neither a JSON hash
    nor a supplied role string authenticates a person. No carrier action occurs.
    Partial decisions remain partial. This function does not overwrite history.
    """
    from freight.buyer_review_workflow import BuyerReviewDecisionInput, build_buyer_review_batch
    from freight.pilot_reporting import ReviewDisposition

    if not isinstance(data, bytes) or not data or len(data) > MAX_DECISION_BYTES:
        raise ValueError("decision data must be nonempty bytes within the size limit")
    try:
        envelope = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_object,
                              parse_constant=_invalid_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid decision JSON") from exc
    if not isinstance(envelope, dict) or set(envelope) != ROOT_KEYS:
        raise ValueError("decision envelope schema mismatch")
    if type(envelope["schema_version"]) is not int or envelope["schema_version"] != 1:
        raise ValueError("unsupported decision schema_version")
    expected_context = {
        "review_packet_hash": review_packet.packet_hash,
        "review_routing_hash": review_routing.routing_hash,
        "truth_hash": truth.truth_hash,
    }
    if any(envelope[key] != value for key, value in expected_context.items()):
        raise ValueError("decision context does not match current review proofs; stale export")
    rows = envelope["decisions"]
    if not isinstance(rows, list) or len(rows) > MAX_DECISIONS:
        raise ValueError("decisions must be a list within the row limit")
    decisions = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != DECISION_KEYS:
            raise ValueError("decision row schema mismatch")
        if not isinstance(row["disposition"], str):
            raise ValueError("decision disposition must be a string")
        try:
            disposition = ReviewDisposition(row["disposition"])
        except ValueError as exc:
            raise ValueError("unsupported decision disposition") from exc
        decisions.append(BuyerReviewDecisionInput(
            case_hash=row["case_hash"], disposition=disposition,
            reviewer_minutes=row["reviewer_minutes"], reviewed_at=row["reviewed_at"],
        ))
    return build_buyer_review_batch(
        review_packet=review_packet, review_routing=review_routing, truth=truth,
        reviewer_role=reviewer_role, decisions=decisions,
    )
