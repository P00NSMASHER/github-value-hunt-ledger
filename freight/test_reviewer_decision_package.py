"""Pure parser/assembly tests. Full buyer-review integration is separate."""
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
