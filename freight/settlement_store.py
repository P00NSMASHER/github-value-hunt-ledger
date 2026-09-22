"""Persistent settlement attribution reference for Freight Recovery.

Exact cents, immutable evidence, one-use allocation capacity, reviewed split
payments, append-only reversal edges, and tenant/business-unit scope are
enforced with SQLite transactions and SQL constraints. This strengthens
EXP-001's internal proof boundary; it is not customer outcome evidence.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

AUTO, REVIEW = "AUTO", "REVIEW"
ALLOCATED, ALREADY_ALLOCATED = "ALLOCATED", "ALREADY_ALLOCATED"
REVERSED, ALREADY_REVERSED = "REVERSED", "ALREADY_REVERSED"
T = TypeVar("T")


@dataclass(frozen=True)
class RecoveryClaim:
    claim_id: str
    reference: str
    payer_id: str
    payee_id: str
    currency: str
    amount_cents: int
    issued_at: str
    source_hash: str
    fee_disqualified: bool = False


@dataclass(frozen=True)
class SettlementEventRecord:
    event_id: str
    reference: str
    payer_id: str
    payee_id: str
    currency: str
    amount_cents: int
    booked_at: str
    source_hash: str
    source_kind: str = "EXTERNAL"


@dataclass(frozen=True)
class CounterEventRecord:
    counter_id: str
    original_event_id: str
    currency: str
    amount_cents: int
    observed_at: str
    source_hash: str
    source_kind: str = "RETURN"


@dataclass(frozen=True)
class Decision:
    status: str
    edge_ids: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class AtomicSettlementOutcome:
    event_id: str
    created: bool
    decision: Decision


@dataclass(frozen=True)
class AtomicCounterOutcome:
    counter_id: str
    created: bool
    decision: Decision


@dataclass(frozen=True)
class AtomicEvidencePackageResult:
    settlement_outcomes: tuple[AtomicSettlementOutcome, ...]
    counter_outcomes: tuple[AtomicCounterOutcome, ...]
    store_snapshot_before: dict
    store_snapshot_after: dict


class SettlementStore:
    """Scope-bound settlement repository.

    The buyer/business-unit scope is chosen when the repository is created and
    is never caller-selectable on individual rows. This models an authenticated
    repository/service boundary and prevents settlement evidence from being
    matched or read across tenants that share the same local identifiers.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        buyer_id: str,
        business_unit: str,
        busy_timeout_ms: int = 5000,
    ):
        self.path = str(path)
        self.buyer_id = self._text("buyer_id", buyer_id)
        self.business_unit = self._text("business_unit", business_unit)
        self.busy_timeout_ms = busy_timeout_ms
        if self.path == ":memory:":
            raise ValueError("file-backed SQLite is required for concurrent connections")
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(Path(__file__).with_name("settlement_schema.sql").read_text())
            self._assert_scoped_schema(conn)

    @staticmethod
    def _assert_scoped_schema(conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(recovery_claims)")}
        if not {"buyer_id", "business_unit"}.issubset(cols):
            raise RuntimeError("legacy unscoped settlement schema detected; migrate or rebuild before use")
        triggers = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        required = {
            "allocation_event_counter_lock",
            "allocation_event_net_capacity",
            "counter_event_capacity",
        }
        if not required.issubset(triggers):
            raise RuntimeError("settlement return-capacity guards are missing")
        over_returned = conn.execute("""SELECT e.event_id
          FROM settlement_events e
          JOIN counter_events c
            ON c.buyer_id=e.buyer_id
           AND c.business_unit=e.business_unit
           AND c.original_event_id=e.event_id
          GROUP BY e.buyer_id,e.business_unit,e.event_id,e.amount_cents
          HAVING SUM(c.amount_cents)>e.amount_cents
          LIMIT 1""").fetchone()
        if over_returned is not None:
            raise RuntimeError(
                "settlement database counter capacity invariant violated: "
                + str(over_returned[0])
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=self.busy_timeout_ms / 1000, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        return conn

    def _write(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        delay = 0.005
        last: Exception | None = None
        for _ in range(8):
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE")
                out = fn(conn)
                conn.commit()
                return out
            except sqlite3.OperationalError as exc:
                conn.rollback()
                last = exc
                if "locked" not in str(exc).lower():
                    raise
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            time.sleep(delay)
            delay = min(delay * 2, 0.1)
        assert last is not None
        raise last

    def _read(self, fn: Callable[[sqlite3.Connection], T]) -> T:
        conn = self._connect()
        try:
            return fn(conn)
        finally:
            conn.close()

    @staticmethod
    def _text(name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")
        return value.strip()

    @staticmethod
    def _timestamp(name: str, value: str) -> str:
        text = SettlementStore._text(name, value)
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"{name} must be a timezone-aware ISO-8601 timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{name} must be a timezone-aware ISO-8601 timestamp")
        return (
            parsed.astimezone(timezone.utc)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )

    @staticmethod
    def _positive_cents(name: str, value: int) -> int:
        # Input adapters must perform any explicit, reviewed currency conversion.
        # Silently truncating fractional cents here changes immutable evidence.
        if type(value) is not int or not 0 < value <= 2**63 - 1:
            raise ValueError(f"{name} must be positive integer cents within SQLite range")
        return value

    @staticmethod
    def _same(row: sqlite3.Row, values: dict[str, object]) -> bool:
        return all(row[k] == v for k, v in values.items())

    @property
    def _scope(self) -> tuple[str, str]:
        return self.buyer_id, self.business_unit

    def _claim_values(self, claim: RecoveryClaim) -> dict[str, object]:
        if type(claim.fee_disqualified) is not bool:
            raise ValueError("fee_disqualified must be a boolean")
        return dict(
            buyer_id=self.buyer_id,
            business_unit=self.business_unit,
            claim_id=self._text("claim_id", claim.claim_id),
            reference=self._text("reference", claim.reference),
            payer_id=self._text("payer_id", claim.payer_id),
            payee_id=self._text("payee_id", claim.payee_id),
            currency=self._text("currency", claim.currency),
            amount_cents=self._positive_cents("claim amount", claim.amount_cents),
            issued_at=self._timestamp("issued_at", claim.issued_at),
            source_hash=self._text("source_hash", claim.source_hash),
            fee_disqualified=int(claim.fee_disqualified),
        )

    def _create_claim_conn(self, conn: sqlite3.Connection, v: dict[str, object]) -> bool:
        old = conn.execute(
            "SELECT * FROM recovery_claims WHERE buyer_id=? AND business_unit=? AND claim_id=?",
            (*self._scope, v["claim_id"]),
        ).fetchone()
        if old:
            if self._same(old, v):
                return False
            raise ValueError("claim_id replay conflicts with immutable claim")
        if conn.execute(
            "SELECT 1 FROM recovery_claims WHERE buyer_id=? AND business_unit=? AND source_hash=?",
            (*self._scope, v["source_hash"]),
        ).fetchone():
            raise ValueError("claim source_hash already used")
        conn.execute("""INSERT INTO recovery_claims
          (buyer_id,business_unit,claim_id,reference,payer_id,payee_id,currency,amount_cents,issued_at,source_hash,fee_disqualified)
          VALUES(:buyer_id,:business_unit,:claim_id,:reference,:payer_id,:payee_id,:currency,:amount_cents,:issued_at,:source_hash,:fee_disqualified)""", v)
        return True

    def create_claim(self, claim: RecoveryClaim) -> bool:
        v = self._claim_values(claim)
        return self._write(lambda conn: self._create_claim_conn(conn, v))

    def create_claims(self, claims: tuple[RecoveryClaim, ...]) -> tuple[bool, ...]:
        normalized = tuple(claims)
        values = tuple(self._claim_values(claim) for claim in normalized)
        claim_ids = [str(v["claim_id"]) for v in values]
        source_hashes = [str(v["source_hash"]) for v in values]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("duplicate claim_id in claim batch")
        if len(source_hashes) != len(set(source_hashes)):
            raise ValueError("duplicate source_hash in claim batch")
        if not values:
            return ()

        def op(conn: sqlite3.Connection) -> tuple[bool, ...]:
            return tuple(self._create_claim_conn(conn, v) for v in values)

        return self._write(op)

    def _event_values(self, event: SettlementEventRecord) -> dict[str, object]:
        return dict(
            buyer_id=self.buyer_id,
            business_unit=self.business_unit,
            event_id=self._text("event_id", event.event_id),
            reference=self._text("reference", event.reference),
            payer_id=self._text("payer_id", event.payer_id),
            payee_id=self._text("payee_id", event.payee_id),
            currency=self._text("currency", event.currency),
            amount_cents=self._positive_cents("settlement amount", event.amount_cents),
            booked_at=self._timestamp("booked_at", event.booked_at),
            source_hash=self._text("source_hash", event.source_hash),
            source_kind=self._text("source_kind", event.source_kind),
        )

    def _ingest_event_conn(
        self,
        conn: sqlite3.Connection,
        v: dict[str, object],
    ) -> bool:
        old = conn.execute(
            "SELECT * FROM settlement_events WHERE buyer_id=? AND business_unit=? AND event_id=?",
            (*self._scope, v["event_id"]),
        ).fetchone()
        if old:
            if self._same(old, v):
                return False
            raise ValueError("event_id replay conflicts with immutable settlement event")
        if conn.execute(
            "SELECT 1 FROM settlement_events WHERE buyer_id=? AND business_unit=? AND source_hash=?",
            (*self._scope, v["source_hash"]),
        ).fetchone():
            raise ValueError("settlement source_hash already used")
        conn.execute("""INSERT INTO settlement_events
          (buyer_id,business_unit,event_id,reference,payer_id,payee_id,currency,amount_cents,booked_at,source_hash,source_kind)
          VALUES(:buyer_id,:business_unit,:event_id,:reference,:payer_id,:payee_id,:currency,:amount_cents,:booked_at,:source_hash,:source_kind)""", v)
        return True

    def ingest_event(self, event: SettlementEventRecord) -> bool:
        v = self._event_values(event)
        return self._write(lambda conn: self._ingest_event_conn(conn, v))

    def _counter_values(self, event: CounterEventRecord) -> dict[str, object]:
        return dict(
            buyer_id=self.buyer_id,
            business_unit=self.business_unit,
            counter_id=self._text("counter_id", event.counter_id),
            original_event_id=self._text("original_event_id", event.original_event_id),
            currency=self._text("currency", event.currency),
            amount_cents=self._positive_cents("counter amount", event.amount_cents),
            observed_at=self._timestamp("observed_at", event.observed_at),
            source_hash=self._text("source_hash", event.source_hash),
            source_kind=self._text("source_kind", event.source_kind),
        )

    def _ingest_counter_conn(
        self,
        conn: sqlite3.Connection,
        v: dict[str, object],
    ) -> bool:
        original = conn.execute(
            "SELECT currency,booked_at,amount_cents FROM settlement_events WHERE buyer_id=? AND business_unit=? AND event_id=?",
            (*self._scope, v["original_event_id"]),
        ).fetchone()
        if not original:
            raise ValueError("counter references unknown settlement event")
        if original["currency"] != v["currency"]:
            raise ValueError("counter currency mismatch")
        if v["observed_at"] < original["booked_at"]:
            raise ValueError("counter event predates original settlement")
        old = conn.execute(
            "SELECT * FROM counter_events WHERE buyer_id=? AND business_unit=? AND counter_id=?",
            (*self._scope, v["counter_id"]),
        ).fetchone()
        if old:
            if self._same(old, v):
                return False
            raise ValueError("counter_id replay conflicts with immutable counter event")
        if conn.execute(
            "SELECT 1 FROM counter_events WHERE buyer_id=? AND business_unit=? AND source_hash=?",
            (*self._scope, v["source_hash"]),
        ).fetchone():
            raise ValueError("counter source_hash already used")
        countered_cents = int(conn.execute(
            "SELECT COALESCE(SUM(amount_cents),0) FROM counter_events "
            "WHERE buyer_id=? AND business_unit=? AND original_event_id=?",
            (*self._scope, v["original_event_id"]),
        ).fetchone()[0])
        if countered_cents + int(v["amount_cents"]) > int(original["amount_cents"]):
            raise ValueError("counter events exceed original settlement amount")
        conn.execute("""INSERT INTO counter_events
          (buyer_id,business_unit,counter_id,original_event_id,currency,amount_cents,observed_at,source_hash,source_kind)
          VALUES(:buyer_id,:business_unit,:counter_id,:original_event_id,:currency,:amount_cents,:observed_at,:source_hash,:source_kind)""", v)
        return True

    def ingest_counter(self, event: CounterEventRecord) -> bool:
        v = self._counter_values(event)
        return self._write(lambda conn: self._ingest_counter_conn(conn, v))

    def _claim_residual(self, conn: sqlite3.Connection, claim_id: str) -> int:
        row = conn.execute("""SELECT c.amount_cents
          - COALESCE((SELECT SUM(amount_cents) FROM allocations
              WHERE buyer_id=c.buyer_id AND business_unit=c.business_unit AND claim_id=c.claim_id),0)
          + COALESCE((SELECT SUM(r.amount_cents) FROM reversal_edges r JOIN allocations a
              ON a.buyer_id=r.buyer_id AND a.business_unit=r.business_unit AND a.allocation_id=r.allocation_id
              WHERE a.buyer_id=c.buyer_id AND a.business_unit=c.business_unit AND a.claim_id=c.claim_id),0) AS residual
          FROM recovery_claims c WHERE c.buyer_id=? AND c.business_unit=? AND c.claim_id=?""",
          (*self._scope, claim_id)).fetchone()
        if not row:
            raise ValueError("unknown recovery claim")
        return int(row["residual"])

    def _event_residual(self, conn: sqlite3.Connection, event_id: str) -> int:
        row = conn.execute("""SELECT e.amount_cents
          - COALESCE((SELECT SUM(amount_cents) FROM allocations
              WHERE buyer_id=e.buyer_id AND business_unit=e.business_unit
                AND event_id=e.event_id),0) AS residual,
          EXISTS(SELECT 1 FROM counter_events
              WHERE buyer_id=e.buyer_id AND business_unit=e.business_unit
                AND original_event_id=e.event_id) AS has_counter
          FROM settlement_events e WHERE e.buyer_id=? AND e.business_unit=? AND e.event_id=?""",
          (*self._scope, event_id)).fetchone()
        if not row:
            raise ValueError("unknown settlement event")
        # Once return/counter evidence exists, the original settlement event is
        # closed to new attribution. Existing allocations can be reversed, but
        # any replacement/net remittance must arrive as new settlement evidence.
        # This prevents one counter from first reducing "net capacity" and then
        # later reducing a newly-created allocation a second time.
        if row["has_counter"]:
            return 0
        return int(row["residual"])

    def claim_residual(self, claim_id: str) -> int:
        return self._read(lambda c: self._claim_residual(c, claim_id))

    def event_residual(self, event_id: str) -> int:
        return self._read(lambda c: self._event_residual(c, event_id))

    def _auto_allocate_conn(
        self,
        conn: sqlite3.Connection,
        event_id: str,
        created_at: str,
    ) -> Decision:
        event = conn.execute(
            "SELECT * FROM settlement_events WHERE buyer_id=? AND business_unit=? AND event_id=?",
            (*self._scope, event_id),
        ).fetchone()
        if not event:
            raise ValueError("unknown settlement event")
        if created_at < event["booked_at"]:
            raise ValueError("allocation created_at cannot predate settlement booking")
        old = conn.execute(
            "SELECT allocation_id FROM allocations WHERE buyer_id=? AND business_unit=? AND event_id=? ORDER BY allocation_id",
            (*self._scope, event_id),
        ).fetchall()
        if old:
            return Decision(
                ALREADY_ALLOCATED,
                tuple(r[0] for r in old),
                "event already consumed",
            )
        remaining = self._event_residual(conn, event_id)
        rows = conn.execute("""SELECT c.* FROM recovery_claims c
          LEFT JOIN review_claims r
            ON r.buyer_id=c.buyer_id AND r.business_unit=c.business_unit AND r.claim_id=c.claim_id
          WHERE c.buyer_id=? AND c.business_unit=?
            AND c.reference=? AND c.payer_id=? AND c.payee_id=? AND c.currency=?
            AND c.issued_at<=? AND r.claim_id IS NULL ORDER BY c.claim_id""",
          (*self._scope, event["reference"], event["payer_id"], event["payee_id"], event["currency"], event["booked_at"])).fetchall()
        candidates = [
            row
            for row in rows
            if (res := self._claim_residual(conn, row["claim_id"])) > 0
            and res == remaining
        ]
        if len(candidates) != 1:
            return Decision(
                REVIEW,
                reason=f"exact unique candidate count={len(candidates)}",
            )
        claim = candidates[0]
        edge = f"auto:{event_id}:{claim['claim_id']}"
        fee = 0 if claim["fee_disqualified"] else remaining
        conn.execute("""INSERT INTO allocations
          (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
          VALUES(?,?,?,?,?,?,?,?,?)""",
          (*self._scope, edge, claim["claim_id"], event_id, remaining, AUTO, fee, created_at))
        return Decision(ALLOCATED, (edge,), "exact unique external settlement")

    def auto_allocate(self, event_id: str, *, created_at: str) -> Decision:
        event_id = self._text("event_id", event_id)
        created_at = self._timestamp("created_at", created_at)
        return self._write(
            lambda conn: self._auto_allocate_conn(conn, event_id, created_at)
        )

    def review_allocate(self, *, allocation_id: str, claim_id: str, event_id: str, amount_cents: int, created_at: str) -> str:
        amount_cents = self._positive_cents("allocation amount", amount_cents)
        created_at = self._timestamp("created_at", created_at)

        def op(conn: sqlite3.Connection) -> str:
            old = conn.execute(
                "SELECT * FROM allocations WHERE buyer_id=? AND business_unit=? AND allocation_id=?",
                (*self._scope, allocation_id),
            ).fetchone()
            if old:
                same = old["claim_id"] == claim_id and old["event_id"] == event_id and old["amount_cents"] == amount_cents and old["mode"] == REVIEW and old["created_at"] == created_at
                if same:
                    return ALREADY_ALLOCATED
                raise ValueError("allocation_id replay conflicts with immutable allocation")
            claim = conn.execute(
                "SELECT * FROM recovery_claims WHERE buyer_id=? AND business_unit=? AND claim_id=?",
                (*self._scope, claim_id),
            ).fetchone()
            event = conn.execute(
                "SELECT * FROM settlement_events WHERE buyer_id=? AND business_unit=? AND event_id=?",
                (*self._scope, event_id),
            ).fetchone()
            if not claim or not event:
                raise ValueError("review allocation requires existing claim and settlement event")
            if created_at < event["booked_at"]:
                raise ValueError("allocation created_at cannot predate settlement booking")
            if claim["currency"] != event["currency"]:
                raise ValueError("allocation currency mismatch")
            if (claim["payer_id"], claim["payee_id"]) != (event["payer_id"], event["payee_id"]):
                raise ValueError("allocation payer/payee mismatch")
            if event["booked_at"] < claim["issued_at"]:
                raise ValueError("settlement event predates issued claim")
            if amount_cents > self._claim_residual(conn, claim_id):
                raise ValueError("recovery claim capacity exceeded")
            if amount_cents > self._event_residual(conn, event_id):
                raise ValueError("settlement event capacity exceeded")
            fee = 0 if claim["fee_disqualified"] else amount_cents
            conn.execute("""INSERT INTO allocations
              (buyer_id,business_unit,allocation_id,claim_id,event_id,amount_cents,mode,fee_eligible_cents,created_at)
              VALUES(?,?,?,?,?,?,?,?,?)""",
              (*self._scope, allocation_id, claim_id, event_id, amount_cents, REVIEW, fee, created_at))
            return ALLOCATED
        return self._write(op)

    def review_reverse(
        self,
        *,
        reversal_id: str,
        counter_id: str,
        allocation_id: str,
        amount_cents: int,
        created_at: str,
    ) -> str:
        reversal_id = self._text("reversal_id", reversal_id)
        counter_id = self._text("counter_id", counter_id)
        allocation_id = self._text("allocation_id", allocation_id)
        amount_cents = self._positive_cents("reversal amount", amount_cents)
        created_at = self._timestamp("created_at", created_at)

        def op(conn: sqlite3.Connection) -> str:
            old = conn.execute(
                "SELECT * FROM reversal_edges WHERE buyer_id=? AND business_unit=? AND reversal_id=?",
                (*self._scope, reversal_id),
            ).fetchone()
            if old:
                same = (
                    old["counter_id"] == counter_id
                    and old["allocation_id"] == allocation_id
                    and int(old["amount_cents"]) == amount_cents
                    and old["created_at"] == created_at
                )
                if same:
                    return ALREADY_REVERSED
                raise ValueError(
                    "reversal_id replay conflicts with immutable reversal edge"
                )

            counter = conn.execute(
                "SELECT * FROM counter_events WHERE buyer_id=? AND business_unit=? AND counter_id=?",
                (*self._scope, counter_id),
            ).fetchone()
            allocation = conn.execute(
                "SELECT * FROM allocations WHERE buyer_id=? AND business_unit=? AND allocation_id=?",
                (*self._scope, allocation_id),
            ).fetchone()
            if not counter or not allocation:
                raise ValueError(
                    "review reversal requires existing counter and allocation"
                )
            if counter["original_event_id"] != allocation["event_id"]:
                raise ValueError("counter event does not fund allocation")
            original_event = conn.execute(
                "SELECT currency FROM settlement_events WHERE buyer_id=? AND business_unit=? AND event_id=?",
                (*self._scope, allocation["event_id"]),
            ).fetchone()
            if original_event is None:
                raise ValueError("reversal allocation references unknown settlement event")
            if counter["currency"] != original_event["currency"]:
                raise ValueError("counter currency mismatch with original settlement event")
            if created_at < counter["observed_at"]:
                raise ValueError("reversal created_at cannot predate counter observation")
            if created_at < allocation["created_at"]:
                raise ValueError("reversal created_at cannot predate allocation")

            allocation_reversed = int(conn.execute(
                "SELECT COALESCE(SUM(amount_cents),0) FROM reversal_edges "
                "WHERE buyer_id=? AND business_unit=? AND allocation_id=?",
                (*self._scope, allocation_id),
            ).fetchone()[0])
            live_cents = int(allocation["amount_cents"]) - allocation_reversed
            if amount_cents > live_cents:
                raise ValueError("allocation reversal capacity exceeded")

            counter_used = int(conn.execute(
                "SELECT COALESCE(SUM(amount_cents),0) FROM reversal_edges "
                "WHERE buyer_id=? AND business_unit=? AND counter_id=?",
                (*self._scope, counter_id),
            ).fetchone()[0])
            counter_residual = int(counter["amount_cents"]) - counter_used
            if amount_cents > counter_residual:
                raise ValueError("counter event capacity exceeded")

            conn.execute(
                """INSERT INTO reversal_edges
                  (buyer_id,business_unit,reversal_id,counter_id,allocation_id,amount_cents,created_at)
                  VALUES(?,?,?,?,?,?,?)""",
                (
                    *self._scope,
                    reversal_id,
                    counter_id,
                    allocation_id,
                    amount_cents,
                    created_at,
                ),
            )
            return REVERSED

        return self._write(op)

    def _auto_apply_counter_conn(
        self,
        conn: sqlite3.Connection,
        counter_id: str,
        created_at: str,
    ) -> Decision:
        counter = conn.execute(
            "SELECT * FROM counter_events WHERE buyer_id=? AND business_unit=? AND counter_id=?",
            (*self._scope, counter_id),
        ).fetchone()
        if not counter:
            raise ValueError("unknown counter event")
        if created_at < counter["observed_at"]:
            raise ValueError("reversal created_at cannot predate counter observation")
        old = conn.execute(
            "SELECT reversal_id FROM reversal_edges WHERE buyer_id=? AND business_unit=? AND counter_id=? ORDER BY reversal_id",
            (*self._scope, counter_id),
        ).fetchall()
        if old:
            return Decision(
                ALREADY_REVERSED,
                tuple(r[0] for r in old),
                "counter already applied",
            )
        event = conn.execute(
            "SELECT * FROM settlement_events WHERE buyer_id=? AND business_unit=? AND event_id=?",
            (*self._scope, counter["original_event_id"]),
        ).fetchone()
        if event is None:
            raise ValueError("counter references unknown settlement event")
        if counter["currency"] != event["currency"]:
            raise ValueError("counter currency mismatch with original settlement event")
        live = conn.execute("""SELECT a.*,
          a.amount_cents-COALESCE((SELECT SUM(amount_cents) FROM reversal_edges
             WHERE buyer_id=a.buyer_id AND business_unit=a.business_unit AND allocation_id=a.allocation_id),0) AS live_cents
          FROM allocations a WHERE a.buyer_id=? AND a.business_unit=? AND a.event_id=? ORDER BY a.allocation_id""",
          (*self._scope, counter["original_event_id"])).fetchall()
        live = [r for r in live if r["live_cents"] > 0]
        if not live:
            return Decision(
                REVIEW,
                reason="original event has no live realized allocation",
            )
        total = sum(int(r["live_cents"]) for r in live)
        if counter["amount_cents"] in (event["amount_cents"], total):
            plan = [(r, int(r["live_cents"])) for r in live]
        elif len(live) == 1 and counter["amount_cents"] <= live[0]["live_cents"]:
            plan = [(live[0], int(counter["amount_cents"]))]
        else:
            return Decision(
                REVIEW,
                reason="partial return is ambiguous across live allocation edges",
            )
        if any(created_at < alloc["created_at"] for alloc, _ in plan):
            raise ValueError("reversal created_at cannot predate allocation")
        ids = []
        for i, (alloc, amount) in enumerate(plan, 1):
            edge = f"reversal:{counter_id}:{i}:{alloc['allocation_id']}"
            conn.execute("""INSERT INTO reversal_edges
              (buyer_id,business_unit,reversal_id,counter_id,allocation_id,amount_cents,created_at)
              VALUES(?,?,?,?,?,?,?)""",
              (*self._scope, edge, counter_id, alloc["allocation_id"], amount, created_at))
            ids.append(edge)
        return Decision(REVERSED, tuple(ids), "counter-edge applied")

    def auto_apply_counter(self, counter_id: str, *, created_at: str) -> Decision:
        counter_id = self._text("counter_id", counter_id)
        created_at = self._timestamp("created_at", created_at)
        return self._write(
            lambda conn: self._auto_apply_counter_conn(conn, counter_id, created_at)
        )

    def _snapshot_dict_conn(self, conn: sqlite3.Connection) -> dict:
        tables = (
            ("recovery_claims", "claim_id"),
            ("review_claims", "claim_id"),
            ("settlement_events", "event_id"),
            ("allocations", "allocation_id"),
            ("counter_events", "counter_id"),
            ("reversal_edges", "reversal_id"),
        )
        rows = {
            table: [
                dict(row)
                for row in conn.execute(
                    f"SELECT * FROM {table} WHERE buyer_id=? AND business_unit=? ORDER BY {key}",
                    self._scope,
                )
            ]
            for table, key in tables
        }
        return {
            "schema": 1,
            "buyer_id": self.buyer_id,
            "business_unit": self.business_unit,
            "tables": rows,
        }

    def process_evidence_package(
        self,
        *,
        settlement_events: tuple[SettlementEventRecord, ...] = (),
        counter_events: tuple[CounterEventRecord, ...] = (),
        created_at: str,
    ) -> AtomicEvidencePackageResult:
        created_at = self._timestamp("created_at", created_at)
        event_values = tuple(self._event_values(event) for event in settlement_events)
        counter_values = tuple(
            self._counter_values(counter) for counter in counter_events
        )
        if not event_values and not counter_values:
            raise ValueError("at least one settlement or counter event is required")

        event_ids = [str(value["event_id"]) for value in event_values]
        event_sources = [str(value["source_hash"]) for value in event_values]
        counter_ids = [str(value["counter_id"]) for value in counter_values]
        counter_sources = [str(value["source_hash"]) for value in counter_values]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("duplicate event_id in settlement evidence package")
        if len(event_sources) != len(set(event_sources)):
            raise ValueError("duplicate settlement source_hash in evidence package")
        if len(counter_ids) != len(set(counter_ids)):
            raise ValueError("duplicate counter_id in settlement evidence package")
        if len(counter_sources) != len(set(counter_sources)):
            raise ValueError("duplicate counter source_hash in evidence package")
        for value in event_values:
            if created_at < value["booked_at"]:
                raise ValueError(
                    "created_at cannot predate settlement booking: "
                    + str(value["event_id"])
                )
        for value in counter_values:
            if created_at < value["observed_at"]:
                raise ValueError(
                    "created_at cannot predate counter observation: "
                    + str(value["counter_id"])
                )

        def op(conn: sqlite3.Connection) -> AtomicEvidencePackageResult:
            before = self._snapshot_dict_conn(conn)

            settlements: list[AtomicSettlementOutcome] = []
            for value in event_values:
                event_id = str(value["event_id"])
                created = self._ingest_event_conn(conn, value)
                decision = self._auto_allocate_conn(conn, event_id, created_at)
                settlements.append(
                    AtomicSettlementOutcome(event_id, created, decision)
                )

            counters: list[AtomicCounterOutcome] = []
            for value in counter_values:
                counter_id = str(value["counter_id"])
                created = self._ingest_counter_conn(conn, value)
                decision = self._auto_apply_counter_conn(
                    conn,
                    counter_id,
                    created_at,
                )
                counters.append(
                    AtomicCounterOutcome(counter_id, created, decision)
                )

            # A counter can restore claim capacity after an earlier settlement
            # was initially routed to review. Re-evaluate those cases before
            # freezing the package state so review cases describe final state.
            for index, outcome in enumerate(settlements):
                if outcome.decision.status != REVIEW:
                    continue
                decision = self._auto_allocate_conn(
                    conn,
                    outcome.event_id,
                    created_at,
                )
                settlements[index] = AtomicSettlementOutcome(
                    outcome.event_id,
                    outcome.created,
                    decision,
                )

            # A newly allocated settlement can make an earlier counter
            # auto-reversible. Re-evaluate reviewed counters once after the
            # final settlement pass.
            for index, outcome in enumerate(counters):
                if outcome.decision.status != REVIEW:
                    continue
                decision = self._auto_apply_counter_conn(
                    conn,
                    outcome.counter_id,
                    created_at,
                )
                counters[index] = AtomicCounterOutcome(
                    outcome.counter_id,
                    outcome.created,
                    decision,
                )

            after = self._snapshot_dict_conn(conn)
            return AtomicEvidencePackageResult(
                settlement_outcomes=tuple(settlements),
                counter_outcomes=tuple(counters),
                store_snapshot_before=before,
                store_snapshot_after=after,
            )

        return self._write(op)

    def realized_cents(self, claim_id: str | None = None) -> int:
        def op(conn: sqlite3.Connection) -> int:
            params: tuple[object, ...] = self._scope + ((claim_id,) if claim_id else ())
            clause = " AND claim_id=?" if claim_id else ""
            allocated = int(conn.execute(
                f"SELECT COALESCE(SUM(amount_cents),0) FROM allocations WHERE buyer_id=? AND business_unit=?{clause}",
                params,
            ).fetchone()[0])
            reversed_cents = int(conn.execute(
                f"""SELECT COALESCE(SUM(r.amount_cents),0) FROM reversal_edges r
                JOIN allocations a ON a.buyer_id=r.buyer_id AND a.business_unit=r.business_unit AND a.allocation_id=r.allocation_id
                WHERE r.buyer_id=? AND r.business_unit=?{" AND a.claim_id=?" if claim_id else ""}""",
                params,
            ).fetchone()[0])
            return allocated - reversed_cents
        return self._read(op)

    def fee_eligible_cents(self, claim_id: str | None = None) -> int:
        def op(conn: sqlite3.Connection) -> int:
            params: tuple[object, ...] = self._scope + ((claim_id,) if claim_id else ())
            rows = conn.execute(
                "SELECT * FROM allocations WHERE buyer_id=? AND business_unit=?" + (" AND claim_id=?" if claim_id else ""),
                params,
            ).fetchall()
            total = 0
            for a in rows:
                reversed_cents = int(conn.execute(
                    "SELECT COALESCE(SUM(amount_cents),0) FROM reversal_edges WHERE buyer_id=? AND business_unit=? AND allocation_id=?",
                    (*self._scope, a["allocation_id"]),
                ).fetchone()[0])
                if a["fee_eligible_cents"] == a["amount_cents"]:
                    total += max(int(a["fee_eligible_cents"]) - reversed_cents, 0)
            return total
        return self._read(op)

    def count(self, table: str) -> int:
        allowed = {"recovery_claims", "settlement_events", "allocations", "counter_events", "reversal_edges"}
        if table not in allowed:
            raise ValueError("unsupported count table")
        return self._read(lambda c: int(c.execute(
            f"SELECT COUNT(*) FROM {table} WHERE buyer_id=? AND business_unit=?",
            self._scope,
        ).fetchone()[0]))

    def report_snapshot_json(self) -> str:
        """Read one immutable, scope-bound report snapshot without writing rows.

        A single SQLite read transaction keeps claims, allocations and reversals
        at the same database revision even when another connection writes. The
        returned JSON is operational evidence and can contain customer data.
        """

        def op(conn: sqlite3.Connection) -> str:
            conn.execute("BEGIN")
            try:
                value = self._snapshot_dict_conn(conn)
                return json.dumps(
                    value,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            finally:
                conn.rollback()

        return self._read(op)
