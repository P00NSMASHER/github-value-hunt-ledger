#!/usr/bin/env python3
"""Compile an AI Business OS portfolio-plan JSON file into Hunter bridge seeds."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_business_os.hunter_bridge import compile_hunter_seeds


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True, help="Path to a JSON portfolio plan")
    parser.add_argument(
        "--output",
        default="intelligence/business_os_hunter_seeds.jsonl",
        help="Destination JSONL feed",
    )
    args = parser.parse_args()

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    seeds = compile_hunter_seeds(plan)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(json.dumps(seed, sort_keys=True, ensure_ascii=False) + "\n" for seed in seeds)
    output.write_text(text, encoding="utf-8")
    print(json.dumps({"seed_count": len(seeds), "output": str(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
