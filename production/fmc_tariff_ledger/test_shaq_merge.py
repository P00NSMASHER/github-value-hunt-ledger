import sqlite3
import tempfile
import unittest
from pathlib import Path

import shaq_merge
import shaq_route_crawl


class ShaqMergeTests(unittest.TestCase):
    def make_shard(self, root: Path, name: str, url: str, dest: str, amount: str):
        path = root / name / "shaq_routes.sqlite"
        conn = shaq_route_crawl.init_db(path)
        cur = conn.execute(
            """INSERT INTO shaq_runs(started_at,finished_at,endpoint,parser_version,status)
               VALUES ('a','b','sitemap','test','complete')"""
        )
        run_id = cur.lastrowid
        cur = conn.execute(
            """INSERT INTO shaq_route_pages(
                 run_id,url,fetched_at,http_status,content_type,byte_count,
                 sha256,blob_relpath,parser_status
               ) VALUES (?,?,'now',200,'text/html',1,?,'blobs/x','parsed')""",
            (run_id, url, name * 16),
        )
        page_id = cur.lastrowid
        conn.execute(
            """INSERT INTO shaq_rates(
                 route_page_id,origin_raw,destination_raw,carrier_raw,
                 carrier_normalized,fmc_identity_status,container_type,
                 amount_value,currency,valid_to,rate_basis,source_url,
                 rate_kind,source_label,evidence_excerpt,parser_confidence,
                 parser_version,created_at
               ) VALUES (?, 'Shanghai', ?, 'COSCO', 'COSCO', 'UNRESOLVED',
                         '40HQ', ?, 'USD', '2026-08-14', 'per container', ?,
                         'PUBLISHER_CARRIER_RATE','SHAQ_PUBLIC_ROUTE_PAGE',
                         'row',0.99,'test','now')""",
            (page_id, dest, amount, url),
        )
        conn.commit()
        conn.close()
        return path

    def test_merge_preserves_disjoint_pages_and_benchmark_status(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_shard(root, "a", "https://shaq-log.com/q/a", "Chancay", "5060")
            self.make_shard(root, "b", "https://shaq-log.com/q/b", "Hamburg", "3400")
            out = root / "merged.sqlite"
            dst = shaq_route_crawl.init_db(out)
            for source in sorted(root.rglob("shaq_routes.sqlite")):
                shaq_merge.merge_one(dst, source)
            self.assertEqual(
                dst.execute("SELECT COUNT(*) FROM shaq_route_pages").fetchone()[0], 2
            )
            self.assertEqual(
                dst.execute("SELECT COUNT(*) FROM shaq_rates").fetchone()[0], 2
            )
            self.assertEqual(
                dst.execute(
                    """SELECT COUNT(*) FROM shaq_rate_authority_view
                       WHERE authority_readiness='BENCHMARK_ONLY'"""
                ).fetchone()[0],
                2,
            )
            dst.close()


if __name__ == "__main__":
    unittest.main()
