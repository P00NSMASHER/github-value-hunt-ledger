"""RETALLY live public URL probe concurrency and recovery safeguards."""
import unittest
from public_asset_preflight import run, inspect

LAND = ("https://www.retallyrecovery.com/freight-audit-methodology"
        "?utm_source=facebook&utm_medium=organic_social"
        "&utm_campaign=retally_oct2026_launch&utm_content=probe")
IMG = "https://static.metricool.com/planner/202610/7322512-file-check.png"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 8 + (1080).to_bytes(4, "big") + (1350).to_bytes(4, "big")


def schedule(n=4):
    return {"data":[{
        "uuid":f"qa-{i}",
        "providers":[{"network":"facebook","status":"PENDING"}],
        "draft":False, "autoPublish":True,
        "publicationDate":{"dateTime":f"2026-11-{i+10:02d}T09:00:00",
                           "timezone":"America/New_York"},
        "media":[IMG], "mediaAltText":["RETALLY graphic about freight invoice evidence."],
        "text":LAND.replace("probe",f"probe{i}"),
    } for i in range(n)]}


class ParallelRetryTests(unittest.TestCase):
    def test_transient_500_then_200_recovers_with_auditable_history(self):
        seen=[]
        def first_500_then_200(url,kind):
            seen.append(500 if not seen else 200)
            return seen[-1], {"Content-Type":"text/html"}, b"<html>RETALLY</html>"
        report=run(schedule(1), live=True, only_kind="landing",
                   workers=2, transient_retries=1, fetcher=first_500_then_200)
        self.assertEqual(report["counts"]["PASS"],1)
        self.assertEqual(report["targets"][0]["http_history"],[500,200])
        self.assertEqual(report["targets"][0]["http_attempts"],2)
        self.assertFalse(report["publication_verified"])

    def test_persistent_500_stays_uncertain(self):
        report=run(schedule(1), live=True, only_kind="landing",
                   transient_retries=2, fetcher=lambda *a: (
                       500, {"Content-Type":"text/html"}, b"<html>RETALLY</html>"))
        self.assertEqual(report["counts"]["RECHECK"],1)
        self.assertEqual(report["targets"][0]["http_history"],[500,500,500])
        self.assertFalse(report["publication_verified"])

    def test_404_is_never_retried(self):
        seen=[]
        def missing(*a):
            seen.append(True)
            return 404, {"Content-Type":"text/html"}, b"<html>Not found</html>"
        report=run(schedule(1), live=True, only_kind="landing",
                   transient_retries=2, fetcher=missing)
        self.assertEqual(report["counts"]["FAIL"],1)
        self.assertEqual(len(seen),1)

    def test_timeout_then_200_remains_traceable(self):
        seen=[]
        def transient(url,kind):
            seen.append(True)
            if len(seen)==1:
                raise TimeoutError()
            return 200, {"Content-Type":"text/html"}, b"<html>RETALLY</html>"
        report=run(schedule(1), live=True, only_kind="landing",
                   transient_retries=1, fetcher=transient)
        self.assertEqual(report["counts"]["PASS"],1)
        self.assertEqual(report["targets"][0]["http_history"],["TimeoutError",200])

    def test_parallel_requests_preserve_input_order(self):
        def good(url,kind):
            return 200, {"Content-Type":"text/html"}, b"<html>RETALLY</html>"
        report=run(schedule(5), live=True, only_kind="landing",
                   workers=5, fetcher=good)
        self.assertEqual(report["counts"]["PASS"],5)
        self.assertEqual([x["url"] for x in report["targets"]],
                         sorted(x["url"] for x in report["targets"]))

    def test_offline_parallel_path_never_fetches(self):
        def forbidden(*a):
            raise AssertionError("Do not fetch in offline mode")
        report=run(schedule(1), workers=6, transient_retries=2, fetcher=forbidden)
        self.assertEqual(report["mode"],"offline_manifest")
        self.assertEqual(report["counts"]["NOT_CHECKED"],2)

    def test_parallel_images_validate_dimensions(self):
        result=run(schedule(1),live=True,only_kind="image",workers=4,
                   fetcher=lambda *a:(200,{"Content-Type":"image/png"},PNG))
        self.assertEqual(result["counts"]["PASS"],1)
        self.assertEqual(result["targets"][0]["dimensions"],[1080,1350])

    def test_bounded_worker_and_retry_rejects_unreasonable_load(self):
        for workers in (0, 7, "4", True):
            with self.assertRaisesRegex(ValueError,"workers"):
                run(schedule(1),workers=workers)
        for attempts in (-1, 3, "1", True):
            with self.assertRaisesRegex(ValueError,"transient_retries"):
                run(schedule(1),transient_retries=attempts)

    def test_retry_never_follows_redirect(self):
        tries=[]
        def redirect(*a):
            tries.append(True)
            return 302,{"Content-Type":"text/html","Location":"https://evil.example"},b""
        result=run(schedule(1),live=True,only_kind="landing",
                   transient_retries=2,fetcher=redirect)
        self.assertEqual(result["counts"]["RECHECK"],1)
        self.assertEqual(len(tries),1)

    def test_retry_does_not_mask_invalid_content_type(self):
        count=[]
        def bogus(*a):
            count.append(True)
            return 200,{"Content-Type":"application/json"},b'{"retally":true}'
        result=run(schedule(1),live=True,only_kind="landing",
                   transient_retries=2,fetcher=bogus)
        self.assertEqual(result["counts"]["FAIL"],1)
        self.assertEqual(len(count),1)


if __name__=="__main__":
    unittest.main()
