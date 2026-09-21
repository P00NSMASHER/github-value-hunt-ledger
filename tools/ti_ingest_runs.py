#!/usr/bin/env python3
"""Reconcile immutable worker submissions into the append-only search-run ledger.

Only this integrator writes the ledger. Workers publish one uniquely named JSON
object to search_run_spool; search_runs is accepted as a legacy intake directory.
No submitted values are normalized, inferred, upgraded, or removed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys

from ti_common import ROOT, slug


class IntakeError(ValueError):
    pass


def canonical(record):
    return json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise IntakeError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def decode(raw, source):
    def invalid_constant(value):
        raise IntakeError(f"non-finite JSON number {value}")
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise IntakeError("non-finite JSON number")
        return number
    try:
        return json.loads(raw, object_pairs_hook=_pairs, parse_constant=invalid_constant, parse_float=finite_float)
    except (ValueError, UnicodeError) as exc:
        raise IntakeError(f"{source}: {exc}") from exc


def read_json(path):
    return decode(path.read_bytes(), path)


def read_rows(path, raw=None):
    if raw is None:
        raw = path.read_bytes() if path.exists() else b""
    return [decode(line, f"{path}:{n}") for n, line in enumerate(raw.splitlines(), 1) if line.strip()]


def _type_matches(value, kind):
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "integer": lambda: type(value) is int,
        "number": lambda: type(value) is int or (type(value) is float and math.isfinite(value)),
        "boolean": lambda: type(value) is bool,
        "null": lambda: value is None,
    }[kind]()


def check_schema_supported(schema):
    """Bounded, stdlib-only evaluator for the repository's existing schema.

    Fail closed if the schema grows a keyword we do not implement. This is not
    offered as a general JSON Schema implementation.
    """
    supported = {"$schema", "title", "description", "type", "required", "properties",
                 "additionalProperties", "items", "enum", "const", "minimum",
                 "maximum", "minLength", "pattern", "allOf", "if", "then"}
    unsupported = set(schema) - supported
    if unsupported:
        raise IntakeError(f"search_run.schema.json: unsupported schema keywords {sorted(unsupported)}")
    types = schema.get("type", [])
    if isinstance(types, str):
        types = [types]
    if set(types) - {"object", "array", "string", "integer", "number", "boolean", "null"}:
        raise IntakeError("search_run.schema.json: unsupported schema type")
    if not isinstance(schema.get("additionalProperties", True), bool):
        raise IntakeError("search_run.schema.json: additionalProperties must be boolean")
    for child in schema.get("properties", {}).values():
        check_schema_supported(child)
    for key in ("items", "if", "then"):
        if key in schema:
            check_schema_supported(schema[key])
    for child in schema.get("allOf", []):
        check_schema_supported(child)


def validate_shape(value, schema, path="run"):
    kinds = schema.get("type")
    if kinds and not any(_type_matches(value, kind) for kind in ([kinds] if isinstance(kinds, str) else kinds)):
        raise IntakeError(f"{path}: expected {kinds}")
    if "enum" in schema and not any(canonical(value) == canonical(item) for item in schema["enum"]):
        raise IntakeError(f"{path}: value outside allowed enum")
    if "const" in schema and canonical(value) != canonical(schema["const"]):
        raise IntakeError(f"{path}: value differs from required constant")
    if isinstance(value, dict):
        missing = set(schema.get("required", [])) - set(value)
        if missing:
            raise IntakeError(f"{path}: missing {', '.join(sorted(missing))}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise IntakeError(f"{path}: unexpected properties")
        for key, child in properties.items():
            if key in value:
                validate_shape(value[key], child, f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            validate_shape(item, schema["items"], f"{path}[{index}]")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            raise IntakeError(f"{path}: string too short")
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            raise IntakeError(f"{path}: invalid identifier/format")
    if type(value) in (int, float):
        if type(value) is float and not math.isfinite(value):
            raise IntakeError(f"{path}: non-finite number")
        if "minimum" in schema and value < schema["minimum"]:
            raise IntakeError(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise IntakeError(f"{path}: above maximum")
    for child in schema.get("allOf", []):
        validate_shape(value, child, path)
    if "if" in schema:
        try:
            validate_shape(value, schema["if"], path)
        except IntakeError:
            pass
        else:
            if "then" in schema:
                validate_shape(value, schema["then"], path)


def validate_record(record, intel, schema):
    """Check new records against shape and core ti_validate.py invariants.

    Downstream execution/dispatch validators still run after regeneration in CI.
    Exact ledger replays are never reinterpreted under newer schema requirements.
    """
    if "_draft" in record:
        raise IntakeError("incomplete draft: record actual observations and complete review before removing _draft and publishing")
    validate_shape(record, schema)
    version = record.get("schema_version") or 0
    strategies = {r["strategy_id"] for r in read_rows(intel / "search_strategies.jsonl")}
    caps = {r["capability_id"] for r in read_rows(intel / "capabilities.jsonl")}
    objectives = {r["search_objective_id"] for r in read_json(intel / "search_objectives.json").get("objectives", [])}
    reasons = {v for values in read_json(intel / "reason_codes.json").values() for v in values}
    aliases_path = intel / "query_family_aliases.json"
    aliases = read_json(aliases_path) if aliases_path.exists() else {}
    raw_family = "QF:" + (slug(record.get("query_family") or "unknown")[:120] or "unknown")
    expected_family = aliases.get(raw_family, raw_family)
    if record.get("strategy_id") not in strategies:
        raise IntakeError("unknown strategy_id")
    if version >= 3 and record.get("query_family_id") != expected_family:
        raise IntakeError(f"query_family_id drift; expected {expected_family}")
    if version >= 4 and record.get("search_objective_id") not in objectives:
        raise IntakeError("missing/unknown search_objective_id")
    counts = [record.get(k) for k in ("candidate_count", "deep_inspected", "retained_count", "master_promoted_count")]
    for earlier, later in zip(counts, counts[1:]):
        if earlier is not None and later is not None and later > earlier:
            raise IntakeError("counts violate candidate >= inspected >= retained >= promoted")
    cap_refs = record.get("new_capability_ids", []) + record.get("strengthened_capability_ids", [])
    dispositions = set()
    for disposition in record.get("candidate_dispositions", []):
        key = (disposition.get("repository"), disposition.get("revision"))
        if key in dispositions:
            raise IntakeError(f"duplicate candidate disposition {key}")
        dispositions.add(key)
        cap_refs += disposition.get("capability_ids", [])
        if version >= 3 and disposition.get("reason_code_standard") not in reasons:
            raise IntakeError("missing/unknown candidate reason_code_standard")
        if version >= 8:
            profile = disposition.get("repository_profile")
            if not isinstance(profile, dict) or profile.get("metadata_status") not in {"observed", "unavailable"}:
                raise IntakeError("V8 candidate missing repository_profile metadata_status")
    if set(cap_refs) - caps:
        raise IntakeError(f"unknown capabilities {sorted(set(cap_refs) - caps)}")
    if version >= 5:
        mode, ids = record.get("seed_mode"), record.get("seed_ids")
        if mode == "generated" and not ids:
            raise IntakeError("generated seed_mode requires seed_ids")
        if mode == "free_exploration" and ids:
            raise IntakeError("free_exploration cannot claim seed_ids")
    if version >= 8:
        mode, ids = record.get("coverage_mode"), record.get("coverage_gap_ids")
        if mode == "generated" and not ids:
            raise IntakeError("generated coverage_mode requires coverage_gap_ids")
        if mode == "none" and ids:
            raise IntakeError("none coverage_mode cannot claim coverage_gap_ids")
    if record.get("measurement_quality") == "benchmark" and version >= 4:
        sets = {r["evaluation_set_id"]: r for r in read_json(intel / "strategy_evaluation_sets.json").get("sets", [])}
        evaluation = sets.get(record.get("evaluation_set_id"))
        task_ids = record.get("benchmark_task_ids") or []
        if not evaluation or not task_ids or not record.get("comparison_group_id"):
            raise IntakeError("benchmark missing registered evaluation set, tasks, or comparison group")
        if record["strategy_id"] not in evaluation.get("strategy_ids", []):
            raise IntakeError("benchmark strategy not allowed in evaluation set")
        allowed = {str(t).zfill(2) for t in evaluation.get("task_ids", [])}
        if not set(task_ids).issubset(allowed):
            raise IntakeError("benchmark tasks outside evaluation set")


def _run_id(record, source):
    if not isinstance(record, dict) or not isinstance(record.get("search_run_id"), str) or not record["search_run_id"]:
        raise IntakeError(f"{source}: expected object with nonempty search_run_id")
    return record["search_run_id"]


def build_plan(root):
    intel = root / "intelligence"
    ledger = intel / "search_runs.jsonl"
    if ledger.is_symlink():
        raise IntakeError("canonical ledger cannot be a symlink")
    original = ledger.read_bytes() if ledger.exists() else b""
    existing = {}
    for number, record in enumerate(read_rows(ledger, original), 1):
        rid = _run_id(record, f"{ledger}:{number}")
        if rid in existing:
            raise IntakeError(f"canonical ledger contains duplicate search_run_id {rid}")
        existing[rid] = canonical(record)
    report = {"existing_runs": len(existing), "submission_files": 0, "replayed_files": 0,
              "duplicate_submission_files": 0, "pending_runs": 0, "appended_runs": 0,
              "pending_ids": [], "errors": []}
    pending, snapshots = {}, {}
    for folder in (intel / "search_run_spool", intel / "search_runs"):
        if folder.is_symlink():
            raise IntakeError(f"intake directory cannot be a symlink: {folder}")
        for path in sorted(folder.glob("*.json")):
            report["submission_files"] += 1
            relative = str(path.relative_to(root))
            try:
                if path.is_symlink() or not path.is_file():
                    raise IntakeError("submission must be a regular file")
                snapshots[path] = path.read_bytes()
                record = decode(snapshots[path], relative)
                rid = _run_id(record, relative)
                serialized = canonical(record)
                if rid in existing:
                    if existing[rid] != serialized:
                        old = json.loads(existing[rid])
                        changed = sorted(k for k in set(old) | set(record) if k not in old or k not in record or canonical(old[k]) != canonical(record[k]))
                        raise IntakeError(f"conflicting search_run_id {rid}; fields differ: {', '.join(changed)}")
                    report["replayed_files"] += 1
                elif rid in pending:
                    if canonical(pending[rid]) != serialized:
                        raise IntakeError(f"conflicting submissions for search_run_id {rid}")
                    report["duplicate_submission_files"] += 1
                else:
                    pending[rid] = record
            except (IntakeError, OSError) as exc:
                report["errors"].append(f"{relative}: {exc}")
    schema = read_json(intel / "schemas" / "search_run.schema.json")
    check_schema_supported(schema)
    for rid, record in sorted(pending.items()):
        try:
            validate_record(record, intel, schema)
        except (IntakeError, OSError) as exc:
            report["errors"].append(f"{rid}: {exc}")
    report["pending_ids"] = sorted(pending)
    report["pending_runs"] = len(pending)
    report["error_count"] = len(report["errors"])
    report["ledger_sha256"] = hashlib.sha256(original).hexdigest()
    return report, original, pending, snapshots


def ingest(root, write=False):
    intel = root / "intelligence"
    lock = intel / ".search_runs.ingest.lock"
    locked = False
    try:
        if write:
            try:
                lock.mkdir()
                locked = True
            except FileExistsError as exc:
                raise IntakeError(f"ingestion lock exists: {lock}; inspect any active integrator before removing a stale lock") from exc
        report, original, pending, snapshots = build_plan(root)
        if report["errors"] or not write or not pending:
            return report
        for path, content in snapshots.items():
            if not path.is_file() or path.is_symlink() or path.read_bytes() != content:
                raise IntakeError(f"submission changed during ingestion: {path}")
        ledger = intel / "search_runs.jsonl"
        # O_APPEND preserves existing bytes, including concurrent foreign appends;
        # the lock serializes cooperating integrators. Workers must never write it.
        descriptor = os.open(ledger, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            with os.fdopen(descriptor, "a+b", closefd=False) as stream:
                stream.seek(0)
                if stream.read() != original:
                    raise IntakeError("canonical ledger changed during ingestion; retry from current state")
            payload = (b"\n" if original and not original.endswith(b"\n") else b"")
            payload += ("\n".join(canonical(pending[rid]) for rid in sorted(pending)) + "\n").encode("utf-8")
            written = os.write(descriptor, payload)
            if written != len(payload):
                raise IntakeError("short ledger append; source files preserved, inspect ledger before retry")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        report["appended_runs"] = len(pending)
        report["pending_runs"] = 0
        return report
    finally:
        if locked:
            lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="read-only intake audit; pending valid rows are allowed")
    mode.add_argument("--write", action="store_true", help="append all valid pending rows or reject the whole batch")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (default: parent of tools)")
    args = parser.parse_args()
    try:
        report = ingest(args.root.resolve(), write=args.write)
    except (IntakeError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({"errors": [str(exc)], "appended_runs": 0}, indent=2))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
