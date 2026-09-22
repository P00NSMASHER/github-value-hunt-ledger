#!/usr/bin/env python3
"""Fail-closed service-date resolver for the URDB tariff ledger."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any


def iso_date(value: str) -> str:
    return date.fromisoformat(value).isoformat()


def row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def resolve(
    conn: sqlite3.Connection,
    *,
    service_date: str,
    label: str | None = None,
    utility: str | None = None,
    eiaid: str | None = None,
    name: str | None = None,
    sector: str | None = None,
) -> dict[str, Any]:
    when = iso_date(service_date)
    conn.row_factory = sqlite3.Row

    filters = []
    params: list[Any] = []
    if label:
        filters.append("lower(label)=lower(?)")
        params.append(label.strip())
    if utility:
        filters.append("lower(utility)=lower(?)")
        params.append(utility.strip())
    if eiaid:
        filters.append("eiaid=?")
        params.append(eiaid.strip())
    if name:
        filters.append("lower(name)=lower(?)")
        params.append(name.strip())
    if sector:
        filters.append("lower(sector)=lower(?)")
        params.append(sector.strip())

    if not filters:
        raise ValueError("label or utility/eiaid filters are required")

    base_where = " AND ".join(filters)
    all_rows = conn.execute(
        f"""SELECT * FROM tariff_effective_ledger
            WHERE {base_where}
            ORDER BY effective_from, label""",
        params,
    ).fetchall()
    if not all_rows:
        return {
            "status": "NO_TARIFF",
            "service_date": when,
            "candidates": [],
        }

    dated = []
    undated = []
    for row in all_rows:
        start = (row["effective_from"] or "")[:10]
        end = (row["effective_to"] or "")[:10]
        if not start:
            undated.append(row)
            continue
        try:
            covers = date.fromisoformat(start) <= date.fromisoformat(when)
            if end:
                covers = covers and date.fromisoformat(end) >= date.fromisoformat(when)
        except ValueError:
            undated.append(row)
            continue
        if covers:
            dated.append(row)

    if label and not dated:
        return {
            "status": "OUTSIDE_EFFECTIVE_INTERVAL" if not undated else "UNDATED_ONLY",
            "service_date": when,
            "candidates": [row_dict(r) for r in (undated or all_rows)],
        }

    if not dated:
        return {
            "status": "UNDATED_ONLY" if undated else "NO_EFFECTIVE_TARIFF",
            "service_date": when,
            "candidates": [row_dict(r) for r in undated],
        }

    # Do not choose between overlapping tariffs. A customer account/service-class
    # mapping is required to disambiguate distinct applicable rate schedules.
    if len(dated) != 1:
        return {
            "status": "AMBIGUOUS_TARIFF",
            "service_date": when,
            "candidate_count": len(dated),
            "candidates": [row_dict(r) for r in dated],
        }

    selected = row_dict(dated[0])
    return {
        "status": "RESOLVED",
        "service_date": when,
        "selected": selected,
        "candidates": [selected],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    p.add_argument("--service-date", required=True)
    p.add_argument("--label")
    p.add_argument("--utility")
    p.add_argument("--eiaid")
    p.add_argument("--name")
    p.add_argument("--sector")
    args = p.parse_args()

    conn = sqlite3.connect(args.db)
    result = resolve(
        conn,
        service_date=args.service_date,
        label=args.label,
        utility=args.utility,
        eiaid=args.eiaid,
        name=args.name,
        sector=args.sector,
    )
    conn.close()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
