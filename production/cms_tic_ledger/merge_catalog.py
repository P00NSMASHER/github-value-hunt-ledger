#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from common import init_db


def merge_one(dst: sqlite3.Connection, src_path: Path) -> dict:
    src = sqlite3.connect(src_path)
    src.row_factory = sqlite3.Row
    source_map: dict[int, int] = {}
    entity_map: dict[int, int] = {}

    for row in src.execute("SELECT * FROM registry_snapshots"):
        dst.execute(
            """INSERT OR IGNORE INTO registry_snapshots
               (source_url,fetched_at,http_status,content_type,byte_count,sha256,blob_relpath)
               VALUES (?,?,?,?,?,?,?)""",
            tuple(row[k] for k in (
                "source_url","fetched_at","http_status","content_type","byte_count","sha256","blob_relpath"
            )),
        )

    for row in src.execute("SELECT * FROM source_roots"):
        dst.execute(
            """INSERT OR IGNORE INTO source_roots
               (payer_name,payer_type,root_url,notes,source_tier,registry_sha256,active)
               VALUES (?,?,?,?,?,?,?)""",
            tuple(row[k] for k in (
                "payer_name","payer_type","root_url","notes","source_tier","registry_sha256","active"
            )),
        )
        new = dst.execute(
            "SELECT id FROM source_roots WHERE payer_name=? AND root_url=?",
            (row["payer_name"], row["root_url"]),
        ).fetchone()
        source_map[int(row["id"])] = int(new[0])

    for row in src.execute("SELECT * FROM reporting_entities"):
        new_source = source_map.get(int(row["source_root_id"])) if row["source_root_id"] is not None else None
        dst.execute(
            """INSERT OR IGNORE INTO reporting_entities
               (source_root_id,index_url,index_sha256,reporting_entity_name,
                reporting_entity_type,last_updated_on,schema_version)
               VALUES (?,?,?,?,?,?,?)""",
            (
                new_source,row["index_url"],row["index_sha256"],row["reporting_entity_name"],
                row["reporting_entity_type"],row["last_updated_on"],row["schema_version"],
            ),
        )
        new = dst.execute(
            "SELECT id FROM reporting_entities WHERE index_url=? AND index_sha256=?",
            (row["index_url"], row["index_sha256"]),
        ).fetchone()
        entity_map[int(row["id"])] = int(new[0])

    for row in src.execute("SELECT * FROM plans"):
        dst.execute(
            """INSERT OR IGNORE INTO plans
               (plan_key,reporting_entity_id,plan_name,issuer_name,plan_id_type,
                plan_id,plan_sponsor_name,plan_market_type)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                row["plan_key"], entity_map.get(int(row["reporting_entity_id"])),
                row["plan_name"], row["issuer_name"], row["plan_id_type"], row["plan_id"],
                row["plan_sponsor_name"], row["plan_market_type"],
            ),
        )

    for row in src.execute("SELECT * FROM files"):
        new_source = source_map.get(int(row["source_root_id"])) if row["source_root_id"] is not None else None
        dst.execute(
            """INSERT OR IGNORE INTO files
               (file_key,source_root_id,url,kind,description,first_seen_at,last_seen_at,
                last_updated_on,schema_version,content_length,etag,last_modified,
                source_index_url,source_index_sha256,status)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["file_key"],new_source,row["url"],row["kind"],row["description"],
                row["first_seen_at"],row["last_seen_at"],row["last_updated_on"],row["schema_version"],
                row["content_length"],row["etag"],row["last_modified"],row["source_index_url"],
                row["source_index_sha256"],row["status"],
            ),
        )
        dst.execute(
            """UPDATE files SET
                 last_seen_at=MAX(last_seen_at,?),
                 content_length=COALESCE(content_length,?),
                 etag=COALESCE(etag,?),
                 last_modified=COALESCE(last_modified,?),
                 last_updated_on=COALESCE(last_updated_on,?),
                 schema_version=COALESCE(schema_version,?)
               WHERE file_key=?""",
            (
                row["last_seen_at"],row["content_length"],row["etag"],row["last_modified"],
                row["last_updated_on"],row["schema_version"],row["file_key"],
            ),
        )

    for row in src.execute("SELECT * FROM file_plans"):
        dst.execute(
            "INSERT OR IGNORE INTO file_plans(file_key,plan_key) VALUES (?,?)",
            (row["file_key"], row["plan_key"]),
        )

    for row in src.execute("SELECT * FROM observations"):
        old_source = row["source_root_id"]
        dst.execute(
            """INSERT INTO observations
               (source_root_id,url,parent_url,observed_at,kind,discovery_method,http_status,
                content_type,content_length,etag,last_modified,sha256,blob_relpath,status,note)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                source_map.get(int(old_source)) if old_source is not None else None,
                row["url"],row["parent_url"],row["observed_at"],row["kind"],row["discovery_method"],
                row["http_status"],row["content_type"],row["content_length"],row["etag"],
                row["last_modified"],row["sha256"],row["blob_relpath"],row["status"],row["note"],
            ),
        )

    for row in src.execute("SELECT * FROM errors"):
        old_source = row["source_root_id"]
        dst.execute(
            """INSERT INTO errors(source_root_id,url,occurred_at,stage,error_type,detail)
               VALUES (?,?,?,?,?,?)""",
            (
                source_map.get(int(old_source)) if old_source is not None else None,
                row["url"],row["occurred_at"],row["stage"],row["error_type"],row["detail"],
            ),
        )

    stats = {
        "source_roots": src.execute("SELECT COUNT(*) FROM source_roots").fetchone()[0],
        "files": src.execute("SELECT COUNT(*) FROM files").fetchone()[0],
        "plans": src.execute("SELECT COUNT(*) FROM plans").fetchone()[0],
    }
    src.close()
    dst.commit()
    return stats


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--input-root", required=True)
    p.add_argument("--db", required=True)
    args=p.parse_args()
    dst=init_db(Path(args.db))
    sources=sorted(Path(args.input_root).rglob("catalog.sqlite"))
    if not sources:
        raise SystemExit("no catalog.sqlite shards found")
    shards=[]
    for path in sources:
        shards.append({"path":str(path),"stats":merge_one(dst,path)})
    summary={
        "shards":len(sources),
        "source_roots":dst.execute("SELECT COUNT(*) FROM source_roots").fetchone()[0],
        "reporting_entities":dst.execute("SELECT COUNT(*) FROM reporting_entities").fetchone()[0],
        "plans":dst.execute("SELECT COUNT(*) FROM plans").fetchone()[0],
        "files":dst.execute("SELECT COUNT(*) FROM files").fetchone()[0],
        "in_network_files":dst.execute("SELECT COUNT(*) FROM files WHERE kind='in_network'").fetchone()[0],
        "allowed_amount_files":dst.execute("SELECT COUNT(*) FROM files WHERE kind='allowed_amounts'").fetchone()[0],
        "observations":dst.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
        "errors":dst.execute("SELECT COUNT(*) FROM errors").fetchone()[0],
        "inputs":shards,
    }
    print(json.dumps(summary,indent=2))
    dst.close()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
