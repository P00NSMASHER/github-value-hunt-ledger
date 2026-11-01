"""Durable, append-only local experiment receipts with explicit proof boundaries.

Stored hash chains protect accidental changes, not hostile operators able to
rewrite both this database and its hashes. The legacy 26 finding IDs and
production status live in the independently preserved cumulative register.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import re
from typing import Sequence

from freight.lab_assurance import digest


_SHA = re.compile(r"[a-f0-9]{64}\Z")


@dataclass(frozen=True)
class Experiment:
    experiment_id: str
    finding_id: str
    baseline_artifact_sha256: str
    candidate_artifact_sha256: str
    frozen_input_sha256: str
    independent_test_sha256: str
    original_counterexample_reproduced: bool
    repaired_counterexample_rejected: bool
    known_good_control_passed: bool
    measured_runtime_ms: int | None
    execution_scope: str


def _validate(run: Experiment):
    for key in ("experiment_id","finding_id","execution_scope"):
        value=getattr(run,key)
        if type(value) is not str or not value or len(value)>128 or any(ord(x)<32 for x in value):
            raise ValueError("invalid "+key)
    for key in ("baseline_artifact_sha256","candidate_artifact_sha256","frozen_input_sha256","independent_test_sha256"):
        value=getattr(run,key)
        if type(value) is not str or _SHA.fullmatch(value) is None:
            raise ValueError("invalid "+key)
    for key in ("original_counterexample_reproduced","repaired_counterexample_rejected","known_good_control_passed"):
        if type(getattr(run,key)) is not bool:
            raise ValueError("invalid "+key)
    if run.measured_runtime_ms is not None and (type(run.measured_runtime_ms) is not int or run.measured_runtime_ms<0):
        raise ValueError("runtime must be measured nonnegative milliseconds")
    if run.execution_scope not in {"SYNTHETIC_OFFLINE","REAL_CODE_MOCKED_PROVIDERS","HOSTED_ISOLATED_STAGING"}:
        raise ValueError("unsupported experiment scope")


def verdict(run: Experiment) -> str:
    _validate(run)
    if run.original_counterexample_reproduced and run.repaired_counterexample_rejected and run.known_good_control_passed:
        return "REPAIR_DEMONSTRATED_IN_STATED_TEST_SCOPE_ONLY"
    if run.original_counterexample_reproduced and not run.repaired_counterexample_rejected:
        return "DEFECT_STILL_REPRODUCED"
    return "INCONCLUSIVE"



_EXPERIMENT_KEYS = frozenset(f.name for f in fields(Experiment))
_RECORD_KEYS = _EXPERIMENT_KEYS | {"verdict"}


def _verify_records(con: sqlite3.Connection) -> list[dict]:
    """Re-derive semantics from persisted experiment fields, not a stored label.

    SQLite digest chains are local consistency checks and cannot defend against
    a hostile writer that controls this code and database simultaneously.
    """
    out: list[dict] = []
    previous: str | None = None
    expected_sequence = 1
    rows = con.execute(
        "SELECT sequence,experiment_id,finding_id,receipt_json,"
        "predecessor_sha256,receipt_sha256 FROM experiments ORDER BY sequence"
    )
    for row in rows:
        if type(row["sequence"]) is not int or row["sequence"] != expected_sequence:
            raise ValueError("M40_EXPERIMENT_SEQUENCE_GAP_OR_DELETION")
        try:
            record = json.loads(row["receipt_json"])
        except (TypeError, ValueError) as exc:
            raise ValueError("M40_EXPERIMENT_RECEIPT_INVALID_JSON") from exc
        if type(record) is not dict or set(record) != _RECORD_KEYS:
            raise ValueError("M40_EXPERIMENT_RECEIPT_SCHEMA_CHANGED")
        run = Experiment(**{f: record[f] for f in _EXPERIMENT_KEYS})
        _validate(run)
        if row["experiment_id"] != run.experiment_id or row["finding_id"] != run.finding_id:
            raise ValueError("M40_EXPERIMENT_ROW_IDENTITY_MISMATCH")
        if record["verdict"] != verdict(run):
            raise ValueError("M40_EXPERIMENT_VERDICT_NOT_DERIVED_FROM_FLAGS")
        if row["predecessor_sha256"] != previous:
            raise ValueError("M40_EXPERIMENT_CHAIN_PREDECESSOR_MISMATCH")
        h = digest({"previous": previous, "receipt": record})
        if row["receipt_sha256"] != h:
            raise ValueError("M40_EXPERIMENT_RECEIPT_DIGEST_CHANGED")
        previous = h
        expected_sequence += 1
        out.append({
            "experiment_id": run.experiment_id,
            "finding_id": run.finding_id,
            "verdict": record["verdict"],
            "receipt_sha256": h,
            "scope": run.execution_scope,
        })
    return out


class ExperimentLedger:
    def __init__(self, db_path: str | Path):
        self.path=Path(db_path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(self._connect()) as con, con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS experiments (
                  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                  experiment_id TEXT NOT NULL UNIQUE,
                  finding_id TEXT NOT NULL,
                  receipt_json TEXT NOT NULL,
                  predecessor_sha256 TEXT,
                  receipt_sha256 TEXT NOT NULL UNIQUE
                );
                CREATE TRIGGER IF NOT EXISTS no_experiment_update
                  BEFORE UPDATE ON experiments BEGIN
                  SELECT RAISE(ABORT,'experiments are append-only'); END;
                CREATE TRIGGER IF NOT EXISTS no_experiment_delete
                  BEFORE DELETE ON experiments BEGIN
                  SELECT RAISE(ABORT,'experiments are append-only'); END;
            """)

    def _connect(self):
        con=sqlite3.connect(self.path,timeout=5)
        con.row_factory=sqlite3.Row
        return con

    def append(self,run:Experiment) -> tuple[bool,str]:
        _validate(run)
        record=asdict(run)
        record["verdict"]=verdict(run)
        from contextlib import closing
        with closing(self._connect()) as con, con:
            con.execute("BEGIN IMMEDIATE")
            _verify_records(con)  # Never append or replay over corrupt prior evidence.
            existing=con.execute("SELECT receipt_json,receipt_sha256 FROM experiments WHERE experiment_id=?",
                                 (run.experiment_id,)).fetchone()
            if existing:
                old=json.loads(existing["receipt_json"])
                if old!=record:
                    raise ValueError("experiment ID replay conflicts with prior immutable receipt")
                return False,existing["receipt_sha256"]
            previous=con.execute("SELECT receipt_sha256 FROM experiments ORDER BY sequence DESC LIMIT 1").fetchone()
            prior=previous["receipt_sha256"] if previous else None
            sha=digest({"previous":prior,"receipt":record})
            con.execute("INSERT INTO experiments(experiment_id,finding_id,receipt_json,predecessor_sha256,receipt_sha256) VALUES (?,?,?,?,?)",
                        (run.experiment_id,run.finding_id,json.dumps(record,sort_keys=True),prior,sha))
            return True,sha

    def read_and_verify(self) -> list[dict]:
        with closing(self._connect()) as con:
            return _verify_records(con)
