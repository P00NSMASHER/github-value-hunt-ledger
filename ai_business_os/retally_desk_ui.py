"""Authenticated operator view of the synthetic integration workspace."""

from html import escape
import json
from pathlib import Path
import re

from ai_business_os.retally_inquiry_sync import private_db
from ai_business_os.retally_case_desk import case_evidence, collected_fee_cents, case_disposition, next_action
from ai_business_os.retally_postmill import digest, growth_rows, snapshot
from recoveryworks import DurableRecoveryLedger

CSS = """
*{box-sizing:border-box}html{font:16px/1.45 system-ui,sans-serif;color:#183832;background:#f7f7ef}body{margin:0}
header,main{max-width:1040px;margin:auto;padding:22px 24px}header{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #c6d0bc}
header b{letter-spacing:.12em}header span{font-size:.8rem;color:#41634e}h1{font-size:clamp(2.2rem,5vw,3.8rem);letter-spacing:-.06em;margin:.25em 0}h2{margin:1.25em 0 .55em;letter-spacing:-.04em}
p{margin:.5em 0}small{color:#526c61}a{color:#075e50}nav{display:flex;gap:1.3rem;flex-wrap:wrap;margin:1rem 0}
.grid,.cases{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
article,details,fieldset{background:white;border:1px solid #c7d3c8;border-radius:12px;padding:16px;min-width:0}
.num{font-size:2rem;font-weight:720;letter-spacing:-.04em;display:block}.tag{color:#175747;background:#e2f4e1;padding:3px 9px;border-radius:20px;font-size:.8rem}
.row{padding:.65rem 0;border-bottom:1px solid #dfe6dc;overflow-wrap:anywhere}.row:last-child{border:0}
summary{cursor:pointer;font-weight:600}input,button{font:inherit;max-width:100%;padding:8px;border:1px solid #90a99b;border-radius:6px}
label{display:grid;gap:3px}button{background:#164f41;color:white;border:0;cursor:pointer;margin-top:8px}time,code{overflow-wrap:anywhere}
form{display:grid;gap:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.78rem}
@media(max-width:520px){header,main{padding:16px}.grid{grid-template-columns:1fr 1fr}.grid article{padding:12px}.cases{grid-template-columns:1fr}}
"""


def e(value):
    return escape(str(value), quote=True)


def money(cents):
    return f"${cents / 100:,.2f}"


def render(state, *, csrf=None, selected=None, search="", portable=False):
    if len(search) > 100:
        raise ValueError("search is too long")
    with private_db(state, readonly=True) as db:
        identity = db.execute("SELECT namespace FROM identity").fetchone()
        if not identity or identity[0] != "synthetic":
            raise ValueError("synthetic workspace required")
        services = {"freight": "Freight Recovery", "capturebrief": "CaptureBrief"}
        rows = db.execute("""SELECT d.*,c.account_ref,c.owner,c.stage,c.hold,c.due_date FROM delivery d
                               LEFT JOIN pilot_cases c USING(reference) ORDER BY seq DESC LIMIT 100""").fetchall()
        if selected and (
            not re.fullmatch(r"RA-\d{8}-[A-F0-9]{8}", selected)
            or selected not in {r["reference"] for r in rows}
        ):
            raise ValueError("case unavailable")
        cards = []
        finance = []
        details = []
        campaigns = {}
        blocked = 0
        for r in rows:
            ref = r["reference"]
            svc = services.get(r["service"], r["service"])
            source_hold = ""
            if (
                r["service"] == "capturebrief"
                and db.execute(
                    "SELECT 1 FROM case_artifacts WHERE reference=? AND kind='quality'", (ref,)
                ).fetchone()
            ):
                _, quality = case_evidence(db, r["account_ref"], ref, "quality")
                if quality.get("quality", {}).get("customer_report_creation_blocked") is True:
                    source_hold = "Source conflict · delivery blocked"
            state_name = source_hold or r["hold"] or r["reason"] or r["stage"] or r["phase"]
            disposition = case_disposition(db, ref) if r["stage"] else "active"
            action_text = (
                next_action(r["stage"], source_hold or r["hold"], disposition)
                if r["stage"]
                else "Reconcile the CRM delivery."
            )
            if disposition != "active":
                state_name = disposition
            blocked += int(bool(source_hold or r["hold"] or r["reason"] or disposition == "disputed"))
            campaign = None
            if r["campaign"]:
                campaign = campaigns.setdefault(
                    r["campaign"], {"inquiries": 0, "qualified": 0, "recovered": 0, "collected": 0}
                )
                campaign["inquiries"] += 1
                campaign["qualified"] += int(bool(r["stage"]) and r["stage"] != "inquiry")
            target = "#" + ref if portable else "?case=" + ref
            card_matches = (
                not search
                or search.casefold()
                in " ".join(
                    str(v or "") for v in (ref, r["account_ref"], svc, r["owner"], state_name, r["campaign"])
                ).casefold()
            )
            if card_matches:
                cards.append(
                    f'<article><small>{e(svc)}</small><h3><a href="{e(target)}">{e(ref)}</a></h3><span class="tag">{e(state_name)}</span><p>{e(r["owner"] or "Awaiting CRM")} · {e(r["due_date"] or "No due date")}</p><small>CRM lead {e(r["lead_id"] or "pending")} · task {e(r["task_id"] or "pending")}</small><p>{e(action_text)}</p></article>'
                )
            if not r["stage"]:
                continue
            hashes = {
                kind: case_evidence(db, r["account_ref"], ref, kind)[0]
                for (kind,) in db.execute(
                    "SELECT DISTINCT kind FROM case_artifacts WHERE reference=? ORDER BY kind", (ref,)
                )
            }
            if "recovery_ledger" in hashes:
                _, obj = case_evidence(db, r["account_ref"], ref, "recovery_ledger")
                ledger = DurableRecoveryLedger.from_bundle(obj["bundle"])
                if any(
                    record.finding.currency != "USD" or record.finding.reference != ref
                    for record in ledger.records()
                ):
                    raise ValueError("wrong case or currency in fixture ledger")
                totals = ledger.rollup()["totals"]
                _, payment = case_evidence(db, r["account_ref"], ref, "fee_receipts")
                collected = collected_fee_cents(payment)
                if campaign:
                    campaign["recovered"] += totals["recovered_cents"]
                    campaign["collected"] += collected
                finance.append(
                    f"<article><small>USD · {e(ref)}</small><p>Flagged <b>{money(totals['potential_cents'])}</b></p><p>Recovered after reversal <b>{money(totals['recovered_cents'])}</b></p><p>Fee assessed <b>{money(totals['fee_cents'])}</b></p><p>Fee cash collected <b>{money(collected)}</b></p><small>Restored ledger head <code>{e(ledger.journal.head_hash[:16])}</code></small></article>"
                )
            if selected != ref and not portable:
                continue
            trail = "".join(
                f'<div class="row">{e(ev[0])} · {e(ev[1])}</div>'
                for ev in db.execute(
                    "SELECT action,occurred_at FROM case_events WHERE reference=? ORDER BY seq", (ref,)
                )
            )
            sources = "".join(
                f'<div class="row">{e(k)} <code>{e(v[:16])}</code></div>' for k, v in sorted(hashes.items())
            )
            preview = ""
            if "deliverable" in hashes:
                _, doc = case_evidence(db, r["account_ref"], ref, "deliverable")
                if isinstance(doc.get("preview"), str):
                    preview = (
                        "<details><summary>Read private operator preview</summary><pre>"
                        + e(doc["preview"][:24000])
                        + "</pre></details>"
                    )
            form = ""
            if csrf:
                form = f'<form method="post" action="/ui/retally/triage"><input type="hidden" name="csrf" value="{e(csrf)}"><input type="hidden" name="ref" value="{e(ref)}"><label>Owner<input required maxlength="80" name="owner" value="{e(r["owner"])}"></label><label>Due date<input required type="date" name="due" value="{e(r["due_date"])}"></label><label>Hold reason<input maxlength="200" name="hold" value="{e(r["hold"] or "")}"></label><button>Save case update</button></form>'
                options = ("decline", "cancel", "dispute") if disposition == "active" else ("reopen",)
                choices = "".join(f'<option value="{a}">{a.title()}</option>' for a in options)
                form += f'<details><summary>Change case disposition</summary><form method="post" action="/ui/retally/disposition"><input type="hidden" name="csrf" value="{e(csrf)}"><input type="hidden" name="ref" value="{e(ref)}"><input type="hidden" name="expected" value="{e(disposition)}"><label>Change<select aria-label="Change" name="action">{choices}</select></label><label>Reason<input required maxlength="200" name="reason"></label><button>Record disposition</button></form></details>'
            details.append(
                f'<article id="{e(ref)}"><small>{e(r["account_ref"])} · {e(svc)}</small><h3>{e(ref)}</h3><p>{e(r["stage"])} · Private preview</p>{form}{preview}<details><summary>Case history</summary>{trail}</details><details><summary>Evidence versions</summary>{sources}</details></article>'
            )
        drafts = (
            growth_rows(db)
            if db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='social_calendar'"
            ).fetchone()
            else []
        )
        social = ""
        for draft in drafts:
            button = ""
            if csrf and draft["stage"] in {"draft", "review"}:
                action = "review" if draft["stage"] == "draft" else "approve"
                label = "Send to private review" if action == "review" else "Approve draft internally"
                button = f'<form method="post" action="/ui/retally/editorial"><input type="hidden" name="csrf" value="{e(csrf)}"><input type="hidden" name="slug" value="{e(draft["slug"])}"><input type="hidden" name="action" value="{action}"><input type="hidden" name="version_hash" value="{e(digest(snapshot(draft)))}"><button>{label}</button></form>'
            remote = (
                ("Verified Postmill draft " + e(draft["remote_id"])) if draft["remote_id"] else "Local draft"
            )
            social += f'<details class="row"><summary>{e(draft["title"])} · {e(draft["stage"])}</summary><p>{e(draft["copy"])}</p><small>{e(draft["audience"])} · {remote} · Provider publication unverified</small>{button}</details>'
        checked = max((r["checked_at"] or "" for r in rows), default="") or "Unknown"
    css = (
        ("<style>" + CSS + "</style>") if portable else '<link rel="stylesheet" href="/ui/retally/style.css">'
    )
    tiles = "".join(
        f'<article><small>{e(label)}</small><span class="num">{n}</span></article>'
        for label, n in (
            ("Accepted inquiries", len(rows)),
            ("CRM linked", sum(r["phase"] == "done" for r in rows)),
            ("Holds and sync errors", blocked),
            ("Organic drafts", len(drafts)),
        )
    )
    origins = "".join(
        f"<p><b>{e(k)}</b><br>{v['inquiries']} tagged test inquiry · {v['qualified']} qualified · {money(v['recovered'])} recovered · {money(v['collected'])} collected (USD)</p>"
        for k, v in campaigns.items()
    )
    prime = json.loads((Path(__file__).parent / "prime_pilot" / "receipt.json").read_text())
    model_dir = Path(__file__).parent / "prime_pilot" / "cpu" / "receipts"
    attempt = json.loads((model_dir / "attempt-2.json").read_text())
    worker = (
        f"<p>Prime Agent · local CPU coding test. Model {e(attempt['model'])}. "
        f"An independent verifier rejected the first patch and accepted the second in {e(attempt['elapsed_seconds'])}s. "
        f"Patch <code>{e(attempt['verifier']['diff_sha256'][:16])}</code>.</p>"
        f"<p>Separate worker restart test · {e(prime['elapsed_seconds'])}s · lease state {e(prime['goal_state'])}.</p>"
    )
    search_box = (
        ""
        if portable
        else f'<form method="get" action="/ui/retally"><label>Find an account, case or owner<input type="search" name="q" maxlength="100" value="{e(search)}"></label><button>Search cases</button></form>'
    )
    if not cards:
        cards.append("<p>No matching cases.</p>")
    logout = (
        (
            f'<form method="post" action="/ui/logout"><input type="hidden" name="csrf" value="{e(csrf)}"><button>Sign out</button></form>'
        )
        if csrf
        else ""
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RETALLY | Operator desk</title>'
        + css
        + "<header><b>RETALLY</b><span>PRIVATE PILOT · SYNTHETIC DATA</span>"
        + logout
        + "</header><main><small>BUSINESS OPERATIONS</small>"
        "<h1>Operator desk</h1><p>Review the latest 100 inquiries, follow each case, and reconcile the fees.</p>"
        '<nav><a href="#today">Today</a><a href="#cases">Customers &amp; cases</a><a href="#growth">Growth</a><a href="#finance">Financials</a><a href="#ops">Operations</a></nav>'
        '<h2 id="today">Today</h2><div class="grid">'
        + tiles
        + f'</div><h2 id="cases">Customers &amp; cases</h2>{search_box}<div class="cases">'
        + "".join(cards + details)
        + '</div><h2 id="growth">Growth</h2><article>'
        + (social or "Social calendar unavailable.")
        + origins
        + '<small>Real reach, leads and conversion rates are unverified.</small></article><h2 id="finance">Financials</h2><div class="cases">'
        + ("".join(finance) or "No reconciled fixture ledger.")
        + '</div><h2 id="ops">Operations</h2><article>Last CRM checkpoint <time>'
        + e(checked)
        + "</time>"
        + worker
        + "<p>Fixture amounts and staged drafts are excluded from commercial reporting.</p></article></main></html>"
    )
