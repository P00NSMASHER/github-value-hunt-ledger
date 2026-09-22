"""Conservative carrier identity normalization for SHAQ rate evidence."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone


CORP_WORDS = {
    "CO", "COMPANY", "CORP", "CORPORATION", "INC", "INCORPORATED",
    "LTD", "LIMITED", "LLC", "LINE", "LINES", "SHIPPING", "GROUP",
}


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_carrier(value: str) -> str:
    value = value.upper().replace("&", " AND ")
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    tokens = [t for t in value.split() if t and t not in CORP_WORDS]
    return " ".join(tokens)


@dataclass(frozen=True)
class IdentityResult:
    carrier_raw: str
    carrier_normalized: str
    fmc_organization_no: str | None
    status: str
    confidence: float
    evidence: str | None = None


def resolve_identity(conn: sqlite3.Connection, carrier_raw: str) -> IdentityResult:
    normalized = normalize_carrier(carrier_raw)

    exact = conn.execute(
        """SELECT fmc_organization_no, confidence, reviewed, evidence
           FROM carrier_identity_map
           WHERE carrier_raw_pattern=? AND carrier_normalized=?
           ORDER BY reviewed DESC, confidence DESC
           LIMIT 1""",
        (carrier_raw, normalized),
    ).fetchone()
    if exact:
        org, confidence, reviewed, evidence = exact
        return IdentityResult(
            carrier_raw=carrier_raw,
            carrier_normalized=normalized,
            fmc_organization_no=org,
            status="REVIEWED_EXACT" if reviewed and org else "MAPPED_REVIEW_REQUIRED",
            confidence=float(confidence),
            evidence=evidence,
        )

    # Normalized aliases may be suggested but never authorize money-bearing joins.
    aliases = conn.execute(
        """SELECT DISTINCT fmc_organization_no, confidence, reviewed, evidence
           FROM carrier_identity_map
           WHERE carrier_normalized=?
           ORDER BY reviewed DESC, confidence DESC""",
        (normalized,),
    ).fetchall()
    reviewed_orgs = {
        row[0] for row in aliases if row[2] and row[0]
    }
    if len(reviewed_orgs) == 1:
        org = next(iter(reviewed_orgs))
        best = next(row for row in aliases if row[0] == org and row[2])
        return IdentityResult(
            carrier_raw=carrier_raw,
            carrier_normalized=normalized,
            fmc_organization_no=org,
            status="REVIEWED_NORMALIZED_ALIAS",
            confidence=float(best[1]),
            evidence=best[3],
        )

    return IdentityResult(
        carrier_raw=carrier_raw,
        carrier_normalized=normalized,
        fmc_organization_no=None,
        status="UNRESOLVED",
        confidence=0.0,
    )


def add_reviewed_mapping(
    conn: sqlite3.Connection,
    *,
    carrier_raw_pattern: str,
    fmc_organization_no: str,
    evidence: str,
    confidence: float = 1.0,
) -> None:
    normalized = normalize_carrier(carrier_raw_pattern)
    conn.execute(
        """INSERT INTO carrier_identity_map(
             carrier_raw_pattern, carrier_normalized, fmc_organization_no,
             mapping_method, confidence, reviewed, evidence, created_at
           ) VALUES (?, ?, ?, 'MANUAL_REVIEWED_EXACT', ?, 1, ?, ?)
           ON CONFLICT(carrier_raw_pattern, carrier_normalized)
           DO UPDATE SET
             fmc_organization_no=excluded.fmc_organization_no,
             mapping_method=excluded.mapping_method,
             confidence=excluded.confidence,
             reviewed=1,
             evidence=excluded.evidence""",
        (
            carrier_raw_pattern,
            normalized,
            fmc_organization_no,
            confidence,
            evidence,
            utcnow(),
        ),
    )
    conn.commit()
