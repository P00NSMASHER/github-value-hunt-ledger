#!/usr/bin/env python3
"""Fail-closed effective-date resolver for the FMC tariff rule ledger."""

from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Candidate:
    entity_class: str
    organization_no: str
    legal_name: str
    trade_name: str
    tariff_location: str
    evidence_url: str
    final_url: str | None
    source_sha256: str | None
    fetched_at: str
    effective_from: str
    effective_to: str | None
    source_version: str | None
    rule_type: str
    term_kind: str
    amount_value: str | None
    currency: str | None
    unit: str | None
    quantity_value: str | None
    confidence: float
    parser_version: str
    evidence_locator: str | None
    evidence_excerpt: str


def _valid_iso_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def _authority_key(row: sqlite3.Row) -> tuple[str, str]:
    version = (row["source_version"] or "").strip()
    digest = (row["source_sha256"] or "").strip()
    return version, digest


def _rows_to_candidates(rows: list[sqlite3.Row]) -> list[Candidate]:
    seen: set[tuple[Any, ...]] = set()
    out: list[Candidate] = []
    for row in rows:
        key = (
            row["source_sha256"],
            row["effective_from"],
            row["effective_to"],
            row["source_version"],
            row["rule_type"],
            row["term_kind"],
            row["amount_value"],
            row["currency"],
            row["unit"],
            row["quantity_value"],
            row["evidence_locator"],
            row["evidence_excerpt"],
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(Candidate(**{field: row[field] for field in Candidate.__dataclass_fields__}))
    return out


def resolve_rule(
    conn: sqlite3.Connection,
    organization_no: str,
    service_date: str,
    rule_type: str,
    *,
    currency: str | None = None,
    min_confidence: float = 0.80,
) -> dict[str, Any]:
    service_date = _valid_iso_date(service_date)
    organization_no = organization_no.strip()
    rule_type = rule_type.strip()

    entity = conn.execute(
        """SELECT entity_class, organization_no, legal_name, trade_name
           FROM entities
           WHERE organization_no=?
           ORDER BY active DESC, id DESC
           LIMIT 1""",
        (organization_no,),
    ).fetchone()
    if entity is None:
        return {
            "status": "NO_ENTITY",
            "organization_no": organization_no,
            "service_date": service_date,
            "rule_type": rule_type,
            "candidates": [],
        }

    params: list[Any] = [organization_no, rule_type, min_confidence]
    currency_sql = ""
    if currency:
        currency_sql = " AND (currency=? OR currency IS NULL)"
        params.append(currency.upper())

    dated = conn.execute(
        f"""SELECT *
            FROM carrier_rule_effective_ledger
            WHERE organization_no=?
              AND lower(rule_type)=lower(?)
              AND confidence>=?
              AND effective_from IS NOT NULL
              {currency_sql}
              AND date(effective_from) <= date(?)
              AND (effective_to IS NULL OR date(effective_to) >= date(?))
            ORDER BY date(effective_from) DESC, source_version DESC, source_sha256""",
        (*params, service_date, service_date),
    ).fetchall()

    if not dated:
        undated_params: list[Any] = [organization_no, rule_type, min_confidence]
        undated_currency_sql = ""
        if currency:
            undated_currency_sql = " AND (currency=? OR currency IS NULL)"
            undated_params.append(currency.upper())
        undated = conn.execute(
            f"""SELECT *
                FROM carrier_rule_effective_ledger
                WHERE organization_no=?
                  AND lower(rule_type)=lower(?)
                  AND confidence>=?
                  AND effective_from IS NULL
                  {undated_currency_sql}
                ORDER BY fetched_at DESC
                LIMIT 50""",
            undated_params,
        ).fetchall()
        return {
            "status": "UNDATED_ONLY" if undated else "NO_EFFECTIVE_RULE",
            "organization_no": organization_no,
            "legal_name": entity["legal_name"],
            "trade_name": entity["trade_name"],
            "service_date": service_date,
            "rule_type": rule_type,
            "candidates": [asdict(x) for x in _rows_to_candidates(undated)],
        }

    latest_start = max(row["effective_from"] for row in dated)
    latest = [row for row in dated if row["effective_from"] == latest_start]

    authority_keys = {_authority_key(row) for row in latest}
    nonempty_versions = {v for v, _ in authority_keys if v}
    hashes = {h for _, h in authority_keys if h}

    # Multiple explicit versions effective on the same latest date are a hard conflict.
    ambiguous = len(nonempty_versions) > 1
    # If version labels are absent, multiple source hashes are not safe to collapse.
    if not nonempty_versions and len(hashes) > 1:
        ambiguous = True

    candidates = _rows_to_candidates(latest)
    return {
        "status": "AMBIGUOUS_AUTHORITY" if ambiguous else "RESOLVED",
        "organization_no": organization_no,
        "legal_name": entity["legal_name"],
        "trade_name": entity["trade_name"],
        "service_date": service_date,
        "rule_type": rule_type,
        "selected_effective_from": latest_start,
        "authority_versions": sorted(nonempty_versions),
        "source_hashes": sorted(hashes),
        "candidates": [asdict(x) for x in candidates],
    }


def resolve_all_rules(
    conn: sqlite3.Connection,
    organization_no: str,
    service_date: str,
    *,
    min_confidence: float = 0.80,
) -> dict[str, Any]:
    service_date = _valid_iso_date(service_date)
    rows = conn.execute(
        """SELECT DISTINCT rule_type
           FROM carrier_rule_effective_ledger
           WHERE organization_no=?
             AND confidence>=?
           ORDER BY rule_type""",
        (organization_no, min_confidence),
    ).fetchall()
    if not rows:
        entity = conn.execute(
            "SELECT 1 FROM entities WHERE organization_no=? LIMIT 1",
            (organization_no,),
        ).fetchone()
        return {
            "status": "NO_RULES" if entity else "NO_ENTITY",
            "organization_no": organization_no,
            "service_date": service_date,
            "rules": {},
        }

    resolved = {
        row["rule_type"]: resolve_rule(
            conn,
            organization_no,
            service_date,
            row["rule_type"],
            min_confidence=min_confidence,
        )
        for row in rows
    }
    statuses = {value["status"] for value in resolved.values()}
    overall = (
        "AMBIGUOUS_AUTHORITY"
        if "AMBIGUOUS_AUTHORITY" in statuses
        else "RESOLVED_WITH_GAPS"
        if statuses - {"RESOLVED"}
        else "RESOLVED"
    )
    return {
        "status": overall,
        "organization_no": organization_no,
        "service_date": service_date,
        "rules": resolved,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Resolve effective FMC tariff evidence")
    p.add_argument("--db", required=True)
    p.add_argument("--organization-no", required=True)
    p.add_argument("--date", required=True)
    p.add_argument("--rule-type")
    p.add_argument("--currency")
    p.add_argument("--min-confidence", type=float, default=0.80)
    p.add_argument("--output")
    args = p.parse_args()

    conn = sqlite3.connect(Path(args.db))
    conn.row_factory = sqlite3.Row
    if args.rule_type:
        result = resolve_rule(
            conn,
            args.organization_no,
            args.date,
            args.rule_type,
            currency=args.currency,
            min_confidence=args.min_confidence,
        )
    else:
        result = resolve_all_rules(
            conn,
            args.organization_no,
            args.date,
            min_confidence=args.min_confidence,
        )
    conn.close()

    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
