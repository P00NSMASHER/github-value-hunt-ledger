#!/usr/bin/env python3
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTEL = ROOT / "intelligence"

def slug(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")

def load_jsonl(name):
    path = INTEL / name
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out

def write_jsonl(name, rows):
    path = INTEL / name
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(x, sort_keys=False, ensure_ascii=False) for x in rows)
    path.write_text(text + ("\n" if rows else ""), encoding="utf-8")

def _field(block, label):
    m = re.search(r"^-\s*" + re.escape(label) + r":\s*(.*)$", block, re.I | re.M)
    return m.group(1).strip() if m else None

def _list_field(block, label):
    value = _field(block, label)
    if not value:
        return []
    return [x.strip().strip(chr(96)) for x in re.split(r";\s*|,\s*(?=[A-Za-z0-9])", value) if x.strip()]

def parse_capabilities():
    text = (ROOT / "CAPABILITIES.md").read_text(encoding="utf-8")
    matches = list(re.finditer(r"^###\s+(CAP-\d+)\s+—\s+(.+)$", text, re.M))
    out = []

    def semantic_list(value):
        if not value:
            return []
        parts = re.split(r";\s*|\s+\+\s+|,\s+(?=[A-Za-z0-9])", value)
        cleaned = []
        for part in parts:
            part = part.strip().strip(chr(96)).strip("*").strip()
            if part and part not in cleaned:
                cleaned.append(part)
        return cleaned

    for i, m in enumerate(matches):
        block = text[m.end(): matches[i+1].start() if i + 1 < len(matches) else len(text)]

        compact = re.search(r"^-\s*Ability/maturity:\s*\*\*([^*]+)\*\*\s*—\s*(.*)$", block, re.I | re.M)
        if compact:
            maturity = compact.group(1).strip()
            ability = compact.group(2).strip()
            evidence = _field(block, "Evidence")
            target_text = _field(block, "Targets") or _field(block, "Target")
            limitation_next = _field(block, "Limitation/next test")
            limitation = None
            next_test = None
            if limitation_next:
                pieces = limitation_next.split(";", 1)
                limitation = pieces[0].strip()
                next_test = pieces[1].strip() if len(pieces) > 1 else limitation_next.strip()
            components = semantic_list(evidence)
            targets = semantic_list(target_text)
            missing_piece = limitation
        else:
            maturity = _field(block, "Maturity")
            ability = _field(block, "Ability")
            evidence = _field(block, "Evidence basis")
            components = _list_field(block, "Primary components")
            targets = _list_field(block, "Reusable targets")
            limitation = _field(block, "Limitation")
            missing_piece = _field(block, "Missing piece")
            next_test = _field(block, "Next test")

        state = "watch"
        if maturity:
            upper = maturity.upper()
            if "PROVEN" in upper:
                state = "runtime_or_stack_proven"
            elif "BENCHMARK" in upper:
                state = "benchmarked"
            elif "VALIDATED" in upper:
                state = "source_or_test_validated"

        out.append({
            "capability_id": m.group(1),
            "name": m.group(2).strip(),
            "ability": ability,
            "maturity": maturity,
            "evidence_basis": evidence,
            "primary_components": components,
            "reusable_targets": targets,
            "limitation": limitation,
            "missing_piece": missing_piece,
            "next_falsifiable_test": next_test,
            "evidence_state": state,
            "confidence": "medium",
            "source_markdown": "CAPABILITIES.md",
            "last_updated": "2026-09-20"
        })
    return out

def _section_list(block, start_label, end_labels):
    start = re.search(r"^-\s*" + re.escape(start_label) + r":\s*(.*)$", block, re.I | re.M)
    if not start:
        return []
    first = start.group(1).strip()
    tail = block[start.end():]
    stop = len(tail)
    for label in end_labels:
        x = re.search(r"^-\s*" + re.escape(label) + r":", tail, re.I | re.M)
        if x:
            stop = min(stop, x.start())
    raw = ([first] if first else []) + tail[:stop].splitlines()
    vals = []
    for line in raw:
        line = re.sub(r"^\s*(?:\d+\.|-)\s*", "", line).strip()
        if line:
            vals.append(line)
    return vals

def parse_search_skills():
    text = (ROOT / "SEARCH_SKILLS.md").read_text(encoding="utf-8")
    heads = list(re.finditer(r"^##\s+([^\n]+)$", text, re.M))
    out = []
    skip = {"Skill schema", "Empirical attribution rule"}
    for i, m in enumerate(heads):
        title = m.group(1).strip()
        if title in skip or title == "SEARCH_SKILLS":
            continue
        block = text[m.end(): heads[i+1].start() if i + 1 < len(heads) else len(text)]
        skill_name = _field(block, "SKILL NAME")
        if not skill_name:
            continue
        strategy_id = "STRAT:" + slug(skill_name)
        out.append({
            "strategy_id": strategy_id,
            "name": skill_name,
            "when_to_use": _field(block, "WHEN TO USE"),
            "procedure": _section_list(block, "PROCEDURE", ["WHY IT WORKED", "EXAMPLES", "FAILURE MODES", "NEXT IMPROVEMENT"]),
            "why_it_worked": _field(block, "WHY IT WORKED"),
            "examples": _section_list(block, "EXAMPLES", ["FAILURE MODES", "NEXT IMPROVEMENT"]),
            "failure_modes": _section_list(block, "FAILURE MODES", ["NEXT IMPROVEMENT"]),
            "next_improvement": _field(block, "NEXT IMPROVEMENT"),
            "status": "active",
            "source_markdown": "SEARCH_SKILLS.md"
        })
    return out

def parse_hunter_records(include_archive=True):
    files = sorted((ROOT / "hunters").glob("**/*.md"))
    if not include_archive:
        files = [p for p in files if "archive" not in p.parts]
    out = []
    heading = re.compile(r"^###\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:\s+—\s+(.+))?\s*$")
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for i, line in enumerate(lines):
            m = heading.match(line)
            if not m:
                continue
            buf = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith("### ") and not lines[j].startswith("## "):
                buf.append(lines[j]); j += 1
            block = "\n".join(buf)
            def pick(patterns):
                for p in patterns:
                    x = re.search(p, block, re.I | re.M)
                    if x:
                        return x.group(1).strip().strip(chr(96))
                return None
            revision = pick([
                r"^-\s*Exact commit / revision:\s*([^\n]+)",
                r"^-\s*Exact inspected revision:\s*([^\n]+)",
                r"^-\s*Exact revision:\s*([^\n]+)",
                r"^-\s*Commit:\s*([^\n]+)",
                r"^-\s*Revision:\s*([^\n]+)"
            ])
            if revision and not re.fullmatch(r"[0-9a-f]{7,40}", revision, re.I):
                hm = re.search(r"[0-9a-f]{7,40}", revision, re.I)
                revision = hm.group(0) if hm else revision[:80]
            rel = str(path.relative_to(ROOT))
            state = "archive" if "archive" in path.parts else ("pending" if "pending" in path.parts else "current")
            out.append({
                "repository": m.group(1),
                "revision": revision,
                "title_suffix": m.group(2),
                "date_seen": pick([r"^-\s*Date inspected:\s*([^\n]+)", r"^-\s*Date discovered:\s*([^\n]+)"]),
                "status": pick([r"^-\s*Status:\s*\**([^\n]+)"]),
                "category": pick([r"^-\s*Category:\s*\**([^\n]+)"]),
                "score_text": pick([r"^-\s*(?:Value score|Score):\s*\**([^\n]+)"]),
                "capability_summary": pick([r"^-\s*(?:What it contains|Concrete capability):\s*([^\n]+)"]),
                "value_summary": pick([r"^-\s*(?:Why it matters|Rare or undernoticed value|Why it wins):\s*([^\n]+)"]),
                "source_catalog": rel,
                "source_state": state
            })
    return out

def status_bucket(status):
    s = (status or "").lower()
    if "quarant" in s or "safety" in s:
        return "quarantined"
    if "reject" in s or "deprior" in s:
        return "rejected"
    if "strong" in s:
        return "strong"
    if "master" in s or "elite" in s:
        if any(word in s for word in ("contender", "referral", "candidate", "watch")):
            return "watch"
        return "master"
    if "watch" in s:
        return "watch"
    return "unknown"

def normalize_run_time(run):
    return run.get("timestamp") or run.get("date")
