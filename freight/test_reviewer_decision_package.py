"""Parser/assembly tests and real-core single/split import parity regressions."""
import hashlib
import json
from dataclasses import asdict

import pytest
from freight import reviewer_decision_package as pkg

CTX = dict(review_packet_hash="a"*64, review_routing_hash="b"*64, truth_hash="c"*64)


def row(index=0, **change):
    return dict(case_hash=hashlib.sha256(str(index).encode()).hexdigest(),
                disposition="CONFIRMED", reviewer_minutes=3,
                reviewed_at="2026-09-21T09:00:00-04:00") | change


def encode(rows=None, **change):
    value = dict(schema_version=1, **CTX, decisions=[row()] if rows is None else rows)
    return json.dumps(value | change).encode()


def merge(*files):
    return pkg.merge_decision_exports(files, **CTX)


def test_two_thousand_and_one_decisions_preserved_across_exports():
    first, last = encode([row(i) for i in range(2000)]), encode([row(2000)])
    result = merge(first, last)
    assert len(result.decisions) == 2001
    assert {x.case_hash for x in result.decisions} == {row(i)["case_hash"] for i in range(2001)}
    assert result.source_file_count == 2


def test_exact_replay_is_idempotent_and_reported():
    data = encode()
    result = merge(data, data)
    assert len(result.decisions) == 1
    assert result.duplicate_file_count == 1
    assert len(result.source_file_hashes) == 1


def test_identical_rows_across_different_files_are_idempotent():
    result = merge(encode(), encode([row(), row(1)]))
    assert len(result.decisions) == 2
    assert result.duplicate_decision_count == 1


def test_input_order_does_not_change_canonical_decisions_or_sources():
    a, b = encode([row(1)]), encode([row(0)])
    assert merge(a, b) == merge(b, a)


def test_offsets_normalize_without_changing_review_instant():
    result = merge(encode(), encode([row(reviewed_at="2026-09-21T13:00:00Z")]))
    assert len(result.decisions) == 1
    assert result.decisions[0].reviewed_at == "2026-09-21T13:00:00.000000Z"


@pytest.mark.parametrize("change", [dict(disposition="FALSE_POSITIVE"),
    dict(reviewer_minutes=4), dict(reviewed_at="2026-09-21T13:01:00Z")])
def test_conflicts_reject_the_entire_handoff(change):
    with pytest.raises(ValueError, match="conflicting"):
        merge(encode(), encode([row(1), row(**change)]))


@pytest.mark.parametrize("key", tuple(CTX))
def test_stale_context_in_later_file_rejects_everything(key):
    with pytest.raises(ValueError, match="context"):
        merge(encode(), encode([row(1)], **{key:"0"*64}))


def test_duplicate_rows_in_one_file_remain_invalid():
    with pytest.raises(ValueError, match="within one export"):
        merge(encode([row(), row()]))


@pytest.mark.parametrize("minutes", [True, -1, 1.5, "3", None, 2**53])
def test_effort_requires_safe_nonnegative_integer(minutes):
    with pytest.raises(ValueError, match="reviewer_minutes"):
        merge(encode([row(reviewer_minutes=minutes)]))


@pytest.mark.parametrize("time", ["2026-02-30T09:00:00Z", "2026-09-21T09:00:00",
    "2026-09-21T09:00:00-00:00", "2026-09-21T09:00:00+01:60", "2026-09-21T09:00:00+24:00",
    "2026-09-21T24:00:00Z", "2026-09-21T09:00:00.1234567Z", None,
    "0001-01-01T00:00:00+01:00"])
def test_invalid_dates_offsets_and_precision_are_rejected(time):
    with pytest.raises(ValueError, match="reviewed_at"):
        merge(encode([row(reviewed_at=time)]))


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'\xff', b'[[[', b'[]'])
def test_ambiguous_or_malformed_json_is_rejected(raw):
    with pytest.raises(ValueError):
        merge(raw)


@pytest.mark.parametrize("change", [dict(schema_version=True), dict(schema_version=2),
    dict(reviewer_role="Controller"), dict(decisions={}), dict(truth_hash=None)])
def test_unknown_identity_fields_and_wrong_schema_fail(change):
    with pytest.raises(ValueError):
        merge(encode(**change))


@pytest.mark.parametrize("change", [dict(case_hash="bad"), dict(disposition="APPROVED"),
    dict(approved=True), dict(disposition=[]), dict(reviewer_role="Controller")])
def test_bad_or_extra_row_fields_fail(change):
    with pytest.raises(ValueError):
        merge(encode([row(**change)]))


def test_empty_decisions_are_valid_but_no_files_is_not():
    assert merge(encode([])).decisions == ()
    with pytest.raises(ValueError, match="at least one"):
        merge()


def test_per_file_size_and_row_limits():
    with pytest.raises(ValueError, match="size limit"):
        merge(b" " * (pkg.MAX_FILE_BYTES+1))
    with pytest.raises(ValueError, match="row limit"):
        merge(encode([row(i) for i in range(pkg.MAX_FILE_DECISIONS+1)]))


def test_total_files_bytes_and_decisions_are_bounded(monkeypatch):
    with pytest.raises(ValueError, match="too many"):
        pkg.merge_decision_exports((encode() for _ in range(pkg.MAX_EXPORT_FILES+1)), **CTX)
    monkeypatch.setattr(pkg, "MAX_PACKAGE_BYTES", len(encode())+1)
    with pytest.raises(ValueError, match="byte limit"):
        merge(encode(), encode())
    monkeypatch.setattr(pkg, "MAX_PACKAGE_BYTES", 100000)
    monkeypatch.setattr(pkg, "MAX_COMBINED_DECISIONS", 1)
    with pytest.raises(ValueError, match="decision limit"):
        merge(encode([row(), row(1)]))


def test_raw_bytes_are_not_treated_as_a_file_collection():
    with pytest.raises(ValueError, match="iterable"):
        pkg.merge_decision_exports(encode(), **CTX)


def test_source_bytes_and_inputs_are_not_mutated_or_returned():
    raw = encode()
    result = merge(raw)
    assert raw == encode()
    assert result.source_file_hashes == (hashlib.sha256(raw).hexdigest(),)
    assert "reviewer_role" not in asdict(result)


def _review_context(count=2):
    from freight.contracts import PopulationRow, freeze_population
    from freight.finding_factory import ChargeRule, InvoiceCharge, FIXED, derive_batch
    from freight.review_packet import build_review_packet
    from freight.review_queue import build_review_queue
    from freight.review_routing import route_review_packet

    population = freeze_population(
        'synthetic', 'qa', 'synthetic import parity',
        [PopulationRow(f'I{i}', f'S{i}', 'C', 'K', 'USD', f'source-{i}')
         for i in range(count + 1)],
    )
    charges = tuple(
        InvoiceCharge('synthetic', 'qa', f'I{i}', f'S{i}', 'C', 'K', 'USD',
                      f'X{i}', 'DETENTION' if i < count else 'UNKNOWN',
                      '2026-09-10', 1, 12500, f'line-{i}')
        for i in range(count + 1)
    )
    rules = (ChargeRule('synthetic', 'qa', 'C', 'K', 'USD', 'synthetic-rate',
                        'DETENTION', FIXED, '2026-09-01', None,
                        'a' * 64, True, 10000, None),)
    factory = derive_batch(population, charges, rules)
    queue = build_review_queue(factory)
    packet = build_review_packet(factory, queue, charges, rules)
    return dict(review_packet=packet, review_routing=route_review_packet(packet),
                truth=factory.truth)


def _decision_export(ctx, **changes):
    row = dict(case_hash=ctx['review_routing'].buyer_review_case_hashes[0],
               disposition='UNRESOLVED', reviewer_minutes=3,
               reviewed_at='2026-09-21T09:00:00-04:00')
    row.update(changes)
    return json.dumps(dict(
        schema_version=1, review_packet_hash=ctx['review_packet'].packet_hash,
        review_routing_hash=ctx['review_routing'].routing_hash,
        truth_hash=ctx['truth'].truth_hash, decisions=[row],
    )).encode()


@pytest.mark.parametrize('entrypoint', ['single', 'multiple'])
@pytest.mark.parametrize('change', [
    {'reviewed_at': '2026-09-21T09:00:00+00:60'},
    {'reviewed_at': '2026-09-21T09:00:00-00:00'},
    {'reviewed_at': '2026-09-21T09:00:00.1234567Z'},
    {'reviewer_minutes': 2**53},
])
def test_both_entrypoints_reject_noncanonical_export_values(entrypoint, change):
    from freight.reviewer_workbench import (
        import_reviewer_decisions, import_reviewer_decision_files,
    )

    ctx = _review_context()
    raw = _decision_export(ctx, **change)
    with pytest.raises(ValueError):
        if entrypoint == 'single':
            import_reviewer_decisions(data=raw, reviewer_role='Synthetic Controller', **ctx)
        else:
            import_reviewer_decision_files(files=(raw,), reviewer_role='Synthetic Controller', **ctx)


def test_valid_single_and_multiple_exports_produce_identical_bound_reviews():
    from freight.reviewer_workbench import (
        import_reviewer_decisions, import_reviewer_decision_files,
    )

    ctx = _review_context()
    raw = _decision_export(ctx)
    single = import_reviewer_decisions(data=raw, reviewer_role='Synthetic Controller', **ctx)
    multiple = import_reviewer_decision_files(files=(raw,), reviewer_role='Synthetic Controller', **ctx)
    assert single == multiple
    assert single.unresolved_count == 1 and single.confirmed_count == 0
    from freight.buyer_review_workflow import verify_buyer_review_batch
    verify_buyer_review_batch(batch=single, **ctx)
