"""Synthetic adversarial acceptance for licensed temporal-charge review."""
from dataclasses import replace

import pytest

from freight.canonical_schema import ChargeLine, ShipmentFacts, SourceArtifact, build_record
from freight.detention_review import (
    DetentionTimeline,
    compile_detention_policy,
    detention_to_review_case,
    review_detention_charge,
)
from freight.vendor_detention_rounding import rounded_minutes


def fixture_record(*, charge_code="DETENTION", billed=21_000, sources=None, additional_charges=()):
    artifacts = (
        ("invoice", "CARRIER_INVOICE", "a"),
        ("start", "GATE_EVENT", "b"),
        ("end", "ELD_EVENT", "c"),
        ("rate", "CONTRACT", "d"),
        ("payment", "PAYMENT_CONFIRMATION", "e"),
    ) if sources is None else sources
    return build_record(
        buyer_id="BUYER-1", business_unit="BU-1", invoice_id="INV-1",
        invoice_date="2026-09-15", customer_id="CUSTOMER-1", currency="USD",
        shipment=ShipmentFacts(
            shipment_id="SHIP-1", carrier_id="CARRIER-1", mode="TL",
            service_date="2026-09-14", origin_postal="17901",
            destination_postal="21224", actual_weight_grams=10_000,
            package_count=1,
        ),
        charges=(ChargeLine("DET-1", charge_code, billed), *additional_charges),
        sources=tuple(SourceArtifact(
            source_id=k, kind=kind, sha256=sha * 64,
            observed_at="2026-09-15T00:00:00.000000Z", transport="API",
        ) for k, kind, sha in artifacts),
    )


def policy_payload(**overrides):
    values = dict(
        policy_id="RATE-1", buyer_id="BUYER-1", business_unit="BU-1",
        customer_id="CUSTOMER-1", carrier_id="CARRIER-1",
        origin_postal="17901", destination_postal="21224", currency="USD",
        mode="TL", charge_code="DETENTION", effective_from="2026-01-01",
        effective_to="2026-12-31", free_minutes=60, grace_minutes=15,
        billing_increment_minutes=15, cents_per_increment=1500,
        rounding_mode="CEILING_TO_INCREMENT",
    )
    values.update(overrides)
    return values


def rule(*, verified=True, **overrides):
    return compile_detention_policy(
        policy_payload(**overrides), source_sha256="d" * 64,
        verified_controlling_authority=verified,
    )


def timeline(**overrides):
    values = dict(
        start_at="2026-09-14T07:50:00-04:00",
        end_at="2026-09-14T12:35:00-04:00",
        start_source_sha256="b" * 64,
        end_source_sha256="c" * 64,
        prior_paid_cents=6000,
        prior_payment_source_sha256="e" * 64,
    )
    values.update(overrides)
    return DetentionTimeline(**values)


def test_realistic_detention_stays_review_only_and_enters_existing_human_queue():
    candidate = review_detention_charge(fixture_record(), "DET-1", rule(), timeline())
    assert candidate.elapsed_minutes == 285
    assert candidate.billable_minutes == 210
    assert candidate.rounded_minutes == 210
    assert candidate.supported_remaining_cents == 15_000
    assert candidate.candidate_excess_cents == 6_000
    assert candidate.status == "REVIEW"
    assert candidate.validated_cents == candidate.recovered_cents == candidate.fee_eligible_cents == 0
    assert candidate.case_id == "time:" + candidate.proof_hash
    case = detention_to_review_case(candidate)
    assert case.amount_cents == 6000
    assert "HUMAN_REVIEW_REQUIRED" in case.blocker_codes
    assert candidate.proof_hash in case.evidence_hashes
    assert review_detention_charge(fixture_record(), "DET-1", rule(), timeline()) == candidate


def test_prior_payment_reduces_supported_remaining_without_double_credit():
    out = review_detention_charge(
        fixture_record(), "DET-1", rule(),
        timeline(prior_paid_cents=0, prior_payment_source_sha256=None),
    )
    assert out.supported_remaining_cents == 21_000
    assert out.candidate_excess_cents == 0
    assert detention_to_review_case(out) is None


def test_license_adapted_rounding_modes_and_thresholds():
    assert rounded_minutes(11, 15, "CEILING_TO_INCREMENT") == 15
    assert rounded_minutes(11, 15, "FLOOR_TO_INCREMENT") == 0
    assert rounded_minutes(7, 15, "HALF_UP_TO_INCREMENT") == 0
    assert rounded_minutes(8, 15, "HALF_UP_TO_INCREMENT") == 15
    assert rounded_minutes(0, 15, "CEILING_TO_INCREMENT") == 0


@pytest.mark.parametrize("mode,expected", [
    ("CEILING_TO_INCREMENT", 15), ("FLOOR_TO_INCREMENT", 0),
    ("HALF_UP_TO_INCREMENT", 15),
])
def test_contract_rounding_is_explicit_not_guessed(mode, expected):
    out = review_detention_charge(
        fixture_record(billed=1_500), "DET-1",
        rule(free_minutes=0, grace_minutes=0, rounding_mode=mode),
        timeline(end_at="2026-09-14T08:01:00-04:00", prior_paid_cents=0, prior_payment_source_sha256=None),
    )
    assert out.rounded_minutes == expected
    assert out.validated_cents == 0


def test_dst_fall_back_is_offset_aware_and_hashes_canonical_utc_instants():
    t = timeline(
        start_at="2026-11-01T01:30:00-04:00", end_at="2026-11-01T01:15:00-05:00",
        prior_paid_cents=0, prior_payment_source_sha256=None,
    )
    with_offset = review_detention_charge(fixture_record(), "DET-1", rule(), t)
    utc = review_detention_charge(
        fixture_record(), "DET-1", rule(),
        replace(t, start_at="2026-11-01T05:30:00Z", end_at="2026-11-01T06:15:00Z"),
    )
    assert with_offset.elapsed_minutes == 45
    assert with_offset.timeline_hash == utc.timeline_hash
    assert with_offset == utc


def test_unverified_contract_cannot_create_financial_candidate():
    result = review_detention_charge(fixture_record(), "DET-1", rule(verified=False), timeline())
    assert result.status == "NEED_EVIDENCE"
    assert "CONTRACT_NOT_HUMAN_VERIFIED" in result.blocker_codes
    assert result.candidate_excess_cents is None
    assert detention_to_review_case(result) is None


@pytest.mark.parametrize("overrides,blocker", [
    ({"currency": "EUR"}, "CONTRACT_SCOPE_MISMATCH"),
    ({"carrier_id": "OTHER"}, "CONTRACT_SCOPE_MISMATCH"),
    ({"origin_postal": "21224", "destination_postal": "17901"}, "CONTRACT_SCOPE_MISMATCH"),
    ({"charge_code": "DEMURRAGE"}, "CONTRACT_SCOPE_MISMATCH"),
    ({"effective_to": "2026-09-13"}, "CONTRACT_NOT_EFFECTIVE_ON_SERVICE_DATE"),
])
def test_scope_currency_date_and_charge_type_are_fail_closed(overrides, blocker):
    out = review_detention_charge(fixture_record(), "DET-1", rule(**overrides), timeline())
    assert blocker in out.blocker_codes
    assert out.candidate_excess_cents is None


def test_invoice_only_events_do_not_become_independent_timeline_proof():
    out = review_detention_charge(
        fixture_record(), "DET-1", rule(),
        timeline(start_source_sha256="a" * 64),
    )
    assert "MISSING_INDEPENDENT_TIME_EVENT" in out.blocker_codes
    assert out.candidate_excess_cents is None


def test_missing_prior_payment_document_blocks_without_guessing():
    out = review_detention_charge(
        fixture_record(), "DET-1", rule(),
        timeline(prior_payment_source_sha256=None),
    )
    assert "MISSING_PRIOR_PAYMENT_EVIDENCE" in out.blocker_codes
    assert out.candidate_excess_cents is None


def test_duplicated_same_type_charge_lines_are_not_double_counted():
    out = review_detention_charge(
        fixture_record(additional_charges=(ChargeLine("DET-2", "DETENTION", 3000),)),
        "DET-1", rule(), timeline(),
    )
    assert "MULTIPLE_SAME_TYPE_CHARGES_REQUIRE_ALLOCATION" in out.blocker_codes
    assert out.candidate_excess_cents is None


def test_prior_paid_above_gross_requires_reconciliation():
    out = review_detention_charge(
        fixture_record(), "DET-1", rule(), timeline(prior_paid_cents=22_000),
    )
    assert "PRIOR_PAID_EXCEEDS_SUPPORTED_GROSS" in out.blocker_codes
    assert out.supported_remaining_cents is None


def test_no_source_contract_is_not_sufficient_even_if_verified_flag_is_true():
    sources = (
        ("invoice", "CARRIER_INVOICE", "a"),
        ("start", "GATE_EVENT", "b"),
        ("end", "ELD_EVENT", "c"),
        ("payment", "PAYMENT_CONFIRMATION", "e"),
    )
    out = review_detention_charge(
        fixture_record(sources=sources), "DET-1", rule(), timeline(),
    )
    assert "CONTRACT_SOURCE_NOT_IN_RECORD" in out.blocker_codes


def test_evidence_or_contract_change_changes_proof_hash():
    a = review_detention_charge(fixture_record(), "DET-1", rule(), timeline())
    b = review_detention_charge(fixture_record(), "DET-1", rule(cents_per_increment=1400), timeline())
    c = review_detention_charge(
        fixture_record(), "DET-1", rule(), timeline(end_at="2026-09-14T12:34:00-04:00"),
    )
    assert len({a.proof_hash, b.proof_hash, c.proof_hash}) == 3


@pytest.mark.parametrize("invalid", [
    {"start_at": "2026-09-14T07:50:00"},
    {"end_at": "2026-09-14T07:49:00-04:00"},
    {"end_source_sha256": "source"},
    {"prior_paid_cents": True},
    {"prior_paid_cents": -1},
])
def test_malformed_time_evidence_or_money_is_rejected(invalid):
    with pytest.raises(ValueError):
        review_detention_charge(
            fixture_record(), "DET-1", rule(), timeline(**invalid),
        )


@pytest.mark.parametrize("overrides", [
    {"billing_increment_minutes": 0},
    {"billing_increment_minutes": 1441},
    {"free_minutes": True},
    {"cents_per_increment": 2**63},
    {"rounding_mode": "UNDEFINED"},
    {"currency": "US$"},
    {"effective_from": "2026-02-30"},
])
def test_invalid_contract_rule_fails_compile(overrides):
    with pytest.raises(ValueError):
        rule(**overrides)


def test_mutated_policy_or_canonical_record_is_rejected():
    with pytest.raises(ValueError, match="policy hash mismatch"):
        review_detention_charge(
            fixture_record(), "DET-1", replace(rule(), free_minutes=0), timeline(),
        )
    with pytest.raises(ValueError, match="record hash mismatch"):
        review_detention_charge(
            replace(fixture_record(), invoice_id="FORGED"), "DET-1", rule(), timeline(),
        )


def test_unsupported_charge_and_oversized_session_are_blocked():
    with pytest.raises(ValueError, match="supported time-based"):
        review_detention_charge(
            fixture_record(charge_code="FUEL"), "DET-1", rule(), timeline(),
        )
    out = review_detention_charge(
        fixture_record(), "DET-1", rule(),
        timeline(end_at="2026-11-01T12:35:00-04:00"),
    )
    assert "TIME_WINDOW_EXCEEDS_45_DAYS" in out.blocker_codes
    assert out.candidate_excess_cents is None


def test_overflow_is_rejected_instead_of_wrapping_dollars():
    with pytest.raises(ValueError, match="exceeds integer cents"):
        review_detention_charge(
            fixture_record(), "DET-1", rule(cents_per_increment=2**62),
            timeline(prior_paid_cents=0, prior_payment_source_sha256=None),
        )


def test_review_case_tampering_is_rejected_before_human_queue():
    candidate = review_detention_charge(fixture_record(), "DET-1", rule(), timeline())
    with pytest.raises(ValueError, match="candidate hash mismatch"):
        detention_to_review_case(replace(candidate, candidate_excess_cents=21_000))


def test_conflicting_source_kinds_cannot_turn_invoice_into_gate_evidence():
    sources = (
        ("invoice", "CARRIER_INVOICE", "a"),
        ("forged", "GATE_EVENT", "a"),
        ("end", "ELD_EVENT", "c"),
        ("rate", "CONTRACT", "d"),
        ("payment", "PAYMENT_CONFIRMATION", "e"),
    )
    out = review_detention_charge(
        fixture_record(sources=sources), "DET-1", rule(),
        timeline(start_source_sha256="a" * 64),
    )
    assert "MISSING_INDEPENDENT_TIME_EVENT" in out.blocker_codes
    assert out.candidate_excess_cents is None


# The portfolio's required GitHub Action uses 'python -m unittest discover'.
# It would otherwise import these pytest-style functions without executing any
# of them, yielding a misleading green CI status. Bridge every one of the 36
# synthetic cases into the required unittest runner (without duplicating logic).
import unittest


class TemporalUnittestGate(unittest.TestCase):
    def test_all_36_adversarial_cases_are_executed_by_required_ci(self):
        direct = (
            test_realistic_detention_stays_review_only_and_enters_existing_human_queue,
            test_prior_payment_reduces_supported_remaining_without_double_credit,
            test_license_adapted_rounding_modes_and_thresholds,
            test_dst_fall_back_is_offset_aware_and_hashes_canonical_utc_instants,
            test_unverified_contract_cannot_create_financial_candidate,
            test_invoice_only_events_do_not_become_independent_timeline_proof,
            test_missing_prior_payment_document_blocks_without_guessing,
            test_duplicated_same_type_charge_lines_are_not_double_counted,
            test_prior_paid_above_gross_requires_reconciliation,
            test_no_source_contract_is_not_sufficient_even_if_verified_flag_is_true,
            test_evidence_or_contract_change_changes_proof_hash,
            test_mutated_policy_or_canonical_record_is_rejected,
            test_unsupported_charge_and_oversized_session_are_blocked,
            test_overflow_is_rejected_instead_of_wrapping_dollars,
            test_review_case_tampering_is_rejected_before_human_queue,
            test_conflicting_source_kinds_cannot_turn_invoice_into_gate_evidence,
        )
        executed = 0
        for scenario in direct:
            with self.subTest(case=scenario.__name__):
                scenario()
                executed += 1
        for mode, expected in (
            ("CEILING_TO_INCREMENT", 15), ("FLOOR_TO_INCREMENT", 0),
            ("HALF_UP_TO_INCREMENT", 15),
        ):
            with self.subTest(case="rounding", mode=mode):
                test_contract_rounding_is_explicit_not_guessed(mode, expected)
                executed += 1
        for changes, blocker in (
            ({"currency": "EUR"}, "CONTRACT_SCOPE_MISMATCH"),
            ({"carrier_id": "OTHER"}, "CONTRACT_SCOPE_MISMATCH"),
            ({"origin_postal": "21224", "destination_postal": "17901"}, "CONTRACT_SCOPE_MISMATCH"),
            ({"charge_code": "DEMURRAGE"}, "CONTRACT_SCOPE_MISMATCH"),
            ({"effective_to": "2026-09-13"}, "CONTRACT_NOT_EFFECTIVE_ON_SERVICE_DATE"),
        ):
            with self.subTest(case="scope", changes=changes):
                test_scope_currency_date_and_charge_type_are_fail_closed(changes, blocker)
                executed += 1
        for invalid in (
            {"start_at": "2026-09-14T07:50:00"},
            {"end_at": "2026-09-14T07:49:00-04:00"},
            {"end_source_sha256": "source"},
            {"prior_paid_cents": True},
            {"prior_paid_cents": -1},
        ):
            with self.subTest(case="malformed", invalid=invalid):
                test_malformed_time_evidence_or_money_is_rejected(invalid)
                executed += 1
        for invalid in (
            {"billing_increment_minutes": 0},
            {"billing_increment_minutes": 1441},
            {"free_minutes": True},
            {"cents_per_increment": 2**63},
            {"rounding_mode": "UNDEFINED"},
            {"currency": "US$"},
            {"effective_from": "2026-02-30"},
        ):
            with self.subTest(case="invalid_contract", invalid=invalid):
                test_invalid_contract_rule_fails_compile(invalid)
                executed += 1
        self.assertEqual(executed, 36)
