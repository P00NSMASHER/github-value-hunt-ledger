#!/usr/bin/env python3
"""Ingest OpenEI URDB bulk data plus normalized release history.

Evidence layers:
1. exact current OpenEI usurdb.csv.gz bytes + SHA-256;
2. current normalized Parquet generated from those exact bytes;
3. monthly urdb-for-ai release artifacts pinned by Git commit SHA;
4. tariff-level supersedes/superseded_by version graph.

Current operational tables always come from the official bulk observed in this
run. GitHub release history is used as a historical snapshot series, not as a
claim that a monthly snapshot is identical to today's OpenEI bytes.
"""

from __future__ import annotations

import argparse
import ast
import csv
import gzip
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests


OFFICIAL_BULK_URL = "https://apps.openei.org/USURDB/download/usurdb.csv.gz"
HISTORY_REPO = "erock25/urdb-for-ai"
HISTORY_API = f"https://api.github.com/repos/{HISTORY_REPO}"
HISTORY_RAW = f"https://raw.githubusercontent.com/{HISTORY_REPO}"
RELEASE_FILES = (
    "metadata.json",
    "rates.parquet",
    "energy_rates.parquet",
    "demand_rates.parquet",
    "flat_demand_months.parquet",
    "schedules.parquet",
)
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun",
          "jul", "aug", "sep", "oct", "nov", "dec"]
SCHEDULE_COLS = {
    "energyweekdayschedule": "energy_weekday",
    "energyweekendschedule": "energy_weekend",
    "demandweekdayschedule": "demand_weekday",
    "demandweekendschedule": "demand_weekend",
    "coincidentschedule": "coincident",
}
RATE_STRUCTURES = {
    "energyratestructure": ("energy", None, ["max", "rate", "adj", "sell"]),
    "demandratestructure": ("demand", "tou", ["max", "rate", "adj", "unit"]),
    "flatdemandstructure": ("demand", "flat", ["max", "rate", "adj", "unit"]),
    "coincidentratestructure": ("demand", "coincident", ["max", "rate", "adj", "unit"]),
}
NUMERIC_SCALARS = [
    "peakkwcapacitymin", "peakkwcapacitymax", "peakkwhusagemin", "peakkwhusagemax",
    "voltageminimum", "voltagemaximum", "fixedchargefirstmeter", "fixedchargeeaaddl",
    "mincharge", "annualmincharge", "demandreactivepowercharge", "lookbackpercent",
    "lookbackrange", "demandwindow",
]
DATE_SCALARS = ["startdate", "enddate", "latest_update"]


def utcnow() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_blob(root: Path, source: Path, digest: str | None = None) -> str:
    digest = digest or sha256_file(source)
    rel = Path("blobs") / "sha256" / digest[:2] / digest
    dst = root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        tmp = dst.with_name(f"{dst.name}.{os.getpid()}.tmp")
        shutil.copy2(source, tmp)
        os.replace(tmp, dst)
    return str(rel)


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(Path(__file__).with_name("schema.sql").read_text())
    conn.commit()
    return conn


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "RecoveryWorks-URDB-Ledger/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def download(
    url: str,
    dest: Path,
    *,
    timeout: int = 120,
    max_bytes: int = 2_000_000_000,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256()
    total = 0
    with requests.get(
        url,
        stream=True,
        timeout=timeout,
        allow_redirects=True,
        headers=headers or {"User-Agent": "RecoveryWorks-URDB-Ledger/1.0"},
    ) as resp:
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_content(1024 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"download exceeds max_bytes={max_bytes}: {url}")
                h.update(chunk)
                fh.write(chunk)
        return {
            "final_url": resp.url,
            "status": resp.status_code,
            "sha256": h.hexdigest(),
            "byte_count": total,
            "etag": resp.headers.get("etag"),
            "last_modified": resp.headers.get("last-modified"),
            "content_type": resp.headers.get("content-type"),
        }


def record_error(
    conn: sqlite3.Connection,
    stage: str,
    source: str | None,
    exc: Exception,
) -> None:
    conn.execute(
        """INSERT INTO ingestion_errors
           (occurred_at,stage,source,error_type,detail)
           VALUES(?,?,?,?,?)""",
        (utcnow(), stage, source, type(exc).__name__, str(exc)[:4000]),
    )


def persist_snapshot(
    conn: sqlite3.Connection,
    root: Path,
    *,
    source_kind: str,
    source_version: str | None,
    requested_url: str,
    path: Path,
    meta: dict[str, Any],
) -> int:
    rel = write_blob(root, path, meta["sha256"])
    conn.execute(
        """INSERT OR IGNORE INTO source_snapshots(
             source_kind,source_version,requested_url,observed_at,sha256,
             byte_count,blob_relpath,etag,last_modified
           ) VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            source_kind, source_version, requested_url, utcnow(),
            meta["sha256"], meta["byte_count"], rel,
            meta.get("etag"), meta.get("last_modified"),
        ),
    )
    row = conn.execute(
        """SELECT id FROM source_snapshots
           WHERE source_kind=? AND requested_url=? AND sha256=?""",
        (source_kind, requested_url, meta["sha256"]),
    ).fetchone()
    assert row
    return int(row[0])


def inspect_bulk(path: Path) -> tuple[int, int, list[str]]:
    with gzip.open(path, "rt", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = sum(1 for _ in reader)
    return rows, len(header), header


def melt_structure(df: pd.DataFrame, prefix: str, fields: list[str]) -> pd.DataFrame:
    pat = re.compile(rf"^{prefix}/period(\d+)/tier(\d+)({'|'.join(fields)})$")
    keys: set[tuple[int, int]] = set()
    for col in df.columns:
        m = pat.match(col)
        if m:
            keys.add((int(m.group(1)), int(m.group(2))))
    frames: list[pd.DataFrame] = []
    for period, tier in sorted(keys):
        cols = {field: f"{prefix}/period{period}/tier{tier}{field}" for field in fields}
        present = {field: col for field, col in cols.items() if col in df.columns}
        if not present:
            continue
        sub = df[["label", *present.values()]].copy()
        sub.columns = ["label", *present.keys()]
        sub = sub.dropna(subset=list(present.keys()), how="all")
        if sub.empty:
            continue
        sub.insert(1, "period", period)
        sub.insert(2, "tier", tier)
        frames.append(sub)
    if not frames:
        return pd.DataFrame(columns=["label", "period", "tier", *fields])
    out = pd.concat(frames, ignore_index=True)
    for field in fields:
        if field == "unit" or field not in out.columns:
            continue
        out[field] = pd.to_numeric(out[field], errors="coerce")
    return out.sort_values(["label", "period", "tier"], ignore_index=True)


def parse_schedules(df: pd.DataFrame) -> pd.DataFrame:
    rows: list[tuple[Any, ...]] = []
    for csv_col, schedule_name in SCHEDULE_COLS.items():
        if csv_col not in df.columns:
            continue
        for label, raw in df[["label", csv_col]].dropna().itertuples(index=False):
            try:
                grid = ast.literal_eval(raw)
            except (ValueError, SyntaxError, TypeError):
                continue
            if not isinstance(grid, list) or len(grid) != 12:
                continue
            for month, hours in enumerate(grid, start=1):
                if not isinstance(hours, list) or len(hours) != 24:
                    continue
                start = 0
                for hour in range(1, 25):
                    if hour == 24 or hours[hour] != hours[start]:
                        rows.append((
                            label, schedule_name, month, int(hours[start]), start, hour - 1
                        ))
                        start = hour
    return pd.DataFrame(
        rows,
        columns=["label", "schedule", "month", "period", "hour_start", "hour_end"],
    )


def normalize_official_bulk(raw_path: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(raw_path, dtype=str, low_memory=False)

    structure_pat = re.compile(
        r"^(energyratestructure|demandratestructure|flatdemandstructure|"
        r"coincidentratestructure)/"
    )
    flat_month_cols = [f"flatDemandMonth_{m}" for m in MONTHS]
    scalar_cols = [
        c for c in df.columns
        if not structure_pat.match(c)
        and c not in SCHEDULE_COLS
        and c not in flat_month_cols
    ]

    rates = df[scalar_cols].copy()
    for col in DATE_SCALARS:
        if col in rates.columns:
            rates[col] = pd.to_datetime(rates[col], errors="coerce", utc=True)
    for col in NUMERIC_SCALARS:
        if col in rates.columns:
            rates[col] = pd.to_numeric(rates[col], errors="coerce")
    if "is_default" in rates.columns:
        rates["is_default"] = rates["is_default"].astype(str).str.lower().map(
            {"true": True, "false": False}
        )
    if "approved" in rates.columns:
        rates["approved"] = rates["approved"].astype(str).str.lower().map(
            {"true": True, "false": False}
        )
    rates["status"] = (
        rates["enddate"].isna().map({True: "Active", False: "Ended"})
        if "enddate" in rates.columns
        else "Unknown"
    )

    if {"label", "supersedes"}.issubset(df.columns):
        sup = df.loc[df["supersedes"].notna(), ["label", "supersedes"]].copy()
        sup = sup[sup["supersedes"].astype(str).str.strip() != ""]
        reverse = sup.drop_duplicates("supersedes", keep="first").set_index("supersedes")["label"]
        rates["superseded_by"] = rates["label"].map(reverse)
    else:
        rates["superseded_by"] = None

    def has(col: str) -> pd.Series:
        if col not in df.columns:
            return pd.Series(False, index=df.index)
        return df[col].notna() & (df[col].astype(str).str.strip() != "")

    rates["has_energy_rates"] = has("energyratestructure/period0/tier0rate")
    rates["has_demand_rates"] = has("demandratestructure/period0/tier0rate")
    rates["has_flat_demand"] = has("flatdemandstructure/period0/tier0rate")
    rates["has_coincident_demand"] = has("coincidentratestructure/period0/tier0rate")
    rates.to_parquet(out_dir / "rates.parquet", index=False)

    energy = melt_structure(df, "energyratestructure", ["max", "rate", "adj", "sell"])
    if not energy.empty:
        if "energyrateunit" in df.columns:
            units = df.drop_duplicates("label").set_index("label")["energyrateunit"]
            energy["unit"] = energy["label"].map(units).fillna("kWh")
        else:
            energy["unit"] = "kWh"
    energy.to_parquet(out_dir / "energy_rates.parquet", index=False)

    demand_parts: list[pd.DataFrame] = []
    for prefix, (_, tag, fields) in RATE_STRUCTURES.items():
        if tag is None:
            continue
        part = melt_structure(df, prefix, fields)
        if part.empty:
            continue
        part.insert(1, "structure", tag)
        demand_parts.append(part)
    demand = (
        pd.concat(demand_parts, ignore_index=True)
        if demand_parts
        else pd.DataFrame(columns=["label", "structure", "period", "tier", "max", "rate", "adj", "unit"])
    )
    if not demand.empty:
        if "demandrateunit" in df.columns:
            dunit = df.drop_duplicates("label").set_index("label")["demandrateunit"]
            if "unit" not in demand.columns:
                demand["unit"] = None
            demand["unit"] = demand["unit"].fillna(demand["label"].map(dunit)).fillna("kW")
        elif "unit" not in demand.columns:
            demand["unit"] = "kW"
    demand.to_parquet(out_dir / "demand_rates.parquet", index=False)

    present_months = [c for c in flat_month_cols if c in df.columns]
    if present_months:
        fdm = df[["label", *present_months]].copy().melt(
            id_vars="label", var_name="month_name", value_name="period"
        ).dropna()
        fdm["month"] = fdm["month_name"].str.replace("flatDemandMonth_", "", regex=False).map(
            {m: i + 1 for i, m in enumerate(MONTHS)}
        )
        fdm["period"] = pd.to_numeric(fdm["period"], errors="coerce")
        fdm = fdm.dropna(subset=["month", "period"])[["label", "month", "period"]]
    else:
        fdm = pd.DataFrame(columns=["label", "month", "period"])
    fdm.to_parquet(out_dir / "flat_demand_months.parquet", index=False)

    schedules = parse_schedules(df)
    schedules.to_parquet(out_dir / "schedules.parquet", index=False)

    return {
        "tariff_count": int(len(rates)),
        "utility_count": int(rates["utility"].nunique()) if "utility" in rates.columns else 0,
        "active_count": int((rates["status"] == "Active").sum()),
        "column_count": int(len(df.columns)),
        "tables": {
            "rates": int(len(rates)),
            "energy_rates": int(len(energy)),
            "demand_rates": int(len(demand)),
            "flat_demand_months": int(len(fdm)),
            "schedules": int(len(schedules)),
        },
    }


def scalar(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()
        except Exception:
            pass
    if isinstance(value, bool):
        return value
    return str(value)


def truthy_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return int(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return 1
    if text in {"false", "0", "no"}:
        return 0
    return None


def row_fingerprint(row: pd.Series, columns: Iterable[str]) -> str:
    payload = {
        col: scalar(row[col])
        for col in columns
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def get_col(row: pd.Series, name: str) -> Any:
    return row[name] if name in row.index else None


def insert_release(
    conn: sqlite3.Connection,
    *,
    release_key: str,
    commit_sha: str | None,
    commit_date: str | None,
    message: str | None,
    metadata: dict[str, Any],
    metadata_sha: str | None,
) -> int:
    conn.execute(
        """INSERT OR IGNORE INTO releases(
             release_key,commit_sha,commit_date,message,built_utc,source_url,
             tariff_count,utility_count,active_count,metadata_sha256
           ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
        (
            release_key, commit_sha, commit_date, message,
            metadata.get("built_utc"), metadata.get("source"),
            metadata.get("tariff_count"), metadata.get("utility_count"),
            metadata.get("active_count"), metadata_sha,
        ),
    )
    row = conn.execute("SELECT id FROM releases WHERE release_key=?", (release_key,)).fetchone()
    assert row
    return int(row[0])


def insert_release_file(
    conn: sqlite3.Connection,
    *,
    release_id: int,
    logical_name: str,
    source_url: str,
    path: Path,
    root: Path,
) -> tuple[str, str]:
    digest = sha256_file(path)
    rel = write_blob(root, path, digest)
    conn.execute(
        """INSERT OR IGNORE INTO release_files(
             release_id,logical_name,source_url,sha256,byte_count,blob_relpath
           ) VALUES(?,?,?,?,?,?)""",
        (release_id, logical_name, source_url, digest, path.stat().st_size, rel),
    )
    return digest, rel


def selected_observation(row: pd.Series) -> dict[str, Any]:
    fields = (
        "label", "utility", "eiaid", "name", "sector", "servicetype",
        "startdate", "enddate", "supersedes", "superseded_by", "status",
        "source", "uri", "fixedchargefirstmeter", "mincharge",
    )
    return {field: scalar(get_col(row, field)) for field in fields}


def ingest_release_observations(
    conn: sqlite3.Connection,
    release_id: int,
    rates_path: Path,
) -> int:
    df = pd.read_parquet(rates_path)
    columns = list(df.columns)
    rows = []
    for _, row in df.iterrows():
        label = scalar(get_col(row, "label"))
        if not label:
            continue
        obs = selected_observation(row)
        rows.append((
            release_id,
            label,
            obs["utility"], obs["eiaid"], obs["name"], obs["sector"],
            obs["servicetype"], obs["startdate"], obs["enddate"],
            obs["supersedes"], obs["superseded_by"], obs["status"],
            obs["source"], obs["uri"], obs["fixedchargefirstmeter"],
            obs["mincharge"], truthy_int(get_col(row, "approved")),
            truthy_int(get_col(row, "is_default")),
            row_fingerprint(row, columns),
        ))
    conn.executemany(
        """INSERT OR REPLACE INTO tariff_release_observations(
             release_id,label,utility,eiaid,name,sector,servicetype,startdate,enddate,
             supersedes,superseded_by,status,source,uri,fixedchargefirstmeter,mincharge,
             approved,is_default,row_fingerprint
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    return len(rows)


def discover_history_commits(limit: int = 100) -> list[dict[str, Any]]:
    resp = requests.get(
        f"{HISTORY_API}/commits",
        params={"path": "data/metadata.json", "per_page": min(limit, 100)},
        headers=github_headers(),
        timeout=60,
    )
    resp.raise_for_status()
    result = []
    for item in resp.json():
        result.append({
            "sha": item["sha"],
            "date": item["commit"]["committer"]["date"],
            "message": item["commit"]["message"],
        })
    return result[:limit]


def ingest_history_releases(
    conn: sqlite3.Connection,
    root: Path,
    *,
    limit: int,
) -> dict[str, Any]:
    commits = discover_history_commits(limit)
    stats = {"release_count": 0, "observation_rows": 0, "files": 0}
    releases_dir = root / "release-cache"
    releases_dir.mkdir(parents=True, exist_ok=True)

    for commit in reversed(commits):
        sha = commit["sha"]
        tmpdir = releases_dir / sha
        tmpdir.mkdir(parents=True, exist_ok=True)
        downloaded: dict[str, tuple[Path, dict[str, Any], str]] = {}
        for logical_name in RELEASE_FILES:
            url = f"{HISTORY_RAW}/{sha}/data/{logical_name}"
            path = tmpdir / logical_name
            meta = download(url, path, timeout=120, max_bytes=200_000_000)
            downloaded[logical_name] = (path, meta, url)

        metadata_path, metadata_meta, metadata_url = downloaded["metadata.json"]
        metadata = json.loads(metadata_path.read_text())
        release_id = insert_release(
            conn,
            release_key=f"github:{sha}",
            commit_sha=sha,
            commit_date=commit["date"],
            message=commit["message"],
            metadata=metadata,
            metadata_sha=metadata_meta["sha256"],
        )

        for logical_name, (path, _, url) in downloaded.items():
            insert_release_file(
                conn,
                release_id=release_id,
                logical_name=logical_name,
                source_url=url,
                path=path,
                root=root,
            )
            stats["files"] += 1

        stats["observation_rows"] += ingest_release_observations(
            conn, release_id, downloaded["rates.parquet"][0]
        )
        stats["release_count"] += 1
        conn.commit()

    return stats


def chain_info(df: pd.DataFrame) -> dict[str, tuple[str, int, int]]:
    labels = {
        str(v).strip()
        for v in df.get("label", pd.Series(dtype=str)).dropna().tolist()
        if str(v).strip()
    }
    supersedes: dict[str, str | None] = {}
    for _, row in df.iterrows():
        label = scalar(get_col(row, "label"))
        if not label:
            continue
        prev = scalar(get_col(row, "supersedes"))
        supersedes[label] = prev if prev in labels else None

    out: dict[str, tuple[str, int, int]] = {}
    for label in labels:
        seen: list[str] = []
        cur = label
        cycle = 0
        while cur and cur not in seen and len(seen) < 100:
            seen.append(cur)
            cur = supersedes.get(cur)
        if cur in seen:
            cycle = 1
            root = min(seen[seen.index(cur):])
        else:
            root = seen[-1] if seen else label
        depth = max(0, len(seen) - 1)
        out[label] = (root, depth, cycle)
    return out


def load_current_tariffs(
    conn: sqlite3.Connection,
    rates_path: Path,
    *,
    release_id: int,
    source_file_sha: str,
) -> dict[str, Any]:
    df = pd.read_parquet(rates_path)
    if "superseded_by" not in df.columns and {"label", "supersedes"}.issubset(df.columns):
        sup = df.loc[df["supersedes"].notna(), ["label", "supersedes"]]
        reverse = sup.drop_duplicates("supersedes", keep="first").set_index("supersedes")["label"]
        df["superseded_by"] = df["label"].map(reverse)

    chains = chain_info(df)
    conn.execute("DELETE FROM current_tariffs")
    conn.execute("DELETE FROM tariff_history_edges")

    tariff_rows = []
    edge_rows = []
    columns = list(df.columns)
    for _, row in df.iterrows():
        label = scalar(get_col(row, "label"))
        if not label:
            continue
        fp = row_fingerprint(row, columns)
        tariff_rows.append((
            label,
            scalar(get_col(row, "utility")),
            scalar(get_col(row, "eiaid")),
            scalar(get_col(row, "name")),
            scalar(get_col(row, "description")),
            scalar(get_col(row, "sector")),
            scalar(get_col(row, "servicetype")),
            scalar(get_col(row, "startdate")),
            scalar(get_col(row, "enddate")),
            scalar(get_col(row, "supersedes")),
            scalar(get_col(row, "superseded_by")),
            scalar(get_col(row, "status")),
            scalar(get_col(row, "source")),
            scalar(get_col(row, "uri")),
            scalar(get_col(row, "fixedchargefirstmeter")),
            scalar(get_col(row, "fixedchargeeaaddl")),
            scalar(get_col(row, "mincharge")),
            scalar(get_col(row, "annualmincharge")),
            truthy_int(get_col(row, "approved")),
            truthy_int(get_col(row, "is_default")),
            truthy_int(get_col(row, "has_energy_rates")),
            truthy_int(get_col(row, "has_demand_rates")),
            truthy_int(get_col(row, "has_flat_demand")),
            truthy_int(get_col(row, "has_coincident_demand")),
            release_id,
            source_file_sha,
            fp,
        ))
        root, depth, cycle = chains.get(label, (label, 0, 0))
        edge_rows.append((
            label,
            scalar(get_col(row, "supersedes")),
            scalar(get_col(row, "superseded_by")),
            root, depth, cycle,
        ))

    conn.executemany(
        """INSERT INTO current_tariffs(
             label,utility,eiaid,name,description,sector,servicetype,startdate,enddate,
             supersedes,superseded_by,status,source,uri,fixedchargefirstmeter,
             fixedchargeeaaddl,mincharge,annualmincharge,approved,is_default,
             has_energy_rates,has_demand_rates,has_flat_demand,has_coincident_demand,
             release_id,source_file_sha256,row_fingerprint
           ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        tariff_rows,
    )
    conn.executemany(
        """INSERT INTO tariff_history_edges(
             label,supersedes,superseded_by,chain_root,chain_depth,cycle_detected
           ) VALUES(?,?,?,?,?,?)""",
        edge_rows,
    )
    conn.commit()
    return {
        "tariffs": len(tariff_rows),
        "chains": len({v[0] for v in chains.values()}),
        "cycles": sum(v[2] for v in chains.values()),
        "linked_to_predecessor": sum(
            1 for _, row in df.iterrows()
            if scalar(get_col(row, "supersedes"))
        ),
    }


def persist_current_normalized_files(
    conn: sqlite3.Connection,
    root: Path,
    current_dir: Path,
    release_id: int,
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(current_dir.glob("*")):
        if not path.is_file():
            continue
        digest, _ = insert_release_file(
            conn,
            release_id=release_id,
            logical_name=f"normalized_current/{path.name}",
            source_url=f"derived://official-bulk/{path.name}",
            path=path,
            root=root,
        )
        hashes[path.name] = digest
    return hashes


def run_ingest(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.out).resolve()
    root.mkdir(parents=True, exist_ok=True)
    db = Path(args.db)
    if not db.is_absolute():
        db = root / db
    conn = init_db(db)

    run_id = conn.execute(
        "INSERT INTO ingestion_runs(started_at,status) VALUES(?,?)",
        (utcnow(), "running"),
    ).lastrowid
    conn.commit()

    stats: dict[str, Any] = {"started_at": utcnow(), "errors": []}

    try:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            raw_bulk = tmp / "usurdb.csv.gz"
            bulk_meta = download(
                OFFICIAL_BULK_URL,
                raw_bulk,
                timeout=args.timeout,
                max_bytes=args.max_bulk_bytes,
            )
            persist_snapshot(
                conn,
                root,
                source_kind="openei_official_bulk",
                source_version=None,
                requested_url=OFFICIAL_BULK_URL,
                path=raw_bulk,
                meta=bulk_meta,
            )
            bulk_rows, bulk_columns, _ = inspect_bulk(raw_bulk)
            stats["official_bulk"] = {
                **{k: v for k, v in bulk_meta.items() if k != "content_type"},
                "tariff_rows": bulk_rows,
                "columns": bulk_columns,
            }

            current_dir = root / "current"
            current_stats = normalize_official_bulk(raw_bulk, current_dir)
            current_meta = {
                "built_utc": utcnow(),
                "source": OFFICIAL_BULK_URL,
                "tariff_count": current_stats["tariff_count"],
                "utility_count": current_stats["utility_count"],
                "active_count": current_stats["active_count"],
                "official_bulk_sha256": bulk_meta["sha256"],
                "tables": current_stats["tables"],
            }
            (current_dir / "metadata.json").write_text(
                json.dumps(current_meta, indent=2) + "\n",
                encoding="utf-8",
            )
            official_release_id = insert_release(
                conn,
                release_key=f"openei:{bulk_meta['sha256']}",
                commit_sha=None,
                commit_date=None,
                message="Official OpenEI URDB bulk observation",
                metadata=current_meta,
                metadata_sha=sha256_file(current_dir / "metadata.json"),
            )
            current_hashes = persist_current_normalized_files(
                conn, root, current_dir, official_release_id
            )
            current_graph = load_current_tariffs(
                conn,
                current_dir / "rates.parquet",
                release_id=official_release_id,
                source_file_sha=current_hashes["rates.parquet"],
            )
            stats["current_normalized"] = {**current_stats, **current_graph}

        try:
            stats["github_release_history"] = ingest_history_releases(
                conn, root, limit=args.history_limit
            )
        except Exception as exc:
            record_error(conn, "github_release_history", HISTORY_REPO, exc)
            stats["errors"].append({
                "stage": "github_release_history",
                "error_type": type(exc).__name__,
                "detail": str(exc),
            })
            conn.commit()

        latest_github = conn.execute(
            """SELECT id,commit_sha,commit_date,tariff_count,utility_count,active_count
               FROM releases
               WHERE commit_sha IS NOT NULL
               ORDER BY datetime(commit_date) DESC LIMIT 1"""
        ).fetchone()
        official = conn.execute(
            """SELECT id,tariff_count,utility_count,active_count
               FROM releases WHERE id=?""",
            (official_release_id,),
        ).fetchone()
        if latest_github:
            stats["latest_release_comparison"] = {
                "github_commit_sha": latest_github[1],
                "github_commit_date": latest_github[2],
                "github_tariffs": latest_github[3],
                "official_tariffs": official[1],
                "tariff_delta": int(official[1] or 0) - int(latest_github[3] or 0),
                "github_utilities": latest_github[4],
                "official_utilities": official[2],
                "github_active": latest_github[5],
                "official_active": official[3],
            }

        stats["release_count"] = conn.execute("SELECT COUNT(*) FROM releases").fetchone()[0]
        stats["source_snapshot_count"] = conn.execute(
            "SELECT COUNT(*) FROM source_snapshots"
        ).fetchone()[0]
        stats["release_file_count"] = conn.execute(
            "SELECT COUNT(*) FROM release_files"
        ).fetchone()[0]
        stats["tariff_release_observations"] = conn.execute(
            "SELECT COUNT(*) FROM tariff_release_observations"
        ).fetchone()[0]
        stats["current_tariffs"] = conn.execute(
            "SELECT COUNT(*) FROM current_tariffs"
        ).fetchone()[0]
        stats["history_chains"] = conn.execute(
            "SELECT COUNT(DISTINCT chain_root) FROM tariff_history_edges"
        ).fetchone()[0]
        stats["ended_tariffs"] = conn.execute(
            "SELECT COUNT(*) FROM current_tariffs WHERE status='Ended'"
        ).fetchone()[0]
        stats["active_tariffs"] = conn.execute(
            "SELECT COUNT(*) FROM current_tariffs WHERE status='Active'"
        ).fetchone()[0]
        stats["error_rows"] = conn.execute(
            "SELECT COUNT(*) FROM ingestion_errors"
        ).fetchone()[0]
        stats["finished_at"] = utcnow()

        conn.execute(
            """UPDATE ingestion_runs
               SET finished_at=?,status='complete',stats_json=?
               WHERE id=?""",
            (stats["finished_at"], json.dumps(stats, sort_keys=True), run_id),
        )
        conn.commit()
        (root / "summary.json").write_text(
            json.dumps(stats, indent=2) + "\n",
            encoding="utf-8",
        )
        return stats
    except Exception as exc:
        record_error(conn, "ingest", None, exc)
        conn.execute(
            """UPDATE ingestion_runs
               SET finished_at=?,status='failed',stats_json=?
               WHERE id=?""",
            (
                utcnow(),
                json.dumps({"error_type": type(exc).__name__, "detail": str(exc)}),
                run_id,
            ),
        )
        conn.commit()
        raise
    finally:
        conn.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=".urdb_ledger")
    p.add_argument("--db", default="urdb.sqlite")
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--max-bulk-bytes", type=int, default=2_000_000_000)
    p.add_argument("--history-limit", type=int, default=100)
    args = p.parse_args()
    stats = run_ingest(args)
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
