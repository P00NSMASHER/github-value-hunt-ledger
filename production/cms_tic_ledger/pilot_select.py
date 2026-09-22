#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--db", required=True)
    args=p.parse_args()
    conn=sqlite3.connect(args.db)
    queries=[
        """SELECT f.file_key,f.url,sr.payer_name,f.content_length
           FROM files f JOIN source_roots sr ON sr.id=f.source_root_id
           WHERE f.kind='in_network'
             AND lower(f.url) LIKE '%fidelis-ex%'
           ORDER BY f.url LIMIT 1""",
        """SELECT f.file_key,f.url,sr.payer_name,f.content_length
           FROM files f JOIN source_roots sr ON sr.id=f.source_root_id
           WHERE f.kind='in_network'
             AND (lower(sr.payer_name) LIKE '%centene%' OR lower(f.source_index_url) LIKE '%fidelis%')
           ORDER BY COALESCE(f.content_length,999999999999),f.url LIMIT 1""",
        """SELECT f.file_key,f.url,sr.payer_name,f.content_length
           FROM files f JOIN source_roots sr ON sr.id=f.source_root_id
           WHERE f.kind='in_network' AND f.content_length IS NOT NULL
           ORDER BY f.content_length,f.url LIMIT 1""",
    ]
    row=None
    for q in queries:
        row=conn.execute(q).fetchone()
        if row:
            break
    conn.close()
    if not row:
        print(json.dumps({"status":"NO_PILOT_FILE"}))
        return 2
    result={
        "status":"SELECTED",
        "file_key":row[0],
        "url":row[1],
        "payer_name":row[2],
        "content_length":row[3],
    }
    print(json.dumps(result))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
