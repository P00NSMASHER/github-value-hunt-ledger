from freight.performance_benchmark import (
    MODES,
    build_authority_book,
    build_report,
    make_record,
    run_failure_injection,
    run_interruption_recovery,
    run_trial,
    validate_report,
)
from freight.rating_engine import RATED, rate_record


def test_all_six_modes_rate_without_review_in_nominal_benchmark():
    book = build_authority_book()
    seen = set()
    for index in range(len(MODES)):
        record = make_record(index)
        seen.add(record.mode)
        result = rate_record(record, book)
        assert result.status == RATED
        assert result.expected_total_cents is not None
        assert result.rating_hash
    assert seen == set(MODES)


def test_small_scale_replay_is_bitwise_deterministic():
    trial = run_trial(120, 1, replay=True)
    assert trial.primary.record_count == 120
    assert trial.primary.rated_count == 120
    assert trial.primary.review_count == 0
    assert trial.deterministic_replay is True
    assert trial.aggregate_replay_equal is True
    assert trial.primary.result_digest == trial.replay.result_digest


def test_failure_injection_routes_exact_missing_authority_count_to_review():
    result = run_failure_injection(count=200, missing_authority_every=17)
    assert result.actual_review_count == result.expected_review_count
    assert result.rated_count + result.actual_review_count == 200
    assert result.deterministic_replay is True


def test_interruption_recovery_replays_last_chunk_without_double_counting():
    result = run_interruption_recovery(
        count=120,
        chunk_size=20,
        fail_after_chunks=3,
    )
    assert result.replayed_chunk_count == 1
    assert result.deterministic_resume is True
    assert result.no_duplicate_aggregate is True
    assert result.baseline_digest == result.resumed_digest
    assert result.baseline_variance_cents == result.resumed_variance_cents


def test_report_validation_accepts_replayed_small_tiers():
    report = build_report(
        (60, 120),
        small_trials=1,
        medium_trials=1,
        large_trials=1,
        replay_max_count=120,
        failure_count=60,
        interruption_count=60,
        interruption_chunk_size=10,
        memory_probe_count=60,
    )
    validate_report(report)
    assert report.mode_count == 6
    assert len(report.trials) == 2
    assert report.interruption_recovery.deterministic_resume is True
    assert report.interruption_recovery.no_duplicate_aggregate is True
    assert report.memory_probe.record_count == 60
    assert report.memory_probe.python_peak_heap_mb > 0
    assert report.report_hash
