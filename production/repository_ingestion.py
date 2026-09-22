"""Deterministic elite-repository ingestion queue.

This module converts the existing Markdown hunt ledger into an auditable,
machine-readable queue. It never fetches or executes third-party code and it
never promotes a repository merely because it is queued.

Authority order:
1. existing ledger evidence (MASTER + hunters/*.md)
2. existing structured capability registry
3. later frozen source-ingestion packet + independent verification

A queued record is research intake only.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Iterable

REPO_RE = re.compile(r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")
URL_RE = re.compile(r"https://github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)")
REVISION_PATTERNS = (
    re.compile(r"^- Exact commit / revision:\s*`?(?P<v>[^`\n]+)`?\s*$", re.M),
    re.compile(r"^- Exact revision:\s*`?(?P<v>[^`\n]+)`?\s*$", re.M),
    re.compile(r"^- Revision:\s*`?(?P<v>[^`\n.]+)`?\.??\s*$", re.M),
)
SCORE_PATTERNS = (
    re.compile(r"^- Value score:\s*(?P<v>.+)$", re.M),
    re.compile(r"^- Scores?:\s*(?P<v>.+)$", re.M),
)
STATUS_RE = re.compile(r"^- Status:\s*(?P<v>.+)$", re.M)
TOTAL_SCORE_RE = re.compile(r"(?P<n>\d{2})/30")
HEADING_RE = re.compile(r"^###\s+(?P<title>.+)$", re.M)


@dataclass(frozen=True)
class RepositoryIntake:
    repository: str
    revision: str | None
    ledger_score: int | None
    source_files: tuple[str, ...]
    source_sections: tuple[str, ...]
    master_present: bool
    capability_ids: tuple[str, ...]
    ingestion_priority: str
    structural_state: str
    next_stage: str
    record_sha256: str = ""

    def with_hash(self) -> "RepositoryIntake":
        payload = asdict(self)
        payload["record_sha256"] = ""
        digest = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return RepositoryIntake(**{**payload, "record_sha256": digest})


def _sections(text: str) -> Iterable[tuple[str, str]]:
    matches = list(HEADING_RE.finditer(text))
    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        yield match.group("title").strip(), text[start:end]


def _repo_from_section(title: str, section: str) -> str | None:
    url = URL_RE.search(section)
    if url:
        return url.group("repo").rstrip(").,;")
    heading = REPO_RE.search(title)
    if heading:
        return heading.group("repo").rstrip(").,;")
    return None


def _revision(section: str) -> str | None:
    for pattern in REVISION_PATTERNS:
        match = pattern.search(section)
        if match:
            value = match.group("v").strip().strip("`")
            return value or None
    return None


def _score(title: str, section: str) -> int | None:
    for pattern in SCORE_PATTERNS:
        match = pattern.search(section)
        if match:
            total = TOTAL_SCORE_RE.search(match.group("v"))
            if total:
                return int(total.group("n"))
    total = TOTAL_SCORE_RE.search(title)
    return int(total.group("n")) if total else None


def _status(section: str) -> str:
    match = STATUS_RE.search(section)
    return match.group("v").strip() if match else ""


def _elite(title: str, section: str, score: int | None, *, master: bool) -> bool:
    if master:
        return True
    if score is not None and score >= 25:
        return True
    marker = f"{title} {_status(section)}"
    return bool(re.search(r"MASTER\s+(?:contender|referral)", marker, re.I))


def _load_capability_links(root: Path) -> dict[str, set[str]]:
    links: dict[str, set[str]] = {}
    path = root / "intelligence" / "capabilities.jsonl"
    if not path.exists():
        return links
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        obj = json.loads(raw)
        cid = obj.get("capability_id")
        if not cid:
            continue
        haystack = json.dumps(obj, sort_keys=True)
        for repo in set(REPO_RE.findall(haystack)):
            links.setdefault(repo, set()).add(cid)
    return links


def _priority(score: int | None, master: bool) -> str:
    if score is not None and score >= 29:
        return "P0"
    if master or (score is not None and score >= 28):
        return "P1"
    return "P2"


def build_repository_intake(root: Path) -> list[RepositoryIntake]:
    capability_links = _load_capability_links(root)
    merged: dict[tuple[str, str | None], dict] = {}

    sources: list[tuple[Path, bool]] = [(root / "MASTER.md", True)]
    sources.extend((path, False) for path in sorted((root / "hunters").glob("[0-9][0-9].md")))

    for path, master in sources:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for title, section in _sections(text):
            repo = _repo_from_section(title, section)
            if not repo:
                continue
            score = _score(title, section)
            if not _elite(title, section, score, master=master):
                continue
            rev = _revision(section)
            key = (repo, rev)
            row = merged.setdefault(
                key,
                {
                    "repository": repo,
                    "revision": rev,
                    "ledger_score": score,
                    "source_files": set(),
                    "source_sections": set(),
                    "master_present": False,
                },
            )
            if score is not None:
                row["ledger_score"] = max(score, row["ledger_score"] or score)
            row["source_files"].add(str(path.relative_to(root)))
            row["source_sections"].add(title)
            row["master_present"] = row["master_present"] or master

    records: list[RepositoryIntake] = []
    for row in merged.values():
        caps = tuple(sorted(capability_links.get(row["repository"], set())))
        master = bool(row["master_present"])
        structural_state = "CAPABILITY_LINKED" if caps else (
            "MASTER_UNMAPPED" if master else "ELITE_CATALOG_UNMAPPED"
        )
        next_stage = (
            "FREEZE_SOURCE_INGESTION_PACKET"
            if caps
            else "CAPABILITY_LINK_REVIEW_THEN_FREEZE_SOURCE_PACKET"
        )
        records.append(
            RepositoryIntake(
                repository=row["repository"],
                revision=row["revision"],
                ledger_score=row["ledger_score"],
                source_files=tuple(sorted(row["source_files"])),
                source_sections=tuple(sorted(row["source_sections"])),
                master_present=master,
                capability_ids=caps,
                ingestion_priority=_priority(row["ledger_score"], master),
                structural_state=structural_state,
                next_stage=next_stage,
            ).with_hash()
        )

    return sorted(
        records,
        key=lambda r: (
            {"P0": 0, "P1": 1, "P2": 2}[r.ingestion_priority],
            -(r.ledger_score or 0),
            r.repository.lower(),
            r.revision or "",
        ),
    )


def render_json(records: list[RepositoryIntake], root: Path) -> dict:
    payload = {
        "schema_version": 1,
        "policy_effect": "none",
        "activates_work": False,
        "meaning": (
            "Research intake queue only. Presence does not mean source code was copied, "
            "executed, verified, deployed, or globally promoted."
        ),
        "source_authority": [
            "MASTER.md",
            "hunters/*.md",
            "intelligence/capabilities.jsonl",
        ],
        "counts": {
            "records": len(records),
            "p0": sum(r.ingestion_priority == "P0" for r in records),
            "p1": sum(r.ingestion_priority == "P1" for r in records),
            "p2": sum(r.ingestion_priority == "P2" for r in records),
            "capability_linked": sum(r.structural_state == "CAPABILITY_LINKED" for r in records),
            "unmapped": sum(r.structural_state != "CAPABILITY_LINKED" for r in records),
        },
        "records": [asdict(r) for r in records],
    }
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["queue_sha256"] = sha256(stable).hexdigest()
    return payload


def render_markdown(payload: dict) -> str:
    counts = payload["counts"]
    lines = [
        "# Repository Ingestion Queue",
        "",
        "Generated from the existing elite hunt ledger. This queue is non-activating.",
        "Queued != copied, executed, verified, deployed, or promoted.",
        "",
        f"- Queue SHA-256: `{payload['queue_sha256']}`",
        f"- Records: **{counts['records']}**",
        f"- P0 / P1 / P2: **{counts['p0']} / {counts['p1']} / {counts['p2']}**",
        f"- Capability-linked: **{counts['capability_linked']}**",
        f"- Structurally unmapped: **{counts['unmapped']}**",
        "",
        "| Priority | Repository | Revision | Score | State | Capabilities |",
        "|---|---|---|---:|---|---|",
    ]
    for row in payload["records"]:
        caps = ", ".join(row["capability_ids"]) or "—"
        lines.append(
            f"| {row['ingestion_priority']} | `{row['repository']}` | "
            f"`{row['revision'] or 'UNKNOWN'}` | {row['ledger_score'] or '—'} | "
            f"{row['structural_state']} | {caps} |"
        )
    lines += [
        "",
        "## Required next stage",
        "",
        "A source-ingestion packet must freeze exact revision, selected source/test/schema evidence, "
        "artifact hashes, intended capability role, third-party dependency caveats, and an independent "
        "verification plan. Untrusted repository code remains non-executable outside the existing sandbox boundary.",
    ]
    return "\n".join(lines) + "\n"
