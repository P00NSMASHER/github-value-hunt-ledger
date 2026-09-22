from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.ti_elite_ingestion import load_registry, ordered_queue, summarize, validate_registry


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "intelligence" / "ELITE_SOURCE_INGESTION.json"


def test_elite_registry_is_valid_and_pinned():
    payload = load_registry(REGISTRY)
    summary = summarize(payload)
    assert summary["sources"] >= 50
    assert summary["p0_open"] > 0
    assert summary["started"] == ["ELITE-037"]
    assert all(len(row["revision"]) == 40 for row in payload["sources"])


def test_queue_starts_with_open_p0_work():
    payload = load_registry(REGISTRY)
    queue = ordered_queue(payload)
    open_p0 = [row for row in queue if row["priority"] == "P0" and row["status"] in {"STARTED", "QUEUED"}]
    assert open_p0
    assert open_p0[0]["status"] == "STARTED"
    assert open_p0[0]["repository"] == "bsaffel/moneybin"


def test_duplicate_pin_fails_closed():
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["sources"].append(dict(payload["sources"][0], source_id="ELITE-999"))
    with pytest.raises(ValueError, match="duplicate repository\+revision pin"):
        validate_registry(payload)


def test_floating_revision_fails_closed():
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    payload["sources"][0]["revision"] = "main"
    with pytest.raises(ValueError, match="exact 40-character revision required"):
        validate_registry(payload)
