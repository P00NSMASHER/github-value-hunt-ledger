"""Generate a lightweight Freight Recovery client status dashboard.

This is a presentation layer over governed audit/recovery state. It does not
create findings, authorize claims, or establish settlement truth.
"""
from __future__ import annotations
import argparse, json
from html import escape
from pathlib import Path

COUNT_KEYS = (
    "records_reviewed",
    "candidates_flagged",
    "findings_validated",
    "claims_authorized",
    "claims_submitted",
    "claims_approved",
    "recoveries_posted",
    "recoveries_reversed",
)
MONEY_KEYS = (
    "candidate_difference_cents",
    "validated_difference_cents",
    "approved_claim_cents",
    "gross_recovered_cents",
    "reversal_cents",
    "net_recovered_cents",
    "fee_eligible_recovered_cents",
)


def _require_int(payload, key):
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{key} must be a nonnegative integer")
    return value


def validate(payload):
    clean = dict(payload)
    for key in ("customer", "population_id", "period", "updated_at"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be non-empty text")
        clean[key] = value.strip()
    clean["synthetic"] = bool(payload.get("synthetic", False))
    for key in COUNT_KEYS + MONEY_KEYS:
        clean[key] = _require_int(payload, key)

    chain = [
        clean["records_reviewed"],
        clean["candidates_flagged"],
        clean["findings_validated"],
        clean["claims_authorized"],
        clean["claims_submitted"],
        clean["claims_approved"],
        clean["recoveries_posted"],
    ]
    if any(a < b for a, b in zip(chain, chain[1:])):
        raise ValueError("recovery state counts cannot increase downstream")
    if clean["recoveries_reversed"] > clean["recoveries_posted"]:
        raise ValueError("reversals cannot exceed posted recoveries")
    if clean["validated_difference_cents"] > clean["candidate_difference_cents"]:
        raise ValueError("validated difference cannot exceed candidate difference")
    if clean["approved_claim_cents"] > clean["validated_difference_cents"]:
        raise ValueError("approved claims cannot exceed validated difference")
    if clean["reversal_cents"] > clean["gross_recovered_cents"]:
        raise ValueError("reversal value cannot exceed gross recovered")
    if clean["net_recovered_cents"] != clean["gross_recovered_cents"] - clean["reversal_cents"]:
        raise ValueError("net recovered must equal gross recovered minus reversals")
    if clean["fee_eligible_recovered_cents"] > clean["net_recovered_cents"]:
        raise ValueError("fee-eligible recovery cannot exceed net recovery")

    notes = payload.get("notes") or []
    if not isinstance(notes, list) or not all(isinstance(x, str) and x.strip() for x in notes):
        raise ValueError("notes must be a list of non-empty strings")
    clean["notes"] = notes
    return clean


def money(cents):
    return "$" + f"{cents / 100:,.2f}"


def render_html(payload):
    p = validate(payload)
    label = "FICTIONAL / SYNTHETIC EXAMPLE" if p["synthetic"] else "CUSTOMER STATUS"
    stages = [
        ("Records reviewed", p["records_reviewed"]),
        ("Candidates flagged", p["candidates_flagged"]),
        ("Findings validated", p["findings_validated"]),
        ("Claims authorized", p["claims_authorized"]),
        ("Claims submitted", p["claims_submitted"]),
        ("Claims approved", p["claims_approved"]),
        ("Recoveries posted", p["recoveries_posted"]),
        ("Recoveries reversed", p["recoveries_reversed"]),
    ]
    cards = "".join(
        f'<article class="status-card"><span>{escape(name)}</span><strong>{value:,}</strong></article>'
        for name, value in stages
    )
    notes = "".join(f"<li>{escape(x)}</li>" for x in p["notes"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Recovery Status | {escape(p['customer'])}</title>
<style>
:root{{--ink:#071426;--paper:#f5f3ed;--white:#fff;--line:#d8d7d1;--accent:#1747e8;--muted:#697386}}
*{{box-sizing:border-box}}body{{margin:0;font-family:Arial,sans-serif;background:var(--paper);color:var(--ink)}}main{{max-width:1100px;margin:auto;padding:36px 20px 64px}}
header{{background:var(--ink);color:white;padding:30px;border-radius:18px}}.label{{font-size:12px;letter-spacing:.12em;text-transform:uppercase;opacity:.75}}
h1{{margin:.35rem 0}}.meta{{opacity:.8}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}}.status-card,.money-card{{background:white;border:1px solid var(--line);border-radius:14px;padding:18px}}.status-card span,.money-card span{{display:block;color:var(--muted);font-size:13px}}.status-card strong,.money-card strong{{font-size:28px;display:block;margin-top:8px}}.money{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.net{{border:2px solid var(--accent)}}section{{margin-top:28px}}li{{margin:.5rem 0}}footer{{margin-top:30px;color:var(--muted);font-size:13px}}@media(max-width:800px){{.grid,.money{{grid-template-columns:1fr 1fr}}}}@media(max-width:500px){{.grid,.money{{grid-template-columns:1fr}}}}
</style></head><body><main>
<header><div class="label">{label}</div><h1>Freight Recovery Status</h1><p>{escape(p['customer'])}</p><p class="meta">Population {escape(p['population_id'])} · {escape(p['period'])} · Updated {escape(p['updated_at'])}</p></header>
<section><h2>Recovery pipeline</h2><div class="grid">{cards}</div></section>
<section><h2>Money states</h2><div class="money">
<article class="money-card"><span>Candidate difference</span><strong>{money(p['candidate_difference_cents'])}</strong></article>
<article class="money-card"><span>Validated difference</span><strong>{money(p['validated_difference_cents'])}</strong></article>
<article class="money-card"><span>Approved claim value</span><strong>{money(p['approved_claim_cents'])}</strong></article>
<article class="money-card"><span>Gross recovered</span><strong>{money(p['gross_recovered_cents'])}</strong></article>
<article class="money-card"><span>Reversals</span><strong>{money(p['reversal_cents'])}</strong></article>
<article class="money-card net"><span>Net actual recovered</span><strong>{money(p['net_recovered_cents'])}</strong></article>
<article class="money-card"><span>Fee-eligible recovered</span><strong>{money(p['fee_eligible_recovered_cents'])}</strong></article>
</div></section>
<section><h2>Status notes</h2><ul>{notes or '<li>No current notes.</li>'}</ul></section>
<footer>Candidate difference ≠ validated finding ≠ approved claim ≠ recovered funds. This dashboard is a status view over governed evidence, not a source of financial truth.</footer>
</main></body></html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("payload")
    parser.add_argument("output")
    args = parser.parse_args()
    payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    Path(args.output).write_text(render_html(payload), encoding="utf-8")


if __name__ == "__main__":
    main()
