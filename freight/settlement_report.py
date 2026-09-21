"""Read-only pilot reports from a consistent persistent settlement snapshot.

Claims are not finding proof. Reporting requires an explicit one-to-one binding
to the exact frozen finding, normalized payer/payee identity and proof source.
No allocations, reversals, authorizations or outcome records are created here.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from freight.contracts import (
    IncumbentOutput, RecoveryCertificate, TruthManifest, VALIDATED, canonical_hash,
)
from freight.pilot_reporting import (
    FindingReview, PilotMetrics, ReviewDisposition, build_pilot_metrics, render_markdown,
)
from freight.settlement_store import SettlementStore


@dataclass(frozen=True)
class ClaimFindingBinding:
    claim_id: str
    finding_id: str
    finding_proof_hash: str


@dataclass(frozen=True)
class PersistentPilotReport:
    metrics: PilotMetrics
    truth_hash: str
    population_hash: str
    incumbent_output_hash: str
    settlement_snapshot_hash: str
    bindings_hash: str
    reviews_hash: str
    certificates: tuple[RecoveryCertificate, ...]
    report_hash: str
    # Preserve privately alongside the report; never put customer rows in Hunter.
    settlement_snapshot_json: str


class _CertificateSnapshot:
    def __init__(self, truth: TruthManifest, certificates: tuple[RecoveryCertificate, ...]):
        self.buyer_id = truth.buyer_id
        self.business_unit = truth.business_unit
        self._certificates = {cert.finding_id: cert for cert in certificates}

    def certificate(self, finding_id: str) -> RecoveryCertificate:
        return self._certificates[finding_id]


def _verify_frozen_proof(truth: TruthManifest, incumbent: IncumbentOutput) -> None:
    if len({f.finding_id for f in truth.findings}) != len(truth.findings):
        raise ValueError("duplicate frozen finding")
    for finding in truth.findings:
        if (finding.buyer_id, finding.business_unit) != (truth.buyer_id, truth.business_unit):
            raise ValueError("finding scope mismatch")
        if any(type(value) is not int or value < 0 for value in (
            finding.expected_cents, finding.actual_cents,
        )):
            raise ValueError("finding amounts must be non-negative integer cents")
        body = {"schema": 2, **asdict(finding)}
        body.pop("proof_hash")
        if canonical_hash(body) != finding.proof_hash:
            raise ValueError("frozen finding proof hash mismatch")
    body = {"schema": 2, **asdict(truth)}
    body.pop("truth_hash")
    if canonical_hash(body) != truth.truth_hash:
        raise ValueError("frozen truth hash mismatch")
    body = {"schema": 2, **asdict(incumbent)}
    body.pop("output_hash")
    if canonical_hash(body) != incumbent.output_hash:
        raise ValueError("incumbent output hash mismatch")


def build_persistent_pilot_report(
    truth: TruthManifest,
    incumbent: IncumbentOutput,
    store: SettlementStore,
    bindings: tuple[ClaimFindingBinding, ...],
    reviews: tuple[FindingReview, ...] = (),
    *,
    expected_snapshot_hash: str | None = None,
) -> PersistentPilotReport:
    """Derive current net cents; preserve the exact historical input snapshot.

    The caller must already hold the applicable engagement/report authorization.
    This function supplies arithmetic/provenance, not permission to process data.
    """
    if (store.buyer_id, store.business_unit) != (truth.buyer_id, truth.business_unit):
        raise ValueError("settlement store scope mismatch")
    _verify_frozen_proof(truth, incumbent)
    snapshot_json = store.report_snapshot_json()
    snapshot = json.loads(snapshot_json)
    snapshot_hash = canonical_hash(snapshot)
    if expected_snapshot_hash is not None and expected_snapshot_hash != snapshot_hash:
        raise ValueError("settlement snapshot changed; rebuild and review report")

    tables = snapshot["tables"]
    claims = {row["claim_id"]: row for row in tables["recovery_claims"]}
    events = {row["event_id"]: row for row in tables["settlement_events"]}
    counters = {row["counter_id"]: row for row in tables["counter_events"]}
    findings = {finding.finding_id: finding for finding in truth.findings}
    by_finding: dict[str, ClaimFindingBinding] = {}
    bound_claims: set[str] = set()
    for binding in bindings:
        if binding.claim_id in bound_claims or binding.finding_id in by_finding:
            raise ValueError("claim/finding bindings must be one-to-one")
        claim = claims.get(binding.claim_id)
        finding = findings.get(binding.finding_id)
        if claim is None or finding is None:
            raise ValueError("binding references unknown claim or finding")
        if finding.status != VALIDATED or finding.validated_cents <= 0 or not finding.authority_id:
            raise ValueError("claim requires a positive authority-validated finding")
        if binding.finding_proof_hash != finding.proof_hash or claim["source_hash"] != finding.proof_hash:
            raise ValueError("claim must reference the exact frozen finding proof")
        if (claim["reference"], claim["payer_id"], claim["payee_id"], claim["currency"]) != (
            finding.invoice_id, finding.carrier_id, finding.customer_id, finding.currency,
        ):
            raise ValueError("claim identity/currency does not match frozen finding")
        if not 0 < claim["amount_cents"] <= finding.validated_cents:
            raise ValueError("claim exceeds frozen finding capacity")
        if binding.finding_id in incumbent.finding_ids and not claim["fee_disqualified"]:
            raise ValueError("incumbent claim must be fee-disqualified")
        bound_claims.add(binding.claim_id)
        by_finding[binding.finding_id] = binding

    proof_hashes = {finding.proof_hash for finding in truth.findings}
    if any(claim["source_hash"] in proof_hashes and claim_id not in bound_claims
           for claim_id, claim in claims.items()):
        raise ValueError("a claim for this frozen truth is missing its explicit binding")
    for review in reviews:
        if review.finding_id in by_finding and review.disposition is not ReviewDisposition.CONFIRMED:
            raise ValueError("unresolved or false-positive finding cannot support a recovery claim")

    reversals = tables["reversal_edges"]
    reversal_totals: dict[str, int] = {}
    counter_totals: dict[str, int] = {}
    for reversal in reversals:
        allocation_id, counter_id = reversal["allocation_id"], reversal["counter_id"]
        reversal_totals[allocation_id] = reversal_totals.get(allocation_id, 0) + reversal["amount_cents"]
        counter_totals[counter_id] = counter_totals.get(counter_id, 0) + reversal["amount_cents"]
    event_live: dict[str, int] = {}
    for allocation in tables["allocations"]:
        net = allocation["amount_cents"] - reversal_totals.get(allocation["allocation_id"], 0)
        if net < 0:
            raise ValueError("reversal exceeds allocation")
        event_id = allocation["event_id"]
        event_live[event_id] = event_live.get(event_id, 0) + net
    selected_allocations = [row for row in tables["allocations"] if row["claim_id"] in bound_claims]
    selected_events = {row["event_id"] for row in selected_allocations}
    for counter_id, counter in counters.items():
        event_id = counter["original_event_id"]
        if event_id not in selected_events:
            continue
        applied = counter_totals.get(counter_id, 0)
        if applied > counter["amount_cents"]:
            raise ValueError("reversal exceeds counter event")
        if applied < counter["amount_cents"] and event_live.get(event_id, 0):
            raise ValueError("unresolved counter event could change reported recovery")

    certificates = []
    for finding_id, finding in sorted(findings.items()):
        binding = by_finding.get(finding_id)
        allocations = [row for row in selected_allocations
                       if binding is not None and row["claim_id"] == binding.claim_id]
        realized = fee_eligible = 0
        settlement_proofs = []
        for allocation in allocations:
            claim = claims[allocation["claim_id"]]
            event = events[allocation["event_id"]]
            if (event["payer_id"], event["payee_id"], event["currency"]) != (
                claim["payer_id"], claim["payee_id"], claim["currency"],
            ):
                raise ValueError("settlement identity/currency mismatch")
            expected_fee = 0 if claim["fee_disqualified"] else allocation["amount_cents"]
            if allocation["fee_eligible_cents"] != expected_fee:
                raise ValueError("ambiguous allocation fee eligibility")
            net = allocation["amount_cents"] - reversal_totals.get(allocation["allocation_id"], 0)
            realized += net
            fee_eligible += net if expected_fee else 0
            edges = [row for row in reversals if row["allocation_id"] == allocation["allocation_id"]]
            settlement_proofs.append(canonical_hash({
                "schema": 1, "settlement_snapshot_hash": snapshot_hash,
                "claim": claim, "allocation": allocation, "event": event,
                "reversals": edges,
                "counters": [counters[row["counter_id"]] for row in edges],
            }))
        if binding is not None and realized > claims[binding.claim_id]["amount_cents"]:
            raise ValueError("net recovery exceeds claim capacity")
        body = {
            "schema": 3,
            "buyer_id": truth.buyer_id, "business_unit": truth.business_unit,
            "finding_id": finding_id, "finding_proof_hash": finding.proof_hash,
            "validated_cents": finding.validated_cents,
            "realized_cents": realized, "fee_eligible_cents": fee_eligible,
            "settlement_proof_hashes": tuple(settlement_proofs),
            "settlement_snapshot_hash": snapshot_hash,
        }
        certificate_fields = {key: value for key, value in body.items()
                              if key not in {"schema", "settlement_snapshot_hash"}}
        certificates.append(RecoveryCertificate(**certificate_fields, certificate_hash=canonical_hash(body)))

    certificates = tuple(certificates)
    metrics = build_pilot_metrics(truth, incumbent, _CertificateSnapshot(truth, certificates), reviews)
    bindings_hash = canonical_hash([asdict(binding) for binding in sorted(bindings, key=lambda b: b.claim_id)])
    reviews_hash = canonical_hash([asdict(review) for review in sorted(reviews, key=lambda r: r.finding_id)])
    body = {
        "schema": 1, "metrics": asdict(metrics), "truth_hash": truth.truth_hash,
        "population_hash": truth.population_hash, "incumbent_output_hash": incumbent.output_hash,
        "settlement_snapshot_hash": snapshot_hash, "bindings_hash": bindings_hash,
        "reviews_hash": reviews_hash, "certificates": [asdict(cert) for cert in certificates],
    }
    return PersistentPilotReport(
        metrics=metrics, truth_hash=truth.truth_hash, population_hash=truth.population_hash,
        incumbent_output_hash=incumbent.output_hash, settlement_snapshot_hash=snapshot_hash,
        bindings_hash=bindings_hash, reviews_hash=reviews_hash, certificates=certificates,
        report_hash=canonical_hash(body), settlement_snapshot_json=snapshot_json,
    )


def assert_report_current(report: PersistentPilotReport, store: SettlementStore) -> None:
    """Recheck immediately before use; historical reports remain valid as-of only."""
    if (report.metrics.buyer_id, report.metrics.business_unit) != (store.buyer_id, store.business_unit):
        raise ValueError("report/store scope mismatch")
    if canonical_hash(json.loads(store.report_snapshot_json())) != report.settlement_snapshot_hash:
        raise ValueError("settlement snapshot changed; rebuild and review report")


def render_persistent_markdown(report: PersistentPilotReport) -> str:
    return render_markdown(report.metrics) + "\n" + "\n".join([
        "## Persistent settlement provenance",
        "Amounts are net of applied returns/reversals in this exact snapshot. Later events require a new report.",
        "Validated and challenger-only totals reflect the frozen truth; review outcomes are shown separately. Corrections require a newly approved truth.",
        "- Truth: `" + report.truth_hash + "`",
        "- Population: `" + report.population_hash + "`",
        "- Incumbent output: `" + report.incumbent_output_hash + "`",
        "- Settlement snapshot: `" + report.settlement_snapshot_hash + "`",
        "- Claim bindings: `" + report.bindings_hash + "`",
        "- Reviews: `" + report.reviews_hash + "`",
        "- Report: `" + report.report_hash + "`",
    ]) + "\n"
