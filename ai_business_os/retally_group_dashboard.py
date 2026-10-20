"""Offline HTML presentation for the RETALLY Group planning view.

The renderer has no network, storage, database, or financial authority. It accepts
the public planning projection only; customer records and live private state do
not belong in this export.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from html import escape
from urllib.parse import urlsplit


_KINDS = {
    "business": "Business",
    "product_family": "Product family",
    "venture": "Venture",
}
_FINANCIAL_KEYS = (
    "qualified_leads",
    "paying_customers",
    "cash_collected",
    "contribution_profit",
)


def _text(value: object) -> str:
    return escape("" if value is None else str(value), quote=True)


def _label(value: object) -> str:
    return str(value or "Unassigned").replace("_", " ").capitalize()


def _safe_https(value: object) -> str | None:
    """Validate links separately from the model, including URL parser edge cases."""
    if not isinstance(value, str) or not value or "\\" in value:
        return None
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    try:
        parts = urlsplit(value)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or (parts.port is not None and not 1 <= parts.port <= 65535)
        ):
            return None
    except ValueError:
        return None
    return value


def _sources(
    sources: Sequence[Mapping[str, object]],
    private_source_refs: Sequence[Mapping[str, object]] = (),
) -> str:
    if not sources and not private_source_refs:
        return '<p class="source-pending">Source binding pending</p>'
    rows = []
    for source in sources:
        label = _text(source.get("label", "Source"))
        url = _safe_https(source.get("url"))
        link = (
            f'<a href="{_text(url)}" target="_blank" rel="noopener noreferrer">{label}'
            '<span class="sr-only"> (opens in a new tab)</span></a>'
            if url
            else f"<span>{label}</span>"
        )
        date = source.get("observed_on")
        observed = f'<span class="source-date">Observed {_text(date)}</span>' if date else ""
        rows.append(f"<li>{link}{observed}</li>")
    for ref in private_source_refs:
        rows.append(
            '<li class="private-source">'
            f'<span>{_text(ref.get("label"))}</span>'
            f'<span class="source-date">Record {_text(ref.get("record_key"))}</span>'
            f'<span class="source-date">Source as of {_text(ref.get("source_as_of"))}; '
            f'Reviewed {_text(ref.get("reviewed_on"))}</span></li>'
        )
    return '<ul class="sources">' + "".join(rows) + "</ul>"


def _count(value: object) -> str:
    if type(value) is not int or value < 0:
        raise ValueError("catalog totals must be nonnegative integers")
    return str(value)


def _entry(entry: Mapping[str, object], division_names: Mapping[str, str]) -> str:
    kind = str(entry.get("kind", ""))
    if kind not in _KINDS:
        raise ValueError("unsupported planning entry kind")
    division_id = str(entry.get("division_id", ""))
    evidence = entry.get("evidence_status")
    if evidence == "REPOSITORY_DOCUMENTED":
        evidence_label, evidence_class = "Repository documented", "documented"
    elif evidence == "PRIVATE_ARTIFACT_DOCUMENTED":
        evidence_label, evidence_class = "Private source reviewed", "documented"
    else:
        evidence_label, evidence_class = "Source unresolved", "unresolved"
    search = " ".join(
        str(entry.get(key, "")) for key in ("name", "purpose", "stage", "next_action")
    )
    return (
        f'<article class="business-card" data-division="{_text(division_id)}" '
        f'data-kind="{_text(kind)}" data-search="{_text(search)}">'
        '<div class="card-top">'
        f'<span class="division-label">{_text(division_names.get(division_id, division_id))}</span>'
        f'<span class="kind">{_text(_KINDS[kind])}</span></div>'
        f'<h3>{_text(entry.get("name"))}</h3>'
        f'<p class="purpose">{_text(entry.get("purpose"))}</p>'
        '<dl class="entry-facts">'
        f'<div><dt>Stage</dt><dd>{_text(entry.get("stage"))}</dd></div>'
        f'<div><dt>Owner role</dt><dd>{_text(_label(entry.get("owner_role")))}</dd></div>'
        '</dl><div class="next-action"><span class="mini-label">Next milestone</span>'
        f'<p>{_text(entry.get("next_action"))}</p></div>'
        '<footer class="card-footer">'
        f'<span class="evidence {evidence_class}">{evidence_label}</span>'
        + _sources(entry.get("sources", []), entry.get("private_source_refs", []))
        + "</footer></article>"
    )


def _service(service: Mapping[str, object], *, expansion: bool = False) -> str:
    style = "service expansion" if expansion else "service"
    return (
        f'<li class="{style}"><span class="service-dot" aria-hidden="true"></span><div>'
        f'<h4>{_text(service.get("name"))}</h4><p>{_text(service.get("scope"))}</p>'
        '</div></li>'
    )


_CSS = """
:root{color-scheme:light;--ink:#172925;--muted:#53655e;--green:#126749;--mint:#dff3e8;--line:#d8e1da;--paper:#f5f7f3;--white:#fff;--amber:#745119}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--green);text-underline-offset:3px}a:hover{text-decoration-thickness:2px}button,input,select{font:inherit}button,a,input,select,summary{touch-action:manipulation}:focus-visible{outline:3px solid #3d956c;outline-offset:4px}.wrap{width:min(1180px,calc(100% - 48px));margin:auto}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.skip-link{position:absolute;top:-80px;left:16px;z-index:4;padding:12px;background:white}.skip-link:focus{top:12px}
.masthead{background:#132b23;color:#f5fff8;border-bottom:4px solid #51b783}.topbar{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:24px 0;border-bottom:1px solid #365044}.wordmark{font-size:21px;font-weight:850;letter-spacing:.13em}.wordmark span{color:#80d9a7}.topbar-label{color:#cadbce;font-size:12px;letter-spacing:.13em;text-transform:uppercase}.preview-pill{border:1px solid #64816e;border-radius:999px;padding:6px 12px;font-size:12px;color:#d5efdf;white-space:nowrap}.hero{padding:46px 0 36px;display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:48px;align-items:end}.eyebrow{font-size:12px;font-weight:750;letter-spacing:.14em;text-transform:uppercase;color:#8ed9ad;margin:0 0 12px}h1{font-size:clamp(34px,5vw,56px);line-height:1.08;letter-spacing:-.045em;margin:0 0 14px;font-weight:750}.hero-copy{font-size:17px;max-width:650px;margin:0;color:#d0e0d5}.snapshot{border-left:1px solid #4d6957;padding-left:24px;color:#d5e4da}.snapshot p{margin:4px 0}.snapshot strong{color:white;font-size:16px}.snapshot .small{font-size:12px;color:#b4cbbd}.section-nav{display:flex;flex-wrap:wrap;gap:8px 24px;padding:0 0 22px}.section-nav a{color:#d5efdf;font-size:13px;text-decoration:none}.section-nav a:hover{text-decoration:underline}
.notice{display:flex;align-items:flex-start;gap:14px;margin:26px 0 24px;padding:17px 20px;border:1px solid #bdd4c4;background:#eaf3ec;border-radius:10px}.notice-marker{border:1px solid #759b83;border-radius:50%;width:24px;height:24px;flex:0 0 24px;text-align:center;line-height:22px;font-weight:700}.notice p{margin:0}.notice strong{display:block}.notice .muted{font-size:13px;margin-top:3px}.muted{color:var(--muted)}.finance-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.metric{background:var(--white);border:1px solid var(--line);border-radius:12px;padding:20px}.metric-label{font-size:13px;color:var(--muted);margin:0 0 14px}.metric-value{font-size:24px;font-weight:700;letter-spacing:-.035em;line-height:1.2;margin:0}.metric-note{font-size:12px;color:var(--muted);margin:7px 0 0}.inventory{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin:20px 0 10px;padding:20px 0;border-bottom:1px solid var(--line)}.inventory div{display:flex;flex-direction:column;border-right:1px solid var(--line);padding-right:12px}.inventory div:last-child{border:0}.inventory dt{font-size:12px;color:var(--muted);margin-top:6px}.inventory dd{order:-1;margin:0;font-size:25px;font-weight:750;line-height:1.1}.inventory-note{font-size:12px;color:var(--muted);margin:8px 0 0}
section{padding-top:42px}section:last-of-type{padding-bottom:48px}.section-heading{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;margin-bottom:20px}.section-heading h2{font-size:26px;line-height:1.2;letter-spacing:-.035em;margin:0 0 7px}.section-heading p{margin:0;color:var(--muted);max-width:760px}.section-number{font-size:12px;font-weight:750;letter-spacing:.12em;color:var(--green);padding-top:5px;white-space:nowrap}.division-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}.division-card{border-top:3px solid #81b99b;background:#eaf0e9;padding:16px;border-radius:0 0 8px 8px}.division-card h3{font-size:14px;margin:0 0 7px}.division-card p{font-size:13px;color:#43584c;margin:0}.filters{display:flex;align-items:end;gap:12px;padding:17px 18px;background:#edf1eb;border:1px solid var(--line);border-radius:10px;margin-bottom:20px}.filters[hidden]{display:none}.filter-field{display:flex;flex-direction:column;gap:5px}.search-field{flex:1;min-width:180px}.filter-field label{font-size:12px;font-weight:650}.filters input,.filters select{border:1px solid #adbbb0;background:white;border-radius:7px;padding:10px 12px;min-height:44px;color:var(--ink);width:100%}.filters button{min-height:44px;border:1px solid #adbbb0;background:white;border-radius:7px;padding:10px 14px;color:var(--ink);cursor:pointer}.filter-count{font-size:13px;color:var(--muted);margin:0 0 16px}.directory{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.business-card{background:white;border:1px solid var(--line);border-radius:12px;padding:24px;display:flex;flex-direction:column;min-width:0}.business-card[hidden]{display:none}.card-top{display:flex;justify-content:space-between;gap:12px;align-items:start;margin-bottom:12px}.division-label{color:var(--green);font-size:11px;font-weight:750;text-transform:uppercase;letter-spacing:.06em}.kind{font-size:11px;color:#586a5d;background:#f0f3ed;padding:2px 8px;border-radius:4px;white-space:nowrap}.business-card h3{font-size:23px;letter-spacing:-.025em;line-height:1.2;margin:0 0 10px}.purpose{margin:0 0 18px;color:#465a50;font-size:14px}.entry-facts{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:0 0 18px}.entry-facts dt{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:#66796d;margin-bottom:4px}.entry-facts dd{margin:0;font-size:13px;font-weight:600;overflow-wrap:anywhere}.next-action{background:#f3f7f0;border-left:3px solid #8cbc9b;padding:12px 14px;margin-bottom:18px;flex:1}.mini-label{font-size:11px;font-weight:750;text-transform:uppercase;letter-spacing:.08em;color:#526d5c}.next-action p{font-size:13px;margin:6px 0 0}.card-footer{padding-top:14px;border-top:1px solid #e3e9e2}.evidence{display:inline-block;font-size:11px;font-weight:650;border-radius:999px;padding:3px 9px}.documented{background:#e4f1e8;color:#246344}.unresolved{background:#f9efd9;color:var(--amber)}.sources{list-style:none;padding:0;margin:10px 0 0;font-size:12px}.sources li{margin-top:6px;overflow-wrap:anywhere}.source-date{display:block;color:#687b6d;font-size:11px;margin-top:1px}.source-pending{font-size:12px;color:var(--muted);margin:10px 0 0}.empty-result{padding:30px;border:1px dashed #99b19e;border-radius:10px;text-align:center;color:var(--muted)}
.recovery-box{border:1px solid var(--line);background:white;border-radius:12px;overflow:hidden}.recovery-head{background:#ecf4ed;padding:20px 24px;border-bottom:1px solid var(--line)}.recovery-head h3{font-size:17px;margin:0 0 4px}.recovery-head p{font-size:13px;color:var(--muted);margin:0}.services{list-style:none;margin:0;padding:24px;display:grid;grid-template-columns:repeat(3,1fr);gap:22px}.service{display:flex;gap:10px;align-items:start;min-width:0}.service-dot{width:8px;height:8px;background:#469c6c;border-radius:50%;flex:0 0 8px;margin-top:7px}.service.expansion .service-dot{background:#93a798}.service h4{font-size:14px;line-height:1.4;margin:0 0 5px}.service p{font-size:12px;line-height:1.5;color:var(--muted);margin:0}.roadmap{border-top:1px solid var(--line);background:#f8faf6}.roadmap summary{padding:17px 24px;cursor:pointer;font-size:14px;font-weight:650}.roadmap summary span{font-weight:400;color:var(--muted)}.roadmap .services{padding-top:6px}.shared-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.shared-card{background:#20392c;color:#f2fbf4;border-radius:12px;padding:24px;min-width:0}.shared-index{font-size:12px;letter-spacing:.12em;color:#9bd3ac}.shared-card h3{font-size:21px;margin:15px 0 10px;letter-spacing:-.025em}.shared-card p{color:#d0e1d4;font-size:14px;margin:0 0 20px}.shared-card .sources{margin-top:16px;padding-top:14px;border-top:1px solid #49614f}.shared-card a{color:#b4ebc4}.shared-card .source-date{color:#b6ccbc}.shared-card .source-pending{color:#c0d3c4}.workflow{list-style:none;counter-reset:steps;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;padding:0;margin:0}.workflow>li{counter-increment:steps;background:white;border:1px solid var(--line);border-radius:10px;padding:20px;min-width:0}.workflow>li::before{content:counter(steps,decimal-leading-zero);display:block;font-size:12px;color:var(--green);font-weight:750;letter-spacing:.08em;margin-bottom:12px}.workflow h3{font-size:16px;margin:0 0 5px;line-height:1.3}.owner{font-size:11px;color:var(--muted);margin:0 0 15px}.evidence-list{padding-left:16px;font-size:12px;color:#49604f;margin:0}.evidence-list li{margin-top:6px}.workflow-note{font-size:13px;color:var(--muted);padding:14px 0 0;margin:0}.priorities{list-style:none;display:grid;grid-template-columns:1fr;gap:12px;padding:0;margin:0}.priority{display:grid;grid-template-columns:145px minmax(0,1fr);gap:26px;padding:24px;background:white;border:1px solid var(--line);border-radius:12px}.timeframe{font-size:13px;font-weight:700;margin:0 0 10px}.status{display:inline-block;font-size:11px;letter-spacing:.03em;border:1px solid #cadace;padding:3px 8px;border-radius:4px;color:#45634e;background:#eff5ed}.priority h3{font-size:18px;line-height:1.3;letter-spacing:-.02em;margin:0 0 8px}.priority .owner{margin-bottom:10px}.done-when{font-size:13px;margin:0;color:#49604f}.done-when strong{font-weight:650;color:#243e2b}.footer{border-top:1px solid var(--line);background:#edf2e9;padding:24px 0 32px}.footer-grid{display:flex;justify-content:space-between;gap:24px}.footer p{font-size:12px;color:var(--muted);margin:0 0 6px;max-width:740px}.footer strong{color:var(--ink)}.footer-label{font-weight:800;letter-spacing:.13em;font-size:12px;color:#2f5f43;white-space:nowrap}
@media(max-width:980px){.hero{grid-template-columns:1fr;gap:24px}.snapshot{border-left:0;border-top:1px solid #4d6957;padding:16px 0 0;display:flex;flex-wrap:wrap;gap:8px 24px}.snapshot p{margin:0}.division-grid,.finance-grid{grid-template-columns:repeat(2,1fr)}.workflow{grid-template-columns:repeat(2,minmax(0,1fr))}.shared-grid{grid-template-columns:1fr}.shared-card{display:grid;grid-template-columns:32px 1fr;column-gap:16px}.shared-index{grid-row:1/4;padding-top:4px}.shared-card h3{margin-top:0}.shared-card .sources{grid-column:2}.inventory{grid-template-columns:repeat(3,1fr);row-gap:20px}.inventory div:nth-child(3){border:0}.filters{flex-wrap:wrap}.search-field{flex-basis:100%}.filter-field:not(.search-field){flex:1}.services{grid-template-columns:repeat(2,1fr)}}
@media(max-width:640px){.wrap{width:calc(100% - 32px)}.topbar{padding:18px 0;flex-wrap:wrap;gap:8px}.topbar-label{display:none}.hero{padding:32px 0 26px}.hero-copy{font-size:15px}.section-nav{gap:12px 20px}.snapshot{gap:5px 16px}.snapshot strong{font-size:13px}.notice{padding:15px;margin-top:20px}.notice p{font-size:13px}.finance-grid{gap:10px}.metric{padding:16px}.metric-value{font-size:20px}.metric-label{margin-bottom:10px;font-size:12px}.metric-note{font-size:11px}.inventory{gap:14px}.inventory dd{font-size:23px}.inventory dt{font-size:11px}.section-heading{gap:15px}.section-heading h2{font-size:24px}.section-heading p{font-size:14px}.section-number{font-size:10px}.directory,.division-grid{grid-template-columns:1fr}.division-grid{gap:9px}.division-card{padding:13px 15px}.business-card{padding:20px}.business-card h3{font-size:22px}.filters{padding:14px}.filter-field:not(.search-field){flex-basis:calc(50% - 8px);min-width:110px}.filters button{width:100%}.services{grid-template-columns:1fr;padding:20px;gap:18px}.recovery-head{padding:20px}.roadmap summary{padding:17px 20px}.roadmap summary span{display:block;margin:4px 0 0 17px;font-size:12px}.workflow{grid-template-columns:1fr}.workflow>li{padding:18px 20px}.workflow>li::before{float:right;margin:0}.priority{grid-template-columns:1fr;gap:14px;padding:20px}.priority-phase{display:flex;align-items:center;justify-content:space-between;gap:12px}.timeframe{margin:0}.footer-grid{flex-direction:column;gap:16px}.entry-facts{gap:12px}.shared-card{padding:20px}section{padding-top:34px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{body{font-size:10pt;background:white}.wrap{width:100%}.masthead{background:white;color:#132b23;border-bottom:2px solid #126749}.hero{padding:20px 0;grid-template-columns:1fr}.topbar{padding:10px 0;border-color:#cadace}.wordmark,.wordmark span,.topbar-label,.eyebrow,.hero-copy,.snapshot,.snapshot strong,.snapshot .small{color:#172925}.preview-pill{color:#172925;border-color:#77887b}.snapshot{border:0;padding:0}.section-nav,.filters,.filter-count,.skip-link,.empty-result{display:none!important}.finance-grid,.division-grid{grid-template-columns:repeat(2,1fr)}.directory,.shared-grid,.workflow{display:block}.business-card,.shared-card,.workflow>li,.priority{break-inside:avoid;margin-bottom:12px}.business-card[hidden]{display:flex!important}.notice,.metric,.business-card,.division-card,.shared-card,.recovery-head,.roadmap,.workflow>li,.priority{background:white;color:#172925}.shared-card p,.shared-card a,.shared-card .source-date{color:#172925}.shared-card{border:1px solid #cadace}.shared-card .sources{border-color:#cadace}.shared-index{color:#172925}.sources a{color:#172925}.services{grid-template-columns:repeat(2,1fr)}.roadmap>.services{display:grid!important}.roadmap summary{list-style:none}.section-heading{break-after:avoid}.section-heading h2{font-size:20pt}.section-number{color:#172925}.footer{background:white}.inventory dd{font-size:18pt}h1{font-size:32pt}section{padding-top:24px}.metric-value{font-size:18pt}}
"""

_SCRIPT = """
(() => {
  const filters = document.getElementById('directory-filters');
  const search = document.getElementById('directory-search');
  const division = document.getElementById('division-filter');
  const kind = document.getElementById('kind-filter');
  const count = document.getElementById('directory-count');
  const empty = document.getElementById('empty-result');
  const cards = Array.from(document.querySelectorAll('.business-card'));
  if (!filters || !search || !division || !kind || !count || !empty) return;
  const apply = () => {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    cards.forEach(card => {
      const matches = (!division.value || card.dataset.division === division.value)
        && (!kind.value || card.dataset.kind === kind.value)
        && (!query || (card.dataset.search || '').toLocaleLowerCase().includes(query));
      card.hidden = !matches;
      if (matches) visible += 1;
    });
    count.textContent = `${visible} of ${cards.length} catalog entries shown`;
    empty.hidden = visible !== 0;
  };
  search.addEventListener('input', apply);
  division.addEventListener('change', apply);
  kind.addEventListener('change', apply);
  document.getElementById('clear-filters').addEventListener('click', () => {
    search.value = ''; division.value = ''; kind.value = ''; apply(); search.focus();
  });
  filters.hidden = false;
  apply();
})();
"""


def render_dashboard(view: dict) -> str:
    """Render the sanitized planning view as one self-contained HTML document.

    Monetary and customer metrics cannot be presented as live evidence in this
    preview. Data is escaped for its HTML context; source URLs are separately
    checked before becoming links. Filtering never stores or transmits input.
    """
    if not isinstance(view, dict) or view.get("mode") != "PLANNING_PREVIEW":
        raise ValueError("the HTML export accepts PLANNING_PREVIEW only")
    metrics = view.get("financial_metrics", {})
    if not isinstance(metrics, Mapping) or any(metrics.get(key) is not None for key in _FINANCIAL_KEYS):
        raise ValueError("planning preview cannot render financial or customer values")
    boundaries = view.get("boundaries", {})
    if not isinstance(boundaries, Mapping) or boundaries.get("live_customer_state") != "NOT_CONNECTED":
        raise ValueError("planning preview cannot export connected private customer state")
    if (
        boundaries.get("legal_identity") != "UNVERIFIED"
        or boundaries.get("public_brand_rollout") != "PLANNED"
        or type(boundaries.get("new_external_spend_cents")) is not int
        or boundaries["new_external_spend_cents"] != 0
    ):
        raise ValueError("planning preview cannot assert legal, brand, or spending authority")

    totals = view["totals"]
    divisions = view["divisions"]
    entries = view["entries"]
    division_names = {str(row["id"]): str(row["name"]) for row in divisions}
    initial = [row for row in view["services"] if row.get("initial_rollout") is True]
    expansion = [row for row in view["services"] if row.get("initial_rollout") is False]

    inventory_labels = (
        ("businesses", "Business records"),
        ("product_families", "Product families"),
        ("ventures", "Venture entries"),
        ("shared_systems", "Shared systems"),
        ("initial_recovery_services", "Initial recovery services"),
        ("expansion_recovery_services", "Expansion services"),
    )
    inventory = "".join(
        f'<div><dt>{_text(label)}</dt><dd>{_count(totals[key])}</dd></div>'
        for key, label in inventory_labels
    )
    metric_cards = "".join(
        '<article class="metric">'
        f'<h3 class="metric-label">{label}</h3><p class="metric-value">Not connected</p>'
        f'<p class="metric-note">{note}</p></article>'
        for label, note in (
            ("Qualified leads", "Requires private customer evidence"),
            ("Paying customers", "Requires verified payment evidence"),
            ("Cash collected", "RETALLY fees, separate from recovered funds"),
            ("Contribution profit", "Requires attributed revenue and costs"),
        )
    )
    division_cards = "".join(
        f'<article class="division-card"><h3>{_text(row["name"])}</h3>'
        f'<p>{_text(row.get("purpose"))}</p></article>' for row in divisions
    )
    division_options = "".join(
        f'<option value="{_text(row["id"])}">{_text(row["name"])}</option>' for row in divisions
    )
    entry_cards = "".join(_entry(entry, division_names) for entry in entries)
    initial_services = "".join(_service(row) for row in initial)
    expansion_services = "".join(_service(row, expansion=True) for row in expansion)
    shared_cards = "".join(
        '<article class="shared-card">'
        f'<span class="shared-index" aria-hidden="true">{index:02d}</span>'
        f'<h3>{_text(row["name"])}</h3><p>{_text(row.get("purpose"))}</p>'
        + _sources(row.get("sources", []))
        + "</article>"
        for index, row in enumerate(view["shared_systems"], 1)
    )
    workflow = "".join(
        f'<li><h3>{_text(row["label"])}</h3>'
        f'<p class="owner">{_text(_label(row.get("owner_role")))}</p><ul class="evidence-list">'
        + "".join(f"<li>{_text(item)}</li>" for item in row.get("required_evidence", []))
        + "</ul></li>"
        for row in view["workflow"]
    )
    priorities = "".join(
        '<li class="priority"><div class="priority-phase">'
        f'<p class="timeframe">{_text(row.get("timeframe"))}</p>'
        f'<span class="status">{_text(_label(row.get("status")))}</span></div><div>'
        f'<h3>{_text(row["title"])}</h3>'
        f'<p class="owner">Owner role: {_text(_label(row.get("owner_role")))}</p>'
        f'<p class="done-when"><strong>Complete when:</strong> {_text(row.get("done_when"))}</p>'
        "</div></li>"
        for row in view["priorities"]
    )

    return "".join((
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta name="referrer" content="no-referrer">',
        '<meta name="color-scheme" content="light">',
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; ',
        "style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; ",
        "img-src 'none'; font-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'\">",
        '<title>', _text(view["title"]), ' — Operating plan</title><style>', _CSS, '</style></head><body>',
        '<a class="skip-link" href="#main">Skip to operating plan</a>',
        '<header class="masthead"><div class="wrap"><div class="topbar">',
        '<div class="wordmark">RET<span>A</span>LLY</div>',
        '<div class="topbar-label">Group operations</div><span class="preview-pill">Planning preview</span>',
        '</div><div class="hero"><div><p class="eyebrow">Business register &amp; operating plan</p><h1>',
        _text(view["title"]), '</h1><p class="hero-copy">Focused businesses. Shared operations. ',
        'A clear next milestone for every part of the portfolio.</p></div><div class="snapshot">',
        '<p class="small">Source snapshot</p><p><strong>', _text(view["as_of"]), '</strong></p>',
        '<p class="small">Catalog version ', _text(view["catalog_version"]), '</p></div></div>',
        '<nav class="section-nav" aria-label="Operating plan sections">',
        '<a href="#directory">Business register</a><a href="#recovery">Recovery services</a>',
        '<a href="#shared">Shared systems</a><a href="#workflow">Customer workflow</a>',
        '<a href="#priorities">Next milestones</a></nav></div></header>',
        '<main id="main" class="wrap"><div class="notice" role="note">',
        '<span class="notice-marker" aria-hidden="true">i</span><div>',
        '<p><strong>Customer and financial systems are not connected.</strong></p>',
        '<p class="muted">This is a planning view. Unknown results remain unverified; ',
        'catalog inclusion does not establish commercial readiness.</p></div></div>',
        '<div class="finance-grid" aria-label="Financial and customer evidence">', metric_cards, '</div>',
        '<dl class="inventory" aria-label="Catalog inventory">', inventory, '</dl>',
        '<p class="inventory-note">Inventory counts describe this catalog, not launched companies ',
        'or paying customers. Recovery offerings belong to one recovery business.</p>',
        '<section id="directory" aria-labelledby="directory-heading"><div class="section-heading">',
        '<div><h2 id="directory-heading">Business register</h2><p>Each offer keeps its customer focus ',
        'and product identity within a shared management structure.</p></div>',
        '<span class="section-number" aria-hidden="true">01 / PORTFOLIO</span></div>',
        '<div class="division-grid">', division_cards, '</div>',
        '<div class="filters" id="directory-filters" hidden><div class="filter-field search-field">',
        '<label for="directory-search">Search the register</label>',
        '<input id="directory-search" type="search" autocomplete="off" placeholder="Name, purpose, or milestone">',
        '</div><div class="filter-field"><label for="division-filter">Division</label>',
        '<select id="division-filter"><option value="">All divisions</option>', division_options, '</select></div>',
        '<div class="filter-field"><label for="kind-filter">Entry type</label>',
        '<select id="kind-filter"><option value="">All types</option><option value="business">Businesses</option>',
        '<option value="product_family">Product families</option><option value="venture">Ventures</option>',
        '</select></div><button type="button" id="clear-filters">Clear filters</button></div>',
        '<p class="filter-count" id="directory-count" role="status" aria-live="polite">',
        _count(len(entries)), ' catalog entries</p><div class="directory">', entry_cards, '</div>',
        '<p class="empty-result" id="empty-result" hidden>No entries match these filters. ',
        'Try another term or clear the filters.</p></section>',
        '<section id="recovery" aria-labelledby="recovery-heading"><div class="section-heading"><div>',
        '<h2 id="recovery-heading">One recovery business, defined services</h2>',
        '<p>Share the evidence and case-management foundation while keeping each service’s ',
        'scope and acceptance requirements explicit.</p></div>',
        '<span class="section-number" aria-hidden="true">02 / RECOVERY</span></div>',
        '<div class="recovery-box"><div class="recovery-head"><h3>', _count(len(initial)),
        ' services in the initial rollout focus</h3><p>Selection establishes priority. ',
        'Customer delivery remains subject to each service’s acceptance requirements.</p></div>',
        '<ul class="services">', initial_services, '</ul><details class="roadmap"><summary>',
        _count(len(expansion)), ' services on the expansion roadmap ',
        '<span>Open to view future coverage</span></summary><ul class="services">',
        expansion_services, '</ul></details></div></section>',
        '<section id="shared" aria-labelledby="shared-heading"><div class="section-heading"><div>',
        '<h2 id="shared-heading">Shared systems</h2><p>Reuse the existing engineering and evidence ',
        'foundations. Each system retains its own authority and release controls.</p></div>',
        '<span class="section-number" aria-hidden="true">03 / OPERATIONS</span></div>',
        '<div class="shared-grid">', shared_cards, '</div></section>',
        '<section id="workflow" aria-labelledby="workflow-heading"><div class="section-heading"><div>',
        '<h2 id="workflow-heading">Common customer workflow</h2>',
        '<p>One engagement structure, with product-specific scope, evidence, and permissions.</p></div>',
        '<span class="section-number" aria-hidden="true">04 / DELIVERY</span></div>',
        '<ol class="workflow">', workflow, '</ol>',
        '<p class="workflow-note">This workflow describes required records. It does not grant ',
        'customer consent, confirm payment, approve a release, or authorize external contact.</p></section>',
        '<section id="priorities" aria-labelledby="priorities-heading"><div class="section-heading"><div>',
        '<h2 id="priorities-heading">Next milestones</h2>',
        '<p>Coordinate work around concrete outcomes and accountable roles.</p></div>',
        '<span class="section-number" aria-hidden="true">05 / EXECUTION</span></div>',
        '<ol class="priorities">', priorities, '</ol></section></main>',
        '<footer class="footer"><div class="wrap footer-grid"><div>',
        '<p><strong>Operating plan only.</strong> Legal identity is unverified; public brand rollout is planned.</p>',
        '<p>Private customer records remain in the authorized operating system. ',
        'No customer information is collected or stored by this page.</p>',
        '<p><strong>$0 in new external spending authorized.</strong> This is a budget constraint, ',
        'not a report of actual costs or revenue.</p></div>',
        '<div class="footer-label">RETALLY GROUP</div></div></footer>',
        '<script>', _SCRIPT, '</script></body></html>',
    ))
