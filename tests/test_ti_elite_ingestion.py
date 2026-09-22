from __future__ import annotations

import json
from pathlib import Path
import unittest

from tools.ti_elite_ingestion import load_registry, ordered_queue, summarize, validate_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "intelligence" / "ELITE_SOURCE_INGESTION.json"


class EliteIngestionRegistryTests(unittest.TestCase):
    def test_elite_registry_is_valid_and_pinned(self):
        payload = load_registry(REGISTRY)
        summary = summarize(payload)
        self.assertGreaterEqual(summary["sources"], 50)
        self.assertGreater(summary["p0_open"], 0)
        self.assertEqual(summary["started"], ["ELITE-037"])
        self.assertTrue(all(len(row["revision"]) == 40 for row in payload["sources"]))

    def test_queue_starts_with_open_p0_work(self):
        payload = load_registry(REGISTRY)
        queue = ordered_queue(payload)
        open_p0 = [
            row for row in queue
            if row["priority"] == "P0" and row["status"] in {"STARTED", "QUEUED"}
        ]
        self.assertTrue(open_p0)
        self.assertEqual(open_p0[0]["status"], "STARTED")
        self.assertEqual(open_p0[0]["repository"], "bsaffel/moneybin")

    def test_duplicate_pin_fails_closed(self):
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        payload["sources"].append(dict(payload["sources"][0], source_id="ELITE-999"))
        with self.assertRaisesRegex(ValueError, r"duplicate repository\+revision pin"):
            validate_registry(payload)

    def test_floating_revision_fails_closed(self):
        payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
        payload["sources"][0]["revision"] = "main"
        with self.assertRaisesRegex(ValueError, "exact 40-character revision required"):
            validate_registry(payload)


if __name__ == "__main__":
    unittest.main()
