import gzip
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import ingest


class URDBIngestTests(unittest.TestCase):
    def test_normalize_official_bulk_preserves_rates_tiers_and_schedule(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            grid = json.dumps([[0] * 24 for _ in range(12)])
            df = pd.DataFrame([{
                "label": "TARIFF-V2",
                "utility": "Example Electric",
                "eiaid": "12345",
                "name": "General Service",
                "sector": "Commercial",
                "servicetype": "Bundled",
                "startdate": "2026-01-01",
                "enddate": "",
                "supersedes": "TARIFF-V1",
                "approved": "true",
                "is_default": "false",
                "energyrateunit": "kWh",
                "energyratestructure/period0/tier0rate": "0.10",
                "energyratestructure/period0/tier0max": "1000",
                "energyratestructure/period0/tier1rate": "0.15",
                "energyratestructure/period0/tier1max": "",
                "demandrateunit": "kW",
                "demandratestructure/period0/tier0rate": "12.50",
                "energyweekdayschedule": grid,
            }])
            raw = root / "usurdb.csv.gz"
            with gzip.open(raw, "wt", encoding="utf-8", newline="") as fh:
                df.to_csv(fh, index=False)

            stats = ingest.normalize_official_bulk(raw, root / "current")
            self.assertEqual(stats["tariff_count"], 1)
            self.assertEqual(stats["utility_count"], 1)
            self.assertEqual(stats["active_count"], 1)

            rates = pd.read_parquet(root / "current" / "rates.parquet")
            energy = pd.read_parquet(root / "current" / "energy_rates.parquet")
            demand = pd.read_parquet(root / "current" / "demand_rates.parquet")
            schedules = pd.read_parquet(root / "current" / "schedules.parquet")

            self.assertEqual(rates.iloc[0]["status"], "Active")
            self.assertTrue(bool(rates.iloc[0]["has_energy_rates"]))
            self.assertTrue(bool(rates.iloc[0]["has_demand_rates"]))
            self.assertEqual(len(energy), 2)
            self.assertEqual(list(energy["rate"]), [0.10, 0.15])
            self.assertEqual(len(demand), 1)
            self.assertEqual(float(demand.iloc[0]["rate"]), 12.5)
            self.assertEqual(len(schedules), 12)
            self.assertTrue((schedules["hour_start"] == 0).all())
            self.assertTrue((schedules["hour_end"] == 23).all())

    def test_chain_info_walks_supersedes_and_detects_cycle(self):
        df = pd.DataFrame([
            {"label": "A1", "supersedes": None},
            {"label": "A2", "supersedes": "A1"},
            {"label": "A3", "supersedes": "A2"},
            {"label": "B1", "supersedes": "B2"},
            {"label": "B2", "supersedes": "B1"},
        ])
        info = ingest.chain_info(df)
        self.assertEqual(info["A1"], ("A1", 0, 0))
        self.assertEqual(info["A2"], ("A1", 1, 0))
        self.assertEqual(info["A3"], ("A1", 2, 0))
        self.assertEqual(info["B1"][2], 1)
        self.assertEqual(info["B2"][2], 1)
        self.assertEqual(info["B1"][0], info["B2"][0])

    def test_load_current_tariffs_builds_effective_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rates_path = root / "rates.parquet"
            pd.DataFrame([
                {
                    "label": "A1",
                    "utility": "Example Electric",
                    "eiaid": "123",
                    "name": "GS",
                    "sector": "Commercial",
                    "servicetype": "Bundled",
                    "startdate": pd.Timestamp("2025-01-01", tz="UTC"),
                    "enddate": pd.Timestamp("2025-12-31", tz="UTC"),
                    "supersedes": None,
                    "superseded_by": "A2",
                    "status": "Ended",
                    "has_energy_rates": True,
                },
                {
                    "label": "A2",
                    "utility": "Example Electric",
                    "eiaid": "123",
                    "name": "GS",
                    "sector": "Commercial",
                    "servicetype": "Bundled",
                    "startdate": pd.Timestamp("2026-01-01", tz="UTC"),
                    "enddate": pd.NaT,
                    "supersedes": "A1",
                    "superseded_by": None,
                    "status": "Active",
                    "has_energy_rates": True,
                },
            ]).to_parquet(rates_path, index=False)

            conn = ingest.init_db(root / "ledger.sqlite")
            rid = ingest.insert_release(
                conn,
                release_key="fixture",
                commit_sha=None,
                commit_date=None,
                message="fixture",
                metadata={"tariff_count": 2},
                metadata_sha="fixturehash",
            )
            stats = ingest.load_current_tariffs(
                conn, rates_path, release_id=rid, source_file_sha="sourcehash"
            )
            self.assertEqual(stats["tariffs"], 2)
            self.assertEqual(stats["chains"], 1)
            rows = conn.execute(
                """SELECT label,chain_root,chain_depth
                   FROM tariff_effective_ledger ORDER BY chain_depth"""
            ).fetchall()
            self.assertEqual(rows, [("A1", "A1", 0), ("A2", "A1", 1)])
            conn.close()


if __name__ == "__main__":
    unittest.main()
