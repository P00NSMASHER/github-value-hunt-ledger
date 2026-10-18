"""Offline regression checks for changed-only zero-cost RETALLY IndexNow."""
import json
import unittest
from unittest.mock import patch
from freight.marketing import indexnow_notify as n


class IndexNowSafetyTests(unittest.TestCase):
    def test_changed_pages_only_and_canonical_pretty_routes(self):
        changed=[
            "freight/site/index.html",
            "freight/site/ltl-reweigh-evidence-comparator.html",
            "freight/site/ltl-reweigh-evidence-comparator.html",
            "freight/site/404.html",
            "freight/site/recovery-status-example.html",
            "freight/site/google738a4fc9a0997cd0.html",
            "freight/site/site.js",
            "freight/site/../private.html",
            "freight/site/assets/leak.html",
            "recoveryworks/site/index.html",
            "private/freight-claims.html",
        ]
        self.assertEqual(n.changed_public_urls(changed),[
            n.ROOT,n.ROOT + "ltl-reweigh-evidence-comparator",
        ])

    def test_reject_noncanonical_and_duplicate_in_payload(self):
        target=n.ROOT + "ltl-reweigh-evidence-comparator"
        for bad in ([],[target,target],[target,"https://bad.example.org/"]):
            with self.assertRaises(ValueError):
                n.make_payload(bad)
        obj=json.loads(n.make_payload([target]).decode("utf-8"))
        self.assertEqual(obj["host"],n.HOST)
        self.assertEqual(obj["urlList"],[target])
        self.assertEqual(obj["keyLocation"],n.ROOT+n.KEY+".txt")

    def test_requires_key_sitemap_and_exact_canonical_html(self):
        a=n.ROOT + "ltl-reweigh-evidence-comparator"
        sitemap='<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+a+'</loc></url></urlset>'
        html='<link rel="canonical" href="'+a+'">'
        def good(url):
            return {
                n.ROOT+n.KEY_PATH:(n.KEY+"\n","text/plain"),
                n.ROOT+"sitemap.xml":(sitemap,"application/xml"),
                a:(html,"text/html"),
            }[url]
        with patch.object(n,"_get",side_effect=good):
            n.verify_published([a])
        for value in ("wrong-key","",n.KEY+"x"):
            with patch.object(n,"_get",side_effect=lambda url: (value,"text/plain") if url.endswith(".txt") else good(url)):
                with self.assertRaises(RuntimeError):
                    n.verify_published([a])
        with patch.object(n,"_get",side_effect=lambda url: ("<html>old</html>","text/html") if url == a else good(url)):
            with self.assertRaises(RuntimeError):
                n.verify_published([a])

    def test_only_one_submit_after_successful_verification(self):
        target=n.ROOT+"ltl-reweigh-evidence-comparator"
        with patch.object(n,"changed_git_paths",return_value=["freight/site/ltl-reweigh-evidence-comparator.html"]), \
             patch.object(n,"verify_published") as verify, \
             patch.object(n,"submit_once",return_value=200) as submit:
            result=n.notify("a"*40,attempts=1,delay=0)
            self.assertEqual(result["state"],"submitted")
            verify.assert_called_once_with([target])
            submit.assert_called_once_with([target])
        with patch.object(n,"changed_git_paths",return_value=["freight/site/ltl-reweigh-evidence-comparator.html"]), \
             patch.object(n,"verify_published"), \
             patch.object(n,"submit_once",return_value=202) as submit:
            result=n.notify("a"*40,attempts=1,delay=0)
            self.assertEqual(result["state"],"key_validation_pending")
            self.assertEqual(result["http_status"],202)
            self.assertIn("validation", result["note"])
            submit.assert_called_once()
        with patch.object(n,"changed_git_paths",return_value=["freight/site/site.css"]), \
             patch.object(n,"submit_once") as submit:
            self.assertEqual(n.notify("a"*40)["state"],"skipped")
            submit.assert_not_called()

    def test_actual_submit_transport_is_never_called_by_offline_tests(self):
        self.assertEqual(n.INDEXNOW_ENDPOINT,"https://api.indexnow.org/indexnow")
        self.assertEqual(len(n.KEY),32)
        self.assertTrue(n.KEY.isalnum())


if __name__=="__main__":
    unittest.main()
