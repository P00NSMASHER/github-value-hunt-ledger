#!/usr/bin/env python3
"""Quality and RecoveryWorks-readiness report for an ingested URDB artifact."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd


def build_report(db_path: Path, current_dir: Path) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rates = pd.read_parquet(current_dir / "rates.parquet")
    energy = pd.read_parquet(current_dir / "energy_rates.parquet")
    demand = pd.read_parquet(current_dir / "demand_rates.parquet")
    schedules = pd.read_parquet(current_dir / "schedules.parquet")
    flat_months = pd.read_parquet(current_dir / "flat_demand_months.parquet")

    official = conn.execute(
        """SELECT id,release_key,tariff_count,utility_count,active_count
           FROM releases WHERE commit_sha IS NULL
           ORDER BY id DESC LIMIT 1"""
    ).fetchone()
    latest_git = conn.execute(
        """SELECT id,release_key,commit_sha,commit_date,tariff_count,utility_count,active_count
           FROM releases WHERE commit_sha IS NOT NULL
           ORDER BY datetime(commit_date) DESC LIMIT 1"""
    ).fetchone()

    delta = {}
    if official and latest_git:
        official_labels = {
            r[0]: r[1] for r in conn.execute(
                "SELECT label,row_fingerprint FROM current_tariffs"
            )
        }
        hist_labels = {
            r[0]: r[1] for r in conn.execute(
                """SELECT label,row_fingerprint
                   FROM tariff_release_observations WHERE release_id=?""",
                (latest_git["id"],),
            )
        }
        shared = official_labels.keys() & hist_labels.keys()
        delta = {
            "latest_git_commit": latest_git["commit_sha"],
            "latest_git_date": latest_git["commit_date"],
            "new_labels_since_git_release": len(official_labels.keys() - hist_labels.keys()),
            "labels_absent_from_official_current": len(hist_labels.keys() - official_labels.keys()),
            "shared_labels": len(shared),
            "shared_labels_changed": sum(
                official_labels[label] != hist_labels[label] for label in shared
            ),
        }

    chain_depth = [
        int(r[0]) for r in conn.execute(
            "SELECT chain_depth FROM tariff_history_edges"
        )
    ]

    energy_group = (
        energy.groupby("label").agg(
            periods=("period", "nunique"),
            tiers=("tier", "max"),
            rows=("tier", "size"),
        )
        if not energy.empty else pd.DataFrame()
    )
    if not energy_group.empty:
        energy_group["tier_count_max"] = energy_group["tiers"] + 1

    demand_by_label = (
        demand.groupby("label").agg(
            structures=("structure", "nunique"),
            periods=("period", "nunique"),
            rows=("tier", "size"),
        )
        if not demand.empty else pd.DataFrame()
    )

    simple_energy = 0
    tiered_energy = 0
    tou_energy = 0
    if not energy_group.empty:
        simple_energy = int(
            ((energy_group["periods"] == 1) & (energy_group["tier_count_max"] == 1)).sum()
        )
        tiered_energy = int((energy_group["tier_count_max"] > 1).sum())
        tou_energy = int((energy_group["periods"] > 1).sum())

    fixed_units = []
    if "fixedchargeunits" in rates.columns:
        fixed_units = (
            rates["fixedchargeunits"].dropna().astype(str)
            .value_counts().head(20).to_dict()
        )
    min_units = []
    if "minchargeunits" in rates.columns:
        min_units = (
            rates["minchargeunits"].dropna().astype(str)
            .value_counts().head(20).to_dict()
        )

    report = {
        "current": {
            "tariffs": int(len(rates)),
            "utilities": int(rates["utility"].nunique()) if "utility" in rates else 0,
            "active": int((rates["status"] == "Active").sum()) if "status" in rates else 0,
            "ended": int((rates["status"] == "Ended").sum()) if "status" in rates else 0,
            "startdate_present": int(rates["startdate"].notna().sum()) if "startdate" in rates else 0,
            "enddate_present": int(rates["enddate"].notna().sum()) if "enddate" in rates else 0,
        },
        "tables": {
            "energy_rate_rows": int(len(energy)),
            "energy_tariffs": int(energy["label"].nunique()) if not energy.empty else 0,
            "demand_rate_rows": int(len(demand)),
            "demand_tariffs": int(demand["label"].nunique()) if not demand.empty else 0,
            "flat_demand_month_rows": int(len(flat_months)),
            "schedule_rows": int(len(schedules)),
            "schedule_tariffs": int(schedules["label"].nunique()) if not schedules.empty else 0,
        },
        "version_history": {
            "chains": conn.execute(
                "SELECT COUNT(DISTINCT chain_root) FROM tariff_history_edges"
            ).fetchone()[0],
            "linked_revisions": conn.execute(
                "SELECT COUNT(*) FROM tariff_history_edges WHERE supersedes IS NOT NULL AND supersedes<>''"
            ).fetchone()[0],
            "cycle_rows": conn.execute(
                "SELECT COUNT(*) FROM tariff_history_edges WHERE cycle_detected=1"
            ).fetchone()[0],
            "max_chain_depth": max(chain_depth) if chain_depth else 0,
            "historical_release_count": conn.execute(
                "SELECT COUNT(*) FROM releases WHERE commit_sha IS NOT NULL"
            ).fetchone()[0],
            "historical_observation_rows": conn.execute(
                "SELECT COUNT(*) FROM tariff_release_observations"
            ).fetchone()[0],
        },
        "latest_release_delta": delta,
        "rate_complexity": {
            "single_period_single_tier_energy_tariffs": simple_energy,
            "tiered_energy_tariffs": tiered_energy,
            "multi_period_energy_tariffs": tou_energy,
            "demand_tariffs": int(len(demand_by_label)),
            "multi_structure_demand_tariffs": (
                int((demand_by_label["structures"] > 1).sum())
                if not demand_by_label.empty else 0
            ),
            "fixed_charge_units": fixed_units,
            "minimum_charge_units": min_units,
        },
        "recoveryworks_boundary": {
            "dataset_rate_is_account_enrollment_proof": False,
            "exact_tariff_label_or_account_service_class_required": True,
            "overlapping_effective_candidates_fail_closed": True,
            "complex_tariff_logic_requires_explicit_supported_conversion": True,
        },
    }
    conn.close()
    return report


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--current-dir", required=True)
    p.add_argument("--output")
    args = p.parse_args()
    report = build_report(Path(args.db), Path(args.current_dir))
    payload = json.dumps(report, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(payload)
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
