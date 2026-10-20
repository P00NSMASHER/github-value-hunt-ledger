"""Adverse and integration checks for private RETALLY source observations."""

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from ai_business_os.ceo_command_center import CommandCenterError, CommandCenterOperator
from ai_business_os.production_bridge import (
    ProductionBridgeError, ProductionReadBridge, RETALLY_GROUP_SOURCE_SQL,
    _assert_read_only_sql,
)
from ai_business_os.retally_group import GroupCatalogError, build_group_view, load_catalog
from ai_business_os.retally_group_dashboard import render_dashboard
from ai_business_os.retally_group_private import (
    GroupObservationError, build_private_group_observation, normalize_source_snapshot,
)
from ai_business_os.test_ceo_command_center import FakeProduction


FINGERPRINT = "a" * 64
NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def source_snapshot():
    return {
        "schema_fingerprint": FINGERPRINT,
        "observed_at": (NOW - timedelta(seconds=60)).isoformat(),
        "businesses": [
            {"id": "business-freight", "slug": "freightrecovery",
             "customer_records": 2, "financial_event_records": 5, "external_outcome_records": 7},
            {"id": "business-recovery", "slug": "recoveryworks",
             "customer_records": 3, "financial_event_records": 6, "external_outcome_records": 8},
            {"id": "business-research", "slug": "capturebrief",
             "customer_records": 11, "financial_event_records": 13, "external_outcome_records": 17},
            {"id": "excluded-private-business", "slug": "unrelated-private-project",
             "customer_records": 19, "financial_event_records": 23, "external_outcome_records": 29},
        ],
        "unattributed_external_outcome_records": 31,
    }


def observe(snapshot=None, **kwargs):
    return build_private_group_observation(
        source_snapshot() if snapshot is None else snapshot,
        expected_schema_fingerprint=FINGERPRINT, now=NOW, **kwargs,
    )


class PrivateGroupObservationTests(unittest.TestCase):
    def test_exact_shapes_reject_private_extras_and_missing_fields(self):
        for level in ("snapshot", "business"):
            for mutation in ("extra", "missing"):
                with self.subTest(level=level, mutation=mutation):
                    snapshot = source_snapshot()
                    target = snapshot if level == "snapshot" else snapshot["businesses"][0]
                    if mutation == "extra":
                        target["confidential_payload"] = "private-value-must-not-appear"
                    else:
                        del target[next(iter(target))]
                    with self.assertRaises(GroupObservationError) as caught:
                        observe(snapshot)
                    self.assertNotIn("private-value-must-not-appear", str(caught.exception))

    def test_business_array_and_rows_require_structured_values(self):
        for value in (None, {}, (), 1, True, "null", "{}", "[null]", "[[]]", "not-json"):
            with self.subTest(value=value):
                snapshot = source_snapshot()
                snapshot["businesses"] = value
                with self.assertRaises(GroupObservationError):
                    observe(snapshot)

    def test_duplicate_identity_rows_cannot_double_count(self):
        for key in ("id", "slug"):
            snapshot = source_snapshot()
            snapshot["businesses"][1][key] = snapshot["businesses"][0][key]
            with self.subTest(key=key), self.assertRaisesRegex(GroupObservationError, "duplicate"):
                observe(snapshot)

    def test_identity_fields_are_strict_and_errors_do_not_echo_private_input(self):
        for key in ("id", "slug"):
            for value in (None, True, 42, "", "private secret with spaces", {"secret": "value"}):
                with self.subTest(key=key, value=value):
                    snapshot = source_snapshot()
                    snapshot["businesses"][0][key] = value
                    with self.assertRaises(GroupObservationError) as caught:
                        observe(snapshot)
                    self.assertNotIn("secret", str(caught.exception))

    def test_counts_reject_boolean_float_negative_oversized_and_string_values(self):
        for key in ("customer_records", "financial_event_records", "external_outcome_records",
                    "unattributed_external_outcome_records"):
            for value in (False, True, 1.0, -1, 2**63, "1", None, float("nan")):
                with self.subTest(key=key, value=value):
                    snapshot = source_snapshot()
                    target = snapshot if key.startswith("unattributed") else snapshot["businesses"][0]
                    target[key] = value
                    with self.assertRaises(GroupObservationError):
                        observe(snapshot)

    def test_fingerprints_require_valid_matching_digests(self):
        for value in (None, True, 1, "", "a" * 63, "g" * 64, "b" * 64):
            snapshot = source_snapshot()
            snapshot["schema_fingerprint"] = value
            with self.subTest(value=value), self.assertRaises(GroupObservationError):
                observe(snapshot)
        for value in (None, True, "bad"):
            with self.subTest(expected=value), self.assertRaises(GroupObservationError):
                normalize_source_snapshot(source_snapshot(), expected_schema_fingerprint=value)
        normalized = normalize_source_snapshot(source_snapshot(), expected_schema_fingerprint="A" * 64)
        self.assertEqual(FINGERPRINT, normalized["schema_fingerprint"])

    def test_naive_invalid_and_future_observation_times_fail(self):
        for value in (None, True, "not-a-date", "2026-10-20", "2026-10-20T11:59:00",
                      datetime(2026, 10, 20, 11, 59), NOW + timedelta(microseconds=1)):
            with self.subTest(value=value):
                snapshot = source_snapshot()
                snapshot["observed_at"] = value
                with self.assertRaises(GroupObservationError):
                    observe(snapshot)
        with self.assertRaises(GroupObservationError):
            build_private_group_observation(source_snapshot(),
                                            expected_schema_fingerprint=FINGERPRINT,
                                            now=NOW.replace(tzinfo=None))

    def test_freshness_boundary_describes_observation_age(self):
        snapshot = source_snapshot()
        snapshot["observed_at"] = NOW - timedelta(seconds=300)
        self.assertEqual("CURRENT", observe(snapshot)["freshness"])
        snapshot["observed_at"] -= timedelta(microseconds=1)
        stale = observe(snapshot)
        self.assertEqual("STALE", stale["freshness"])
        self.assertTrue(all(value is None for value in stale["verified_metrics"].values()))
        for value in (True, False, 0, -1, 1.5, "300"):
            with self.subTest(value=value), self.assertRaises(GroupObservationError):
                observe(max_age_seconds=value)

    def test_invalid_and_unknown_offsets_fail_but_postgres_utc_is_accepted(self):
        for offset in ("+00:60", "+01:99", "+24:00", "-00:00", "-00"):
            snapshot = source_snapshot()
            snapshot["observed_at"] = "2026-10-20T11:00:00" + offset
            with self.subTest(offset=offset), self.assertRaises(GroupObservationError):
                observe(snapshot)
        snapshot = source_snapshot()
        snapshot["observed_at"] = "2026-10-20 11:59:00.000000+00"
        self.assertEqual("CURRENT", observe(snapshot)["freshness"])

    def test_replay_and_row_order_have_identical_observations_without_input_mutation(self):
        snapshot = source_snapshot()
        original = copy.deepcopy(snapshot)
        first = observe(snapshot)
        reordered = copy.deepcopy(snapshot)
        reordered["businesses"].reverse()
        reordered["observed_at"] = "2026-10-20T07:59:00-04:00"
        self.assertEqual(first, observe(reordered))
        self.assertEqual(first, observe(snapshot))
        self.assertEqual(original, snapshot)
        first["entries"][0]["candidate_businesses"][0]["observed_record_counts"]["customer_records"] = 999
        self.assertEqual(original, snapshot)

    def test_serialized_businesses_are_supported_but_duplicate_json_keys_fail(self):
        snapshot = source_snapshot()
        expected = observe(snapshot)
        snapshot["businesses"] = json.dumps(snapshot["businesses"])
        self.assertEqual(expected, observe(snapshot))
        snapshot["businesses"] = '[{"id":"hidden-private-value","id":"second"}]'
        with self.assertRaises(GroupObservationError) as caught:
            observe(snapshot)
        self.assertNotIn("hidden-private-value", str(caught.exception))

    def test_multiple_aliases_preserve_separate_source_counts_without_approved_binding(self):
        view = observe()
        recovery = next(row for row in view["entries"] if row["catalog_id"] == "retally-recovery")
        self.assertEqual("MULTIPLE_SOURCE_RECORDS", recovery["binding_status"])
        self.assertFalse(recovery["binding_approved"])
        candidates = recovery["candidate_businesses"]
        self.assertEqual(["business-freight", "business-recovery"],
                         [row["private_business_id"] for row in candidates])
        self.assertEqual([2, 3], [row["observed_record_counts"]["customer_records"] for row in candidates])
        self.assertNotIn("observed_record_counts", recovery)
        self.assertNotIn("totals", view)
        research = next(row for row in view["entries"] if row["catalog_id"] == "capturebrief")
        self.assertEqual("REVIEW_REQUIRED", research["binding_status"])
        self.assertFalse(research["binding_approved"])

    def test_unmapped_private_identities_are_counted_without_disclosure(self):
        view = observe()
        self.assertEqual(1, view["unmapped_business_records"])
        self.assertEqual(4, view["observed_business_records"])
        self.assertEqual(2, view["matched_catalog_entries"])
        self.assertEqual(len(load_catalog()["entries"]) - 2, view["unmatched_catalog_entries"])
        rendered = json.dumps(view)
        self.assertNotIn("excluded-private-business", rendered)
        self.assertNotIn("unrelated-private-project", rendered)
        self.assertEqual(31, view["unattributed_external_outcome_records"])
        missing = next(row for row in view["entries"] if row["catalog_id"] == "permitplate")
        self.assertEqual("NO_SOURCE_MATCH", missing["binding_status"])
        self.assertEqual([], missing["candidate_businesses"])

    def test_source_counts_never_establish_financial_truth_or_operating_authority(self):
        view = observe()
        self.assertTrue(all(value is None for value in view["verified_metrics"].values()))
        self.assertTrue(all(value is False for value in view["authority"].values()))
        self.assertEqual("RECORDS_VISIBLE_TO_PRIVATE_EXECUTOR_ONLY", view["coverage"])
        empty = source_snapshot()
        empty["businesses"] = []
        empty["unattributed_external_outcome_records"] = 0
        empty_view = observe(empty)
        self.assertEqual(0, empty_view["observed_business_records"])
        self.assertIsNone(empty_view["verified_metrics"]["paying_customers"])

    def test_private_observation_cannot_be_public_catalog_or_html(self):
        view = observe()
        with self.assertRaises(ValueError):
            render_dashboard(view)
        catalog = load_catalog()
        catalog["private_observation"] = view
        with self.assertRaises(GroupCatalogError):
            build_group_view(catalog)


class FakeGroupProduction(FakeProduction):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.source_rows = [source_snapshot()]
        self.source_rows[0]["observed_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)

    def read(self, sql, params):
        self.calls.append((sql, params))
        # The source statement contains the fingerprint function, too.
        if sql == RETALLY_GROUP_SOURCE_SQL:
            return copy.deepcopy(self.source_rows)
        return super().read(sql, params)


class GroupSourceBridgeTests(unittest.TestCase):
    def setUp(self):
        self.prod = FakeGroupProduction()
        self.bridge = ProductionReadBridge(self.prod.read)

    def test_snapshot_uses_one_guard_then_one_read_only_aggregate_statement(self):
        result = self.bridge.retally_group_source_snapshot(expected_schema_fingerprint=FINGERPRINT)
        self.assertEqual(4, len(result["businesses"]))
        self.assertEqual(2, len(self.prod.calls))
        self.assertEqual(1, sum(sql == RETALLY_GROUP_SOURCE_SQL for sql, _ in self.prod.calls))
        for sql, params in self.prod.calls:
            _assert_read_only_sql(sql)
            self.assertEqual((), params)
        self.assertEqual([], self.prod.writes)

    def test_sql_selects_counts_without_customer_identity_or_money_payloads(self):
        normalized = " ".join(RETALLY_GROUP_SOURCE_SQL.split()).lower()
        _assert_read_only_sql(RETALLY_GROUP_SOURCE_SQL)
        self.assertNotRegex(normalized, r"\b(?:c|f|e)\.id\b")
        self.assertNotRegex(normalized, r"\b(?:display_name|canonical_key|external_ids|metadata|amount_cents|source_ref|source_sha256|currency)\b")
        self.assertNotRegex(normalized, r"\bselect\s+\*")
        self.assertNotIn(";", normalized)
        for table in ("customers", "financial_events", "external_outcomes"):
            self.assertIn("from ai_business_os_prod." + table, normalized)

    def test_schema_drift_blocks_source_read_before_query(self):
        self.prod.fingerprint = "b" * 64
        with self.assertRaisesRegex(ProductionBridgeError, "schema drift"):
            self.bridge.retally_group_source_snapshot(expected_schema_fingerprint=FINGERPRINT)
        self.assertEqual(1, len(self.prod.calls))
        self.assertNotEqual(RETALLY_GROUP_SOURCE_SQL, self.prod.calls[0][0])

    def test_drift_between_guard_and_source_snapshot_fails_closed(self):
        self.prod.source_rows[0]["schema_fingerprint"] = "b" * 64
        with self.assertRaisesRegex(ProductionBridgeError, "schema drift"):
            self.bridge.retally_group_source_snapshot(expected_schema_fingerprint=FINGERPRINT)
        self.assertEqual(2, len(self.prod.calls))

    def test_invalid_expected_digest_fails_before_any_query(self):
        for fingerprint in (None, True, 1, "not-a-digest"):
            with self.subTest(fingerprint=fingerprint), self.assertRaises(ProductionBridgeError):
                self.bridge.retally_group_source_snapshot(expected_schema_fingerprint=fingerprint)
        self.assertEqual([], self.prod.calls)

    def test_missing_or_multiple_source_snapshots_are_not_silently_selected(self):
        for rows in ([], [source_snapshot(), source_snapshot()]):
            with self.subTest(count=len(rows)):
                self.prod.source_rows = rows
                with self.assertRaisesRegex(ProductionBridgeError, "exactly one"):
                    self.bridge.retally_group_source_snapshot(expected_schema_fingerprint=FINGERPRINT)

    def test_bad_snapshot_values_are_normalized_to_safe_bridge_error(self):
        self.prod.source_rows[0]["businesses"][0]["customer_records"] = "private-credential-like-value"
        with self.assertRaises(ProductionBridgeError) as caught:
            self.bridge.retally_group_source_snapshot(expected_schema_fingerprint=FINGERPRINT)
        self.assertNotIn("private-credential-like-value", str(caught.exception))


class GroupCommandCenterTests(unittest.TestCase):
    def setUp(self):
        self.prod = FakeGroupProduction()
        self.operator = CommandCenterOperator(
            ProductionReadBridge(self.prod.read), expected_schema_fingerprint=FINGERPRINT,
        )

    def test_default_dashboard_does_not_read_optional_source_or_register(self):
        def unexpected_register_read():
            self.fail("default dashboard invoked private register reader")
        self.operator.customer_register_reader = unexpected_register_read
        view = self.operator.dashboard()
        self.assertIsNone(view["retally_group"]["private_observation"])
        self.assertEqual(1, view["planning"]["summary"]["build_items"])
        self.assertFalse(any(sql == RETALLY_GROUP_SOURCE_SQL for sql, _ in self.prod.calls))
        self.assertEqual([], self.prod.writes)

    def test_opt_in_observes_source_once_and_preserves_unconnected_register(self):
        view = self.operator.dashboard(include_private_group=True)
        observation = view["retally_group"]["private_observation"]
        self.assertEqual("CURRENT", observation["freshness"])
        self.assertEqual(2, observation["matched_catalog_entries"])
        self.assertEqual("NOT_CONNECTED", observation["customer_register"]["mode"])
        self.assertIsNone(observation["customer_register"]["observed_account_count"])
        self.assertIsNone(observation["verified_metrics"]["cash_collected"])
        self.assertEqual(1, sum(sql == RETALLY_GROUP_SOURCE_SQL for sql, _ in self.prod.calls))
        self.assertEqual("NOT_CONNECTED", view["retally_group"]["catalog"]["boundaries"]["live_customer_state"])
        self.assertEqual([], self.prod.writes)

    def test_explicit_empty_register_is_an_observation_not_verified_zero_revenue(self):
        calls = []
        empty = json.loads(Path(__file__).with_name("RETALLY_GROUP_CUSTOMER_REGISTER.empty.json").read_text())
        def reader():
            calls.append("read")
            return copy.deepcopy(empty)
        self.operator.customer_register_reader = reader
        result = self.operator.group_observation()
        self.assertEqual(["read"], calls)
        self.assertEqual({"accounts": 0, "engagements": 0, "referrals": 0},
                         result["customer_register"]["observed_counts"])
        self.assertTrue(all(value is None for value in result["customer_register"]["verified_metrics"].values()))
        self.assertEqual([], self.prod.writes)

    def test_private_provider_errors_are_redacted(self):
        def broken_reader():
            raise RuntimeError("private-provider-secret-must-not-appear")
        self.operator.customer_register_reader = broken_reader
        with self.assertRaises(CommandCenterError) as caught:
            self.operator.group_observation()
        self.assertNotIn("private-provider-secret", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_invalid_register_cannot_enter_command_center_observation(self):
        self.operator.customer_register_reader = lambda: {"private_customer_payload": "secret-value"}
        with self.assertRaises(CommandCenterError) as caught:
            self.operator.group_observation()
        self.assertNotIn("secret-value", str(caught.exception))

    def test_private_group_switch_requires_boolean_before_reads(self):
        for flag in (None, 0, 1, "true", {}):
            with self.subTest(flag=flag), self.assertRaises(CommandCenterError):
                self.operator.dashboard(include_private_group=flag)
        self.assertEqual([], self.prod.calls)


if __name__ == "__main__":
    unittest.main()
