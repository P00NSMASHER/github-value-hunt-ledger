"""Synthetic cross-language and adversarial checks for the NYC private reader.

Golden hashes below were generated with Node 24 by executing the actual public
curated-stripe-onboarding.js, stripe-subscriber.js and subscriber-profile.js at
7be09a82249ab1ef6b6a9de7402690dbefd47f5e. Two processSnapshot calls retained three
synthetic subscriptions and moved the second to HOLD_SUBSCRIPTION_CHANGED.
No live provider response, private customer payload or production state is used.
"""

from concurrent.futures import ThreadPoolExecutor
import copy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import threading
import unittest
from unittest.mock import patch

from ai_business_os.retally_customer_register import build_register_observation
from ai_business_os.retally_permitplate import (
    ANCHOR_PATH, LEDGER_PATH, SOURCE_CONTRACT_COMMIT, PermitPlateError, PermitPlateNYCReader,
    _producer_json, _seal,
)


NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
KEY = b"synthetic-observation-key-no-live-secret-001"
REVISION = "a" * 40
NEXT_REVISION = "b" * 40
INIT = "2026-10-19T10:00:00.000Z"
CHECKED = "2026-10-20T11:00:00.000Z"
ERROR = "PermitPlate NYC observation failed closed"
CALENDAR = "America/New_York weekdays only; holiday adjustment requires review"
GOLDEN_LEDGER = "9f356591ac880d53bf951f69bb15a4ffcbe95e8ed5fff1cd6c90de557fdddb03"
GOLDEN_BASELINE = "9d4af4d7298ef59d98dd1b3c0b52354eefea7c71d0fb99e07b6f68a06161d5bc"
GOLDEN_ANCHOR = "ec6c1bf43a09b6270ba0cdeca3d07bb493f9490566f3913bfb585e9dca7eed2d"


def fixture():
    definitions = (
        ("one", "cus_synthetic_customer", "café🚀@例え.invalid", "PENDING_FOUNDER_REVIEW",
         "acbf046e5f92daef7f36aa7177ea9f6903406167492dc81e4c047e1db5ee19bd"),
        ("two", "cus_synthetic_customer", "second@example.invalid", "HOLD_SUBSCRIPTION_CHANGED",
         "ee28ea2444b18ba1d540c1f1328592e541c78d39cd370a8e54a550f321b73394"),
        ("three", None, "surrogate@example.invalid", "PENDING_FOUNDER_REVIEW",
         "b265267565b0e35a19d5e341b897ffd24fbf429013e3c28060ee26b0b99be97a"),
    )
    subscriptions = {}
    for name, customer, email, state, fingerprint in definitions:
        subscription = "sub_synthetic_" + name
        subscriptions[subscription] = {
            "subscriptionId": subscription, "checkoutSessionId": "cs_synthetic_" + name,
            "recipientEmail": email, "category": "Insurance", "boroughs": ["Queens"],
            "starterSnapshotEnabled": True, "stripeCustomerId": customer,
            "profileFingerprint": fingerprint, "baselineAt": "2026-10-18T10:00:00.000Z",
            "firstBriefTargetDate": "2026-10-23", "targetDateCalendar": CALENDAR,
            "state": state, "transportAllowed": False, "ownerAuthorizationGranted": False,
            "firstDiscoveredAt": INIT,
        }
    return {
        "version": "PermitPlate-private-checkout-intake-v1.0.0", "initializedAt": INIT,
        "checkedAt": CHECKED, "subscriptions": subscriptions, "ledgerFingerprint": GOLDEN_LEDGER,
    }, {
        "version": "PermitPlate-private-checkout-anchor-v1.0.0", "initializedAt": INIT,
        "baselineLedgerFingerprint": GOLDEN_BASELINE, "anchorFingerprint": GOLDEN_ANCHOR,
    }


def synthetic_hash(value):
    # Test mutations have ASCII keys and no nonintegral numeric fields. Golden
    # producer fixtures above separately establish real serialization parity.
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def reseal(ledger, anchor, *, reset_anchor=False):
    if reset_anchor:
        anchor["initializedAt"] = ledger["initializedAt"]
        anchor["baselineLedgerFingerprint"] = synthetic_hash({
            "version": ledger["version"], "initializedAt": ledger["initializedAt"],
            "checkedAt": ledger["initializedAt"], "subscriptions": {},
        })
    ledger["ledgerFingerprint"] = synthetic_hash({key: value for key, value in ledger.items() if key != "ledgerFingerprint"})
    anchor["anchorFingerprint"] = synthetic_hash({key: value for key, value in anchor.items() if key != "anchorFingerprint"})


def file_result(text, *, revision=REVISION):
    raw = text.encode("utf-8")
    return {
        "commit_sha": revision,
        "blob_sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\x00" + raw).hexdigest(),
        "content": text,
    }


class Source:
    def __init__(self, ledger=None, anchor=None):
        self.ledger, self.anchor = fixture() if ledger is None else (ledger, anchor)
        self.revision = REVISION
        self.resolve_calls = 0
        self.read_calls = []
        self.response_mutation = None
        self.raw = {}

    def resolve(self):
        self.resolve_calls += 1
        return self.revision

    def read(self, revision, path):
        self.read_calls.append((revision, path))
        data = {LEDGER_PATH: self.ledger, ANCHOR_PATH: self.anchor}[path]
        content = self.raw.get(path, json.dumps(data, ensure_ascii=False))
        response = file_result(content, revision=revision)
        if self.response_mutation:
            self.response_mutation(response, path)
        return response

    def reader(self, **kwargs):
        return PermitPlateNYCReader(self.resolve, self.read, pseudonym_key=KEY, **kwargs)


class PermitPlateSourceTests(unittest.TestCase):
    def assert_failed(self, reader, *, now=NOW):
        with self.assertRaises(PermitPlateError) as caught:
            reader.observe(now=now)
        self.assertEqual(ERROR, str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)
        return caught.exception

    def test_pinned_javascript_producer_fixture_including_unicode_is_accepted(self):
        ledger, anchor = fixture()
        self.assertEqual(GOLDEN_LEDGER, _seal({key: value for key, value in ledger.items() if key != "ledgerFingerprint"}))
        self.assertEqual(GOLDEN_ANCHOR, _seal({key: value for key, value in anchor.items() if key != "anchorFingerprint"}))
        source = Source(ledger, anchor)
        result = source.reader().observe(now=NOW)
        self.assertEqual({"accounts": 2, "engagements": 3, "referrals": 0}, result["register_observation"]["observed_counts"])
        self.assertEqual(1, source.resolve_calls)
        self.assertEqual([(REVISION, LEDGER_PATH), (REVISION, ANCHOR_PATH)], source.read_calls)
        self.assertEqual(SOURCE_CONTRACT_COMMIT, result["source_observation"]["source_contract_commit"])

    def test_utf16_key_order_and_javascript_string_escapes_match_golden_vector(self):
        vector = {"\ue000": "private sentinel", "\U00010000": "café🚀", "ascii": '\n\t\b\f\r"\\/\u2028\u2029'}
        self.assertEqual("5feda2fdf64679a2531ce03a73f9cb261bfadca210992de0abfa60a7911bdaaa", _seal(vector))
        serialized = _producer_json(vector)
        self.assertLess(serialized.index("\U00010000"), serialized.index("\ue000"))
        self.assertEqual(vector, json.loads(serialized))
        for invalid in (1, 1.0, float("nan"), {"x": "\ud800"}):
            with self.subTest(value=repr(invalid)):
                with self.assertRaises((PermitPlateError, UnicodeError)):
                    _producer_json(invalid)

    def test_escaped_and_literal_unicode_bytes_have_different_blobs_and_same_seal(self):
        source = Source()
        literal = source.reader().observe(now=NOW)
        source.raw[LEDGER_PATH] = json.dumps(source.ledger, ensure_ascii=True)
        escaped = source.reader().observe(now=NOW)
        self.assertNotEqual(literal["source_observation"]["ledger_blob_sha"], escaped["source_observation"]["ledger_blob_sha"])
        self.assertEqual(literal["source_observation"]["ledger_fingerprint"], escaped["source_observation"]["ledger_fingerprint"])
        self.assertEqual(literal["register_observation"], escaped["register_observation"])

    def test_empty_observed_snapshot_is_distinct_from_missing_source(self):
        source = Source()
        source.ledger["subscriptions"] = {}
        reseal(source.ledger, source.anchor)
        result = source.reader().observe(now=NOW)
        self.assertEqual({"accounts": 0, "engagements": 0, "referrals": 0}, result["register_observation"]["observed_counts"])
        source.raw[LEDGER_PATH] = "null"
        self.assert_failed(source.reader())
        source.raw = {ANCHOR_PATH: "null"}
        self.assert_failed(source.reader())

    def test_reader_configuration_is_strict_and_never_echoes_keys(self):
        for key in (b"", b"x" * 31, "private-key-sentinel", bytearray(b"x" * 32), None):
            with self.subTest(key_type=type(key).__name__):
                with self.assertRaisesRegex(PermitPlateError, "reader configuration is invalid"):
                    PermitPlateNYCReader(lambda: REVISION, lambda *args: {}, pseudonym_key=key)
        for age in (0, -1, True, 1.5, "32400", None):
            with self.assertRaises(PermitPlateError):
                Source().reader(max_age_seconds=age)
        for resolve, read in ((None, lambda *args: {}), (lambda: REVISION, 123)):
            with self.assertRaises(PermitPlateError):
                PermitPlateNYCReader(resolve, read, pseudonym_key=KEY)

    def test_invalid_revisions_fail_before_reading_any_file(self):
        for revision in (None, "main", "a" * 39, "a" * 41, "A" * 40, REVISION + "\n", 123, []):
            source = Source()
            source.revision = revision
            with self.subTest(revision_type=type(revision).__name__):
                self.assert_failed(source.reader())
                self.assertEqual([], source.read_calls)

    def test_exact_file_metadata_and_utf8_blob_digest_are_required(self):
        mutations = (
            lambda r: r.update({"commit_sha": NEXT_REVISION}),
            lambda r: r.update({"commit_sha": 1}),
            lambda r: r.update({"blob_sha": "0" * 40}),
            lambda r: r.update({"blob_sha": "A" * 40}),
            lambda r: r.update({"content": r["content"] + " "}),
            lambda r: r.update({"content": r["content"].encode()}),
            lambda r: r.update({"raw_private_payload": "private-sentinel"}),
            lambda r: r.pop("blob_sha"),
        )
        for path in (LEDGER_PATH, ANCHOR_PATH):
            for mutation in mutations:
                source = Source()
                source.response_mutation = lambda r, p, target=path, mutate=mutation: mutate(r) if p == target else None
                with self.subTest(path=path, mutation=mutations.index(mutation)):
                    self.assert_failed(source.reader())

    def test_resolved_revision_stays_pinned_if_supplier_branch_moves_between_reads(self):
        source = Source()
        def change_branch(response, path):
            if path == LEDGER_PATH:
                source.revision = NEXT_REVISION
        source.response_mutation = change_branch
        result = source.reader().observe(now=NOW)
        self.assertEqual(1, source.resolve_calls)
        self.assertEqual(REVISION, result["source_observation"]["source_revision"])
        self.assertTrue(all(revision == REVISION for revision, _ in source.read_calls))

    def test_malformed_duplicate_and_nonfinite_json_fail_without_private_errors(self):
        malformed = (
            '{"private-sentinel":}', '{"private-sentinel":1,"private-sentinel":2}',
            '{"subscriptions":{"sub_synthetic_one":{},"sub_synthetic_one":{}}}',
            '{"subscriptions":{"sub_synthetic_one":{"state":"a","state":"b"}}}',
            '{"private-sentinel":NaN}', '{"private-sentinel":Infinity}',
            '{"private-sentinel":1}', '{"private-sentinel":1.1}',
            '[' * 2000 + '"private-sentinel"' + ']' * 2000,
        )
        for text in malformed:
            source = Source()
            source.raw[LEDGER_PATH] = text
            self.assert_failed(source.reader())

    def test_unknown_or_missing_fields_at_every_source_level_fail(self):
        for target in ("ledger", "anchor", "entry"):
            for operation in ("add", "remove"):
                source = Source()
                value = source.ledger if target == "ledger" else source.anchor if target == "anchor" else source.ledger["subscriptions"]["sub_synthetic_one"]
                if operation == "add":
                    value["private-sentinel"] = "private-sentinel"
                else:
                    del value[next(iter(value))]
                reseal(source.ledger, source.anchor)
                with self.subTest(target=target, operation=operation):
                    self.assert_failed(source.reader())

    def test_versions_container_types_and_source_seals_fail_closed(self):
        for target, field, value in (
            ("ledger", "version", "future-version"), ("anchor", "version", "future-version"),
            ("ledger", "subscriptions", []), ("ledger", "subscriptions", None),
            ("ledger", "ledgerFingerprint", "0" * 64), ("anchor", "anchorFingerprint", "0" * 64),
        ):
            source = Source()
            data = source.ledger if target == "ledger" else source.anchor
            data[field] = value
            with self.subTest(target=target, field=field):
                self.assert_failed(source.reader())

    def test_self_consistent_but_false_initialization_anchor_is_rejected(self):
        source = Source()
        source.anchor["baselineLedgerFingerprint"] = "f" * 64
        reseal(source.ledger, source.anchor)
        self.assert_failed(source.reader())
        source = Source()
        source.anchor["initializedAt"] = "2026-10-18T10:00:00.000Z"
        reseal(source.ledger, source.anchor)
        self.assert_failed(source.reader())

    def test_identifiers_and_duplicate_checkout_or_profile_identity_are_rejected(self):
        for field, value in (
            ("subscriptionId", "sub_different_identity"), ("subscriptionId", True),
            ("checkoutSessionId", "cs_"), ("checkoutSessionId", "cs_synthetic_one\n"),
            ("checkoutSessionId", "cs_synthetic_é"), ("stripeCustomerId", "cus_"),
            ("stripeCustomerId", "private-sentinel"), ("stripeCustomerId", []),
            ("profileFingerprint", "ABC"), ("profileFingerprint", "f" * 63),
        ):
            source = Source()
            source.ledger["subscriptions"]["sub_synthetic_one"][field] = value
            reseal(source.ledger, source.anchor)
            with self.subTest(field=field, value_type=type(value).__name__):
                self.assert_failed(source.reader())
        for field in ("checkoutSessionId", "profileFingerprint"):
            source = Source()
            source.ledger["subscriptions"]["sub_synthetic_two"][field] = source.ledger["subscriptions"]["sub_synthetic_one"][field]
            reseal(source.ledger, source.anchor)
            self.assert_failed(source.reader())
        source = Source()
        row = source.ledger["subscriptions"].pop("sub_synthetic_one")
        row["subscriptionId"] = "sub_private/invalid"
        source.ledger["subscriptions"][row["subscriptionId"]] = row
        reseal(source.ledger, source.anchor)
        self.assert_failed(source.reader())

    def test_types_enums_and_no_send_flags_cannot_be_coerced(self):
        mutations = (
            ("recipientEmail", "missing-at-sign"), ("recipientEmail", " first@example.invalid"),
            ("recipientEmail", "private\x00@example.invalid"), ("recipientEmail", 123),
            ("category", "Other"), ("category", []), ("boroughs", "Queens"),
            ("boroughs", []), ("boroughs", ["Queens", "Queens"]),
            ("boroughs", ["Queens", "Manhattan"]), ("boroughs", ["ALL NYC"]),
            ("starterSnapshotEnabled", 1), ("state", "PAID"), ("state", []),
            ("transportAllowed", 0), ("transportAllowed", True),
            ("ownerAuthorizationGranted", "false"), ("ownerAuthorizationGranted", True),
            ("targetDateCalendar", "Some other calendar"), ("firstBriefTargetDate", "2026-02-30"),
            ("firstBriefTargetDate", "2026-10-23T00:00:00Z"),
        )
        for field, value in mutations:
            source = Source()
            source.ledger["subscriptions"]["sub_synthetic_one"][field] = value
            reseal(source.ledger, source.anchor)
            with self.subTest(field=field, value_type=type(value).__name__):
                self.assert_failed(source.reader())

    def test_all_source_timestamps_reject_unknown_offsets_future_and_invalid_dates(self):
        malformed = (
            "2026-10-19", "2026-10-19T10:00:00", "2026-10-19 10:00:00Z",
            "2026-02-30T10:00:00Z", "2026-10-19T10:00:00-00:00",
            "2026-10-19T10:00:00+24:00", "2026-10-19T10:00:00+01:99",
            "2026-10-19T10:00:00+00:60", "2026-10-19T10:00:00.0000001Z",
            "2026-10-20T12:00:00.000001Z", "2026-10-19T10:00:00Z\n", None,
        )
        for field in ("initializedAt", "checkedAt", "baselineAt", "firstDiscoveredAt"):
            for value in malformed:
                source = Source()
                target = source.ledger if field in ("initializedAt", "checkedAt") else source.ledger["subscriptions"]["sub_synthetic_one"]
                target[field] = value
                reseal(source.ledger, source.anchor, reset_anchor=field == "initializedAt")
                with self.subTest(field=field, value=value):
                    self.assert_failed(source.reader())

    def test_source_timestamps_follow_baseline_discovery_check_and_read_order(self):
        mutations = (
            ("initializedAt", "2026-10-20T11:30:00Z"),
            ("checkedAt", "2026-10-19T09:00:00Z"),
            ("baselineAt", "2026-10-19T10:00:01Z"),
            ("firstDiscoveredAt", "2026-10-19T09:59:59Z"),
            ("firstDiscoveredAt", "2026-10-20T11:00:01Z"),
        )
        for field, value in mutations:
            source = Source()
            target = source.ledger if field in ("initializedAt", "checkedAt") else source.ledger["subscriptions"]["sub_synthetic_one"]
            target[field] = value
            reseal(source.ledger, source.anchor, reset_anchor=field == "initializedAt")
            self.assert_failed(source.reader())
        source = Source()
        source.ledger["checkedAt"] = "2026-10-20T13:00:00+02:00"
        reseal(source.ledger, source.anchor)
        self.assertEqual(3600, source.reader().observe(now=NOW)["source_observation"]["source_age_seconds"])

    def test_target_date_can_precede_initialization_and_is_not_observed_delivery(self):
        source = Source()
        row = source.ledger["subscriptions"]["sub_synthetic_one"]
        row["baselineAt"] = "2026-10-01T10:00:00Z"
        row["firstBriefTargetDate"] = "2026-10-08"
        reseal(source.ledger, source.anchor)
        result = source.reader().observe(now=NOW)
        self.assertEqual(0, result["register_observation"]["declared_stage_counts"]["delivered"])

    def test_observation_time_requires_known_aware_datetime(self):
        for value in (datetime(2026, 10, 20, 12), "2026-10-20T12:00:00Z", 0):
            self.assert_failed(Source().reader(), now=value)
        result = Source().reader().observe(now=NOW.astimezone(timezone(timedelta(hours=2))))
        self.assertEqual("2026-10-20T12:00:00Z", result["source_observation"]["read_observed_at"])

    def test_read_time_never_refreshes_source_age_and_stale_source_remains_visible(self):
        source = Source()
        at_threshold = NOW + timedelta(hours=8)
        result = source.reader().observe(now=at_threshold)
        self.assertEqual("CURRENT", result["source_observation"]["freshness"])
        self.assertEqual(32400, result["source_observation"]["source_age_seconds"])
        stale = source.reader().observe(now=at_threshold + timedelta(microseconds=1))
        self.assertEqual("STALE", stale["source_observation"]["freshness"])
        self.assertEqual("2026-10-20T11:00:00Z", stale["source_observation"]["source_checked_at"])
        self.assertEqual(3, stale["register_observation"]["observed_counts"]["engagements"])
        self.assertEqual("STALE", source.reader(max_age_seconds=3599).observe(now=NOW)["source_observation"]["freshness"])
        self.assertEqual("LOCAL_OBSERVATION_POLICY_NOT_SOURCE_SLA", stale["source_observation"]["freshness_policy"])

    def test_supplier_and_parser_failures_are_fixed_and_unlogged(self):
        def fail(*args):
            raise RuntimeError("secret=private-sentinel; customer@example.invalid; private-repo")
        readers = (
            PermitPlateNYCReader(fail, fail, pseudonym_key=KEY),
            PermitPlateNYCReader(lambda: REVISION, fail, pseudonym_key=KEY),
            PermitPlateNYCReader(lambda: REVISION, lambda *args: None, pseudonym_key=KEY),
        )
        for reader in readers:
            with patch("builtins.print") as printed:
                self.assert_failed(reader)
                printed.assert_not_called()


class PermitPlateProjectionTests(unittest.TestCase):
    def capture_register(self, source, *, key=KEY):
        captured = []
        def capture(register, **kwargs):
            captured.append(copy.deepcopy(register))
            return build_register_observation(register, **kwargs)
        with patch("ai_business_os.retally_permitplate.build_register_observation", side_effect=capture):
            result = PermitPlateNYCReader(source.resolve, source.read, pseudonym_key=key).observe(now=NOW)
        return captured[0], result

    def test_projection_is_conservative_with_no_invented_evidence_or_authority(self):
        register, result = self.capture_register(Source())
        self.assertEqual([], register["referrals"])
        for account in register["accounts"]:
            self.assertIsNone(account["private_contact_ref"])
            self.assertEqual("2026-10-19T10:00:00Z", account["created_at"])
        for engagement in register["engagements"]:
            self.assertEqual("permitplate", engagement["catalog_entry_id"])
            self.assertEqual("private:permitplate:nyc_curated", engagement["service_ref"])
            self.assertEqual("inquiry", engagement["stage"])
            self.assertEqual("UNKNOWN", engagement["payment_status"])
            self.assertIsNone(engagement["currency"])
            self.assertEqual("2026-10-20T11:00:00Z", engagement["updated_at"])
            for field in ("agreement_ref", "customer_authorization_ref", "release_approval_ref", "input_manifest_ref",
                          "quality_review_ref", "delivery_receipt_ref", "financial_reconciliation_ref", "retention_policy_ref"):
                self.assertIsNone(engagement[field])
        observation = result["register_observation"]
        self.assertTrue(all(value is None for value in observation["verified_metrics"].values()))
        self.assertEqual(3, observation["declared_payment_status_counts"]["UNKNOWN"])
        self.assertFalse(observation["external_actions_authorized"])
        self.assertFalse(observation["production_state_mutation_authorized"])

    def test_hmac_refs_are_stable_domain_separated_and_do_not_use_email(self):
        first, _ = self.capture_register(Source())
        second, _ = self.capture_register(Source())
        self.assertEqual(first, second)
        different_key, _ = self.capture_register(Source(), key=b"different-synthetic-key-0000000000000000")
        self.assertNotEqual(first["accounts"], different_key["accounts"])
        source = Source()
        for row in source.ledger["subscriptions"].values():
            row["recipientEmail"] = "one-shared-email@example.invalid"
        reseal(source.ledger, source.anchor)
        same_email, _ = self.capture_register(source)
        self.assertEqual(first, same_email)
        self.assertEqual(first["engagements"][0]["account_ref"], first["engagements"][2]["account_ref"])
        self.assertNotEqual(first["engagements"][0]["account_ref"], first["engagements"][1]["account_ref"])
        self.assertEqual(2, len(first["accounts"]))
        refs = [row["account_ref"].split(":", 1)[1] for row in first["accounts"]]
        refs += [row["engagement_ref"].split(":", 1)[1] for row in first["engagements"]]
        self.assertEqual(len(refs), len(set(refs)))

    def test_shared_customer_created_at_uses_earliest_retained_discovery(self):
        source = Source()
        source.ledger["subscriptions"]["sub_synthetic_one"]["firstDiscoveredAt"] = "2026-10-20T09:00:00Z"
        reseal(source.ledger, source.anchor)
        register, _ = self.capture_register(source)
        shared_ref = register["engagements"][0]["account_ref"]
        account = next(row for row in register["accounts"] if row["account_ref"] == shared_ref)
        self.assertEqual("2026-10-19T10:00:00Z", account["created_at"])

    def test_exact_output_allowlist_preserves_holds_and_surrogates_without_identity_leaks(self):
        result = Source().reader().observe(now=NOW)
        self.assertEqual({"register_observation", "source_observation"}, set(result))
        source = result["source_observation"]
        self.assertEqual({
            "mode", "source_contract_commit", "source_version", "source_revision", "ledger_blob_sha",
            "anchor_blob_sha", "ledger_fingerprint", "source_authentication", "immutable_revision_consistent",
            "integrity", "continuity", "source_checked_at", "read_observed_at", "source_age_seconds",
            "freshness", "freshness_policy", "max_source_age_seconds", "source_state_counts", "held_subscriptions",
            "account_identity_scope", "source_customer_accounts", "subscription_surrogate_accounts",
            "live_payment_verification", "evidence_verification", "external_actions_authorized",
            "production_state_mutation_authorized",
        }, set(source))
        self.assertEqual({"PENDING_FOUNDER_REVIEW": 2, "HOLD_SUBSCRIPTION_CHANGED": 1}, source["source_state_counts"])
        self.assertEqual(1, source["held_subscriptions"])
        self.assertEqual(1, source["source_customer_accounts"])
        self.assertEqual(1, source["subscription_surrogate_accounts"])
        self.assertEqual("CALLER_SUPPLIED_READERS_NOT_INDEPENDENTLY_AUTHENTICATED", source["source_authentication"])
        self.assertEqual("CHECKED", source["integrity"])
        self.assertEqual("NOT_PERFORMED", source["live_payment_verification"])
        self.assertEqual("NOT_PERFORMED", source["evidence_verification"])
        text = json.dumps(result, ensure_ascii=False)
        for forbidden in ("sub_synthetic", "cs_synthetic", "cus_synthetic", "example.invalid", "例え.invalid",
                          "profileFingerprint", "private:permitplate", "private-repository-location", KEY.decode()):
            self.assertNotIn(forbidden, text)
        before = fixture()
        source_input = Source()
        source_input.reader().observe(now=NOW)
        self.assertEqual(before, (source_input.ledger, source_input.anchor))


class PermitPlateContinuityTests(unittest.TestCase):
    def assert_failed(self, reader, *, now=NOW):
        with self.assertRaisesRegex(PermitPlateError, "^" + ERROR + "$"):
            reader.observe(now=now)

    def test_repeated_snapshots_are_idempotent_and_hold_recovery_is_visible(self):
        source = Source()
        reader = source.reader()
        first = reader.observe(now=NOW)
        repeated = reader.observe(now=NOW)
        self.assertEqual(first["register_observation"], repeated["register_observation"])
        self.assertEqual("PREVIOUS_SUCCESSFUL_OBSERVATION_CHECKED", repeated["source_observation"]["continuity"])
        source.revision = NEXT_REVISION
        source.ledger["checkedAt"] = "2026-10-20T12:00:00.000Z"
        source.ledger["subscriptions"]["sub_synthetic_two"]["state"] = "PENDING_FOUNDER_REVIEW"
        source.ledger["subscriptions"]["sub_synthetic_one"]["state"] = "HOLD_SUBSCRIPTION_CHANGED"
        reseal(source.ledger, source.anchor)
        recovered = reader.observe(now=NOW)
        self.assertEqual(1, recovered["source_observation"]["held_subscriptions"])
        self.assertEqual(3, recovered["register_observation"]["declared_payment_status_counts"]["UNKNOWN"])

    def test_immutable_identity_drift_is_rejected_even_with_fresh_valid_seals(self):
        for field, value in (
            ("checkoutSessionId", "cs_synthetic_replacement"), ("stripeCustomerId", "cus_synthetic_replacement"),
            ("profileFingerprint", "a" * 64), ("recipientEmail", "changed@example.invalid"),
            ("category", "POS"), ("boroughs", ["Manhattan"]), ("starterSnapshotEnabled", False),
            ("baselineAt", "2026-10-17T10:00:00Z"), ("firstDiscoveredAt", "2026-10-19T11:00:00Z"),
            ("firstBriefTargetDate", "2026-10-24"),
        ):
            source = Source()
            reader = source.reader()
            reader.observe(now=NOW)
            source.revision = NEXT_REVISION
            source.ledger["checkedAt"] = "2026-10-20T12:00:00Z"
            source.ledger["subscriptions"]["sub_synthetic_one"][field] = value
            reseal(source.ledger, source.anchor)
            with self.subTest(field=field):
                self.assert_failed(reader)

    def test_source_reversion_reinitialization_missing_entries_and_same_time_rewrite_fail(self):
        for mutation in ("rollback", "reinitialize", "missing", "same-time-rewrite", "same-revision-rewrite"):
            source = Source()
            reader = source.reader()
            reader.observe(now=NOW)
            if mutation != "same-revision-rewrite":
                source.revision = NEXT_REVISION
            source.ledger["checkedAt"] = "2026-10-20T12:00:00Z"
            if mutation == "rollback":
                source.ledger["checkedAt"] = "2026-10-20T10:00:00Z"
            elif mutation == "reinitialize":
                source.ledger["initializedAt"] = "2026-10-18T10:00:00Z"
            elif mutation == "missing":
                del source.ledger["subscriptions"]["sub_synthetic_one"]
            elif mutation == "same-time-rewrite":
                source.ledger["checkedAt"] = CHECKED
                source.ledger["subscriptions"]["sub_synthetic_one"]["state"] = "HOLD_SUBSCRIPTION_CHANGED"
            reseal(source.ledger, source.anchor, reset_anchor=mutation == "reinitialize")
            with self.subTest(mutation=mutation):
                self.assert_failed(reader)

    def test_read_clock_rollback_is_rejected_and_new_reader_has_no_prior_checkpoint(self):
        source = Source()
        reader = source.reader()
        reader.observe(now=NOW)
        self.assert_failed(reader, now=NOW - timedelta(minutes=1))
        new_instance = source.reader().observe(now=NOW - timedelta(minutes=1))
        self.assertEqual("INITIAL_OBSERVATION", new_instance["source_observation"]["continuity"])

    def test_failed_observation_does_not_advance_successful_continuity(self):
        source = Source()
        reader = source.reader()
        reader.observe(now=NOW)
        original = copy.deepcopy(source.ledger)
        source.revision = NEXT_REVISION
        source.ledger["checkedAt"] = "2026-10-20T12:00:00Z"
        source.ledger["subscriptions"]["sub_synthetic_one"]["recipientEmail"] = "changed@example.invalid"
        reseal(source.ledger, source.anchor)
        self.assert_failed(reader)
        source.ledger = original
        source.revision = REVISION
        reader.observe(now=NOW)
        with patch("ai_business_os.retally_permitplate.build_register_observation", side_effect=RuntimeError("private-sentinel")):
            self.assert_failed(reader)
        reader.observe(now=NOW)

    def test_new_subscription_addition_is_retained_without_customer_merge_from_email(self):
        source = Source()
        reader = source.reader()
        reader.observe(now=NOW)
        source.revision = NEXT_REVISION
        source.ledger["checkedAt"] = "2026-10-20T12:00:00Z"
        row = copy.deepcopy(source.ledger["subscriptions"]["sub_synthetic_three"])
        row.update({"subscriptionId": "sub_synthetic_four", "checkoutSessionId": "cs_synthetic_four",
                    "profileFingerprint": "c" * 64, "firstDiscoveredAt": "2026-10-20T12:00:00Z"})
        source.ledger["subscriptions"]["sub_synthetic_four"] = row
        reseal(source.ledger, source.anchor)
        result = reader.observe(now=NOW)
        self.assertEqual({"accounts": 3, "engagements": 4, "referrals": 0}, result["register_observation"]["observed_counts"])
        self.assertEqual(2, result["source_observation"]["subscription_surrogate_accounts"])

    def test_simultaneous_observations_are_serialized_before_resolving_revision(self):
        source = Source()
        first_read = threading.Event()
        release_first = threading.Event()
        second_entered = threading.Event()
        second_resolved = threading.Event()
        def resolve():
            result = source.resolve()
            if source.resolve_calls == 2:
                second_resolved.set()
            return result
        def read(revision, path):
            if path == LEDGER_PATH and not first_read.is_set():
                first_read.set()
                if not release_first.wait(3):
                    raise RuntimeError("test read timed out")
            return source.read(revision, path)
        reader = PermitPlateNYCReader(resolve, read, pseudonym_key=KEY)
        def second_call():
            second_entered.set()
            return reader.observe(now=NOW)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(reader.observe, now=NOW)
            try:
                self.assertTrue(first_read.wait(2))
                second = pool.submit(second_call)
                self.assertTrue(second_entered.wait(2))
                self.assertFalse(second_resolved.wait(0.05))
            finally:
                release_first.set()
            first_result, second_result = first.result(timeout=3), second.result(timeout=3)
        self.assertEqual(first_result["register_observation"], second_result["register_observation"])
        self.assertEqual("PREVIOUS_SUCCESSFUL_OBSERVATION_CHECKED", second_result["source_observation"]["continuity"])


if __name__ == "__main__":
    unittest.main()
