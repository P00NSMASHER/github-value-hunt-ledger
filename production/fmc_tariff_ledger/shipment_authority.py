#!/usr/bin/env python3
"""Combine reviewed contract-rate evidence with effective FMC tariff rules.

The envelope is the handoff object for money-bearing freight review. It does not
calculate a recovery. It answers:
- is there one defensible contract base rate for this exact carrier/lane/container/date?
- what public/market benchmark context exists without being treated as authority?
- which FMC tariff rules were effective for the same carrier/date?
- are any authority conflicts unresolved?

Lane matching is exact after whitespace/case normalization. Port alias/entity fuzzy
matching must be resolved upstream and reviewed before this module is called.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any

import resolve


def norm_text(value: str) -> str:
    return " ".join((value or "").strip().upper().split())


def norm_container(value: str) -> str:
    value = norm_text(value).replace(" CONTAINER", "")
    return {"40HC": "40HQ", "20DRY": "20GP", "40DRY": "40GP"}.get(value, value)


def _rate_evidence_rows(
    conn: sqlite3.Connection,
    *,
    fmc_organization_no: str,
    origin: str,
    destination: str,
    container_type: str,
    currency: str,
    shipment_date: str,
    readiness: str,
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
          v.*,
          p.sha256 AS page_sha256,
          p.url AS page_url,
          q.response_sha256 AS query_response_sha256,
          q.raw_relpath AS query_raw_relpath
        FROM shaq_rate_authority_view v
        LEFT JOIN shaq_route_pages p ON p.id=v.route_page_id
        LEFT JOIN shaq_queries q ON q.id=v.query_id
        WHERE v.authority_readiness=?
          AND COALESCE(v.fmc_organization_no, '')=?
          AND upper(trim(v.origin_raw))=?
          AND upper(trim(v.destination_raw))=?
          AND upper(trim(v.container_type))=?
          AND upper(trim(v.currency))=?
          AND (v.valid_from IS NULL OR date(v.valid_from) <= date(?))
          AND (v.valid_to IS NULL OR date(v.valid_to) >= date(?))
        ORDER BY
          CASE WHEN v.valid_from IS NULL THEN 1 ELSE 0 END,
          date(v.valid_from) DESC,
          v.id
        """,
        (
            readiness,
            fmc_organization_no,
            norm_text(origin),
            norm_text(destination),
            norm_container(container_type),
            currency.upper().strip(),
            shipment_date,
            shipment_date,
        ),
    ).fetchall()


def _benchmark_rows(
    conn: sqlite3.Connection,
    *,
    origin: str,
    destination: str,
    container_type: str,
    currency: str,
    shipment_date: str,
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
          v.*,
          p.sha256 AS page_sha256,
          p.url AS page_url,
          q.response_sha256 AS query_response_sha256
        FROM shaq_rate_authority_view v
        LEFT JOIN shaq_route_pages p ON p.id=v.route_page_id
        LEFT JOIN shaq_queries q ON q.id=v.query_id
        WHERE v.authority_readiness='BENCHMARK_ONLY'
          AND upper(trim(v.origin_raw))=?
          AND upper(trim(v.destination_raw))=?
          AND upper(trim(v.container_type))=?
          AND upper(trim(v.currency))=?
          AND (v.valid_from IS NULL OR date(v.valid_from) <= date(?))
          AND (v.valid_to IS NULL OR date(v.valid_to) >= date(?))
        ORDER BY v.valid_to DESC, v.id
        LIMIT 200
        """,
        (
            norm_text(origin),
            norm_text(destination),
            norm_container(container_type),
            currency.upper().strip(),
            shipment_date,
            shipment_date,
        ),
    ).fetchall()


def _serialize_rate(row: sqlite3.Row) -> dict[str, Any]:
    keep = [
        "id",
        "origin_raw",
        "destination_raw",
        "carrier_raw",
        "carrier_normalized",
        "fmc_organization_no",
        "fmc_identity_status",
        "container_type",
        "amount_value",
        "currency",
        "valid_from",
        "valid_to",
        "rate_basis",
        "transit_time",
        "source_url",
        "rate_kind",
        "source_label",
        "source_contract_reference",
        "evidence_excerpt",
        "parser_confidence",
        "parser_version",
        "authority_readiness",
        "page_sha256",
        "page_url",
        "query_response_sha256",
    ]
    return {key: row[key] for key in keep if key in row.keys()}


def resolve_contract_rate(
    conn: sqlite3.Connection,
    *,
    fmc_organization_no: str,
    origin: str,
    destination: str,
    container_type: str,
    currency: str,
    shipment_date: str,
) -> dict[str, Any]:
    rows = _rate_evidence_rows(
        conn,
        fmc_organization_no=fmc_organization_no,
        origin=origin,
        destination=destination,
        container_type=container_type,
        currency=currency,
        shipment_date=shipment_date,
        readiness="AUTHORITY_READY",
    )

    if not rows:
        benchmarks = _benchmark_rows(
            conn,
            origin=origin,
            destination=destination,
            container_type=container_type,
            currency=currency,
            shipment_date=shipment_date,
        )
        return {
            "status": "NO_AUTHORITY_READY_CONTRACT_RATE",
            "contract_candidates": [],
            "benchmark_context": summarize_benchmarks(benchmarks),
        }

    # Prefer the latest explicit validity start if any. Rows without valid_from
    # cannot supersede an explicitly dated row.
    explicit_starts = [row["valid_from"] for row in rows if row["valid_from"]]
    if explicit_starts:
        latest = max(explicit_starts)
        rows = [row for row in rows if row["valid_from"] == latest]

    values: dict[Decimal, list[sqlite3.Row]] = {}
    for row in rows:
        try:
            value = Decimal(str(row["amount_value"]))
        except Exception:
            continue
        values.setdefault(value, []).append(row)

    if not values:
        return {
            "status": "CONTRACT_RATE_NON_NUMERIC",
            "contract_candidates": [_serialize_rate(row) for row in rows],
            "benchmark_context": {},
        }

    rate_bases = {
        " ".join(str(row["rate_basis"] or "").lower().split())
        for row in rows
    }
    if len(rate_bases) > 1:
        return {
            "status": "AMBIGUOUS_CONTRACT_RATE_BASIS",
            "distinct_rate_bases": sorted(rate_bases),
            "contract_candidates": [_serialize_rate(row) for row in rows],
            "benchmark_context": {},
        }

    if len(values) > 1:
        return {
            "status": "AMBIGUOUS_CONTRACT_RATE",
            "distinct_amounts": sorted(str(value) for value in values),
            "contract_candidates": [_serialize_rate(row) for row in rows],
            "benchmark_context": {},
        }

    amount = next(iter(values))
    selected = values[amount]
    benchmarks = _benchmark_rows(
        conn,
        origin=origin,
        destination=destination,
        container_type=container_type,
        currency=currency,
        shipment_date=shipment_date,
    )
    return {
        "status": "RESOLVED",
        "amount_value": str(amount),
        "currency": currency.upper().strip(),
        "rate_basis": selected[0]["rate_basis"],
        "contract_candidates": [_serialize_rate(row) for row in selected],
        "benchmark_context": summarize_benchmarks(benchmarks),
    }


def summarize_benchmarks(rows: list[sqlite3.Row]) -> dict[str, Any]:
    if not rows:
        return {"status": "NONE", "count": 0, "rows": []}
    values = []
    for row in rows:
        try:
            values.append(Decimal(str(row["amount_value"])))
        except Exception:
            pass
    summary: dict[str, Any] = {
        "status": "AVAILABLE",
        "count": len(rows),
        "rows": [_serialize_rate(row) for row in rows[:50]],
    }
    if values:
        summary.update(
            {
                "min": str(min(values)),
                "max": str(max(values)),
                "distinct_amounts": len(set(values)),
            }
        )
    return summary


def build_envelope(
    rate_conn: sqlite3.Connection,
    fmc_conn: sqlite3.Connection,
    *,
    fmc_organization_no: str,
    shipment_date: str,
    origin: str,
    destination: str,
    container_type: str,
    currency: str = "USD",
    rule_types: list[str] | None = None,
) -> dict[str, Any]:
    rate = resolve_contract_rate(
        rate_conn,
        fmc_organization_no=fmc_organization_no,
        origin=origin,
        destination=destination,
        container_type=container_type,
        currency=currency,
        shipment_date=shipment_date,
    )

    if rule_types:
        rules = {
            rule_type: resolve.resolve_rule(
                fmc_conn,
                fmc_organization_no,
                shipment_date,
                rule_type,
            )
            for rule_type in rule_types
        }
        rule_statuses = {value["status"] for value in rules.values()}
        rules_status = (
            "AMBIGUOUS_AUTHORITY"
            if "AMBIGUOUS_AUTHORITY" in rule_statuses
            else "RESOLVED_WITH_GAPS"
            if rule_statuses - {"RESOLVED"}
            else "RESOLVED"
        )
        rule_result = {"status": rules_status, "rules": rules}
    else:
        rule_result = resolve.resolve_all_rules(
            fmc_conn,
            fmc_organization_no,
            shipment_date,
        )

    blockers = []
    if rate["status"] != "RESOLVED":
        blockers.append(rate["status"])
    if rule_result["status"] == "AMBIGUOUS_AUTHORITY":
        blockers.append("AMBIGUOUS_TARIFF_AUTHORITY")

    if blockers:
        status = "NOT_READY_FOR_MONEY_ASSERTION"
    elif rule_result["status"] == "RESOLVED":
        status = "AUTHORITY_ENVELOPE_READY"
    else:
        status = "BASE_RATE_READY_RULE_GAPS"

    return {
        "status": status,
        "asserted_recovery": "0.00",
        "fmc_organization_no": fmc_organization_no,
        "shipment_date": shipment_date,
        "lane": {
            "origin": origin,
            "destination": destination,
            "container_type": norm_container(container_type),
            "currency": currency.upper().strip(),
        },
        "base_rate_authority": rate,
        "tariff_rule_authority": rule_result,
        "blockers": blockers,
        "policy": {
            "exact_lane_match_only": True,
            "benchmark_rows_never_authorize_base_rate": True,
            "ambiguous_contract_amount_abstains": True,
            "ambiguous_tariff_version_abstains": True,
        },
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Build freight shipment authority envelope")
    p.add_argument("--rate-db", required=True)
    p.add_argument("--fmc-db", required=True)
    p.add_argument("--fmc-organization-no", required=True)
    p.add_argument("--shipment-date", required=True)
    p.add_argument("--origin", required=True)
    p.add_argument("--destination", required=True)
    p.add_argument("--container-type", required=True)
    p.add_argument("--currency", default="USD")
    p.add_argument("--rule-type", action="append")
    p.add_argument("--output")
    args = p.parse_args()

    rate_conn = sqlite3.connect(Path(args.rate_db))
    rate_conn.row_factory = sqlite3.Row
    fmc_conn = sqlite3.connect(Path(args.fmc_db))
    fmc_conn.row_factory = sqlite3.Row
    result = build_envelope(
        rate_conn,
        fmc_conn,
        fmc_organization_no=args.fmc_organization_no,
        shipment_date=args.shipment_date,
        origin=args.origin,
        destination=args.destination,
        container_type=args.container_type,
        currency=args.currency,
        rule_types=args.rule_type,
    )
    rate_conn.close()
    fmc_conn.close()
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(payload, end="")
    if args.output:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
