"""Independent negative tests for the M38 Control Center scenario consumer.

Real offline M35/M37/M38 source policy is exercised, not mocked; changed
fingerprints are invented candidate metadata, never original-publisher data.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from freight import research_source_lineage_m37 as m37
from freight import research_claim_quarantine_m38 as m38
from freight import research_scenario_control_m38 as scenario
from freight import lab_phase4_control_center as control

AS_OF = date(2026, 10, 13)
VALUES = {
    "M35-01": "545435.000", "M35-02": "402827.246",
    "M35-03": "142607.754", "M35-04": "73.85",
    "M35-05": "8.05", "M35-06": "4.02",
    "M35-07": "1.18", "M35-08": "0.45",
}
ROOT_IMPACT = {
    "BEA": {"M35-01", "M35-03", "M35-04", "M35-05", "M35-08"},
    "CENSUS": {"M35-02", "M35-03", "M35-04", "M35-07"},
    "BLS_PPI": {"M35-07", "M35-08"},
    "BLS_SECTORAL": {"M35-06"},
    "PILOT": set(),
}


def candidate(*roots: str) -> dict:
    """Plausible-looking, deliberately unauthenticated revision fingerprints."""
    receipts = {
        root: sha256(("synthetic-unverified-source-edition-2026-10-13-"
                      + root).encode("utf-8")).hexdigest()
        for root in roots
    }
    result = m37.candidate_template(as_of=AS_OF, root=roots[0],
                                    digest=receipts[roots[0]])
    result["source_receipts"] = receipts
    return result


class ScenarioConsumptionTests(unittest.TestCase):
    def test_census_all_surfaces_redact_exact_four_and_preserve_four(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            incoming = path / "synthetic-census-revision.json"
            incoming.write_text(json.dumps(candidate("CENSUS")))
            target = path / "control"
            with patch("sys.argv", [
                "control", "--as-of-date", AS_OF.isoformat(),
                "--candidate", str(incoming), "--out", str(target),
            ]):
                control.main()
            expected_files = {
                "index.html", "phase4_control.json",
                "source_change_impact.json", "source_change_impact.html",
                "claim_quarantine.json", "claim_quarantine.html",
            }
            self.assertEqual({p.name for p in target.iterdir()}, expected_files)
            full = json.loads((target / "phase4_control.json").read_text())
            source = json.loads((target / "source_change_impact.json").read_text())
            safe = json.loads((target / "claim_quarantine.json").read_text())
            held = ROOT_IMPACT["CENSUS"]
            self.assertEqual(set(safe["quarantined_claim_ids"]), held)
            self.assertEqual(set(source["affected_internal_source_claim_ids"]), held)
            self.assertEqual(full["scope"], scenario.SCOPE)
            self.assertTrue(full["scenario_only"])
            self.assertFalse(full["legacy_unquarantined_source_reports_exported"])
            self.assertEqual(full["existing_lab_executions_replayed_in_this_scenario"], 0)
            self.assertEqual(full["independent_human_customer_pilot_controls_unmet"], 18)
            self.assertEqual(full["external_customer_marketing_or_recovery_claims_authorized"], 0)
            self.assertIsNone(full["actual_recovered_cash_usd"])
            self.assertEqual(full["claim_quarantine"]["receipt_sha256"], safe["receipt_sha256"])
            rows = {x["claim_id"]: x for x in safe["claims"]}
            old = {x["claim_id"]: x for x in source["claims"]}
            for claim_id, historical in VALUES.items():
                with self.subTest(claim=claim_id):
                    if claim_id in held:
                        self.assertIsNone(rows[claim_id]["safe_internal_value"])
                        self.assertIsNone(old[claim_id]["prior_internal_value"])
                    else:
                        self.assertEqual(rows[claim_id]["safe_internal_value"], historical)
                        self.assertEqual(old[claim_id]["prior_internal_value"], historical)
            for file in target.iterdir():
                content = file.read_text()
                for claim_id in held:
                    self.assertNotIn(VALUES[claim_id], content,
                                     f"{file.name} leaked held {claim_id}")
            self.assertIn("545435.000", (target / "index.html").read_text())
            self.assertIn("4.02", (target / "index.html").read_text())
            self.assertIn("Research Lab Control Center", (target / "index.html").read_text())

    def test_each_source_family_has_exact_bounded_blast_radius(self):
        for root, affected in ROOT_IMPACT.items():
            with self.subTest(root=root):
                info = scenario.scenario_bundle(as_of=AS_OF,
                                                candidate=candidate(root))
                claim = info["claim_quarantine"]
                source = info["source_impact"]
                self.assertEqual(set(claim["quarantined_claim_ids"]), affected)
                self.assertEqual(set(source["affected_internal_source_claim_ids"]), affected)
                self.assertEqual(claim["qualified_values_still_visible_for_internal_research_only"],
                                 8 - len(affected))
                self.assertEqual(claim["external_claims_authorized"], 0)
                self.assertFalse(claim["source_revision_independently_verified"])
                self.assertEqual(claim["pending_source_replay_count"], 1)
                self.assertEqual(claim["independent_source_revalidation_queue"][0]["root"], root)
                self.assertEqual(claim["independently_unverified_human_pilot_controls"], 18)
                self.assertTrue(all(c["safe_internal_value"] is None
                                    for c in claim["claims"][8:]))

    def test_multiple_source_revision_union_and_pilot_are_not_extra_invalidations(self):
        info = scenario.scenario_bundle(
            as_of=AS_OF, candidate=candidate("BEA", "CENSUS", "PILOT"))
        expected = ROOT_IMPACT["BEA"] | ROOT_IMPACT["CENSUS"]
        self.assertEqual(set(info["claim_quarantine"]["quarantined_claim_ids"]), expected)
        self.assertEqual(info["claim_quarantine"]["pending_source_replay_count"], 3)
        self.assertEqual(info["claim_quarantine"]["qualified_values_still_visible_for_internal_research_only"],
                         1)
        self.assertEqual(info["claim_quarantine"]["claims"][5]["safe_internal_value"], "4.02")

    def test_all_statistical_roots_quarantine_all_eight(self):
        info = scenario.scenario_bundle(
            as_of=AS_OF, candidate=candidate("BEA", "CENSUS", "BLS_PPI", "BLS_SECTORAL"))
        self.assertEqual(info["claim_quarantine"]["qualified_values_withheld_pending_independent_replay"], 8)
        self.assertEqual(info["claim_quarantine"]["qualified_values_still_visible_for_internal_research_only"], 0)
        self.assertEqual(info["claim_quarantine"]["external_claims_authorized"], 0)

    def test_external_commercial_recovery_lookup_stays_empty(self):
        c = candidate("CENSUS")
        for claim_id in m38.m35.ALL_IDS:
            with self.subTest(claim_id=claim_id):
                view = m38.claim_view(as_of=AS_OF, claim_id=claim_id,
                                      purpose=m38.EXTERNAL, candidate=c)
                self.assertIsNone(view["safe_value"])
                self.assertFalse(view["external_publication_authorized"])
                self.assertFalse(view["real_customer_evidence_or_cash_verified"])

    def test_fake_publisher_and_buyer_approvals_refused_before_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for field in ("original_publisher_replay_verified",
                          "real_customer_evidence_verified",
                          "external_publication_authorized"):
                with self.subTest(field=field):
                    forged = candidate("CENSUS")
                    forged[field] = True
                    source = base / (field + ".json")
                    source.write_text(json.dumps(forged))
                    out = base / (field + "-result")
                    with self.assertRaises(ValueError):
                        scenario.write_scenario(as_of=AS_OF,candidate_path=source,out=out)
                    self.assertFalse(out.exists())

    def test_nonempty_directory_refused_to_prevent_legacy_archive_mix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "candidate.json"
            incoming.write_text(json.dumps(candidate("CENSUS")))
            target = root / "existing"
            target.mkdir()
            legacy = target / "claim_clearance.json"
            legacy.write_text("legacy raw historical value: 402827.246")
            with self.assertRaisesRegex(ValueError, "FRESH_OUTPUT_DIRECTORY_REQUIRED"):
                scenario.write_scenario(as_of=AS_OF,candidate_path=incoming,out=target)
            self.assertEqual(list(target.iterdir()), [legacy])
            self.assertNotIn("index.html", [p.name for p in target.iterdir()])

    def test_unknown_source_and_unverified_fake_claim_disallowed(self):
        incoming = candidate("CENSUS")
        incoming["source_receipts"]["RETAIL_CLIENT"] = "a" * 64
        with self.assertRaises(ValueError):
            scenario.scenario_bundle(as_of=AS_OF,candidate=incoming)
        incoming = candidate("CENSUS")
        incoming["signed_buyer_approval"] = "mock"
        with self.assertRaises(ValueError):
            scenario.scenario_bundle(as_of=AS_OF,candidate=incoming)


if __name__ == "__main__":
    unittest.main()
