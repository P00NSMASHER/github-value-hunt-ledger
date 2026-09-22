#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from production.repository_ingestion import build_repository_intake, render_json, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--json-out", default="intelligence/REPOSITORY_INGESTION_QUEUE.json")
    parser.add_argument("--md-out", default="intelligence/REPOSITORY_INGESTION_QUEUE.md")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    records = build_repository_intake(root)
    payload = render_json(records, root)
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    md_text = render_markdown(payload)

    json_path = root / args.json_out
    md_path = root / args.md_out

    if args.check:
        ok = json_path.exists() and md_path.exists()
        ok = ok and json_path.read_text(encoding="utf-8") == json_text
        ok = ok and md_path.read_text(encoding="utf-8") == md_text
        return 0 if ok else 1

    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json_text, encoding="utf-8")
    md_path.write_text(md_text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
