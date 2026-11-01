"""Adversarial package-consumer tests using invented records, never customer proof."""
from dataclasses import asdict, replace
import hashlib

import pytest

from freight.contracts import (
    AuthorityRef, PopulationManifest, PopulationRow, TruthManifest,
    SealedIncumbentSubmission, IncumbentOutput, Finding, REVIEW, VALIDATED,
    canonical_hash, freeze_population, freeze_truth, make_finding,
    seal_incumbent_submission, open_incumbent_output,
)
from freight.pilot_package import SourceEntry, build_data_room_manifest, build_pilot_package


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def chain():
    """A valid mixed clean/validated/review population with two authorities."""
    buyer, unit = "synthetic-buyer", "synthetic-unit"
    rows = [PopulationRow(f"invoice-{i}", f"shipment-{i}", "customer", "carrier",
                          "USD", digest(f"row-{i}")) for i in range(1, 4)]
    population = freeze_population(buyer, unit, "all three synthetic invoices", rows)
    authorities = [AuthorityRef(f"authority-{i}", buyer, unit, "customer", "carrier",
                               "USD", digest(f"authority-{i}")) for i in (1, 2)]
    findings = [make_finding(
        finding_id=f"finding-{i}", buyer_id=buyer, business_unit=unit,
        invoice_id=f"invoice-{i}", shipment_id=f"shipment-{i}", customer_id="customer",
        carrier_id="carrier", currency="USD", authority_id="authority-1" if i == 1 else None,
        expected_cents=10000, actual_cents=12500, status=VALIDATED if i == 1 else REVIEW,
    ) for i in (1, 2)]
    truth = freeze_truth(population, authorities, findings)
    submission = seal_incumbent_submission(population, digest("incumbent-source"))
    incumbent = open_incumbent_output(population=population, truth=truth,
                                     submission=submission, finding_ids=["finding-1"])
    entries = [SourceEntry(kind, buyer, unit, kind, digest(source), True, True, False, 30)
               for kind, source in (("invoice", "invoice-file"), ("authority", "authority-1"),
                                     ("incumbent_output", "incumbent-source"))]
    room = build_data_room_manifest(buyer, unit, entries)
    return [room, population, truth, submission, incumbent]


# Deliberately independent test-only rehasher: it checks no policy and proves no consent.
SHAPES = {PopulationManifest: (2, "manifest_hash"), TruthManifest: (3, "truth_hash"),
          SealedIncumbentSubmission: (1, "sealed_hash"), IncumbentOutput: (2, "output_hash"),
          Finding: (2, "proof_hash")}


def rehash(record):
    schema, field = SHAPES[type(record)]
    body = asdict(record)
    body.pop(field)
    return replace(record, **{field: canonical_hash({"schema": schema, **body})})


def relink(parts, *, finding_hashes=False):
    """An attacker can recompute self-hashes; invalid semantics must still fail."""
    room, population, truth, submission, incumbent = parts
    population = rehash(population)
    if finding_hashes:
        truth = replace(truth, findings=tuple(rehash(f) for f in truth.findings))
    truth = rehash(replace(truth, population_hash=population.manifest_hash))
    submission = rehash(replace(submission, population_hash=population.manifest_hash))
    incumbent = rehash(replace(incumbent, population_hash=population.manifest_hash,
                               truth_hash=truth.truth_hash, submission_hash=submission.sealed_hash,
                               source_hash=submission.source_hash))
    return [room, population, truth, submission, incumbent]


def test_valid_chain_retains_all_population_and_proof_hashes():
    parts = chain()
    package = build_pilot_package(*parts)
    assert package.population_hash == parts[1].manifest_hash
    assert package.truth_hash == parts[2].truth_hash
    assert package.incumbent_submission_hash == parts[3].sealed_hash
    assert package.incumbent_output_hash == parts[4].output_hash
    assert len(parts[1].rows) == 3  # clean cases stay in the population
    assert parts[2].findings[1].validated_cents == 0


def test_canonical_reordering_preserves_identity_and_inputs():
    parts = chain()
    expected = build_pilot_package(*parts)
    parts[1] = replace(parts[1], rows=tuple(reversed(parts[1].rows)))
    parts[2] = replace(parts[2], authorities=tuple(reversed(parts[2].authorities)),
                       findings=tuple(reversed(parts[2].findings)))
    before = [asdict(x) for x in parts]
    assert build_pilot_package(*parts) == expected
    assert [asdict(x) for x in parts] == before


def test_valid_rebuilt_revision_changes_identity_without_asserting_external_truth():
    parts = chain()
    expected = build_pilot_package(*parts)
    f = parts[2].findings[0]
    parts[2] = replace(parts[2], findings=(replace(f, actual_cents=13000), parts[2].findings[1]))
    revised = relink(parts, finding_hashes=True)
    result = build_pilot_package(*revised)
    assert result.package_hash != expected.package_hash
    assert result.population_hash == expected.population_hash
    # Internally consistent invented metadata is not independent proof of a real recovery.
    assert "real_cash_recovered" not in asdict(result)


def test_empty_findings_and_incumbent_results_do_not_invent_an_error():
    parts = chain()
    parts[2] = freeze_truth(parts[1], [], [])
    parts[4] = open_incumbent_output(population=parts[1], truth=parts[2],
                                     submission=parts[3], finding_ids=[])
    assert build_pilot_package(*parts).truth_hash == parts[2].truth_hash


@pytest.mark.parametrize("index, field", [(1, "manifest_hash"), (2, "truth_hash"),
                                         (3, "sealed_hash"), (4, "output_hash")])
@pytest.mark.parametrize("value", [None, "", True, "A" * 64, "a" * 63, digest("wrong")])
def test_supplied_hashes_cannot_replace_content_verification(index, field, value):
    parts = chain()
    parts[index] = replace(parts[index], **{field: value})
    # Preserve the old cross-object equality checks so they cannot be the only defense.
    if index == 1:
        parts[2] = replace(parts[2], population_hash=value)
        parts[3] = replace(parts[3], population_hash=value)
        parts[4] = replace(parts[4], population_hash=value)
    elif index == 2:
        parts[4] = replace(parts[4], truth_hash=value)
    elif index == 3:
        parts[4] = replace(parts[4], submission_hash=value)
    with pytest.raises(ValueError, match="hash mismatch"):
        build_pilot_package(*parts)


@pytest.mark.parametrize("kind", ["selection", "row", "authority", "finding", "output"])
def test_changed_content_cannot_keep_old_package_identity(kind):
    parts = chain()
    if kind == "selection":
        parts[1] = replace(parts[1], selection_rule="cherry-picked subset")
    elif kind == "row":
        parts[1] = replace(parts[1], rows=(replace(parts[1].rows[0], source_hash=digest("changed")),
                                         *parts[1].rows[1:]))
    elif kind == "authority":
        parts[2] = replace(parts[2], authorities=(replace(parts[2].authorities[0],
                              source_hash=digest("changed")), parts[2].authorities[1]))
    elif kind == "finding":
        parts[2] = replace(parts[2], findings=(replace(parts[2].findings[0], actual_cents=999999),
                                             parts[2].findings[1]))
    else:
        parts[4] = replace(parts[4], finding_ids=())
    with pytest.raises(ValueError, match="hash mismatch"):
        build_pilot_package(*parts)


@pytest.mark.parametrize("field, value", [
    ("actual_cents", 13000), ("status", REVIEW), ("proof_hash", digest("wrong")),
    ("proof_hash", None), ("proof_hash", "A" * 64),
])
def test_rehashed_truth_cannot_hide_a_stale_finding_proof(field, value):
    parts = chain()
    parts[2] = replace(parts[2], findings=(replace(parts[2].findings[0], **{field: value}),
                                         parts[2].findings[1]))
    parts = relink(parts, finding_hashes=False)
    with pytest.raises(ValueError, match="finding proof hash mismatch"):
        build_pilot_package(*parts)


@pytest.mark.parametrize("field, value", [
    ("buyer_id", "other-buyer"), ("business_unit", "other-unit"),
    ("invoice_id", "outside-population"), ("shipment_id", "outside-population"),
    ("customer_id", "other-customer"), ("carrier_id", "other-carrier"), ("currency", "EUR"),
    ("authority_id", "missing-authority"), ("authority_id", None),
    ("authority_id", True), ("status", "SETTLED"), ("finding_id", ""),
])
def test_recomputed_hashes_do_not_bypass_finding_semantics(field, value):
    parts = chain()
    parts[2] = replace(parts[2], findings=(replace(parts[2].findings[0], **{field: value}),
                                         parts[2].findings[1]))
    with pytest.raises(ValueError):
        build_pilot_package(*relink(parts, finding_hashes=True))


@pytest.mark.parametrize("field", ["actual_cents", "expected_cents"])
@pytest.mark.parametrize("value", [True, False, 1.5, 10000.0, "10000", None, -1])
def test_money_requires_nonnegative_integer_cents_even_after_rehash(field, value):
    parts = chain()
    parts[2] = replace(parts[2], findings=(replace(parts[2].findings[0], **{field: value}),
                                         parts[2].findings[1]))
    with pytest.raises(ValueError, match="non-negative integer cents"):
        build_pilot_package(*relink(parts, finding_hashes=True))


@pytest.mark.parametrize("field, value", [
    ("buyer_id", "other-buyer"), ("business_unit", "other-unit"),
    ("customer_id", "other-customer"), ("carrier_id", "other-carrier"),
    ("currency", "EUR"), ("source_hash", ""), ("authority_id", ""),
])
def test_recomputed_hashes_do_not_bypass_authority_semantics(field, value):
    parts = chain()
    parts[2] = replace(parts[2], authorities=(replace(parts[2].authorities[0], **{field: value}),
                                            parts[2].authorities[1]))
    with pytest.raises(ValueError):
        build_pilot_package(*relink(parts))


@pytest.mark.parametrize("kind", ["rows", "authorities", "findings", "incumbent"])
def test_duplicate_records_fail_even_when_all_hashes_are_recomputed(kind):
    parts = chain()
    if kind == "rows":
        parts[1] = replace(parts[1], rows=(*parts[1].rows, parts[1].rows[0]))
    elif kind == "authorities":
        parts[2] = replace(parts[2], authorities=(*parts[2].authorities, parts[2].authorities[0]))
    elif kind == "findings":
        parts[2] = replace(parts[2], findings=(*parts[2].findings, parts[2].findings[0]))
    else:
        parts[4] = replace(parts[4], finding_ids=("finding-1", "finding-1"))
    with pytest.raises(ValueError, match="duplicate"):
        build_pilot_package(*relink(parts))


@pytest.mark.parametrize("change", [{"rows": ()}, {"selection_rule": ""}])
def test_invalid_population_is_not_fixed_by_rehashing(change):
    parts = chain()
    parts[1] = replace(parts[1], **change)
    with pytest.raises(ValueError):
        build_pilot_package(*relink(parts))


@pytest.mark.parametrize("field, value", [("invoice_id", ""), ("shipment_id", ""),
                                         ("source_hash", ""), ("customer_id", None)])
def test_invalid_population_rows_fail_before_use(field, value):
    parts = chain()
    parts[1] = replace(parts[1], rows=(replace(parts[1].rows[0], **{field: value}),
                                     *parts[1].rows[1:]))
    with pytest.raises(ValueError):
        build_pilot_package(*relink(parts))


@pytest.mark.parametrize("value", [1, True, None, "", " "])
def test_incumbent_ids_are_not_coerced_into_valid_strings(value):
    parts = chain()
    parts[4] = replace(parts[4], finding_ids=(value,))
    with pytest.raises(ValueError):
        build_pilot_package(*relink(parts))


@pytest.mark.parametrize("index, field", [(1, "buyer_id"), (2, "business_unit"),
                                         (3, "buyer_id"), (4, "business_unit")])
def test_cross_scope_top_level_objects_still_fail(index, field):
    parts = chain()
    parts[index] = replace(parts[index], **{field: "outside"})
    with pytest.raises(ValueError, match="scope mismatch"):
        build_pilot_package(*parts)
