from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal


SourceState = Literal["PRESENT", "VERIFIED_EMPTY", "UNAVAILABLE"]
ProbeResult = Literal["APPLIED", "NOT_APPLIED", "UNKNOWN"]


class AuthorityError(RuntimeError):
    pass


class CapacityError(AuthorityError):
    pass


class IdentityError(AuthorityError):
    pass


class StaleWorkerError(AuthorityError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_hash(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class ProviderOutcomeReceipt:
    """Evidence-bound provider outcome; naked provider status strings are insufficient."""

    logical_effect_id: str
    provider_operation_id: str
    provider: str
    raw_status: str
    phase: Literal["PRE_APPLY", "APPLY_OR_LATER", "POST_APPLY", "COMPLETE", "UNKNOWN"]
    terminal: bool
    effect_scope: Literal["EXACT_SINGLE_EFFECT", "BATCH_OR_UNKNOWN"]
    partial_effect_possible: bool
    operation_identity_matches: bool
    economic_fingerprint_matches: bool = False

    def classify(self, *, expected_logical_effect_id: str) -> ProbeResult:
        exact_identity = (
            bool(self.provider_operation_id.strip())
            and self.operation_identity_matches
            and self.logical_effect_id == expected_logical_effect_id
        )
        exact_scope = self.effect_scope == "EXACT_SINGLE_EFFECT"
        if not exact_identity or not self.terminal or not exact_scope:
            return "UNKNOWN"
        if (
            self.phase == "PRE_APPLY"
            and self.raw_status == "PreProcessingError"
            and not self.partial_effect_possible
        ):
            return "NOT_APPLIED"
        if (
            self.phase == "COMPLETE"
            and self.raw_status == "Processed"
            and not self.partial_effect_possible
            and self.economic_fingerprint_matches
        ):
            return "APPLIED"
        return "UNKNOWN"


class DynamicsRecurringOutcomePolicy:
    """Normalize documented Dynamics recurring-integration status semantics."""

    @staticmethod
    def receipt(
        *,
        logical_effect_id: str,
        provider_operation_id: str,
        message_status: str,
        exact_single_effect: bool,
        operation_identity_matches: bool,
        economic_fingerprint_matches: bool = False,
    ) -> ProviderOutcomeReceipt:
        phase_by_status = {
            "Preprocessing": "PRE_APPLY",
            "PreProcessingError": "PRE_APPLY",
            "Processing": "APPLY_OR_LATER",
            "ProcessedWithErrors": "APPLY_OR_LATER",
            "PostProcessingFailed": "POST_APPLY",
            "Processed": "COMPLETE",
        }
        terminal = message_status in {
            "PreProcessingError",
            "ProcessedWithErrors",
            "PostProcessingFailed",
            "Processed",
        }
        partial_effect_possible = message_status in {
            "Processing",
            "ProcessedWithErrors",
            "PostProcessingFailed",
        }
        return ProviderOutcomeReceipt(
            logical_effect_id=logical_effect_id,
            provider_operation_id=provider_operation_id,
            provider="MICROSOFT_DYNAMICS_365_FO_RECURRING_INTEGRATION",
            raw_status=message_status,
            phase=phase_by_status.get(message_status, "UNKNOWN"),
            terminal=terminal,
            effect_scope="EXACT_SINGLE_EFFECT" if exact_single_effect else "BATCH_OR_UNKNOWN",
            partial_effect_possible=partial_effect_possible,
            operation_identity_matches=operation_identity_matches,
            economic_fingerprint_matches=economic_fingerprint_matches,
        )


@dataclass(frozen=True)
class Balance:
    authority_qty: int
    authority_amount: int
    invoiced_qty: int
    invoiced_amount: int

    @property
    def available_qty(self) -> int:
        return self.authority_qty - self.invoiced_qty

    @property
    def available_amount(self) -> int:
        return self.authority_amount - self.invoiced_amount


class ReceiptAuthorityPolicy:
    """Receipt authority and source health are deliberately separate dimensions."""

    @staticmethod
    def decide(
        *,
        line_type: str,
        evidence_kind: str | None,
        source_state: SourceState,
        direct_invoice_allowed: bool = False,
    ) -> str:
        if direct_invoice_allowed:
            return "ALLOW_DIRECT"
        if source_state == "UNAVAILABLE":
            return "REVIEW_SOURCE_UNAVAILABLE"
        expected = "SERVICE_ENTRY" if line_type == "SERVICE" else "GOODS_RECEIPT"
        if source_state == "VERIFIED_EMPTY":
            return f"REJECT_MISSING_{expected}"
        if evidence_kind == expected:
            return "ALLOW"
        return f"REJECT_WRONG_AUTHORITY_EXPECTED_{expected}"

    @staticmethod
    def missing_receipt_assertion(
        *, source_state: SourceState, candidate_amount: int
    ) -> tuple[int, str]:
        if source_state == "VERIFIED_EMPTY":
            return candidate_amount, "ASSERTABLE_EXCEPTION"
        if source_state == "UNAVAILABLE":
            return 0, "REVIEW_SOURCE_UNAVAILABLE"
        return 0, "NO_EXCEPTION"


class IdentityRegistry:
    """Bitemporal, reviewed identity decisions. NON_MATCH is a hard blocker."""

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.execute(
            """
            CREATE TABLE IF NOT EXISTS identity_decisions(
              id INTEGER PRIMARY KEY,
              external_id TEXT NOT NULL,
              canonical_id TEXT NOT NULL,
              disposition TEXT NOT NULL CHECK(disposition IN ('MATCH','NON_MATCH')),
              valid_at TEXT NOT NULL,
              observed_at TEXT NOT NULL
            )
            """
        )

    def record(
        self,
        external_id: str,
        canonical_id: str,
        disposition: Literal["MATCH", "NON_MATCH"],
        *,
        valid_at: str,
        observed_at: str,
    ) -> None:
        self.db.execute(
            "INSERT INTO identity_decisions(external_id,canonical_id,disposition,valid_at,observed_at) VALUES(?,?,?,?,?)",
            (external_id, canonical_id, disposition, valid_at, observed_at),
        )
        self.db.commit()

    def resolve(self, external_id: str, *, valid_at: str, observed_at: str) -> str:
        rows = self.db.execute(
            """
            SELECT canonical_id, disposition FROM identity_decisions
            WHERE external_id=? AND valid_at<=? AND observed_at<=?
            ORDER BY observed_at, id
            """,
            (external_id, valid_at, observed_at),
        ).fetchall()
        state: dict[str, str] = {}
        for canonical_id, disposition in rows:
            state[canonical_id] = disposition
        matches = [key for key, value in state.items() if value == "MATCH"]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise IdentityError("NO_REVIEWED_MATCH")
        raise IdentityError("AMBIGUOUS_REVIEWED_MATCH")

    @staticmethod
    def assign_same_sku(candidates: Iterable[str]) -> str:
        unique = sorted(set(candidates))
        if len(unique) != 1:
            raise IdentityError("SAME_SKU_DOES_NOT_ESTABLISH_LINE_OWNERSHIP")
        return unique[0]


class AuthorityLedger:
    """SQLite event ledger using integer quantity atoms and integer currency minor units."""

    POSITIVE = {"RECEIPT", "SERVICE_ENTRY", "DIRECT_AUTH", "RERECEIPT"}
    NEGATIVE = {"REJECT", "REFUNDING_RETURN"}

    def __init__(self, path: str | Path):
        self.path = str(path)
        self.db = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self._schema()
        self.identity = IdentityRegistry(self.db)

    def close(self) -> None:
        self.db.close()

    def _schema(self) -> None:
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY,
              event_key TEXT NOT NULL UNIQUE,
              line_id TEXT NOT NULL,
              allocation_id TEXT,
              kind TEXT NOT NULL,
              qty_atoms INTEGER NOT NULL CHECK(qty_atoms>=0),
              amount_minor INTEGER NOT NULL CHECK(amount_minor>=0),
              valid_at TEXT NOT NULL,
              observed_at TEXT NOT NULL,
              operation_key TEXT
            );
            CREATE TABLE IF NOT EXISTS allocations(
              allocation_id TEXT PRIMARY KEY,
              line_id TEXT NOT NULL,
              qty_atoms INTEGER NOT NULL CHECK(qty_atoms>0),
              amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
              valid_at TEXT NOT NULL,
              observed_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS effects(
              operation_key TEXT PRIMARY KEY,
              allocation_id TEXT NOT NULL REFERENCES allocations(allocation_id),
              kind TEXT NOT NULL,
              payload_hash TEXT NOT NULL,
              downstream_key TEXT NOT NULL UNIQUE,
              qty_atoms INTEGER NOT NULL CHECK(qty_atoms>0),
              amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
              state TEXT NOT NULL,
              version INTEGER NOT NULL DEFAULT 0,
              replay_expires_at TEXT,
              valid_at TEXT NOT NULL,
              observed_at TEXT NOT NULL
            );
            """
        )

    def record_authority(
        self,
        event_key: str,
        line_id: str,
        kind: str,
        qty_atoms: int,
        amount_minor: int,
        *,
        valid_at: str,
        observed_at: str,
    ) -> None:
        allowed = self.POSITIVE | self.NEGATIVE | {"PHYSICAL_NONREFUNDING"}
        if kind not in allowed:
            raise AuthorityError(f"unsupported authority event {kind}")
        self.db.execute(
            "INSERT INTO events(event_key,line_id,kind,qty_atoms,amount_minor,valid_at,observed_at) VALUES(?,?,?,?,?,?,?)",
            (event_key, line_id, kind, qty_atoms, amount_minor, valid_at, observed_at),
        )

    def replay(self, line_id: str, *, valid_at: str, observed_at: str) -> Balance:
        rows = self.db.execute(
            """
            SELECT kind,qty_atoms,amount_minor FROM events
            WHERE line_id=? AND valid_at<=? AND observed_at<=?
            ORDER BY valid_at,observed_at,id
            """,
            (line_id, valid_at, observed_at),
        ).fetchall()
        aq = aa = iq = ia = 0
        for kind, qty, amount in rows:
            if kind in self.POSITIVE:
                aq += qty
                aa += amount
            elif kind in self.NEGATIVE:
                aq -= qty
                aa -= amount
            elif kind == "INVOICE_ALLOCATED":
                iq += qty
                ia += amount
            elif kind == "REVERSAL_APPLIED":
                iq -= qty
                ia -= amount
        balance = Balance(aq, aa, iq, ia)
        if min(aq, aa, iq, ia, balance.available_qty, balance.available_amount) < 0:
            raise CapacityError("CONSERVATION_VIOLATION_IN_REPLAY")
        return balance

    def allocate_invoice(
        self,
        allocation_id: str,
        line_id: str,
        qty_atoms: int,
        amount_minor: int,
        *,
        valid_at: str,
        observed_at: str,
    ) -> None:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            balance = self.replay(line_id, valid_at=valid_at, observed_at=observed_at)
            if qty_atoms > balance.available_qty or amount_minor > balance.available_amount:
                raise CapacityError("FORWARD_AUTHORITY_EXCEEDED")
            self.db.execute(
                "INSERT INTO allocations VALUES(?,?,?,?,?,?)",
                (allocation_id, line_id, qty_atoms, amount_minor, valid_at, observed_at),
            )
            self.db.execute(
                "INSERT INTO events(event_key,line_id,allocation_id,kind,qty_atoms,amount_minor,valid_at,observed_at) VALUES(?,?,?,?,?,?,?,?)",
                (f"invoice:{allocation_id}", line_id, allocation_id, "INVOICE_ALLOCATED", qty_atoms, amount_minor, valid_at, observed_at),
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def reserve_effect(
        self,
        operation_key: str,
        allocation_id: str,
        kind: str,
        qty_atoms: int,
        amount_minor: int,
        payload: object,
        *,
        valid_at: str,
        observed_at: str,
        replay_expires_at: str | None = None,
    ) -> dict:
        payload_hash = canonical_hash(payload)
        downstream_key = hashlib.sha256(f"exp002|{operation_key}".encode()).hexdigest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute(
                "SELECT payload_hash,state,version,downstream_key FROM effects WHERE operation_key=?",
                (operation_key,),
            ).fetchone()
            if existing:
                if existing[0] != payload_hash:
                    raise AuthorityError("OPERATION_KEY_PAYLOAD_CONFLICT")
                self.db.execute("COMMIT")
                return {"state": existing[1], "version": existing[2], "downstream_key": existing[3]}
            allocation = self.db.execute(
                "SELECT qty_atoms,amount_minor FROM allocations WHERE allocation_id=?",
                (allocation_id,),
            ).fetchone()
            if not allocation:
                raise AuthorityError("UNKNOWN_ALLOCATION")
            applied = self.db.execute(
                "SELECT COALESCE(SUM(qty_atoms),0),COALESCE(SUM(amount_minor),0) FROM events WHERE allocation_id=? AND kind='REVERSAL_APPLIED'",
                (allocation_id,),
            ).fetchone()
            held = self.db.execute(
                """
                SELECT COALESCE(SUM(qty_atoms),0),COALESCE(SUM(amount_minor),0)
                FROM effects WHERE allocation_id=? AND state IN ('RESERVED','DISPATCHING','UNKNOWN','MANUAL_REVIEW')
                """,
                (allocation_id,),
            ).fetchone()
            if qty_atoms > allocation[0] - applied[0] - held[0] or amount_minor > allocation[1] - applied[1] - held[1]:
                raise CapacityError("REVERSE_AUTHORITY_EXCEEDED")
            self.db.execute(
                "INSERT INTO effects VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (operation_key, allocation_id, kind, payload_hash, downstream_key, qty_atoms, amount_minor, "RESERVED", 0, replay_expires_at, valid_at, observed_at),
            )
            self.db.execute("COMMIT")
            return {"state": "RESERVED", "version": 0, "downstream_key": downstream_key}
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def dispatch(self, operation_key: str, *, expected_version: int) -> tuple[int, str, str]:
        row = self.db.execute(
            "SELECT state,version,downstream_key,payload_hash FROM effects WHERE operation_key=?",
            (operation_key,),
        ).fetchone()
        if not row or row[0] != "RESERVED" or row[1] != expected_version:
            raise StaleWorkerError("DISPATCH_FENCE_REJECTED")
        changed = self.db.execute(
            "UPDATE effects SET state='DISPATCHING',version=version+1 WHERE operation_key=? AND state='RESERVED' AND version=?",
            (operation_key, expected_version),
        ).rowcount
        if changed != 1:
            raise StaleWorkerError("DISPATCH_FENCE_REJECTED")
        return expected_version + 1, row[2], row[3]

    def recover_abandoned_dispatch(self, operation_key: str) -> int:
        changed = self.db.execute(
            "UPDATE effects SET state='UNKNOWN',version=version+1 WHERE operation_key=? AND state='DISPATCHING'",
            (operation_key,),
        ).rowcount
        if changed != 1:
            raise AuthorityError("NO_ABANDONED_DISPATCH")
        return self.db.execute("SELECT version FROM effects WHERE operation_key=?", (operation_key,)).fetchone()[0]

    def record_worker_result(self, operation_key: str, *, expected_version: int) -> None:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                """
                SELECT e.allocation_id,e.qty_atoms,e.amount_minor,e.valid_at,a.line_id
                FROM effects e JOIN allocations a USING(allocation_id)
                WHERE e.operation_key=? AND e.state='DISPATCHING' AND e.version=?
                """,
                (operation_key, expected_version),
            ).fetchone()
            if not row:
                raise StaleWorkerError("ZOMBIE_RESULT_FENCED")
            allocation_id, qty, amount, valid_at, line_id = row
            self.db.execute(
                "INSERT INTO events(event_key,line_id,allocation_id,kind,qty_atoms,amount_minor,valid_at,observed_at,operation_key) VALUES(?,?,?,?,?,?,?,?,?)",
                (f"reversal:{operation_key}", line_id, allocation_id, "REVERSAL_APPLIED", qty, amount, valid_at, utc_now(), operation_key),
            )
            changed = self.db.execute(
                "UPDATE effects SET state='APPLIED',version=version+1 WHERE operation_key=? AND state='DISPATCHING' AND version=?",
                (operation_key, expected_version),
            ).rowcount
            if changed != 1:
                raise StaleWorkerError("ZOMBIE_RESULT_FENCED")
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def reconcile(self, operation_key: str, probe: ProbeResult, *, observed_at: str) -> str:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            row = self.db.execute(
                "SELECT allocation_id,state,version,qty_atoms,amount_minor,valid_at FROM effects WHERE operation_key=?",
                (operation_key,),
            ).fetchone()
            if not row:
                raise AuthorityError("UNKNOWN_EFFECT")
            allocation_id, state, version, qty, amount, valid_at = row
            if state == "APPLIED":
                self.db.execute("COMMIT")
                return "APPLIED"
            if state not in {"UNKNOWN", "MANUAL_REVIEW", "DISPATCHING"}:
                raise AuthorityError(f"CANNOT_RECONCILE_{state}")
            if probe == "APPLIED":
                line_id = self.db.execute(
                    "SELECT line_id FROM allocations WHERE allocation_id=?", (allocation_id,)
                ).fetchone()[0]
                self.db.execute(
                    "INSERT OR IGNORE INTO events(event_key,line_id,allocation_id,kind,qty_atoms,amount_minor,valid_at,observed_at,operation_key) VALUES(?,?,?,?,?,?,?,?,?)",
                    (f"reversal:{operation_key}", line_id, allocation_id, "REVERSAL_APPLIED", qty, amount, valid_at, observed_at, operation_key),
                )
                self.db.execute(
                    "UPDATE effects SET state='APPLIED',version=? WHERE operation_key=?", (version + 1, operation_key)
                )
            elif probe == "NOT_APPLIED":
                self.db.execute(
                    "UPDATE effects SET state='NOT_APPLIED',version=? WHERE operation_key=?", (version + 1, operation_key)
                )
            else:
                self.db.execute(
                    "UPDATE effects SET state='MANUAL_REVIEW',version=? WHERE operation_key=?", (version + 1, operation_key)
                )
            self.db.execute("COMMIT")
            return self.effect_state(operation_key)
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def reconcile_receipt(
        self,
        operation_key: str,
        receipt: ProviderOutcomeReceipt,
        *,
        observed_at: str,
    ) -> str:
        return self.reconcile(
            operation_key,
            receipt.classify(expected_logical_effect_id=operation_key),
            observed_at=observed_at,
        )

    def can_redispatch(self, operation_key: str, *, now: str) -> bool:
        row = self.db.execute(
            "SELECT state,replay_expires_at FROM effects WHERE operation_key=?", (operation_key,)
        ).fetchone()
        return bool(row and row[0] in {"UNKNOWN", "MANUAL_REVIEW"} and row[1] and now <= row[1])

    def effect_state(self, operation_key: str) -> str:
        row = self.db.execute("SELECT state FROM effects WHERE operation_key=?", (operation_key,)).fetchone()
        if not row:
            raise AuthorityError("UNKNOWN_EFFECT")
        return row[0]

    def event_count(self, kind: str, operation_key: str | None = None) -> int:
        if operation_key is None:
            return self.db.execute("SELECT COUNT(*) FROM events WHERE kind=?", (kind,)).fetchone()[0]
        return self.db.execute(
            "SELECT COUNT(*) FROM events WHERE kind=? AND operation_key=?", (kind, operation_key)
        ).fetchone()[0]


class SyntheticTarget:
    """Separate durable target. Absence is UNKNOWN unless an explicit negative receipt exists."""

    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(str(path), isolation_level=None)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS applied(downstream_key TEXT PRIMARY KEY,payload_hash TEXT NOT NULL)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS negative_receipts(downstream_key TEXT PRIMARY KEY, reason TEXT NOT NULL)"
        )

    def apply(self, downstream_key: str, payload_hash: str) -> None:
        prior = self.db.execute(
            "SELECT payload_hash FROM applied WHERE downstream_key=?", (downstream_key,)
        ).fetchone()
        if prior and prior[0] != payload_hash:
            raise AuthorityError("TARGET_KEY_PAYLOAD_CONFLICT")
        self.db.execute("INSERT OR IGNORE INTO applied VALUES(?,?)", (downstream_key, payload_hash))

    def record_authoritative_negative(self, downstream_key: str, reason: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO negative_receipts VALUES(?,?)", (downstream_key, reason))

    def probe(self, downstream_key: str) -> ProbeResult:
        if self.db.execute("SELECT 1 FROM applied WHERE downstream_key=?", (downstream_key,)).fetchone():
            return "APPLIED"
        if self.db.execute("SELECT 1 FROM negative_receipts WHERE downstream_key=?", (downstream_key,)).fetchone():
            return "NOT_APPLIED"
        return "UNKNOWN"

    def applied_count(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM applied").fetchone()[0]
