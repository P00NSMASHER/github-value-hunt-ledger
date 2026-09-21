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
from typing import TYPE_CHECKING, Any, Iterable

from freight.reviewer_decision_package import (
    MAX_FILE_BYTES as MAX_DECISION_BYTES,
    MAX_FILE_DECISIONS as MAX_DECISIONS,
)

if TYPE_CHECKING:
    from freight.buyer_review_workflow import BuyerReviewBatch
    from freight.contracts import TruthManifest
    from freight.review_packet import ReviewPacket
    from freight.review_routing import ReviewRouting

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
        "max_decision_bytes": MAX_DECISION_BYTES,
        "buyer_id": review_packet.buyer_id,
        "business_unit": review_packet.business_unit,
        "review_packet_hash": review_packet.packet_hash,
        "review_routing_hash": review_routing.routing_hash,
        "truth_hash": truth.truth_hash,
        "buyer_review_case_count": review_routing.buyer_review_case_count,
        "evidence_remediation_case_count": review_routing.evidence_remediation_case_count,
        "cases": cases,
    })


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
    # A single export must obey the same schema, timestamp, effort and size
    # rules as a split handoff. Keep one validator and one buyer-review path.
    return import_reviewer_decision_files(
        files=(data,), review_packet=review_packet,
        review_routing=review_routing, truth=truth,
        reviewer_role=reviewer_role,
    )


def import_reviewer_decision_files(
    *,
    files: Iterable[bytes],
    review_packet: ReviewPacket,
    review_routing: ReviewRouting,
    truth: TruthManifest,
    reviewer_role: str,
    previous_batch: BuyerReviewBatch | None = None,
) -> BuyerReviewBatch:
    """Combine split exports and optionally retain a verified prior review batch.

    Every export must belong to the current audit. Conflicts never silently
    replace a prior decision. The caller supplies the authenticated role; a
    previous batch from another role is not relabelled. No history is persisted
    here. Persist the returned new batch only after this entire call succeeds.
    """
    from freight.buyer_review_workflow import (
        BuyerReviewDecisionInput, build_buyer_review_batch, verify_buyer_review_batch,
    )
    from freight.pilot_reporting import ReviewDisposition
    from freight.reviewer_decision_package import (
        MAX_COMBINED_DECISIONS, DraftDecision, canonical_review_time,
        merge_decision_exports,
    )

    if not isinstance(reviewer_role, str) or not reviewer_role.strip():
        raise ValueError("authenticated reviewer_role is required")
    reviewer_role = reviewer_role.strip()
    combined = merge_decision_exports(
        files, review_packet_hash=review_packet.packet_hash,
        review_routing_hash=review_routing.routing_hash, truth_hash=truth.truth_hash,
    )
    rows = {row.case_hash: row for row in combined.decisions}
    if previous_batch is not None:
        verify_buyer_review_batch(
            batch=previous_batch, review_packet=review_packet,
            review_routing=review_routing, truth=truth,
        )
        if previous_batch.reviewer_role != reviewer_role:
            raise ValueError("previous batch reviewer role differs; separate reviewer handoff required")
        for record in previous_batch.records:
            prior = DraftDecision(
                record.case_hash, record.disposition, record.reviewer_minutes,
                canonical_review_time(record.reviewed_at),
            )
            incoming = rows.get(prior.case_hash)
            if incoming is not None and incoming != prior:
                raise ValueError("export conflicts with previously recorded buyer decision")
            rows[prior.case_hash] = prior
    if len(rows) > MAX_COMBINED_DECISIONS:
        raise ValueError("combined decision limit exceeded including previous batch")
    decisions = tuple(
        BuyerReviewDecisionInput(
            case_hash=row.case_hash, disposition=ReviewDisposition(row.disposition),
            reviewer_minutes=row.reviewer_minutes, reviewed_at=row.reviewed_at,
        )
        for row in (rows[key] for key in sorted(rows))
    )
    # This is the existing authoritative proof-validation path, not new approval
    # logic. It rejects unknown/remediation cases and mismatched current proofs.
    return build_buyer_review_batch(
        review_packet=review_packet, review_routing=review_routing, truth=truth,
        reviewer_role=reviewer_role, decisions=decisions,
    )
