"""Adversarial checks for private-register relationships and truthful observation."""

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from ai_business_os.retally_customer_register import (
    CustomerRegisterError, build_register_observation,
    load_customer_register_json, validate_customer_register,
)
from ai_business_os.retally_group import load_catalog


NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
AUTHORITY = "ai_business_os_prod_and_approved_private_service_stores"


def account(ref="account:alpha", created_at="2026-10-18T09:00:00Z"):
    return {"account_ref": ref, "private_contact_ref": None, "created_at": created_at}


def engagement(ref="engagement:alpha", *, account_ref="account:alpha", entry="capturebrief"):
    return {
        "engagement_ref": ref, "account_ref": account_ref, "catalog_entry_id": entry,
        "service_ref": "freight" if entry == "retally-recovery" else None,
        "owner_role": "FULFILLMENT", "stage": "inquiry", "payment_status": "UNKNOWN",
        "agreement_ref": None, "customer_authorization_ref": None,
        "release_approval_ref": None, "input_manifest_ref": None,
        "quality_review_ref": None, "delivery_receipt_ref": None,
        "financial_reconciliation_ref": None, "retention_policy_ref": None,
        "currency": None, "updated_at": "2026-10-19T10:00:00Z",
    }


def register(*, empty=False, with_referral=False):
    data = {"schema_version": 1, "storage_authority": AUTHORITY,
            "accounts": [], "engagements": [], "referrals": []}
    if empty:
        return data
    data["accounts"] = [account()]
    data["engagements"] = [engagement()]
    if with_referral:
        data["engagements"].append(engagement("engagement:target", entry="permitplate"))
        data["referrals"] = [{
            "referral_ref": "referral:alpha", "account_ref": "account:alpha",
            "source_engagement_ref": "engagement:alpha", "target_catalog_entry_id": "permitplate",
            "customer_permission_ref": None, "owner_action_approval_ref": None,
            "status": "PROPOSED", "resulting_engagement_ref": "engagement:target",
        }]
    return data


class RegisterValidationTests(unittest.TestCase):
    def assert_invalid(self, data, message=None):
        with self.assertRaises(CustomerRegisterError) as caught:
            validate_customer_register(data, observed_at=NOW)
        if message:
            self.assertIn(message, str(caught.exception))

    def test_empty_and_populated_registers_roundtrip(self):
        for data in (register(empty=True), register(), register(with_referral=True)):
            self.assertEqual(data, load_customer_register_json(json.dumps(data), observed_at=NOW))
            self.assertIsNone(validate_customer_register(data, observed_at=NOW))

    def test_malformed_offsets_cannot_normalize_into_valid_instants(self):
        for offset in ("+00:60", "+01:99", "-01:99", "+24:00"):
            data = register()
            data["engagements"][0]["updated_at"] = "2026-10-20T12:30:00" + offset
            with self.subTest(offset=offset):
                self.assert_invalid(data)

    def test_template_is_accepted_by_implementation(self):
        template = Path(__file__).with_name("RETALLY_GROUP_CUSTOMER_REGISTER.empty.json").read_text()
        data = load_customer_register_json(template, observed_at=NOW)
        self.assertEqual(register(empty=True), data)

    def test_exact_fields_required_at_every_record_level(self):
        for path in ((), ("accounts", 0), ("engagements", 0), ("referrals", 0)):
            for operation in ("missing", "unknown"):
                with self.subTest(path=path, operation=operation):
                    data = register(with_referral=True)
                    target = data
                    for part in path:
                        target = target[part]
                    if operation == "missing":
                        del target[next(iter(target))]
                    else:
                        target["customer_private_payload"] = {"email": "private-sentinel"}
                    self.assert_invalid(data, "fields are invalid")

    def test_boolean_numbers_and_wrong_container_types_are_rejected(self):
        for value in (True, False, "1", 1.0, None):
            data = register()
            data["schema_version"] = value
            self.assert_invalid(data, "schema version")
        for key in ("accounts", "engagements", "referrals"):
            for value in ({}, (), None, "private-sentinel"):
                data = register()
                data[key] = value
                self.assert_invalid(data, "arrays")
        for value in (None, [], "private-sentinel"):
            self.assert_invalid(value, "fields are invalid")

    def test_strict_scalar_types_and_enums(self):
        mutations = (
            ("account_ref", 1), ("engagement_ref", True), ("catalog_entry_id", []),
            ("owner_role", 7), ("owner_role", "  "), ("stage", "PAID"),
            ("payment_status", "delivered"), ("service_ref", []),
            ("currency", 123), ("currency", "usd"), ("currency", "USD\n"),
            ("agreement_ref", False), ("updated_at", 0),
        )
        for field, value in mutations:
            with self.subTest(field=field, value=value):
                data = register()
                data["engagements"][0][field] = value
                self.assert_invalid(data)

    def test_duplicate_primary_refs_fail_within_and_across_collections(self):
        for key in ("accounts", "engagements", "referrals"):
            data = register(with_referral=True)
            data[key].append(copy.deepcopy(data[key][0]))
            self.assert_invalid(data, "unique")
        data = register()
        data["engagements"][0]["engagement_ref"] = data["accounts"][0]["account_ref"]
        self.assert_invalid(data, "unique")

    def test_unknown_accounts_and_catalog_entries_fail(self):
        data = register()
        data["engagements"][0]["account_ref"] = "account:missing"
        self.assert_invalid(data, "account is missing")
        data = register()
        data["engagements"][0]["catalog_entry_id"] = "unregistered-business"
        self.assert_invalid(data, "catalog entry is invalid")

    def test_service_scope_is_enforced(self):
        data = register()
        data["engagements"] = [engagement(entry="retally-recovery")]
        validate_customer_register(data, observed_at=NOW)
        for value in (None, "private:unknown", "not-a-service"):
            data["engagements"][0]["service_ref"] = value
            self.assert_invalid(data, "recovery service")
        data = register()
        for value in ("freight", "utilities", "https://private.invalid/customer", "arbitrary private text"):
            data["engagements"][0]["service_ref"] = value
            self.assert_invalid(data)
        data["engagements"][0]["service_ref"] = "private:service:example"
        validate_customer_register(data, observed_at=NOW)

    def test_all_recovery_services_come_from_catalog(self):
        data = register()
        data["engagements"] = [engagement(entry="retally-recovery")]
        for service in load_catalog()["services"]:
            data["engagements"][0]["service_ref"] = service["id"]
            validate_customer_register(data, observed_at=NOW)

    def test_observation_time_must_be_aware_and_provided(self):
        for value in (datetime(2026, 10, 20), "2026-10-20T12:00:00Z", None):
            with self.assertRaisesRegex(CustomerRegisterError, "observation time"):
                validate_customer_register(register(), observed_at=value)

    def test_timestamp_formats_future_and_ordering(self):
        for value in (
            "2026-10-19", "2026-10-19T10:00:00", "2026-10-19 10:00:00Z",
            "2026-02-30T10:00:00Z", "2026-10-19T10:00:00-00:00",
            "2026-10-19T10:00:00+24:00", "2026-10-20T12:00:00.000001Z",
            "2026-10-19T10:00:00.1234567Z", "2026-10-19T10:00:00Z\n",
        ):
            with self.subTest(value=value):
                data = register()
                data["engagements"][0]["updated_at"] = value
                self.assert_invalid(data, "timestamp")
        data = register()
        data["accounts"][0]["created_at"] = "2026-10-20T12:00:01Z"
        self.assert_invalid(data, "future")
        data = register()
        data["engagements"][0]["updated_at"] = "2026-10-17T12:00:00Z"
        self.assert_invalid(data, "predates")

    def test_offset_timestamps_are_compared_as_instants(self):
        data = register()
        data["accounts"][0]["created_at"] = "2026-10-20T13:00:00+02:00"
        data["engagements"][0]["updated_at"] = "2026-10-20T07:00:00-04:00"
        validate_customer_register(data, observed_at=NOW)

    def test_referral_identity_and_target_relationships(self):
        mutations = (
            ("account_ref", "account:missing", "account is missing"),
            ("source_engagement_ref", "engagement:missing", "source is missing"),
            ("target_catalog_entry_id", "missing-business", "target is invalid"),
            ("target_catalog_entry_id", "capturebrief", "another catalog entry"),
            ("resulting_engagement_ref", "engagement:missing", "resulting engagement is missing"),
            ("resulting_engagement_ref", "engagement:alpha", "another catalog entry"),
            ("status", "APPROVED", "status is invalid"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field, value=value):
                data = register(with_referral=True)
                data["referrals"][0][field] = value
                self.assert_invalid(data, message)

    def test_cross_account_source_and_result_referrals_are_rejected(self):
        data = register(with_referral=True)
        data["accounts"].append(account("account:beta"))
        data["referrals"][0]["account_ref"] = "account:beta"
        self.assert_invalid(data, "source belongs to another account")
        data["referrals"][0]["account_ref"] = "account:alpha"
        data["engagements"][1]["account_ref"] = "account:beta"
        self.assert_invalid(data, "resulting engagement belongs to another account")

    def test_malformed_json_duplicate_keys_and_invalid_constants_are_rejected_without_echo(self):
        for text in (
            '{"secret_marker":"private-sentinel",}',
            '{"secret_marker":1,"secret_marker":2}',
            '{"accounts":[{"secret_marker":1,"secret_marker":2}]}',
            '{"secret_marker":NaN}', '{"secret_marker":Infinity}',
            '[' * 2000 + '"private-sentinel"' + ']' * 2000,
            '{"secret_marker":' + '9' * 5000 + '}',
        ):
            with self.assertRaises(CustomerRegisterError) as caught:
                load_customer_register_json(text, observed_at=NOW)
            self.assertNotIn("private-sentinel", str(caught.exception))
            self.assertNotIn("secret_marker", str(caught.exception))

    def test_errors_do_not_echo_invalid_private_values_or_catalog_values(self):
        data = register()
        data["engagements"][0]["account_ref"] = "private_sentinel_customer_name"
        with self.assertRaises(CustomerRegisterError) as caught:
            validate_customer_register(data, observed_at=NOW)
        self.assertNotIn("private_sentinel", str(caught.exception))
        catalog = load_catalog()
        catalog["entries"][0]["id"] = "private_sentinel_catalog_name"
        with self.assertRaisesRegex(CustomerRegisterError, "catalog is invalid") as caught:
            validate_customer_register(register(), catalog=catalog, observed_at=NOW)
        self.assertNotIn("private_sentinel", str(caught.exception))


class RegisterObservationTests(unittest.TestCase):
    def test_empty_counts_are_observed_zero_but_verified_metrics_stay_unknown(self):
        result = build_register_observation(register(empty=True), observed_at=NOW)
        self.assertEqual({"accounts": 0, "engagements": 0, "referrals": 0}, result["observed_counts"])
        self.assertTrue(all(value is None for value in result["verified_metrics"].values()))
        self.assertEqual("NOT_ASSESSED", result["source_authentication"])
        self.assertEqual("NOT_ASSESSED", result["snapshot_freshness"])

    def test_paid_delivered_and_authorized_declarations_do_not_verify_outcomes(self):
        data = register(with_referral=True)
        data["engagements"][0]["stage"] = "delivered"
        data["engagements"][0]["payment_status"] = "PAID"
        for row in data["engagements"]:
            for key in row:
                if key.endswith("_ref") and key not in {"engagement_ref", "account_ref", "service_ref"}:
                    row[key] = "private:unverified-sentinel"
        data["referrals"][0].update({
            "status": "AUTHORIZED_INTERNAL_HANDOFF",
            "customer_permission_ref": "private:unverified-permission",
            "owner_action_approval_ref": "private:unverified-approval",
        })
        result = build_register_observation(data, observed_at=NOW)
        self.assertEqual(1, result["declared_stage_counts"]["delivered"])
        self.assertEqual(1, result["declared_payment_status_counts"]["PAID"])
        self.assertEqual(1, result["declared_referral_status_counts"]["AUTHORIZED_INTERNAL_HANDOFF"])
        self.assertEqual("NOT_PERFORMED", result["evidence_verification"])
        self.assertFalse(result["external_actions_authorized"])
        self.assertFalse(result["production_state_mutation_authorized"])
        self.assertTrue(all(value is None for value in result["verified_metrics"].values()))

    def test_null_references_are_counted_as_gaps_without_rejecting_declarations(self):
        data = register(with_referral=True)
        data["engagements"][0]["stage"] = "ready"
        result = build_register_observation(data, observed_at=NOW)
        self.assertEqual(2, result["data_gap_counts"]["missing_customer_authorization_ref"])
        self.assertEqual(1, result["data_gap_counts"]["missing_referral_customer_permission_ref"])
        self.assertEqual(1, result["data_gap_counts"]["missing_private_contact_ref"])
        self.assertEqual(2, result["data_gap_counts"]["missing_currency"])

    def test_observation_excludes_private_references_free_text_and_record_timestamps(self):
        data = register(with_referral=True)
        data["accounts"][0]["private_contact_ref"] = "private:sentinel-contact"
        data["engagements"][0]["owner_role"] = "sentinel private operator"
        data["engagements"][0]["service_ref"] = "private:sentinel-service"
        result = build_register_observation(data, observed_at=NOW)
        serialized = json.dumps(result)
        for value in ("sentinel", "account:alpha", "engagement:alpha", "referral:alpha", "2026-10-"):
            self.assertNotIn(value, serialized)
        self.assertIn("capturebrief", serialized)
        self.assertIn("permitplate", serialized)

    def test_observation_is_deterministic_detached_and_order_independent(self):
        data = register(with_referral=True)
        original = copy.deepcopy(data)
        first = build_register_observation(data, observed_at=NOW)
        second = build_register_observation(data, observed_at=NOW)
        self.assertEqual(first, second)
        data["engagements"].reverse()
        self.assertEqual(first, build_register_observation(data, observed_at=NOW))
        data["engagements"].reverse()
        first["observed_counts"]["accounts"] = 999
        self.assertEqual(original, data)
        self.assertEqual(1, second["observed_counts"]["accounts"])

    def test_catalog_specific_counts_do_not_double_count_account_on_referral(self):
        result = build_register_observation(register(with_referral=True), observed_at=NOW)
        counts = {row["catalog_entry_id"]: row for row in result["catalog_entry_counts"]}
        self.assertEqual(1, result["observed_counts"]["accounts"])
        self.assertEqual(2, result["observed_counts"]["engagements"])
        self.assertEqual(1, counts["capturebrief"]["engagements"])
        self.assertEqual(1, counts["permitplate"]["engagements"])
        self.assertEqual(1, counts["permitplate"]["referrals_received"])


if __name__ == "__main__":
    unittest.main()
