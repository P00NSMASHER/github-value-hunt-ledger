"""Offline browser acceptance for the real private RETALLY OS UI, using synthetic data only.

This test never authenticates to, reads, writes, or posts to production.
Cloudflare Access, D1, email and social providers are not contacted.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
URL = "https://retallyrecovery.com/api/internal/retally-os"
NOW = int(datetime.now(timezone.utc).timestamp())


def render_html() -> str:
    code = ("import {renderRetallyOsPage} from './freight/site/retally_os_ui.mjs';"
            "process.stdout.write(renderRetallyOsPage('visual-synthetic-nonce'));")
    p = subprocess.run(["node", "--input-type=module", "-e", code], cwd=REPO,
                       check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout


def fixture() -> dict:
    return {
        "observedAt": datetime.now(timezone.utc).isoformat(),
        "cases": [
            {"reference": "RA-20261109-A1B2C3D4", "company": "Demo Logistics",
             "contact": "Demo Contact", "email": "demo@example.invalid",
             "service": "freight", "acceptedAt": NOW-1000, "notification": "pending",
             "synthetic": False, "owner": "", "dueOn": "", "status": "reviewing",
             "note": "", "version": 0, "campaign": {"utm_source": "demo"}},
            {"reference": "RA-20261109-1122AABB", "company": "Example Carrier",
             "contact": "Example Person", "email": "fixture@example.invalid",
             "service": "freight", "acceptedAt": NOW-2000, "notification": "pending",
             "synthetic": False, "owner": "Owner", "dueOn": "", "status": "qualified",
             "note": "", "version": 1, "campaign": {"utm_source": "direct"}},
            {"reference": "RA-20261109-DEAD0001", "company": "QA Test Record",
             "contact": "Test Contact", "email": "qa@example.invalid",
             "service": "freight", "acceptedAt": NOW-3000, "notification": "verified",
             "synthetic": True, "owner": "", "dueOn": "", "status": "reviewing",
             "note": "", "version": 0, "campaign": {"utm_source": "test"}},
        ],
        "tasks": [
            {"taskId": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
             "reference": "RA-20261109-A1B2C3D4", "title": "Review demo invoice",
             "owner": "Owner", "dueOn": "2026-11-01", "status": "open",
             "note": "", "version": 1, "synthetic": False,
             "createdAt": NOW-2000, "updatedAt": NOW-1000},
            {"taskId": "aaaaaaaa-bbbb-4ccc-8ddd-ffffffffffff",
             "reference": "RA-20261109-DEAD0001", "title": "QA rehearsal",
             "owner": "Test", "dueOn": "", "status": "open", "note": "",
             "version": 1, "synthetic": True,
             "createdAt": NOW-2000, "updatedAt": NOW-1000},
        ],
        "drafts": [
            {"draftId": "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee",
             "title": "Review freight charges", "body": "Synthetic editorial draft.",
             "channel": "linkedin", "status": "draft",
             "version": 1, "updatedAt": NOW-500},
        ],
    }


def run(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    html = render_html()
    assert '<script nonce="visual-synthetic-nonce">' in html
    assert 'id="mobile-dock"' in html
    assert 'id="case-filters"' in html
    assert 'id="task-filters"' in html
    assert 'onclick=' not in html
    assert '__STYLE__' not in html and '__SCRIPT__' not in html

    data = fixture()
    posts: list[dict] = []
    external: list[str] = []
    problems: list[str] = []
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for width, height, label in [(390, 844, "iphone"), (768, 1024, "tablet"), (1440, 900, "desktop")]:
            page = browser.new_page(viewport={"width": width, "height": height},
                                    device_scale_factor=1, is_mobile=width == 390,
                                    has_touch=width == 390)

            def handle(route):
                req = route.request
                url = urlsplit(req.url)
                if url.scheme != "https" or url.netloc != "retallyrecovery.com" or url.path != "/api/internal/retally-os":
                    external.append(req.url)
                    route.abort()
                    return
                if req.method == "GET" and url.query == "":
                    route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html,
                                  headers={"Content-Security-Policy":
                                   "default-src 'none'; script-src 'nonce-visual-synthetic-nonce'; "
                                   "style-src 'nonce-visual-synthetic-nonce'; connect-src 'self'; "
                                   "form-action 'none'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'; "
                                   "upgrade-insecure-requests"})
                    return
                if req.method == "GET" and url.query == "view=data":
                    route.fulfill(status=200, content_type="application/json",
                                  headers={"Cache-Control": "no-store"}, body=json.dumps(data))
                    return
                if req.method == "POST" and url.query == "":
                    payload = req.post_data_json
                    posts.append(payload)
                    action = payload.get("action")
                    if action == "save_case":
                        x = next(c for c in data["cases"] if c["reference"] == payload["reference"])
                        x.update({"owner": payload["owner"], "status": payload["status"],
                                  "note": payload["note"], "dueOn": payload["dueOn"],
                                  "version": x["version"]+1})
                        reply = {"ok": True, "version": x["version"], "externalSends": 0}
                    elif action == "save_task":
                        existing = next((t for t in data["tasks"] if t["taskId"] == payload["taskId"]), None)
                        if existing:
                            existing.update({k: payload[k] for k in ("title","owner","dueOn","status","note")})
                            existing["version"] += 1
                            reply = {"ok": True, "version": existing["version"], "externalSends": 0}
                        else:
                            x = dict(payload)
                            x.update({"version": 1, "synthetic": False,
                                      "createdAt": NOW, "updatedAt": NOW})
                            data["tasks"].append(x)
                            reply = {"ok": True, "version": 1, "externalSends": 0}
                    elif action == "save_draft":
                        existing = next((d for d in data["drafts"] if d["draftId"] == payload["draftId"]), None)
                        if existing:
                            existing.update({"title": payload["title"], "body": payload["body"],
                                             "channel": payload["channel"], "status": "draft",
                                             "version": existing["version"]+1})
                            reply = {"ok": True, "version": existing["version"], "published": False}
                        else:
                            x = {k: payload[k] for k in ("draftId","title","channel","body")}
                            x.update({"version": 1, "status": "draft", "updatedAt": NOW})
                            data["drafts"].append(x)
                            reply = {"ok": True, "version": 1, "published": False}
                    elif action == "review_draft":
                        existing = next(d for d in data["drafts"] if d["draftId"] == payload["draftId"])
                        existing["status"] = "reviewed"
                        existing["version"] += 1
                        reply = {"ok": True, "version": existing["version"], "published": False}
                    else:
                        raise AssertionError("Unexpected backend action")
                    route.fulfill(status=200, content_type="application/json", body=json.dumps(reply))
                    return
                route.fulfill(status=405, body="Method Not Allowed")

            page.route("**/*", handle)
            page.on("pageerror", lambda err: problems.append(str(err)))
            page.on("console", lambda msg: problems.append(msg.text) if msg.type == "error" else None)
            page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_function("document.getElementById('sync-time').textContent.startsWith('Synced')")
            assert page.locator("#metrics .tile").count() == 4
            assert '2' in page.locator('#metrics .tile').first.inner_text()
            assert '1' in page.locator('#metrics .tile').nth(2).inner_text()
            assert '1' in page.locator('#metrics .tile').nth(3).inner_text()
            assert page.locator("#recent article").count() == 2, "QA fixture must be excluded from real summary"
            nums=page.locator('#urgent .priority-number').all_inner_texts()
            assert nums==[str(i).zfill(2) for i in range(1,len(nums)+1)], nums
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
            assert page.locator("#mobile-dock").is_visible() == (width <= 760)
            page.screenshot(path=str(out / f"{label}-overview.png"), full_page=True)

            if width == 390:
                page.locator("#mobile-dock button[data-tab=cases]").click()
                assert page.locator("#view-title").inner_text() == "Customers & cases"
                assert page.locator("#case-list article[data-ref]:visible").count() == 2
                page.locator("#case-filters button[data-filter=test]").click()
                assert page.locator("#case-list article[data-ref]:visible").count() == 1
                page.locator("#case-filters button[data-filter=live]").click()
                page.evaluate('window.scrollTo(0,0)')
                page.wait_for_timeout(280)
                page.screenshot(path=str(out / "iphone-cases.png"), full_page=True)
                page.locator("#more-toggle").click()
                assert page.locator("#more-sheet").is_visible()
                page.locator("#more-sheet button[data-more-tab=finance]").click()
                assert "Unknown" in page.locator('.panel[data-tab=finance]').inner_text()
                assert page.locator("#more-sheet").is_hidden()
                page.locator("#mobile-dock button[data-tab=tasks]").click()
                assert page.locator("#task-list article[data-task-id]:visible").count() == 1
                page.evaluate('window.scrollTo(0,0)')
                page.wait_for_timeout(280)
                page.screenshot(path=str(out / "iphone-followups.png"), full_page=True)
                page.locator('#task-filters button[data-filter=test]').click()
                assert page.locator('#task-list article[data-task-id]:visible').count() == 1
                page.locator('#task-filters button[data-filter=open]').click()
            if width == 1440:
                page.locator('nav button[data-tab=cases]').click()
                assert page.locator("#case-list article[data-ref]:visible").count() == 2
                page.locator("#case-list article[data-ref]").first.locator("details summary").click()
                page.locator("#case-list article[data-ref]").first.locator("input").first.fill("Owner")
                page.locator("#case-list article[data-ref]").first.locator("button.save").click()
                page.locator('nav button[data-tab=tasks]').click()
                page.locator("#task-title").fill("Check synthetic receipt")
                page.locator("#task-owner").fill("Owner")
                page.locator("#new-task").click()
                assert any(x["action"] == "save_task" for x in posts)
                page.screenshot(path=str(out / "desktop-followups.png"), full_page=True)
                page.locator('nav button[data-tab=social]').click()
                assert "Review freight charges" in page.locator("#drafts").inner_text()
                page.locator("#draft-title").fill("Weekly freight insights")
                page.locator("#draft-body").fill("This is a synthetic draft kept private.")
                page.locator("#new-draft").click()
                assert any(x["action"] == "save_draft" for x in posts)
                page.locator('#drafts .draft').first.get_by_role('button',name='Mark reviewed').click()
                assert any(x['action'] == 'review_draft' for x in posts)
                assert all(x["action"] in {"save_task","save_case","save_draft","review_draft"} for x in posts)
                assert page.locator('#drafts .draft').first.locator('textarea').is_hidden(), 'Draft editor should be collapsed initially'
                page.locator('#drafts .draft').first.locator('details summary').click()
                assert page.locator('#drafts .draft').first.locator('textarea').is_visible()
                page.locator('#drafts .draft').first.locator('details summary').click()
                page.evaluate('window.scrollTo(0,0)')
                page.wait_for_timeout(280)
                page.screenshot(path=str(out / "desktop-content.png"), full_page=True)
            results.append({"width": width, "tabs": 7, "kpis": 4,
                            "horizontalOverflow": False, "consoleErrors": len(problems)})
            page.close()
        browser.close()
    assert not problems, f"Browser JS errors: {problems}"
    assert not external, f"Unexpected external requests: {external}"
    report = {"passed": True, "syntheticOnly": True, "realCustomerData": False,
              "posts": len(posts), "externalProviderCalls": 0,
              "screenshots": [p.name for p in out.glob("*.png")], "viewports": results}
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv)>1 else Path("evidence/retally-os")
    print(json.dumps(run(path), indent=2))
