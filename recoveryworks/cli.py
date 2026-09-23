"""CLI for running Recovery Scan 360 against local/private source exports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from .private_io import atomic_private_write
from .runner import run_scan360_config


def _read_config(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read config {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("scan config must be a JSON object")
    return payload


def write_private_json(path: Path, payload: Mapping[str, Any]) -> None:
    raw = (
        json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=True)
        + "\n"
    ).encode("utf-8")
    atomic_private_write(path, raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="recoveryworks-scan360",
        description="Run AP/Utility Recovery Scan 360 into private durable state.",
    )
    parser.add_argument("--config", required=True, help="Scan 360 JSON config")
    parser.add_argument("--state", required=True, help="Private durable ledger bundle path")
    parser.add_argument("--report", required=True, help="Private report JSON output path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config_path = Path(args.config).resolve()
    config = _read_config(config_path)
    result = run_scan360_config(
        config,
        state_path=Path(args.state),
        base_dir=config_path.parent,
    )
    write_private_json(Path(args.report), result.as_dict())
    print(
        f"Recovery Scan 360 complete: client={result.client_id} "
        f"new_findings={len(result.added_finding_ids)} "
        f"exceptions={len(result.exceptions)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
