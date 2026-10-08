"""Durable, append-only local experiment receipts with explicit proof boundaries.

Stored hash chains protect accidental changes, not hostile operators able to
rewrite both this database and its hashes. The legacy 26 finding IDs and
production status live in the independently preserved cumulative register.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
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
    source_head_sha: str
    candidate_head_sha: str
    frozen_input_sha256: str
    independent_test_sha256: str
    original_counterexample_reproduced: bool
    repaired_counterexample_rejected: bool
    known_good_control_passed: bool
    measured_runtime_ms: int
    execution_scope: str


def _validate(run: Experiment):
    for key in ("experiment_id","finding_id","execution_scope"):
        value=getattr(run,key)
        if type(value) is not str or not value or len(value)>128 or any(ord(x)<32 for x in value):
            raise ValueError("invalid "+key)
    for key in ("source_head_sha","candidate_head_sha","frozen_input_sha256","independent_test_sha256"):
        value=getattr(run,key)
        if type(value) is not str or _SHA.fullmatch(value) is None:
            raise ValueError("invalid "+key)
    for key in ("original_counterexample_reproduced","repaired_counterexample_rejected","known_good_control_passed"):
        if type(getattr(run,key)) is not bool:
            raise ValueError("invalid "+key)
    if type(run.measured_runtime_ms) is not int or run.measured_runtime_ms<0:
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
        from contextlib import closing
        out=[];previous=None
        with closing(self._connect()) as con:
            for row in con.execute("SELECT * FROM experiments ORDER BY sequence"):
                record=json.loads(row["receipt_json"])
                if row["predecessor_sha256"]!=previous:
                    raise ValueError("experiment receipt chain gap")
                expected=digest({"previous":previous,"receipt":record})
                if expected!=row["receipt_sha256"]:
                    raise ValueError("experiment receipt hash mismatch")
                previous=expected
                out.append({"experiment_id":row["experiment_id"],"finding_id":row["finding_id"],
                            "verdict":record["verdict"],"receipt_sha256":expected,
                            "scope":record["execution_scope"]})
        return out
