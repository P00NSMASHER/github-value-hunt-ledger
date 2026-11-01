"""Offline adversarial checks for the reference ledger, not hosted cash proof."""
from dataclasses import asdict, replace
import hashlib
import json
import random

import pytest

from freight.contracts import (
    AuthorityRef, PopulationRow, RecoveryLedger, SettlementEvent,
    REVIEW, VALIDATED, freeze_population, freeze_truth, make_finding,
    open_incumbent_output, seal_incumbent_submission,
)


def digest(body):
    # Independent serialization oracle; do not reuse the implementation's hash helper.
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def fixture():
    rows = [PopulationRow(f"inv-{n}", f"ship-{n}", "cust", "carrier", "USD",
                          digest(f"invented-invoice-{n}")) for n in range(1, 5)]
    population = freeze_population("buyer", "unit", "four invented invoices", rows)
    authorities = [AuthorityRef("rate", "buyer", "unit", "cust", "carrier", "USD",
                                digest("invented-rate"))]
    findings = [make_finding(
        finding_id=f"f-{n}", buyer_id="buyer", business_unit="unit",
        invoice_id=f"inv-{n}", shipment_id=f"ship-{n}", customer_id="cust",
        carrier_id="carrier", currency="USD", authority_id="rate" if n < 3 else None,
        expected_cents=10000, actual_cents=12500 if n < 3 else 15000,
        status=VALIDATED if n < 3 else REVIEW,
    ) for n in range(1, 4)]
    truth = freeze_truth(population, authorities, findings)
    sealed = seal_incumbent_submission(population, digest("invented-incumbent"))
    incumbent = open_incumbent_output(population=population, truth=truth,
                                     submission=sealed, finding_ids=["f-2"])
    return population, truth, incumbent


def event(**changes):
    values = dict(buyer_id="buyer", business_unit="unit", settlement_id="s-new",
                  finding_id="f-1", amount_cents=1000, currency="USD",
                  source_hash=digest("invented-settlement"))
    values.update(changes)
    return SettlementEvent(**values)


def rehash_truth(truth):
    body = asdict(truth)
    body.pop("truth_hash")
    return replace(truth, truth_hash=digest({"schema": 3, **body}))


def rehash_finding(finding):
    body = asdict(finding)
    body.pop("proof_hash")
    return replace(finding, proof_hash=digest({"schema": 2, **body}))


def rehash_incumbent(incumbent):
    body = asdict(incumbent)
    body.pop("output_hash")
    return replace(incumbent, output_hash=digest({"schema": 2, **body}))


def certificates(ledger):
    return tuple(ledger.certificate(f"f-{n}") for n in range(1, 4))


@pytest.mark.parametrize("rehash_outer", [False, True])
@pytest.mark.parametrize("changes", [
    {"actual_cents": 99000}, {"expected_cents": 0}, {"proof_hash": digest("unbound")},
    {"status": REVIEW}, {"invoice_id": "changed-invoice"},
])
def test_ledger_rejects_changed_finding_under_stale_inner_digest(changes, rehash_outer):
    _, truth, _ = fixture()
    changed = replace(truth, findings=(replace(truth.findings[0], **changes), *truth.findings[1:]))
    if rehash_outer:
        changed = rehash_truth(changed)
    with pytest.raises(ValueError):
        RecoveryLedger(changed)


@pytest.mark.parametrize("field", ["truth_hash", "population_hash"])
@pytest.mark.parametrize("bad", [None, "", True, "a" * 63, "A" * 64, "not-a-digest"])
def test_ledger_requires_canonical_manifest_digests(field, bad):
    _, truth, _ = fixture()
    changed = replace(truth, **{field: bad})
    if field == "population_hash":
        changed = rehash_truth(changed)
    with pytest.raises(ValueError):
        RecoveryLedger(changed)


def test_ledger_rejects_valid_shaped_but_unbound_truth_digest():
    _, truth, _ = fixture()
    with pytest.raises(ValueError):
        RecoveryLedger(replace(truth, truth_hash=digest("different-truth")))


@pytest.mark.parametrize("changes", [
    {"buyer_id": "other"}, {"business_unit": "other"},
    {"customer_id": "other"}, {"carrier_id": "other"}, {"currency": "EUR"},
    {"authority_id": "missing"}, {"authority_id": ""}, {"authority_id": False},
    {"status": "SETTLED"}, {"invoice_id": ""}, {"shipment_id": ""},
    {"finding_id": ""}, {"actual_cents": -1}, {"expected_cents": -1},
])
def test_self_hashed_invalid_finding_cannot_create_ledger(changes):
    _, truth, _ = fixture()
    altered = rehash_finding(replace(truth.findings[0], **changes))
    changed = rehash_truth(replace(truth, findings=(altered, *truth.findings[1:])))
    with pytest.raises(ValueError):
        RecoveryLedger(changed)


@pytest.mark.parametrize("field", ["expected_cents", "actual_cents"])
@pytest.mark.parametrize("bad", [True, False, 0.0, 2500.5, "2500", None,
                                  float("inf"), float("nan")])
def test_self_hashed_noninteger_finding_money_is_rejected(field, bad):
    _, truth, _ = fixture()
    altered = rehash_finding(replace(truth.findings[0], **{field: bad}))
    changed = rehash_truth(replace(truth, findings=(altered, *truth.findings[1:])))
    with pytest.raises(ValueError):
        RecoveryLedger(changed)


@pytest.mark.parametrize("changes", [
    {"buyer_id": "other"}, {"business_unit": "other"},
    {"customer_id": "other"}, {"carrier_id": "other"}, {"currency": "EUR"},
    {"authority_id": ""}, {"source_hash": ""},
])
def test_rehashed_invalid_authority_is_rejected(changes):
    _, truth, _ = fixture()
    changed = rehash_truth(replace(truth, authorities=(replace(truth.authorities[0], **changes),)))
    with pytest.raises(ValueError):
        RecoveryLedger(changed)


@pytest.mark.parametrize("part", ["findings", "authorities"])
def test_rehashed_duplicate_proof_members_are_rejected(part):
    _, truth, _ = fixture()
    members = getattr(truth, part)
    changed = rehash_truth(replace(truth, **{part: (*members, members[0])}))
    with pytest.raises(ValueError):
        RecoveryLedger(changed)


def test_rehashed_missing_controlling_authority_is_rejected():
    _, truth, _ = fixture()
    with pytest.raises(ValueError):
        RecoveryLedger(rehash_truth(replace(truth, authorities=())))


@pytest.mark.parametrize("field,bad", [
    ("buyer_id", ""), ("business_unit", ""), ("findings", None),
    ("authorities", None), ("findings", {}), ("authorities", {}),
    ("findings", [None]), ("authorities", [None]),
])
def test_bad_truth_structure_is_a_validation_error(field, bad):
    _, truth, _ = fixture()
    with pytest.raises(ValueError):
        RecoveryLedger(replace(truth, **{field: bad}))


@pytest.mark.parametrize("field,changes", [
    ("finding_ids", ()), ("source_hash", digest("other-source")),
    ("submission_hash", digest("other-submission")), ("output_hash", digest("other-output")),
])
def test_incumbent_tampering_cannot_remove_fee_exclusions(field, changes):
    _, truth, incumbent = fixture()
    with pytest.raises(ValueError):
        RecoveryLedger(truth, replace(incumbent, **{field: changes}))


@pytest.mark.parametrize("field", ["submission_hash", "output_hash"])
@pytest.mark.parametrize("bad", [None, "", True, "A" * 64, "a" * 63])
def test_incumbent_digest_types_are_checked(field, bad):
    _, truth, incumbent = fixture()
    with pytest.raises(ValueError):
        RecoveryLedger(truth, replace(incumbent, **{field: bad}))


@pytest.mark.parametrize("bad", [None, "f-2", [False], [1], [None], [""], ["f-2", "f-2"]])
def test_rehashed_incumbent_ids_are_not_silently_coerced(bad):
    _, truth, incumbent = fixture()
    changed = rehash_incumbent(replace(incumbent, finding_ids=bad))
    with pytest.raises(ValueError):
        RecoveryLedger(truth, changed)


def test_rehashed_incumbent_output_cannot_retain_unbound_submission():
    _, truth, incumbent = fixture()
    changed = rehash_incumbent(replace(incumbent, source_hash=digest("swapped-file")))
    with pytest.raises(ValueError):
        RecoveryLedger(truth, changed)


@pytest.mark.parametrize("field", ["buyer_id", "business_unit", "truth_hash", "population_hash"])
def test_incumbent_must_remain_bound_to_ledger_scope(field):
    _, truth, incumbent = fixture()
    with pytest.raises(ValueError):
        RecoveryLedger(truth, rehash_incumbent(replace(incumbent, **{field: "different"})))


@pytest.mark.parametrize("field", ["incumbent_preidentified", "automatic_credit",
                                   "preexisting_credit", "ambiguous_allocation"])
@pytest.mark.parametrize("bad", ["false", "true", 0, 1, None, [], {}])
def test_invalid_settlement_flags_fail_without_consuming_capacity_or_identity(field, bad):
    _, truth, incumbent = fixture()
    ledger = RecoveryLedger(truth, incumbent)
    before = certificates(ledger)
    with pytest.raises(ValueError):
        ledger.apply(event(**{field: bad}))
    assert certificates(ledger) == before
    assert ledger.apply(event()).allocated_cents == 1000


@pytest.mark.parametrize("bad", [True, False, 0.0, 0.5, "1000", None,
                                  float("inf"), float("nan"), -1])
@pytest.mark.parametrize("ambiguous", [False, True])
def test_invalid_settlement_money_is_rejected_before_any_branch(bad, ambiguous):
    _, truth, incumbent = fixture()
    ledger = RecoveryLedger(truth, incumbent)
    before = certificates(ledger)
    with pytest.raises(ValueError):
        ledger.apply(event(amount_cents=bad, ambiguous_allocation=ambiguous))
    assert certificates(ledger) == before
    assert ledger.apply(event()).allocated_cents == 1000


def test_all_flags_are_validated_even_for_ambiguous_events():
    _, truth, _ = fixture()
    ledger = RecoveryLedger(truth)
    with pytest.raises(ValueError):
        ledger.apply(event(ambiguous_allocation=True, automatic_credit=None))
    assert ledger.certificate("f-1").realized_cents == 0


@pytest.mark.parametrize("field,bad", [
    ("finding_id", None), ("finding_id", []), ("settlement_id", ""),
    ("source_hash", None), ("currency", []),
])
def test_invalid_event_shape_has_no_partial_effect(field, bad):
    _, truth, _ = fixture()
    ledger = RecoveryLedger(truth)
    before = certificates(ledger)
    with pytest.raises(ValueError):
        ledger.apply(event(**{field: bad}))
    assert certificates(ledger) == before


def test_failed_followup_does_not_poison_existing_ledger():
    _, truth, incumbent = fixture()
    ledger = RecoveryLedger(truth, incumbent)
    ledger.apply(event(settlement_id="existing", source_hash=digest("existing"), amount_cents=300))
    before = certificates(ledger)
    with pytest.raises(ValueError):
        ledger.apply(event(preexisting_credit=None))
    assert certificates(ledger) == before
    assert ledger.apply(event()).allocated_cents == 1000
    assert ledger.certificate("f-1").realized_cents == 1300


def test_mutating_caller_finding_cannot_change_verified_ledger_snapshot():
    _, truth, _ = fixture()
    ledger = RecoveryLedger(truth)
    before = ledger.certificate("f-1")
    # Deserialization libraries can bypass frozen dataclass assignment restrictions.
    object.__setattr__(truth.findings[0], "actual_cents", 99000)
    assert ledger.certificate("f-1") == before
    ledger.apply(event(amount_cents=99000))
    assert ledger.certificate("f-1").realized_cents == 2500


def test_clean_and_review_only_truth_remains_supported():
    population, truth, _ = fixture()
    clean = freeze_truth(population, [], [])
    ledger = RecoveryLedger(clean)
    with pytest.raises(ValueError, match="unknown finding"):
        ledger.certificate("nonexistent")
    review = freeze_truth(population, [], [truth.findings[2]])
    ledger = RecoveryLedger(review)
    assert ledger.apply(event(finding_id="f-3")).allocated_cents == 0
    assert ledger.certificate("f-3").fee_eligible_cents == 0


def test_reordering_and_empty_incumbent_results_preserve_valid_behavior():
    population, truth, incumbent = fixture()
    original = RecoveryLedger(truth, incumbent)
    reordered = replace(truth, findings=list(reversed(truth.findings)),
                        authorities=list(reversed(truth.authorities)))
    assert certificates(RecoveryLedger(reordered, incumbent)) == certificates(original)
    sealed = seal_incumbent_submission(population, incumbent.source_hash)
    empty = open_incumbent_output(population=population, truth=truth,
                                  submission=sealed, finding_ids=[])
    ledger = RecoveryLedger(truth, empty)
    assert ledger.apply(event(finding_id="f-2")).fee_eligible_cents == 1000


def test_partial_caps_incumbent_exclusions_and_duplicate_denials():
    _, truth, incumbent = fixture()
    ledger = RecoveryLedger(truth, incumbent)
    assert ledger.apply(event()).allocated_cents == 1000
    with pytest.raises(ValueError, match="duplicate settlement_id"):
        ledger.apply(event(source_hash=digest("unused")))
    with pytest.raises(ValueError, match="source already consumed"):
        ledger.apply(event(settlement_id="unused"))
    assert ledger.apply(event(settlement_id="s-2", source_hash=digest("s-2"), amount_cents=9000)).allocated_cents == 1500
    assert ledger.apply(event(settlement_id="s-3", source_hash=digest("s-3"), finding_id="f-2")).fee_eligible_cents == 0
    cert = ledger.certificate("f-1")
    assert (cert.validated_cents, cert.realized_cents, cert.fee_eligible_cents) == (2500, 2500, 2500)
    body = asdict(cert)
    body.pop("certificate_hash")
    assert cert.certificate_hash == digest({"schema": 2, **body})


@pytest.mark.parametrize("seed", range(12))
def test_invented_engagements_match_independent_integer_accounting(seed):
    _, truth, incumbent = fixture()
    ledger = RecoveryLedger(truth, incumbent)
    rng = random.Random(seed)
    expected = {f"f-{n}": [0, 0] for n in range(1, 4)}
    for n in range(24):
        fid = f"f-{rng.randrange(1, 4)}"
        flags = dict(incumbent_preidentified=bool(rng.randrange(2)),
                     automatic_credit=bool(rng.randrange(2)),
                     preexisting_credit=bool(rng.randrange(2)),
                     ambiguous_allocation=bool(rng.randrange(2)))
        amount = rng.randrange(0, 2000)
        limit = 0 if fid == "f-3" else 2500
        allocated = 0 if flags["ambiguous_allocation"] else min(amount, limit - expected[fid][0])
        eligible = 0 if fid == "f-2" or any(flags.values()) else allocated
        result = ledger.apply(event(settlement_id=f"s-{n}", source_hash=digest(f"s-{n}"),
                                    finding_id=fid, amount_cents=amount, **flags))
        assert (result.allocated_cents, result.fee_eligible_cents) == (allocated, eligible)
        expected[fid][0] += allocated
        expected[fid][1] += eligible
    for fid, totals in expected.items():
        cert = ledger.certificate(fid)
        assert [cert.realized_cents, cert.fee_eligible_cents] == totals
        assert 0 <= cert.fee_eligible_cents <= cert.realized_cents <= cert.validated_cents
