"""Pinned integration plane for the RecoveryOS/Freight Recovery winning stack.

The module deliberately keeps third-party systems outside the money-bearing
authority boundary.  RecoveryOS remains authoritative for findings, buyer
review, claims, settlement and fee eligibility.  External components receive
deterministic, hash-bound jobs that can be executed by isolated adapters.

The design borrows the useful guarantees from AgentLedger and durable workflow
runtimes: stable idempotency keys, append-only execution events, explicit
unknown outcomes, retry from the last durable state, and evidence hashes.
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable

from freight.carrier_action_payload import CarrierActionPayload
from freight.contracts import canonical_hash
from freight.recovery_claim_workflow import (
    RecoveryClaimBatch,
    verify_recovery_claim_batch,
)


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_TEXT = 16_384
MAX_CENTS = 2**63 - 1


class StackCapability(str, Enum):
    CONTRACT_REDLINE = "CONTRACT_REDLINE"
    SETTLEMENT_COMPARATOR = "SETTLEMENT_COMPARATOR"
    AGENT_EVIDENCE = "AGENT_EVIDENCE"
    DURABLE_WORKFLOW = "DURABLE_WORKFLOW"
    FLEET_OPERATIONS = "FLEET_OPERATIONS"
    LANDED_COST = "LANDED_COST"


class StackJobState(str, Enum):
    PREPARED = "PREPARED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class StackComponentPin:
    capability: str
    repository: str
    revision: str
    public_license: str
    execution_boundary: str


COMPONENT_PINS: dict[StackCapability, StackComponentPin] = {
    StackCapability.CONTRACT_REDLINE: StackComponentPin(
        capability=StackCapability.CONTRACT_REDLINE.value,
        repository="AnsonLai/docx-redline-js",
        revision="e5bd19e93f85159f0838bcf31cb4ccc3d48c5cab",
        public_license="MIT",
        execution_boundary="ISOLATED_ADAPTER",
    ),
    StackCapability.SETTLEMENT_COMPARATOR: StackComponentPin(
        capability=StackCapability.SETTLEMENT_COMPARATOR.value,
        repository="kingsleyonoh/sla-penalty-settlement-engine",
        revision="ea66727de51df7ee67a9f03f2549845fa6247b3d",
        public_license="AGPL-3.0",
        execution_boundary="INDEPENDENT_COMPARATOR_ONLY",
    ),
    StackCapability.AGENT_EVIDENCE: StackComponentPin(
        capability=StackCapability.AGENT_EVIDENCE.value,
        repository="yaogdu/AgentLedger",
        revision="dd966e3b3d9eb54032c51701d30efcfbaa2379b0",
        public_license="Apache-2.0",
        execution_boundary="ISOLATED_ADAPTER",
    ),
    StackCapability.DURABLE_WORKFLOW: StackComponentPin(
        capability=StackCapability.DURABLE_WORKFLOW.value,
        repository="microsoft/duroxide-python",
        revision="0a29c32cdfd322c349fa6a9f480fc45fd78ea3ef",
        public_license="MIT",
        execution_boundary="ISOLATED_ADAPTER",
    ),
    StackCapability.FLEET_OPERATIONS: StackComponentPin(
        capability=StackCapability.FLEET_OPERATIONS.value,
        repository="fleetbase/fleetbase",
        revision="4ff6980c6db6f3e8103b3ec425a089aa6d251af4",
        public_license="AGPL-3.0",
        execution_boundary="EXTERNAL_SYSTEM_ADAPTER_ONLY",
    ),
    StackCapability.LANDED_COST: StackComponentPin(
        capability=StackCapability.LANDED_COST.value,
        repository="Budget-Lab-Yale/tariff-rate-tracker",
        revision="5a977726af0ead299e7db9cbca018b04dc2cc2e6",
        public_license="MIT",
        execution_boundary="SOURCE_DATA_ADAPTER",
    ),
}


@dataclass(frozen=True)
class ContractRedlineTarget:
    document_sha256: str
    paragraph_id: str
    fingerprint: str
    find_text: str
    replace_text: str
    author: str = "RecoveryOS"


@dataclass(frozen=True)
class FleetOperationEvidence:
    event_id: str
    order_id: str
    shipment_id: str
    event_type: str
    occurred_at: str
    source_sha256: str
    proof_of_delivery_sha256: str | None = None


@dataclass(frozen=True)
class LandedCostObservation:
    observation_id: str
    hts10: str
    origin_country: str
    destination_country: str
    effective_on: str
    declared_value_cents: int
    currency: str
    baseline_rate_bps: int
    observed_rate_bps: int
    source_sha256: str

    @property
    def estimated_delta_cents(self) -> int:
        numerator = self.declared_value_cents * (
            self.observed_rate_bps - self.baseline_rate_bps
        )
        if numerator >= 0:
            return (numerator + 5_000) // 10_000
        return -((-numerator + 5_000) // 10_000)


@dataclass(frozen=True)
class RecoveryStackJob:
    job_id: str
    buyer_id: str
    business_unit: str
    case_id: str
    capability: str
    repository: str
    revision: str
    execution_boundary: str
    request_hash: str
    idempotency_key: str
    payload_json: str
    requires_human_review: bool
    may_assert_recovery: bool
    job_hash: str

    @property
    def payload(self) -> dict:
        return json.loads(self.payload_json)


@dataclass(frozen=True)
class RecoveryStackPlan:
    buyer_id: str
    business_unit: str
    claim_batch_hash: str
    carrier_payload_hash: str | None
    generated_at: str
    job_count: int
    estimated_landed_cost_delta_cents: int
    jobs: tuple[RecoveryStackJob, ...]
    plan_hash: str


@dataclass(frozen=True)
class StackExecutionEvent:
    event_id: str
    job_id: str
    state: str
    occurred_at: str
    worker_id: str
    result_sha256: str | None
    error_code: str | None
    previous_event_hash: str | None
    event_hash: str


@dataclass(frozen=True)
class StackPlanPersistenceReceipt:
    plan_hash: str
    attempted_job_count: int
    created_job_count: int
    already_present_count: int
    receipt_hash: str


def _text(name: str, value: str, *, max_length: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(name + " is required")
    normalized = value.strip()
    if len(normalized) > max_length:
        raise ValueError(name + " exceeds maximum length")
    return normalized


def _sha(name: str, value: str) -> str:
    text = _text(name, value, max_length=64)
    if not SHA256_RE.fullmatch(text):
        raise ValueError(name + " must be lowercase SHA-256")
    return text


def _timestamp(name: str, value: str) -> str:
    text = _text(name, value, max_length=64)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(name + " must be timezone-aware ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(name + " must be timezone-aware ISO-8601")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _date(name: str, value: str) -> str:
    text = _text(name, value, max_length=10)
    try:
        return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
    except ValueError as exc:
        raise ValueError(name + " must be YYYY-MM-DD") from exc


def _payload_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _make_job(
    *,
    capability: StackCapability,
    buyer_id: str,
    business_unit: str,
    case_id: str,
    payload: dict,
    requires_human_review: bool,
    may_assert_recovery: bool = False,
) -> RecoveryStackJob:
    pin = COMPONENT_PINS[capability]
    request_hash = canonical_hash(payload)
    idempotency_key = canonical_hash({
        "schema": 1,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "case_id": case_id,
        "capability": capability.value,
        "request_hash": request_hash,
    })
    job_id = capability.value.lower() + ":" + idempotency_key
    body = {
        "schema": 1,
        "job_id": job_id,
        "buyer_id": buyer_id,
        "business_unit": business_unit,
        "case_id": case_id,
        "capability": capability.value,
        "repository": pin.repository,
        "revision": pin.revision,
        "execution_boundary": pin.execution_boundary,
        "request_hash": request_hash,
        "idempotency_key": idempotency_key,
        "payload": payload,
        "requires_human_review": requires_human_review,
        "may_assert_recovery": may_assert_recovery,
    }
    return RecoveryStackJob(
        job_id=job_id,
        buyer_id=buyer_id,
        business_unit=business_unit,
        case_id=case_id,
        capability=capability.value,
        repository=pin.repository,
        revision=pin.revision,
        execution_boundary=pin.execution_boundary,
        request_hash=request_hash,
        idempotency_key=idempotency_key,
        payload_json=_payload_json(payload),
        requires_human_review=requires_human_review,
        may_assert_recovery=may_assert_recovery,
        job_hash=canonical_hash(body),
    )


def _validate_redline(target: ContractRedlineTarget) -> ContractRedlineTarget:
    _sha("document_sha256", target.document_sha256)
    _text("paragraph_id", target.paragraph_id, max_length=256)
    _text("fingerprint", target.fingerprint, max_length=512)
    find_text = _text("find_text", target.find_text)
    replace_text = _text("replace_text", target.replace_text)
    _text("author", target.author, max_length=128)
    if find_text == replace_text:
        raise ValueError("redline find_text and replace_text must differ")
    return target


def _validate_fleet_event(event: FleetOperationEvidence) -> FleetOperationEvidence:
    for name in ("event_id", "order_id", "shipment_id", "event_type"):
        _text(name, getattr(event, name), max_length=256)
    _timestamp("fleet event occurred_at", event.occurred_at)
    _sha("fleet source_sha256", event.source_sha256)
    if event.proof_of_delivery_sha256 is not None:
        _sha("proof_of_delivery_sha256", event.proof_of_delivery_sha256)
    return event


def _validate_landed_cost(item: LandedCostObservation) -> LandedCostObservation:
    for name in (
        "observation_id", "hts10", "origin_country", "destination_country", "currency"
    ):
        _text(name, getattr(item, name), max_length=64)
    _date("effective_on", item.effective_on)
    _sha("landed-cost source_sha256", item.source_sha256)
    if type(item.declared_value_cents) is not int or not 0 <= item.declared_value_cents <= MAX_CENTS:
        raise ValueError("declared_value_cents must be non-negative integer cents")
    for name in ("baseline_rate_bps", "observed_rate_bps"):
        value = getattr(item, name)
        if type(value) is not int or not 0 <= value <= 1_000_000:
            raise ValueError(name + " must be an integer between 0 and 1000000")
    return item


def _verify_carrier_payload_integrity(
    payload: CarrierActionPayload,
    recovery_claims: RecoveryClaimBatch,
) -> None:
    if payload.recovery_claim_batch_hash != recovery_claims.batch_hash:
        raise ValueError("carrier payload does not match recovery claim batch")
    if payload.line_count != len(payload.lines) or not payload.lines:
        raise ValueError("carrier payload line count mismatch")
    records = {record.claim_id: record for record in recovery_claims.records}
    total = 0
    for line in payload.lines:
        record = records.get(line.claim_id)
        if record is None:
            raise ValueError("carrier payload references unknown recovery claim")
        if (
            line.finding_id != record.finding_id
            or line.finding_proof_hash != record.finding_proof_hash
            or line.review_hash != record.review_hash
            or line.claim_record_hash != record.record_hash
            or line.reference != record.reference
            or line.amount_cents != record.amount_cents
        ):
            raise ValueError("carrier payload line does not match recovery claim")
        line_body = {
            "schema": 1,
            "proposal_hash": payload.proposal_hash,
            "claim_id": line.claim_id,
            "finding_id": line.finding_id,
            "reference": line.reference,
            "amount_cents": line.amount_cents,
            "finding_proof_hash": line.finding_proof_hash,
            "review_hash": line.review_hash,
            "claim_record_hash": line.claim_record_hash,
        }
        if canonical_hash(line_body) != line.line_hash:
            raise ValueError("carrier payload line hash mismatch")
        total += line.amount_cents
    if total != payload.requested_cents:
        raise ValueError("carrier payload requested amount mismatch")
    body = {
        "schema": 1,
        "proposal_hash": payload.proposal_hash,
        "recovery_claim_batch_hash": payload.recovery_claim_batch_hash,
        "action_type": payload.action_type,
        "target_carrier_id": payload.target_carrier_id,
        "target_customer_id": payload.target_customer_id,
        "currency": payload.currency,
        "requested_cents": payload.requested_cents,
        "line_count": payload.line_count,
        "lines": [asdict(line) for line in payload.lines],
        "subject": payload.subject,
        "body_text": payload.body_text,
    }
    if canonical_hash(body) != payload.payload_hash:
        raise ValueError("carrier payload hash mismatch")


def build_recovery_stack_plan(
    *,
    recovery_claims: RecoveryClaimBatch,
    generated_at: str,
    carrier_payload: CarrierActionPayload | None = None,
    contract_redlines: Iterable[ContractRedlineTarget] = (),
    fleet_events: Iterable[FleetOperationEvidence] = (),
    landed_cost_observations: Iterable[LandedCostObservation] = (),
) -> RecoveryStackPlan:
    """Compile deterministic adapter jobs from an authoritative claim batch."""
    verify_recovery_claim_batch(recovery_claims)
    if not recovery_claims.claims:
        raise ValueError("winning-stack plan requires at least one confirmed recovery claim")
    canonical_generated_at = _timestamp("generated_at", generated_at)
    case_id = "recovery:" + recovery_claims.batch_hash

    if carrier_payload is not None:
        _verify_carrier_payload_integrity(carrier_payload, recovery_claims)

    redlines = tuple(_validate_redline(item) for item in contract_redlines)
    events = tuple(_validate_fleet_event(item) for item in fleet_events)
    landed = tuple(_validate_landed_cost(item) for item in landed_cost_observations)

    jobs: list[RecoveryStackJob] = []
    claim_summary = [
        {
            "claim_id": record.claim_id,
            "finding_id": record.finding_id,
            "amount_cents": record.amount_cents,
            "currency": record.currency,
            "finding_proof_hash": record.finding_proof_hash,
            "claim_record_hash": record.record_hash,
            "fee_disqualified": record.fee_disqualified,
        }
        for record in recovery_claims.records
    ]

    jobs.append(_make_job(
        capability=StackCapability.SETTLEMENT_COMPARATOR,
        buyer_id=recovery_claims.buyer_id,
        business_unit=recovery_claims.business_unit,
        case_id=case_id,
        payload={
            "schema": 1,
            "mode": "INDEPENDENT_COMPARATOR",
            "claim_batch_hash": recovery_claims.batch_hash,
            "claims": claim_summary,
            "authoritative_system": "RecoveryOS",
            "comparator_may_post_settlement": False,
            "comparator_may_assert_recovery": False,
        },
        requires_human_review=True,
    ))
    jobs.append(_make_job(
        capability=StackCapability.AGENT_EVIDENCE,
        buyer_id=recovery_claims.buyer_id,
        business_unit=recovery_claims.business_unit,
        case_id=case_id,
        payload={
            "schema": 1,
            "claim_batch_hash": recovery_claims.batch_hash,
            "evidence_hashes": sorted({
                record.finding_proof_hash for record in recovery_claims.records
            } | {
                record.review_hash for record in recovery_claims.records
            }),
            "side_effect_policy": "DENY_UNLESS_SEPARATELY_AUTHORIZED",
            "replay_external_side_effects": False,
            "unknown_outcome_policy": "REVIEW_BEFORE_RETRY",
        },
        requires_human_review=False,
    ))
    jobs.append(_make_job(
        capability=StackCapability.DURABLE_WORKFLOW,
        buyer_id=recovery_claims.buyer_id,
        business_unit=recovery_claims.business_unit,
        case_id=case_id,
        payload={
            "schema": 1,
            "workflow": "FREIGHT_RECOVERY_CASE",
            "claim_batch_hash": recovery_claims.batch_hash,
            "stages": [
                "EVIDENCE_INTAKE", "BUYER_REVIEW", "CLAIM_PREPARATION",
                "EXTERNAL_ACTION_AUTHORIZATION", "SETTLEMENT_INGESTION",
                "RECOVERY_CERTIFICATE",
            ],
            "resume_from_last_committed_stage": True,
            "external_actions_default": "DISABLED",
        },
        requires_human_review=False,
    ))

    if carrier_payload is not None:
        jobs.append(_make_job(
            capability=StackCapability.AGENT_EVIDENCE,
            buyer_id=recovery_claims.buyer_id,
            business_unit=recovery_claims.business_unit,
            case_id=case_id,
            payload={
                "schema": 1,
                "artifact_type": "CARRIER_ACTION_PREVIEW",
                "claim_batch_hash": recovery_claims.batch_hash,
                "carrier_payload_hash": carrier_payload.payload_hash,
                "proposal_hash": carrier_payload.proposal_hash,
                "requested_cents": carrier_payload.requested_cents,
                "currency": carrier_payload.currency,
                "send_authorized": False,
            },
            requires_human_review=True,
        ))

    for target in redlines:
        jobs.append(_make_job(
            capability=StackCapability.CONTRACT_REDLINE,
            buyer_id=recovery_claims.buyer_id,
            business_unit=recovery_claims.business_unit,
            case_id=case_id,
            payload={
                "schema": 1,
                "contract_version": 8,
                "claim_batch_hash": recovery_claims.batch_hash,
                "document_sha256": target.document_sha256,
                "operation": {
                    "type": "localized-replacement",
                    "paragraphId": target.paragraph_id,
                    "fingerprint": target.fingerprint,
                    "replacements": [{
                        "find": target.find_text,
                        "replace": target.replace_text,
                    }],
                },
                "options": {
                    "author": target.author,
                    "atomic": True,
                    "validate": True,
                    "generateRedlines": True,
                    "requireComplete": True,
                },
                "source_document_may_be_overwritten": False,
            },
            requires_human_review=True,
        ))

    for event in events:
        jobs.append(_make_job(
            capability=StackCapability.FLEET_OPERATIONS,
            buyer_id=recovery_claims.buyer_id,
            business_unit=recovery_claims.business_unit,
            case_id=case_id,
            payload={
                "schema": 1,
                "mode": "READ_ONLY_EVIDENCE_IMPORT",
                "event_id": event.event_id,
                "order_id": event.order_id,
                "shipment_id": event.shipment_id,
                "event_type": event.event_type,
                "occurred_at": _timestamp("fleet event occurred_at", event.occurred_at),
                "source_sha256": event.source_sha256,
                "proof_of_delivery_sha256": event.proof_of_delivery_sha256,
                "may_mutate_fleetbase": False,
            },
            requires_human_review=False,
        ))

    for item in landed:
        jobs.append(_make_job(
            capability=StackCapability.LANDED_COST,
            buyer_id=recovery_claims.buyer_id,
            business_unit=recovery_claims.business_unit,
            case_id=case_id,
            payload={
                "schema": 1,
                **asdict(item),
                "effective_on": _date("effective_on", item.effective_on),
                "estimated_delta_cents": item.estimated_delta_cents,
                "classification": "EXPOSURE_ONLY",
                "may_create_recovery_claim": False,
            },
            requires_human_review=True,
        ))

    jobs_tuple = tuple(sorted(jobs, key=lambda job: (job.capability, job.job_id)))
    if len({job.job_id for job in jobs_tuple}) != len(jobs_tuple):
        raise ValueError("duplicate integration job")
    body = {
        "schema": 1,
        "buyer_id": recovery_claims.buyer_id,
        "business_unit": recovery_claims.business_unit,
        "claim_batch_hash": recovery_claims.batch_hash,
        "carrier_payload_hash": carrier_payload.payload_hash if carrier_payload else None,
        "generated_at": canonical_generated_at,
        "job_count": len(jobs_tuple),
        "estimated_landed_cost_delta_cents": sum(
            item.estimated_delta_cents for item in landed
        ),
        "job_hashes": [job.job_hash for job in jobs_tuple],
    }
    return RecoveryStackPlan(
        buyer_id=recovery_claims.buyer_id,
        business_unit=recovery_claims.business_unit,
        claim_batch_hash=recovery_claims.batch_hash,
        carrier_payload_hash=carrier_payload.payload_hash if carrier_payload else None,
        generated_at=canonical_generated_at,
        job_count=len(jobs_tuple),
        estimated_landed_cost_delta_cents=sum(
            item.estimated_delta_cents for item in landed
        ),
        jobs=jobs_tuple,
        plan_hash=canonical_hash(body),
    )


def verify_recovery_stack_plan(plan: RecoveryStackPlan) -> None:
    if plan.job_count != len(plan.jobs):
        raise ValueError("stack plan job count mismatch")
    if len({job.job_id for job in plan.jobs}) != len(plan.jobs):
        raise ValueError("stack plan contains duplicate jobs")
    for job in plan.jobs:
        if (job.buyer_id, job.business_unit) != (plan.buyer_id, plan.business_unit):
            raise ValueError("stack job scope mismatch")
        if job.case_id != "recovery:" + plan.claim_batch_hash:
            raise ValueError("stack job case mismatch")
        payload = job.payload
        if canonical_hash(payload) != job.request_hash:
            raise ValueError("stack job request hash mismatch")
        capability = StackCapability(job.capability)
        expected = _make_job(
            capability=capability,
            buyer_id=job.buyer_id,
            business_unit=job.business_unit,
            case_id=job.case_id,
            payload=payload,
            requires_human_review=job.requires_human_review,
            may_assert_recovery=job.may_assert_recovery,
        )
        if expected != job:
            raise ValueError("stack job does not match pinned component contract")
        if job.may_assert_recovery:
            raise ValueError("integration jobs may not assert recovery")
    body = {
        "schema": 1,
        "buyer_id": plan.buyer_id,
        "business_unit": plan.business_unit,
        "claim_batch_hash": plan.claim_batch_hash,
        "carrier_payload_hash": plan.carrier_payload_hash,
        "generated_at": plan.generated_at,
        "job_count": plan.job_count,
        "estimated_landed_cost_delta_cents": plan.estimated_landed_cost_delta_cents,
        "job_hashes": [job.job_hash for job in plan.jobs],
    }
    if canonical_hash(body) != plan.plan_hash:
        raise ValueError("stack plan hash mismatch")


class RecoveryStackStore:
    """Scoped append-only durable job/event store for adapter execution."""

    _ALLOWED = {
        StackJobState.PREPARED: {StackJobState.RUNNING},
        StackJobState.RUNNING: {
            StackJobState.SUCCEEDED, StackJobState.FAILED, StackJobState.UNKNOWN,
        },
        StackJobState.FAILED: {StackJobState.RUNNING},
        StackJobState.UNKNOWN: {StackJobState.RUNNING},
        StackJobState.SUCCEEDED: set(),
    }

    def __init__(self, path: str | Path, *, buyer_id: str, business_unit: str):
        self.path = Path(path)
        self.buyer_id = _text("buyer_id", buyer_id, max_length=256)
        self.business_unit = _text("business_unit", business_unit, max_length=256)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS stack_jobs (
                    buyer_id TEXT NOT NULL,
                    business_unit TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    plan_hash TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    job_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    job_json TEXT NOT NULL,
                    PRIMARY KEY (buyer_id, business_unit, job_id)
                );
                CREATE TABLE IF NOT EXISTS stack_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    buyer_id TEXT NOT NULL,
                    business_unit TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    job_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    result_sha256 TEXT,
                    error_code TEXT,
                    previous_event_hash TEXT,
                    event_hash TEXT NOT NULL UNIQUE
                );
                CREATE TRIGGER IF NOT EXISTS stack_jobs_no_update
                BEFORE UPDATE ON stack_jobs BEGIN SELECT RAISE(ABORT, 'stack jobs are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS stack_jobs_no_delete
                BEFORE DELETE ON stack_jobs BEGIN SELECT RAISE(ABORT, 'stack jobs are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS stack_events_no_update
                BEFORE UPDATE ON stack_events BEGIN SELECT RAISE(ABORT, 'stack events are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS stack_events_no_delete
                BEFORE DELETE ON stack_events BEGIN SELECT RAISE(ABORT, 'stack events are immutable'); END;
            """)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def _latest_event(self, conn: sqlite3.Connection, job_id: str) -> sqlite3.Row | None:
        return conn.execute(
            """SELECT * FROM stack_events
               WHERE buyer_id=? AND business_unit=? AND job_id=?
               ORDER BY sequence DESC LIMIT 1""",
            (self.buyer_id, self.business_unit, job_id),
        ).fetchone()

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> StackExecutionEvent:
        return StackExecutionEvent(
            event_id=row["event_id"], job_id=row["job_id"], state=row["state"],
            occurred_at=row["occurred_at"], worker_id=row["worker_id"],
            result_sha256=row["result_sha256"], error_code=row["error_code"],
            previous_event_hash=row["previous_event_hash"], event_hash=row["event_hash"],
        )

    def _append_event(
        self,
        conn: sqlite3.Connection,
        *,
        job_id: str,
        state: StackJobState,
        occurred_at: str,
        worker_id: str,
        result_sha256: str | None = None,
        error_code: str | None = None,
    ) -> StackExecutionEvent:
        canonical_time = _timestamp("occurred_at", occurred_at)
        worker = _text("worker_id", worker_id, max_length=256)
        if result_sha256 is not None:
            _sha("result_sha256", result_sha256)
        if error_code is not None:
            error_code = _text("error_code", error_code, max_length=128)
        previous = self._latest_event(conn, job_id)
        previous_hash = previous["event_hash"] if previous is not None else None
        if previous is not None and canonical_time < previous["occurred_at"]:
            raise ValueError("stack event occurred_at cannot move backwards")
        body = {
            "schema": 1,
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "job_id": job_id,
            "state": state.value,
            "occurred_at": canonical_time,
            "worker_id": worker,
            "result_sha256": result_sha256,
            "error_code": error_code,
            "previous_event_hash": previous_hash,
        }
        event_hash = canonical_hash(body)
        event_id = "stack-event:" + event_hash
        conn.execute(
            """INSERT INTO stack_events
               (buyer_id,business_unit,event_id,job_id,state,occurred_at,worker_id,
                result_sha256,error_code,previous_event_hash,event_hash)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (self.buyer_id, self.business_unit, event_id, job_id, state.value,
             canonical_time, worker, result_sha256, error_code, previous_hash, event_hash),
        )
        row = self._latest_event(conn, job_id)
        assert row is not None
        return self._event_from_row(row)

    def persist_plan(self, plan: RecoveryStackPlan) -> StackPlanPersistenceReceipt:
        verify_recovery_stack_plan(plan)
        if (plan.buyer_id, plan.business_unit) != (self.buyer_id, self.business_unit):
            raise ValueError("stack store scope mismatch")
        created = 0
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            for job in plan.jobs:
                job_json = _payload_json(asdict(job))
                existing = conn.execute(
                    """SELECT plan_hash,job_hash,payload_json,job_json FROM stack_jobs
                       WHERE buyer_id=? AND business_unit=? AND job_id=?""",
                    (self.buyer_id, self.business_unit, job.job_id),
                ).fetchone()
                if existing is not None:
                    if (
                        existing["job_hash"] != job.job_hash
                        or existing["payload_json"] != job.payload_json
                        or existing["job_json"] != job_json
                    ):
                        raise ValueError("idempotency collision for stack job")
                    continue
                conn.execute(
                    """INSERT INTO stack_jobs
                       (buyer_id,business_unit,job_id,plan_hash,capability,request_hash,
                        job_hash,payload_json,job_json) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (self.buyer_id, self.business_unit, job.job_id, plan.plan_hash,
                     job.capability, job.request_hash, job.job_hash, job.payload_json, job_json),
                )
                self._append_event(
                    conn, job_id=job.job_id, state=StackJobState.PREPARED,
                    occurred_at=plan.generated_at, worker_id="RecoveryOS",
                )
                created += 1
            conn.commit()
        body = {
            "schema": 1,
            "plan_hash": plan.plan_hash,
            "attempted_job_count": plan.job_count,
            "created_job_count": created,
            "already_present_count": plan.job_count - created,
        }
        return StackPlanPersistenceReceipt(
            plan_hash=plan.plan_hash,
            attempted_job_count=plan.job_count,
            created_job_count=created,
            already_present_count=plan.job_count - created,
            receipt_hash=canonical_hash(body),
        )

    def transition(
        self,
        job_id: str,
        *,
        state: StackJobState,
        occurred_at: str,
        worker_id: str,
        result_sha256: str | None = None,
        error_code: str | None = None,
    ) -> StackExecutionEvent:
        if not isinstance(state, StackJobState):
            raise ValueError("state must be a StackJobState")
        job_id = _text("job_id", job_id, max_length=256)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            job = conn.execute(
                """SELECT 1 FROM stack_jobs
                   WHERE buyer_id=? AND business_unit=? AND job_id=?""",
                (self.buyer_id, self.business_unit, job_id),
            ).fetchone()
            if job is None:
                raise ValueError("unknown stack job")
            latest = self._latest_event(conn, job_id)
            if latest is None:
                raise ValueError("stack job has no prepared event")
            current = StackJobState(latest["state"])
            if state not in self._ALLOWED[current]:
                raise ValueError(f"invalid stack job transition: {current.value}->{state.value}")
            if (
                current is StackJobState.UNKNOWN
                and state is StackJobState.RUNNING
                and result_sha256 is None
            ):
                raise ValueError("retry from UNKNOWN requires review evidence SHA-256")
            if state is StackJobState.SUCCEEDED and result_sha256 is None:
                raise ValueError("SUCCEEDED requires result_sha256")
            if state in {StackJobState.FAILED, StackJobState.UNKNOWN} and error_code is None:
                raise ValueError(state.value + " requires error_code")
            event = self._append_event(
                conn, job_id=job_id, state=state, occurred_at=occurred_at,
                worker_id=worker_id, result_sha256=result_sha256, error_code=error_code,
            )
            conn.commit()
            return event

    def state(self, job_id: str) -> StackJobState:
        with self._connect() as conn:
            row = self._latest_event(conn, job_id)
            if row is None:
                raise ValueError("unknown stack job")
            return StackJobState(row["state"])

    def verify_event_chain(self, job_id: str) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM stack_events
                   WHERE buyer_id=? AND business_unit=? AND job_id=? ORDER BY sequence""",
                (self.buyer_id, self.business_unit, job_id),
            ).fetchall()
        if not rows:
            raise ValueError("unknown stack job")
        previous_hash: str | None = None
        for row in rows:
            body = {
                "schema": 1,
                "buyer_id": self.buyer_id,
                "business_unit": self.business_unit,
                "job_id": row["job_id"],
                "state": row["state"],
                "occurred_at": row["occurred_at"],
                "worker_id": row["worker_id"],
                "result_sha256": row["result_sha256"],
                "error_code": row["error_code"],
                "previous_event_hash": previous_hash,
            }
            if row["previous_event_hash"] != previous_hash:
                raise ValueError("stack event chain previous hash mismatch")
            if canonical_hash(body) != row["event_hash"]:
                raise ValueError("stack event hash mismatch")
            previous_hash = row["event_hash"]
