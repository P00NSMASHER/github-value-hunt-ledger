"""Synthetic CAP-019 source-authority fixture for EXP-003.

The fixture models a paginated bank/return observation run.  It deliberately
separates local request success, upstream freshness, result content, durable
commit, scope completeness, and cursor advancement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json


@dataclass(frozen=True)
class ObservationCase:
    name: str
    records: tuple[str, ...] = ()
    transport_ok: bool = True
    auth_ok: bool = True
    all_pages_complete: bool = True
    historical_update_complete: bool = True
    upstream_last_success: int = 200
    upstream_last_failure: int | None = None
    required_freshness: int = 150
    expected_accounts: tuple[str, ...] = ("acct-a", "acct-b")
    observed_accounts: tuple[str, ...] = ("acct-a", "acct-b")
    durable_commit_ok: bool = True
    mapped_sibling_commit_ok: bool = True
    refresh_requested: bool = False
    refresh_baseline: int | None = None
    cursor_before: str = "cursor-1"
    cursor_after: str = "cursor-2"


def observe(case: ObservationCase) -> dict:
    coverage = "VERIFIED_WINDOW"
    reasons: list[str] = []

    if not case.transport_ok:
        coverage = "UNAVAILABLE"
        reasons.append("transport_failure")
    elif not case.auth_ok:
        coverage = "UNAVAILABLE"
        reasons.append("authentication_failure")
    elif not case.all_pages_complete:
        coverage = "PARTIAL"
        reasons.append("pagination_incomplete")
    elif not case.historical_update_complete:
        coverage = "INITIALIZING"
        reasons.append("historical_update_incomplete")
    elif set(case.observed_accounts) != set(case.expected_accounts):
        coverage = "PARTIAL"
        reasons.append("source_scope_mismatch")
    elif not case.durable_commit_ok:
        coverage = "PARTIAL"
        reasons.append("durable_commit_failed")
    elif not case.mapped_sibling_commit_ok:
        coverage = "PARTIAL"
        reasons.append("mapped_sibling_commit_failed")
    elif (
        case.upstream_last_failure is not None
        and case.upstream_last_failure > case.upstream_last_success
    ):
        coverage = "UNAVAILABLE"
        reasons.append("upstream_failure_newer_than_success")
    elif case.upstream_last_success < case.required_freshness:
        coverage = "STALE"
        reasons.append("upstream_success_predates_required_window")
    elif (
        case.refresh_requested
        and case.refresh_baseline is not None
        and case.upstream_last_success <= case.refresh_baseline
    ):
        coverage = "STALE"
        reasons.append("refresh_produced_no_newer_source_update")

    ingestion_complete = (
        case.transport_ok
        and case.auth_ok
        and case.all_pages_complete
        and case.durable_commit_ok
        and case.mapped_sibling_commit_ok
        and set(case.observed_accounts) == set(case.expected_accounts)
    )
    cursor_advanced = ingestion_complete
    content = (
        "PRESENT"
        if case.records
        else "VERIFIED_EMPTY"
        if coverage == "VERIFIED_WINDOW"
        else "OBSERVED_EMPTY"
    )
    return {
        "name": case.name,
        "content": content,
        "coverage": coverage,
        "record_count": len(case.records),
        "cursor_before": case.cursor_before,
        "cursor_after": case.cursor_after if cursor_advanced else case.cursor_before,
        "cursor_advanced": cursor_advanced,
        "money_negative_authority": content == "VERIFIED_EMPTY" and coverage == "VERIFIED_WINDOW",
        "reasons": reasons,
    }


CASES = (
    ObservationCase("verified_empty_current"),
    ObservationCase("present_current", records=("return-1",)),
    ObservationCase("transport_failure", transport_ok=False),
    ObservationCase("authentication_failure", auth_ok=False),
    ObservationCase("page_failure", all_pages_complete=False),
    ObservationCase("historical_initializing", historical_update_complete=False),
    ObservationCase("local_success_upstream_stale", upstream_last_success=100),
    ObservationCase(
        "newer_upstream_failure",
        upstream_last_success=180,
        upstream_last_failure=190,
    ),
    ObservationCase("durable_commit_failure", durable_commit_ok=False),
    ObservationCase("mapped_sibling_failure", mapped_sibling_commit_ok=False),
    ObservationCase("source_scope_changed", observed_accounts=("acct-a",)),
    ObservationCase(
        "refresh_without_new_update",
        refresh_requested=True,
        refresh_baseline=200,
        upstream_last_success=200,
    ),
)


EXPECTED = {
    "verified_empty_current": ("VERIFIED_EMPTY", "VERIFIED_WINDOW", True, True),
    "present_current": ("PRESENT", "VERIFIED_WINDOW", True, False),
    "transport_failure": ("OBSERVED_EMPTY", "UNAVAILABLE", False, False),
    "authentication_failure": ("OBSERVED_EMPTY", "UNAVAILABLE", False, False),
    "page_failure": ("OBSERVED_EMPTY", "PARTIAL", False, False),
    "historical_initializing": ("OBSERVED_EMPTY", "INITIALIZING", True, False),
    "local_success_upstream_stale": ("OBSERVED_EMPTY", "STALE", True, False),
    "newer_upstream_failure": ("OBSERVED_EMPTY", "UNAVAILABLE", True, False),
    "durable_commit_failure": ("OBSERVED_EMPTY", "PARTIAL", False, False),
    "mapped_sibling_failure": ("OBSERVED_EMPTY", "PARTIAL", False, False),
    "source_scope_changed": ("OBSERVED_EMPTY", "PARTIAL", False, False),
    "refresh_without_new_update": ("OBSERVED_EMPTY", "STALE", True, False),
}


def unsafe_local_success_is_empty(case: ObservationCase) -> dict:
    result = observe(case)
    if case.transport_ok and case.auth_ok and not case.records:
        result["content"] = "VERIFIED_EMPTY"
        result["coverage"] = "VERIFIED_WINDOW"
        result["money_negative_authority"] = True
    return result


def unsafe_cursor_always_advances(case: ObservationCase) -> dict:
    result = observe(case)
    result["cursor_advanced"] = True
    result["cursor_after"] = case.cursor_after
    return result


def unsafe_ignore_scope(case: ObservationCase) -> dict:
    if set(case.observed_accounts) != set(case.expected_accounts):
        return observe(replace(case, observed_accounts=case.expected_accounts))
    return observe(case)


def mismatches(fn) -> list[str]:
    out = []
    for case in CASES:
        result = fn(case)
        actual = (
            result["content"],
            result["coverage"],
            result["cursor_advanced"],
            result["money_negative_authority"],
        )
        if actual != EXPECTED[case.name]:
            out.append(case.name)
    return out


def run_fixture() -> dict:
    assert not mismatches(observe)

    killed = {
        "local_http_success_equals_verified_empty": mismatches(unsafe_local_success_is_empty),
        "cursor_advances_before_complete_commit": mismatches(unsafe_cursor_always_advances),
        "silent_source_scope_change_is_complete": mismatches(unsafe_ignore_scope),
    }
    assert all(killed.values())

    # Delayed/backdated data must create a new observation, not rewrite the old one.
    delayed_first = observe(
        ObservationCase("delayed-first", upstream_last_success=100)
    )
    delayed_second = observe(
        ObservationCase("delayed-second", records=("backdated-return",), upstream_last_success=220)
    )
    assert delayed_first["content"] == "OBSERVED_EMPTY"
    assert delayed_first["coverage"] == "STALE"
    assert delayed_second["content"] == "PRESENT"
    assert delayed_second["coverage"] == "VERIFIED_WINDOW"
    assert delayed_first != delayed_second

    # An earlier valid empty receipt is only valid as-of its own cutoff. A later
    # return creates a new receipt and revokes any current no-return conclusion.
    cutoff_empty = observe(ObservationCase("cutoff-empty"))
    later_return = observe(
        ObservationCase("later-return", records=("return-late",), upstream_last_success=230)
    )
    assert cutoff_empty["money_negative_authority"] is True
    assert later_return["content"] == "PRESENT"
    assert later_return["money_negative_authority"] is False

    results = [observe(case) for case in CASES]
    body = {
        "base_cases": len(CASES),
        "base_failures": 0,
        "mutants_killed": {name: len(cases) for name, cases in killed.items()},
        "delayed_backdated_lifecycle": "PASS",
        "later_return_revokes_current_empty_conclusion": "PASS",
        "unsafe_verified_empty_cases": sum(
            1
            for result in results
            if result["money_negative_authority"]
            and result["name"] != "verified_empty_current"
        ),
        "results": results,
    }
    body["result_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return body


if __name__ == "__main__":
    print(json.dumps(run_fixture(), sort_keys=True))
