"""Adversarial validation harness for the integrated RecoveryOS freight path.

The suite is synthetic and deliberately separates:
- candidate detection quality (did the system surface a broker-overpayment candidate?),
- validation quality (did proof/authority gates allow VALIDATED dollars?), and
- dollar accuracy (were candidate/validated cents over- or under-stated?).

No external action is performed. Carrier-underbilling scenarios are retained as
supplemental evidence and excluded from broker-overpayment recovery metrics.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
from typing import Iterable

from freight.finding_factory import FIXED, INCLUDED, ChargeRule
from recoveryworks.engine import RecoveryEngine
from recoveryworks.models import EvidenceRef, FindingState, canonical_hash

from .freight_audit import (
    CarrierInvoice,
    FreightAuditDomainAdapter,
    FreightAuditEvidenceBundle,
    LineItem,
    ProofOfDelivery,
    RateConfirmation,
    map_freight_audit_to_recovery,
)
from .freight_authority import FreightAuthorityContext
from .freight_case import build_freight_review_packet


@dataclass(frozen=True)
class FreightAdversarialScenario:
    scenario_id: str
    description: str
    rate_confirmation: RateConfirmation | None
    invoice: CarrierInvoice | None
    pod: ProofOfDelivery | None
    charge_rules: tuple[ChargeRule, ...]
    expected_candidate_cents: int
    expected_validated_cents: int
    expected_case_states: tuple[str, ...]
    expected_supplemental_types: tuple[str, ...] = ()
    expected_integrity_blockers: tuple[str, ...] = ()
    expected_authority_blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class FreightAdversarialResult:
    scenario_id: str
    description: str
    expected_candidate_cents: int
    actual_candidate_cents: int
    expected_validated_cents: int
    actual_validated_cents: int
    actual_review_cents: int
    expected_case_states: tuple[str, ...]
    actual_case_states: tuple[str, ...]
    expected_supplemental_types: tuple[str, ...]
    actual_supplemental_types: tuple[str, ...]
    expected_integrity_blockers: tuple[str, ...]
    actual_integrity_blockers: tuple[str, ...]
    expected_authority_blockers: tuple[str, ...]
    actual_authority_blockers: tuple[str, ...]
    candidate_detected: bool
    expected_candidate_detected: bool
    validated_detected: bool
    expected_validated_detected: bool
    candidate_false_positive: bool
    candidate_false_negative: bool
    validation_false_positive: bool
    validation_false_negative: bool
    candidate_overclaim_cents: int
    candidate_underdetect_cents: int
    validated_overclaim_cents: int
    validated_underdetect_cents: int
    external_action_allowed: bool
    realized_recovery_asserted: bool
    packet_hash: str
    passed: bool
    result_hash: str


@dataclass(frozen=True)
class FreightAdversarialSummary:
    scenario_count: int
    passed_count: int
    failed_count: int
    candidate_true_positive: int
    candidate_true_negative: int
    candidate_false_positive: int
    candidate_false_negative: int
    validation_true_positive: int
    validation_true_negative: int
    validation_false_positive: int
    validation_false_negative: int
    expected_candidate_cents: int
    actual_candidate_cents: int
    candidate_overclaim_cents: int
    candidate_underdetect_cents: int
    expected_validated_cents: int
    actual_validated_cents: int
    validated_overclaim_cents: int
    validated_underdetect_cents: int
    exact_candidate_dollar_cases: int
    exact_validated_dollar_cases: int
    results: tuple[FreightAdversarialResult, ...]
    suite_hash: str


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _source(scenario_id: str, kind: str) -> EvidenceRef:
    label = f"{scenario_id}:{kind}"
    return EvidenceRef(
        evidence_id=label,
        source_hash=_sha(label),
        locator=f"synthetic://freight-adversarial/{scenario_id}/{kind}",
        kind=kind,
        verified=True,
        metadata={"synthetic": True, "scenario_id": scenario_id},
    )


def _rule(
    scenario_id: str,
    charge_code: str,
    *,
    pricing_model: str = FIXED,
    fixed_cents: int | None = None,
    verified: bool = True,
    authority_suffix: str = "primary",
) -> ChargeRule:
    if pricing_model == INCLUDED:
        fixed_cents = None
    return ChargeRule(
        buyer_id="buyer-adversarial",
        business_unit="BU-ADV",
        customer_id="customer-adv",
        carrier_id="carrier-adv",
        currency="USD",
        authority_document_id=f"{scenario_id}-authority-{authority_suffix}",
        charge_code=charge_code,
        pricing_model=pricing_model,
        effective_from="2026-09-01",
        effective_to="2026-09-30",
        document_source_hash=_sha(
            f"{scenario_id}:authority:{authority_suffix}:{charge_code}"
        ),
        verified_controlling_authority=verified,
        fixed_cents=fixed_cents,
        unit_rate_cents=None,
    )


def adversarial_scenarios() -> tuple[FreightAdversarialScenario, ...]:
    """Return the frozen nine-case synthetic adversarial matrix."""
    return (
        FreightAdversarialScenario(
            scenario_id="clean_invoice",
            description="Clean invoice matches the governing rate and should not produce recovery dollars.",
            rate_confirmation=RateConfirmation(
                "LOAD-CLEAN", "broker", "carrier", "A", "B", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            invoice=CarrierInvoice(
                "INV-CLEAN", "LOAD-CLEAN", "carrier", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            pod=ProofOfDelivery("LOAD-CLEAN", True),
            charge_rules=(_rule("clean_invoice", "LINEHAUL", fixed_cents=100_000),),
            expected_candidate_cents=0,
            expected_validated_cents=0,
            expected_case_states=(),
            expected_supplemental_types=("ok",),
        ),
        FreightAdversarialScenario(
            scenario_id="duplicate_fuel",
            description="Duplicate fuel line is reported three ways upstream but must count only once.",
            rate_confirmation=RateConfirmation(
                "LOAD-DUP", "broker", "carrier", "A", "B", 130_000,
                line_items=[
                    LineItem("Linehaul", 100_000),
                    LineItem("Fuel", 30_000),
                ],
            ),
            invoice=CarrierInvoice(
                "INV-DUP", "LOAD-DUP", "carrier", 160_000,
                line_items=[
                    LineItem("Linehaul", 100_000),
                    LineItem("Fuel", 30_000),
                    LineItem("Fuel Surcharge", 30_000),
                ],
            ),
            pod=ProofOfDelivery("LOAD-DUP", True),
            charge_rules=(_rule("duplicate_fuel", "FUEL", fixed_cents=30_000),),
            expected_candidate_cents=30_000,
            expected_validated_cents=30_000,
            expected_case_states=(FindingState.VALIDATED.value,),
            expected_supplemental_types=("line_overcharge", "total_mismatch"),
        ),
        FreightAdversarialScenario(
            scenario_id="wrong_linehaul_rate",
            description="Invoice linehaul exceeds the verified fixed rate by $200.",
            rate_confirmation=RateConfirmation(
                "LOAD-RATE", "broker", "carrier", "A", "B", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            invoice=CarrierInvoice(
                "INV-RATE", "LOAD-RATE", "carrier", 120_000,
                line_items=[LineItem("Linehaul", 120_000)],
            ),
            pod=ProofOfDelivery("LOAD-RATE", True),
            charge_rules=(_rule("wrong_linehaul_rate", "LINEHAUL", fixed_cents=100_000),),
            expected_candidate_cents=20_000,
            expected_validated_cents=20_000,
            expected_case_states=(FindingState.VALIDATED.value,),
            expected_supplemental_types=("total_mismatch",),
        ),
        FreightAdversarialScenario(
            scenario_id="unauthorized_liftgate",
            description="Liftgate charge is not on the rate confirmation and the governing rule says included.",
            rate_confirmation=RateConfirmation(
                "LOAD-LIFT", "broker", "carrier", "A", "B", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            invoice=CarrierInvoice(
                "INV-LIFT", "LOAD-LIFT", "carrier", 112_500,
                line_items=[
                    LineItem("Linehaul", 100_000),
                    LineItem("Liftgate Service", 12_500),
                ],
            ),
            pod=ProofOfDelivery("LOAD-LIFT", True),
            charge_rules=(
                _rule(
                    "unauthorized_liftgate",
                    "LIFTGATE",
                    pricing_model=INCLUDED,
                ),
            ),
            expected_candidate_cents=12_500,
            expected_validated_cents=12_500,
            expected_case_states=(FindingState.VALIDATED.value,),
            expected_supplemental_types=("total_mismatch",),
        ),
        FreightAdversarialScenario(
            scenario_id="unsupported_detention",
            description="Detention is billed but no POD exists, so no recovery dollars are asserted.",
            rate_confirmation=RateConfirmation(
                "LOAD-NOPOD", "broker", "carrier", "A", "B", 110_000,
                line_items=[LineItem("Linehaul", 100_000)],
                approved_accessorials={"detention": 10_000},
            ),
            invoice=CarrierInvoice(
                "INV-NOPOD", "LOAD-NOPOD", "carrier", 110_000,
                line_items=[
                    LineItem("Linehaul", 100_000),
                    LineItem("Detention", 10_000),
                ],
            ),
            pod=None,
            charge_rules=(_rule("unsupported_detention", "DETENTION", fixed_cents=10_000),),
            expected_candidate_cents=0,
            expected_validated_cents=0,
            expected_case_states=(),
            expected_supplemental_types=("detention_unsupported", "missing_pod"),
        ),
        FreightAdversarialScenario(
            scenario_id="missed_detention_revenue",
            description="POD proves detention the carrier failed to bill; retain it without contaminating broker-overpayment totals.",
            rate_confirmation=RateConfirmation(
                "LOAD-UNDER", "broker", "carrier", "A", "B", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
                approved_accessorials={"detention": 8_000},
                free_time_hours=2.0,
            ),
            invoice=CarrierInvoice(
                "INV-UNDER", "LOAD-UNDER", "carrier", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            pod=ProofOfDelivery(
                "LOAD-UNDER", True,
                arrival_time=datetime(2026, 9, 10, 8, 0),
                departure_time=datetime(2026, 9, 10, 12, 15),
            ),
            charge_rules=(_rule("missed_detention_revenue", "DETENTION", fixed_cents=8_000),),
            expected_candidate_cents=0,
            expected_validated_cents=0,
            expected_case_states=(),
            expected_supplemental_types=("detention_underbilled",),
        ),
        FreightAdversarialScenario(
            scenario_id="mismatched_load_ids",
            description="A real rate variance exists but document identity mismatch must block validated dollars.",
            rate_confirmation=RateConfirmation(
                "LOAD-ID-A", "broker", "carrier", "A", "B", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            invoice=CarrierInvoice(
                "INV-ID", "LOAD-ID-B", "carrier", 120_000,
                line_items=[LineItem("Linehaul", 120_000)],
            ),
            pod=ProofOfDelivery("LOAD-ID-A", True),
            charge_rules=(_rule("mismatched_load_ids", "LINEHAUL", fixed_cents=100_000),),
            expected_candidate_cents=20_000,
            expected_validated_cents=0,
            expected_case_states=(FindingState.REVIEW.value,),
            expected_supplemental_types=("load_id_mismatch", "total_mismatch"),
            expected_integrity_blockers=("load_id_mismatch",),
        ),
        FreightAdversarialScenario(
            scenario_id="bad_ocr_pod_timestamps",
            description="OCR-like inverted POD timestamps must not support detention math or recovery.",
            rate_confirmation=RateConfirmation(
                "LOAD-OCR", "broker", "carrier", "A", "B", 110_000,
                line_items=[LineItem("Linehaul", 100_000)],
                approved_accessorials={"detention": 10_000},
            ),
            invoice=CarrierInvoice(
                "INV-OCR", "LOAD-OCR", "carrier", 110_000,
                line_items=[
                    LineItem("Linehaul", 100_000),
                    LineItem("Detention", 10_000),
                ],
            ),
            pod=ProofOfDelivery(
                "LOAD-OCR", True,
                arrival_time=datetime(2026, 9, 10, 12, 0),
                departure_time=datetime(2026, 9, 10, 8, 0),
            ),
            charge_rules=(_rule("bad_ocr_pod_timestamps", "DETENTION", fixed_cents=10_000),),
            expected_candidate_cents=0,
            expected_validated_cents=0,
            expected_case_states=(),
            expected_supplemental_types=("bad_pod_data", "detention_unsupported"),
            expected_integrity_blockers=("bad_pod_data",),
        ),
        FreightAdversarialScenario(
            scenario_id="ambiguous_authority",
            description="Two simultaneously applicable controlling-rate candidates must keep a $200 discrepancy in REVIEW.",
            rate_confirmation=RateConfirmation(
                "LOAD-AMB", "broker", "carrier", "A", "B", 100_000,
                line_items=[LineItem("Linehaul", 100_000)],
            ),
            invoice=CarrierInvoice(
                "INV-AMB", "LOAD-AMB", "carrier", 120_000,
                line_items=[LineItem("Linehaul", 120_000)],
            ),
            pod=ProofOfDelivery("LOAD-AMB", True),
            charge_rules=(
                _rule("ambiguous_authority", "LINEHAUL", fixed_cents=100_000, authority_suffix="a"),
                _rule("ambiguous_authority", "LINEHAUL", fixed_cents=100_000, authority_suffix="b"),
            ),
            expected_candidate_cents=20_000,
            expected_validated_cents=0,
            expected_case_states=(FindingState.REVIEW.value,),
            expected_supplemental_types=("total_mismatch",),
            expected_authority_blockers=("AMBIGUOUS_APPLICABLE_CHARGE_RULE",),
        ),
    )


def _authority_context(scenario: FreightAdversarialScenario) -> FreightAuthorityContext:
    return FreightAuthorityContext(
        buyer_id="buyer-adversarial",
        business_unit="BU-ADV",
        customer_id="customer-adv",
        carrier_id="carrier-adv",
        currency="USD",
        service_date="2026-09-10",
        charge_rules=scenario.charge_rules,
    )


def _evidence_bundle(scenario: FreightAdversarialScenario) -> FreightAuditEvidenceBundle:
    return FreightAuditEvidenceBundle(
        invoice=(
            _source(scenario.scenario_id, "invoice")
            if scenario.invoice is not None else None
        ),
        rate_confirmation=(
            _source(scenario.scenario_id, "rate_confirmation")
            if scenario.rate_confirmation is not None else None
        ),
        pod=(
            _source(scenario.scenario_id, "pod")
            if scenario.pod is not None else None
        ),
    )


def build_adversarial_packet(
    scenario: FreightAdversarialScenario,
):
    """Build the integrated RecoveryOS packet for one frozen synthetic scenario."""
    domain = FreightAuditDomainAdapter().audit(
        scenario.rate_confirmation,
        scenario.invoice,
        scenario.pod,
    )
    mapping = map_freight_audit_to_recovery(
        domain,
        client_id="buyer-adversarial",
        counterparty_id="carrier-adv",
        currency="USD",
        evidence=_evidence_bundle(scenario),
        authority_context=_authority_context(scenario),
    )
    findings = RecoveryEngine().scan(mapping.observations)
    packet = build_freight_review_packet(mapping, findings)
    return mapping, findings, packet


def run_adversarial_scenario(
    scenario: FreightAdversarialScenario,
) -> FreightAdversarialResult:
    mapping, findings, packet = build_adversarial_packet(scenario)

    actual_states = tuple(sorted(case.state for case in packet.cases))
    actual_supplemental = tuple(
        sorted(item.finding_type for item in packet.supplemental_findings)
    )
    actual_integrity = tuple(sorted(set(mapping.integrity_blockers)))
    actual_authority = tuple(
        sorted({
            blocker
            for case in packet.cases
            for blocker in case.authority_blockers
        })
    )

    expected_states = tuple(sorted(scenario.expected_case_states))
    expected_supplemental = tuple(sorted(scenario.expected_supplemental_types))
    expected_integrity = tuple(sorted(scenario.expected_integrity_blockers))
    expected_authority = tuple(sorted(scenario.expected_authority_blockers))

    actual_candidate = packet.candidate_recovery_cents
    actual_validated = packet.validated_candidate_cents
    candidate_detected = actual_candidate > 0
    expected_candidate_detected = scenario.expected_candidate_cents > 0
    validated_detected = actual_validated > 0
    expected_validated_detected = scenario.expected_validated_cents > 0

    candidate_fp = candidate_detected and not expected_candidate_detected
    candidate_fn = expected_candidate_detected and not candidate_detected
    validation_fp = validated_detected and not expected_validated_detected
    validation_fn = expected_validated_detected and not validated_detected

    external_action = any(case.external_action_allowed for case in packet.cases)
    realized_asserted = any(
        case.realized_recovery_asserted for case in packet.cases
    )

    passed = (
        actual_candidate == scenario.expected_candidate_cents
        and actual_validated == scenario.expected_validated_cents
        and actual_states == expected_states
        and actual_supplemental == expected_supplemental
        and actual_integrity == expected_integrity
        and actual_authority == expected_authority
        and not external_action
        and not realized_asserted
    )

    body = {
        "schema": 1,
        "scenario_id": scenario.scenario_id,
        "expected_candidate_cents": scenario.expected_candidate_cents,
        "actual_candidate_cents": actual_candidate,
        "expected_validated_cents": scenario.expected_validated_cents,
        "actual_validated_cents": actual_validated,
        "actual_review_cents": packet.review_candidate_cents,
        "expected_case_states": list(expected_states),
        "actual_case_states": list(actual_states),
        "expected_supplemental_types": list(expected_supplemental),
        "actual_supplemental_types": list(actual_supplemental),
        "expected_integrity_blockers": list(expected_integrity),
        "actual_integrity_blockers": list(actual_integrity),
        "expected_authority_blockers": list(expected_authority),
        "actual_authority_blockers": list(actual_authority),
        "candidate_false_positive": candidate_fp,
        "candidate_false_negative": candidate_fn,
        "validation_false_positive": validation_fp,
        "validation_false_negative": validation_fn,
        "external_action_allowed": external_action,
        "realized_recovery_asserted": realized_asserted,
        "packet_hash": packet.packet_hash,
        "passed": passed,
    }

    return FreightAdversarialResult(
        scenario_id=scenario.scenario_id,
        description=scenario.description,
        expected_candidate_cents=scenario.expected_candidate_cents,
        actual_candidate_cents=actual_candidate,
        expected_validated_cents=scenario.expected_validated_cents,
        actual_validated_cents=actual_validated,
        actual_review_cents=packet.review_candidate_cents,
        expected_case_states=expected_states,
        actual_case_states=actual_states,
        expected_supplemental_types=expected_supplemental,
        actual_supplemental_types=actual_supplemental,
        expected_integrity_blockers=expected_integrity,
        actual_integrity_blockers=actual_integrity,
        expected_authority_blockers=expected_authority,
        actual_authority_blockers=actual_authority,
        candidate_detected=candidate_detected,
        expected_candidate_detected=expected_candidate_detected,
        validated_detected=validated_detected,
        expected_validated_detected=expected_validated_detected,
        candidate_false_positive=candidate_fp,
        candidate_false_negative=candidate_fn,
        validation_false_positive=validation_fp,
        validation_false_negative=validation_fn,
        candidate_overclaim_cents=max(
            actual_candidate - scenario.expected_candidate_cents, 0
        ),
        candidate_underdetect_cents=max(
            scenario.expected_candidate_cents - actual_candidate, 0
        ),
        validated_overclaim_cents=max(
            actual_validated - scenario.expected_validated_cents, 0
        ),
        validated_underdetect_cents=max(
            scenario.expected_validated_cents - actual_validated, 0
        ),
        external_action_allowed=external_action,
        realized_recovery_asserted=realized_asserted,
        packet_hash=packet.packet_hash,
        passed=passed,
        result_hash=canonical_hash(body),
    )


def run_adversarial_validation(
    scenarios: Iterable[FreightAdversarialScenario] | None = None,
) -> FreightAdversarialSummary:
    frozen = tuple(scenarios or adversarial_scenarios())
    results = tuple(run_adversarial_scenario(item) for item in frozen)

    def truth_counts(
        *,
        expected_attr: str,
        actual_attr: str,
    ) -> tuple[int, int, int, int]:
        tp = tn = fp = fn = 0
        for result in results:
            expected = bool(getattr(result, expected_attr))
            actual = bool(getattr(result, actual_attr))
            if expected and actual:
                tp += 1
            elif not expected and not actual:
                tn += 1
            elif not expected and actual:
                fp += 1
            else:
                fn += 1
        return tp, tn, fp, fn

    ctp, ctn, cfp, cfn = truth_counts(
        expected_attr="expected_candidate_detected",
        actual_attr="candidate_detected",
    )
    vtp, vtn, vfp, vfn = truth_counts(
        expected_attr="expected_validated_detected",
        actual_attr="validated_detected",
    )

    body = {
        "schema": 1,
        "scenario_ids": [item.scenario_id for item in frozen],
        "result_hashes": [item.result_hash for item in results],
    }
    return FreightAdversarialSummary(
        scenario_count=len(results),
        passed_count=sum(item.passed for item in results),
        failed_count=sum(not item.passed for item in results),
        candidate_true_positive=ctp,
        candidate_true_negative=ctn,
        candidate_false_positive=cfp,
        candidate_false_negative=cfn,
        validation_true_positive=vtp,
        validation_true_negative=vtn,
        validation_false_positive=vfp,
        validation_false_negative=vfn,
        expected_candidate_cents=sum(
            item.expected_candidate_cents for item in results
        ),
        actual_candidate_cents=sum(
            item.actual_candidate_cents for item in results
        ),
        candidate_overclaim_cents=sum(
            item.candidate_overclaim_cents for item in results
        ),
        candidate_underdetect_cents=sum(
            item.candidate_underdetect_cents for item in results
        ),
        expected_validated_cents=sum(
            item.expected_validated_cents for item in results
        ),
        actual_validated_cents=sum(
            item.actual_validated_cents for item in results
        ),
        validated_overclaim_cents=sum(
            item.validated_overclaim_cents for item in results
        ),
        validated_underdetect_cents=sum(
            item.validated_underdetect_cents for item in results
        ),
        exact_candidate_dollar_cases=sum(
            item.actual_candidate_cents == item.expected_candidate_cents
            for item in results
        ),
        exact_validated_dollar_cases=sum(
            item.actual_validated_cents == item.expected_validated_cents
            for item in results
        ),
        results=results,
        suite_hash=canonical_hash(body),
    )


def adversarial_summary_as_dict(
    summary: FreightAdversarialSummary,
) -> dict:
    return asdict(summary)


def render_adversarial_validation_markdown(
    summary: FreightAdversarialSummary,
) -> str:
    lines = [
        "# RecoveryOS Freight — Adversarial Validation",
        "",
        f"- Scenarios: **{summary.scenario_count}**",
        f"- Passed: **{summary.passed_count}**",
        f"- Failed: **{summary.failed_count}**",
        f"- Candidate detection TP/TN/FP/FN: **{summary.candidate_true_positive}/{summary.candidate_true_negative}/{summary.candidate_false_positive}/{summary.candidate_false_negative}**",
        f"- Validation TP/TN/FP/FN: **{summary.validation_true_positive}/{summary.validation_true_negative}/{summary.validation_false_positive}/{summary.validation_false_negative}**",
        f"- Expected candidate dollars: **USD {summary.expected_candidate_cents / 100:,.2f}**",
        f"- Actual candidate dollars: **USD {summary.actual_candidate_cents / 100:,.2f}**",
        f"- Candidate overclaim / under-detection: **USD {summary.candidate_overclaim_cents / 100:,.2f} / USD {summary.candidate_underdetect_cents / 100:,.2f}**",
        f"- Expected validated dollars: **USD {summary.expected_validated_cents / 100:,.2f}**",
        f"- Actual validated dollars: **USD {summary.actual_validated_cents / 100:,.2f}**",
        f"- Validated overclaim / under-detection: **USD {summary.validated_overclaim_cents / 100:,.2f} / USD {summary.validated_underdetect_cents / 100:,.2f}**",
        f"- Exact candidate-dollar cases: **{summary.exact_candidate_dollar_cases}/{summary.scenario_count}**",
        f"- Exact validated-dollar cases: **{summary.exact_validated_dollar_cases}/{summary.scenario_count}**",
        f"- Suite hash: `{summary.suite_hash}`",
        "",
        "Synthetic validation only. Candidate discrepancies, validated candidates, and realized recovery remain separate states.",
        "",
        "## Scenario results",
        "",
    ]
    for item in summary.results:
        lines.extend([
            f"### {item.scenario_id} — {'PASS' if item.passed else 'FAIL'}",
            f"- {item.description}",
            f"- Candidate cents expected/actual: **{item.expected_candidate_cents}/{item.actual_candidate_cents}**",
            f"- Validated cents expected/actual: **{item.expected_validated_cents}/{item.actual_validated_cents}**",
            f"- Case states: **{', '.join(item.actual_case_states) or 'none'}**",
            f"- Supplemental findings: **{', '.join(item.actual_supplemental_types) or 'none'}**",
            f"- Integrity blockers: **{', '.join(item.actual_integrity_blockers) or 'none'}**",
            f"- Authority blockers: **{', '.join(item.actual_authority_blockers) or 'none'}**",
            "",
        ])
    return "\\n".join(lines)


__all__ = [
    "FreightAdversarialResult",
    "FreightAdversarialScenario",
    "FreightAdversarialSummary",
    "adversarial_scenarios",
    "build_adversarial_packet",
    "adversarial_summary_as_dict",
    "render_adversarial_validation_markdown",
    "run_adversarial_scenario",
    "run_adversarial_validation",
]
