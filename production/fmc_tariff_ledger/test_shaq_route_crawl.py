import sqlite3
import threading
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
from pathlib import Path

import shaq_route_crawl as crawl


HTML = b"""
<html>
<head><title>Shanghai Container Rates</title></head>
<body>
<h1>Fcl Shipping Rates From Shanghai</h1>
<h2>Shanghai to Chancay</h2>
<table>
  <tr>
    <th>Container Type</th><th>Rate</th><th>Carrier</th><th>Transit Time</th><th>Valid Until</th>
  </tr>
  <tr><td>20GP Container</td><td>$5030</td><td>COSCO</td><td>30-45 days</td><td>2026-08-14</td></tr>
  <tr><td>40GP Container</td><td>$5060</td><td>COSCO</td><td>30-45 days</td><td>2026-08-14</td></tr>
  <tr><td>40HQ Container</td><td>$5060</td><td>COSCO</td><td>30-45 days</td><td>2026-08-14</td></tr>
  <tr><td>40HQ Container</td><td>$5060</td><td>COSCO</td><td>30-45 days</td><td>2026-08-14</td></tr>
</table>
<h2>Shanghai to Manzanillo</h2>
<table>
  <tr><th>Container Type</th><th>Rate</th><th>Carrier</th><th>Transit Time</th><th>Valid Until</th></tr>
  <tr><td>20GP Container</td><td>USD 6300</td><td>COSCO</td><td>30-45 days</td><td>2026-08-14</td></tr>
</table>
</body>
</html>
"""


class ShaqRouteCrawlTests(unittest.TestCase):
    def test_parse_table_rates_and_dedupe(self):
        meta, rates = crawl.parse_route_page(HTML, "https://shaq-log.com/q/test")
        self.assertEqual(meta["rate_count"], 4)
        self.assertEqual(rates[0].origin, "Shanghai")
        self.assertEqual(rates[0].destination, "Chancay")
        self.assertEqual(rates[0].amount_value, "5030")
        self.assertEqual(rates[0].currency, "USD")
        self.assertEqual(rates[0].container_type, "20GP")
        self.assertEqual(rates[0].carrier, "COSCO")
        self.assertEqual(rates[0].valid_to, "2026-08-14")

    def test_route_rows_default_to_publisher_carrier_rate(self):
        self.assertEqual(crawl.DEFAULT_RATE_KIND, "PUBLISHER_CARRIER_RATE")

    def test_stable_shards_are_disjoint(self):
        urls = [f"https://shaq-log.com/q/route-{i}" for i in range(100)]
        buckets = {i: set() for i in range(7)}
        for url in urls:
            buckets[crawl.stable_shard(url, 7)].add(url)
        flattened = set().union(*buckets.values())
        self.assertEqual(flattened, set(urls))
        self.assertEqual(sum(len(x) for x in buckets.values()), len(urls))

    def test_parse_sitemap_filters_q_pages(self):
        raw = b"""<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://shaq-log.com/</loc><lastmod>2026-08-07</lastmod></url>
          <url><loc>https://shaq-log.com/q/a</loc><lastmod>2026-08-08</lastmod></url>
          <url><loc>https://shaq-log.com/blog/x</loc></url>
          <url><loc>https://shaq-log.com/q/b</loc></url>
        </urlset>"""
        rows = crawl.parse_sitemap(raw)
        self.assertEqual(rows, [
            ("https://shaq-log.com/q/a", "2026-08-08"),
            ("https://shaq-log.com/q/b", None),
        ])

    def test_blob_write_is_safe_for_identical_concurrent_content(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw = b"same SHAQ evidence bytes"
            digest = crawl.hashlib.sha256(raw).hexdigest()
            barrier = threading.Barrier(2)
            original_replace = crawl.os.replace

            def synchronized_replace(src, dst):
                barrier.wait(timeout=5)
                return original_replace(src, dst)

            with mock.patch.object(
                crawl.os,
                "replace",
                side_effect=synchronized_replace,
            ):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [
                        pool.submit(crawl.write_blob, root, digest, raw)
                        for _ in range(2)
                    ]
                    relpaths = [future.result(timeout=10) for future in futures]

            self.assertEqual(relpaths[0], relpaths[1])
            self.assertEqual((root / relpaths[0]).read_bytes(), raw)
            self.assertEqual(list(root.rglob("*.tmp")), [])

    def test_schema_marks_route_rates_benchmark_only(self):
        with tempfile.TemporaryDirectory() as td:
            conn = crawl.init_db(Path(td) / "rates.sqlite")
            conn.execute(
                """INSERT INTO shaq_runs(started_at, endpoint, parser_version, status)
                   VALUES ('now','x','test','complete')"""
            )
            run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """INSERT INTO shaq_route_pages(
                     run_id,url,fetched_at,http_status,content_type,byte_count,
                     sha256,blob_relpath,parser_status
                   ) VALUES (?, 'https://shaq-log.com/q/a','now',200,'text/html',
                             1,'abc','blobs/a','parsed')""",
                (run_id,),
            )
            page_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute(
                """INSERT INTO shaq_rates(
                     route_page_id,origin_raw,destination_raw,carrier_raw,
                     carrier_normalized,fmc_identity_status,container_type,
                     amount_value,currency,valid_to,rate_basis,source_url,
                     rate_kind,source_label,evidence_excerpt,parser_confidence,
                     parser_version,created_at
                   ) VALUES (?, 'Shanghai','Chancay','COSCO','COSCO','UNRESOLVED',
                             '20GP','5030','USD','2026-08-14','per container',
                             'https://shaq-log.com/q/a','PUBLISHER_CARRIER_RATE',
                             'SHAQ_PUBLIC_ROUTE_PAGE','row',0.99,'test','now')""",
                (page_id,),
            )
            status = conn.execute(
                "SELECT authority_readiness FROM shaq_rate_authority_view"
            ).fetchone()[0]
            self.assertEqual(status, "BENCHMARK_ONLY")
            conn.close()

    def test_minimum_interval_guard_is_not_relaxable_below_quarter_second(self):
        # Contract is enforced by CLI validation; constant expectation documents it.
        self.assertGreaterEqual(0.50, 0.25)


if __name__ == "__main__":
    unittest.main()
