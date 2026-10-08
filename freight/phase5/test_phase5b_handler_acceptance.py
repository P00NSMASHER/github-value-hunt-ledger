"""Fail-closed checks on manually observed Floot staging evidence.

Passing this verifies RECEIPT CONSISTENCY ONLY. It does not connect to Floot,
authenticate the observed source, or independently verify the database again.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

RECEIPT = Path(__file__).with_name("phase5b_handler_acceptance.json")


def validate_receipt(d: dict) -> None:
    if d.get("schema") != 1 or d.get("scope") != "UNPUBLISHED_FLOOT_QA_REPLAY_ACCEPTANCE":
        raise ValueError("WRONG_RECEIPT_SCHEMA_OR_SCOPE")
    e = d["environments"]
    if e["production"]["postgres_system_id"] == e["qa"]["postgres_system_id"]:
        raise ValueError("STAGING_AND_PRODUCTION_SAME_CLUSTER")
    if e["production"]["writes_performed"] != 0 or e["qa"]["published"] is not False:
        raise ValueError("PRODUCTION_OR_QA_SAFETY_VIOLATION")
    if d["independent_signature_verified"] is not False:
        raise ValueError("FAKE_SIGNED_ATTESTATION")
    implementation = d["implementation"]
    if implementation["hosted_production_equivalence"] is not False:
        raise ValueError("UNSUPPORTED_PRODUCTION_EQUIVALENCE")
    if implementation["all_three_copied_sources_equal_after_normalizing_terminal_newline"] is not True:
        raise ValueError("SOURCE_PARITY_UNPROVEN")
    rows = {row["id"]: row for row in d["observations"]}
    required = {"PG_SINGLE_AND_REPLAY","PG_CONCURRENT_INITIAL","PG_CONCURRENT_CONFLICT",
                "PG_HISTORICAL_REPLAY","PG_UNKNOWN_OUTCOME","PG_SCOPING_AND_TIME",
                "REAL_HANDLER_12_DUPLICATES","REAL_HANDLER_FIRST_TRANSITION_RACE",
                "REAL_HANDLER_LIFECYCLE_AND_REPLAY"}
    if not required.issubset(rows):
        raise ValueError("MISSING_MANDATORY_OBSERVATION")
    if any(rows[i]["status"] != "PASS_IN_SCOPE" for i in required):
        raise ValueError("UNSUPPORTED_SUCCESS_STATUS")
    concurrent = rows["PG_CONCURRENT_INITIAL"]
    if concurrent["insertions"] != 1 or concurrent["replays"] != 15:
        raise ValueError("PG_DUPLICATE_CONSERVATION")
    if concurrent["db_row_count"] != 1 or len(concurrent["unique_event_ids"]) != 1:
        raise ValueError("PG_DURABILITY_DISAGREEMENT")
    trial = rows["REAL_HANDLER_12_DUPLICATES"]
    if trial["requests"] != 12 or trial["http_200"] != 12 or trial["db_rows"] != 1:
        raise ValueError("APPLICATION_DUPLICATE_IDEMPOTENCY_DISAGREEMENT")
    if len(trial["unique_event_ids"]) != 1 or trial["unique_hash_count"] != 1:
        raise ValueError("APPLICATION_DUPLICATE_RETURN_DISAGREEMENT")
    first = rows["REAL_HANDLER_FIRST_TRANSITION_RACE"]
    if (first["http_200"], first["http_400"], first["db_rows"]) != (1, 1, 1):
        raise ValueError("COMPETING_FIRST_TRANSITIONS_NOT_SERIALIZED")
    if rows["REAL_HANDLER_LIFECYCLE_AND_REPLAY"]["durable_event_count"] != 4:
        raise ValueError("INCORRECT_STATE_LIFECYCLE")
    limits = d["limits"]
    if (limits["historical_open_findings"], limits["historical_findings_closed_by_this_receipt"]) != (26, 0):
        raise ValueError("HISTORICAL_FINDING_STATUS_OVERCLAIM")
    if limits["real_customer_revenue_cents"] != 0 or limits["real_bank_carrier_evidence"] is not False:
        raise ValueError("FICTIONAL_FINANCES_MISLABELED")
    for key in ("verified_customer_realized_cash","hosted_exact_prod_auth_parity",
                "hosted_exact_prod_schema_parity","production_deployed","external_attestation"):
        if limits[key] is not False:
            raise ValueError("UNSUPPORTED_APPLICATION_CERTIFICATION_" + key.upper())


class AcceptanceReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_isolated_verification_receipt_consistency(self):
        validate_receipt(self.receipt)

    def test_money_mislabel_rejected(self):
        bad = json.loads(json.dumps(self.receipt))
        bad["limits"]["verified_customer_realized_cash"] = True
        with self.assertRaises(ValueError):
            validate_receipt(bad)

    def test_dupe_or_unsafe_ledger_claim_rejected(self):
        bad = json.loads(json.dumps(self.receipt))
        row = next(x for x in bad["observations"] if x["id"] == "PG_CONCURRENT_INITIAL")
        row["insertions"] = 2
        with self.assertRaises(ValueError):
            validate_receipt(bad)

    def test_unverified_original_finding_cannot_be_closed(self):
        bad = json.loads(json.dumps(self.receipt))
        bad["limits"]["historical_findings_closed_by_this_receipt"] = 1
        with self.assertRaises(ValueError):
            validate_receipt(bad)

    def test_missing_qa_parity_is_visible(self):
        bad = json.loads(json.dumps(self.receipt))
        bad["implementation"]["all_three_copied_sources_equal_after_normalizing_terminal_newline"] = False
        with self.assertRaises(ValueError):
            validate_receipt(bad)


if __name__ == "__main__":
    unittest.main()
