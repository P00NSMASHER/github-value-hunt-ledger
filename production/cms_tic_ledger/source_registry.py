from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from common import (
    canonicalize_url,
    fetch_small,
    sha256_bytes,
    stable_key,
    utcnow,
    write_blob,
)

REGISTRY_URL = (
    "https://raw.githubusercontent.com/EndurantDevs/healthcare-mrf-api/"
    "main/specs/mrf_payer_master_list.md"
)

FALLBACK_SOURCES = [
    ("UnitedHealthcare", "national", "https://transparency-in-coverage.uhc.com/", "UHC public TiC portal"),
    ("Anthem / Elevance", "national", "https://www.anthem.com/machine-readable-file/search/", "Anthem/Elevance public TiC search"),
    ("Cigna", "national", "https://www.cigna.com/legal/compliance/machine-readable-files", "Cigna public TiC landing"),
    ("Aetna / CVS", "national", "https://www.aetna.com/individuals-families/member-rights-resources/machine-readable-files.html", "Aetna public MRF landing"),
    ("Humana", "national", "https://developers.humana.com/syntheticdata/Resource/PCTFilesList?fileType=innetwork", "Humana public in-network list endpoint"),
    ("Optum", "national", "https://transparency-in-coverage.optum.com/", "Optum public TiC portal"),
    ("Centene / Fidelis", "national", "https://www.centene.com/content/dam/centene/Centene%20Corporate/json/DOCUMENT/2026-04-28_fidelis_index.json", "Bounded real TOC acceptance source"),
]


@dataclass(frozen=True)
class SourceRoot:
    payer_name: str
    payer_type: str
    root_url: str
    notes: str
    source_tier: str
    registry_sha256: str | None


def _parse_markdown_table(text: str, registry_sha: str) -> list[SourceRoot]:
    rows: list[SourceRoot] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "http" not in line:
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 4 or cols[0].lower() == "payer":
            continue
        payer, payer_type, raw_url = cols[:3]
        notes = " | ".join(cols[3:])
        match = re.search(r"https?://[^\s)<>]+", raw_url)
        if not match:
            continue
        url = canonicalize_url(match.group(0).rstrip(".,;"))
        if not url:
            continue
        rows.append(SourceRoot(payer, payer_type, url, notes, "curated_registry", registry_sha))
    return rows


def load_registry(conn: sqlite3.Connection, output_root: Path, timeout: int = 30) -> list[SourceRoot]:
    roots: list[SourceRoot] = []
    registry_sha = None
    try:
        raw, resp = fetch_small(REGISTRY_URL, timeout=timeout, max_bytes=10_000_000)
        registry_sha = sha256_bytes(raw)
        rel = write_blob(output_root, registry_sha, raw)
        conn.execute(
            """INSERT OR IGNORE INTO registry_snapshots
               (source_url, fetched_at, http_status, content_type, byte_count, sha256, blob_relpath)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                REGISTRY_URL,
                utcnow(),
                resp.status_code,
                resp.headers.get("content-type", "").split(";")[0],
                len(raw),
                registry_sha,
                rel,
            ),
        )
        roots.extend(_parse_markdown_table(raw.decode("utf-8", errors="replace"), registry_sha))
    except Exception:
        pass

    for payer, payer_type, url, notes in FALLBACK_SOURCES:
        roots.append(SourceRoot(payer, payer_type, url, notes, "builtin_seed", registry_sha))

    dedup: dict[tuple[str, str], SourceRoot] = {}
    for root in roots:
        dedup[(root.payer_name.lower(), root.root_url)] = root

    final = sorted(dedup.values(), key=lambda x: (x.payer_name.lower(), x.root_url))
    for root in final:
        conn.execute(
            """INSERT OR IGNORE INTO source_roots
               (payer_name, payer_type, root_url, notes, source_tier, registry_sha256, active)
               VALUES (?, ?, ?, ?, ?, ?, 1)""",
            (
                root.payer_name,
                root.payer_type,
                root.root_url,
                root.notes,
                root.source_tier,
                root.registry_sha256,
            ),
        )
    conn.commit()
    return final


def stable_source_bucket(root: SourceRoot, shard_count: int) -> int:
    return int(stable_key(root.payer_name, root.root_url, length=16), 16) % shard_count
