"""RETALLY M52: atomic, local, durable technical review replay barrier.

M51 verifies two off-bundle Ed25519 technical witnesses but a valid signed
restore request can be presented repeatedly while its signatures are fresh.
M52 atomically consumes ONE restore request and TWO globally unique witness
nonces in a separate, explicitly provisioned SQLite review journal.

This is a LOCAL persisted deduplication gate; an operator with the ability
to delete/replace both the store and its trust environment can reset it.
A real distributed system needs ONE trusted shared source and an external
audit anchor. No restore is performed, no customer approval is granted, and
no signing secret, customer invoice or recovery database byte is recorded.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import os
import sqlite3
from typing import Any

from freight.settlement_file_identity_m47 import (
    create_exclusive_empty, identity, assert_identity,
)
from freight.recovery_witness_m51 import (
    HEX64, ROLES, TOKEN, signing_message,
)

SCOPE="RETALLY_M52_ONE_TIME_TECHNICAL_REVIEW_SQLITE_ONLY"
TECHNICAL_STATUS="TECHNICAL_WITNESSES_RECORDED_NO_CUSTOMER_ACTIVATION"
SQL_SCHEMA="""
CREATE TABLE review_consumptions (
    restore_request_id TEXT PRIMARY KEY NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    result_proof_sha256 TEXT NOT NULL,
    buyer_id TEXT NOT NULL,
    business_unit TEXT NOT NULL,
    audience TEXT NOT NULL,
    reviewed_at_utc TEXT NOT NULL,
    receipt_set_sha256 TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision='TECHNICAL_WITNESSES_RECORDED_NO_CUSTOMER_ACTIVATION')
);
CREATE TABLE witness_nonce_consumptions (
    nonce_hex TEXT PRIMARY KEY NOT NULL,
    restore_request_id TEXT NOT NULL REFERENCES review_consumptions(restore_request_id),
    witness_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('RECOVERY_OPERATOR','INDEPENDENT_SECURITY_REVIEWER')),
    public_key_sha256 TEXT NOT NULL,
    signed_payload_sha256 TEXT NOT NULL,
    UNIQUE(restore_request_id,role),
    UNIQUE(restore_request_id,witness_id)
);
CREATE TRIGGER immutable_review_consumptions_u BEFORE UPDATE ON review_consumptions
BEGIN SELECT RAISE(ABORT,'M52_IMMUTABLE_REVIEW_ROW'); END;
CREATE TRIGGER immutable_review_consumptions_d BEFORE DELETE ON review_consumptions
BEGIN SELECT RAISE(ABORT,'M52_IMMUTABLE_REVIEW_ROW'); END;
CREATE TRIGGER immutable_witness_nonce_u BEFORE UPDATE ON witness_nonce_consumptions
BEGIN SELECT RAISE(ABORT,'M52_IMMUTABLE_WITNESS_NONCE'); END;
CREATE TRIGGER immutable_witness_nonce_d BEFORE DELETE ON witness_nonce_consumptions
BEGIN SELECT RAISE(ABORT,'M52_IMMUTABLE_WITNESS_NONCE'); END;
"""

_CATALOG_TYPES=("table","trigger","index","view")


def _reject(reason:str)->None:
    # Never include customer identifiers, file locations or key material.
    raise ValueError("M52_REPLAY_"+reason)


def _catalog(conn:sqlite3.Connection)->dict:
    rows=conn.execute(
        "SELECT type,name,sql FROM sqlite_master "
        "WHERE type IN ('table','trigger','index','view') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY type,name"
    ).fetchall()
    out={}
    for kind,name,sql in rows:
        if (type(kind) is not str or type(name) is not str
            or type(sql) is not str or not name):
            _reject("INVALID_SQLITE_CATALOG")
        key=(kind,name)
        if key in out:
            _reject("DUPLICATE_SQLITE_CATALOG_OBJECT")
        out[key]=sql
    return out


def _expected_catalog()->dict:
    conn=sqlite3.connect(":memory:")
    try:
        conn.executescript(SQL_SCHEMA)
        result=_catalog(conn)
    finally:
        conn.close()
    if (set(k for k in result if k[0]=="table") != {
        ("table","review_consumptions"),
        ("table","witness_nonce_consumptions"),
    } or len(result)!=6):
        _reject("INCOMPLETE_APPROVED_SCHEMA_POLICY")
    return result


def _validate(conn:sqlite3.Connection)->dict:
    """Validate entire persistent replay record on one SQLite revision."""
    if _catalog(conn)!=_expected_catalog():
        _reject("SQLITE_REPLAY_SCHEMA_DRIFT")
    # M54: the journal's header security mode is part of validation,
    # without modifying M52's committed schema or auto-migrating files.
    from freight.recovery_mode_m54 import mode
    current_security_mode=mode(conn)
    if conn.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
        _reject("SQLITE_INTEGRITY_FAILURE")
    if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
        _reject("SQLITE_FOREIGN_KEY_FAILURE")
    rows=conn.execute(
        "SELECT restore_request_id,manifest_sha256,result_proof_sha256,"
        "buyer_id,business_unit,audience,reviewed_at_utc,receipt_set_sha256,decision "
        "FROM review_consumptions"
    ).fetchall()
    nonce_rows=conn.execute(
        "SELECT nonce_hex,restore_request_id,witness_id,role,"
        "public_key_sha256,signed_payload_sha256 "
        "FROM witness_nonce_consumptions"
    ).fetchall()
    counted={}
    roles={}
    seen_publics={}
    for nonce,req,witness,role,pub,payload in nonce_rows:
        if (type(nonce) is not str or not HEX64.fullmatch(nonce)
            or type(req) is not str or not TOKEN.fullmatch(req)
            or type(witness) is not str or not TOKEN.fullmatch(witness)
            or role not in ROLES or type(pub) is not str
            or not HEX64.fullmatch(pub) or type(payload) is not str
            or not HEX64.fullmatch(payload)):
            _reject("INVALID_DURABLE_NONCE_ENTRY")
        counted[req]=counted.get(req,0)+1
        roles.setdefault(req,set()).add(role)
        seen_publics.setdefault(req,set()).add(pub)
    for req,manifest,proof,buyer,unit,audience,when,receipt_sha,decision in rows:
        if (type(req) is not str or not TOKEN.fullmatch(req)
            or any(type(x) is not str or not x for x in (buyer,unit))
            or type(audience) is not str or not TOKEN.fullmatch(audience)
            or any(type(x) is not str or not HEX64.fullmatch(x)
                   for x in (manifest,proof,receipt_sha))
            or type(when) is not str or not when.endswith("Z")
            or decision != TECHNICAL_STATUS
            or counted.get(req)!=2 or roles.get(req)!=set(ROLES)
            or len(seen_publics.get(req,set()))!=2):
            _reject("PERSISTED_TECHNICAL_RECEIPT_TAMPERED")
        try:
            if datetime.fromisoformat(when.replace("Z","+00:00")).utcoffset() is None:
                _reject("PERSISTED_TECHNICAL_RECEIPT_TAMPERED")
        except ValueError:
            _reject("PERSISTED_TECHNICAL_RECEIPT_TAMPERED")
    if len(nonce_rows)!=2*len(rows):
        _reject("ORPHANED_OR_MISSING_WITNESS_NONCES")
    return {
        "technical_review_rows":len(rows),
        "durable_individual_witness_nonces":len(nonce_rows),
        "schema_and_local_history_consistent":True,
        "checkpoint_required_for_future_reviews":
            current_security_mode==54,
    }


class TechnicalReviewReplayLedger:
    """An explicitly managed separate SQLite journal for consumed reviews.

    Set create=True only for a consciously new journal. Existing mode never
    initializes, truncates or repairs a missing/invalid ledger. The database
    must be stored outside all recovery bundles and controlled by a separate
    administrator; that independent operational custody is not simulated.
    """
    def __init__(self,path:str|Path,*,create:bool=False,
                 busy_timeout_ms:int=5000):
        if (type(create) is not bool
            or type(busy_timeout_ms) is not int
            or busy_timeout_ms<100 or busy_timeout_ms>30000):
            _reject("INVALID_JOURNAL_OPTIONS")
        if str(path)==":memory:":
            _reject("FILE_BACKED_JOURNAL_REQUIRED")
        self.path=Path(path).absolute()
        self.busy_timeout_ms=busy_timeout_ms
        if create:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            if os.path.lexists(self.path):
                _reject("JOURNAL_ALREADY_EXISTS")
            create_exclusive_empty(self.path)
        self._identity=identity(self.path)
        conn=self._connect()
        try:
            if create:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript(SQL_SCHEMA)
            conn.execute("BEGIN")
            try:
                _validate(conn)
            finally:
                conn.rollback()
        finally:
            conn.close()
        self._check_identity()

    def _check_identity(self)->None:
        assert_identity(self.path,self._identity)

    def _connect(self)->sqlite3.Connection:
        self._check_identity()
        try:
            conn=sqlite3.connect(
                self.path.as_uri()+"?mode=rw",uri=True,
                isolation_level=None,
                timeout=self.busy_timeout_ms/1000,
            )
        except sqlite3.Error as err:
            self._check_identity()
            raise ValueError("M52_REPLAY_JOURNAL_UNREADABLE") from err
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
            self._check_identity()
            return conn
        except BaseException:
            conn.close()
            raise

    def verify(self)->dict:
        con=self._connect()
        try:
            con.execute("BEGIN")
            try:
                summary=_validate(con)
                self._check_identity()
                return summary
            finally:
                con.rollback()
        finally:
            con.close()

    def consume(self,*,manifest:dict,result,trust_registry:dict,
                witness_receipts:list|tuple,expected_restore_request_id:str,
                expected_audience:str,as_of_utc:datetime,
                checkpoint:object=None,custodian_trust:object=None,
                journal_namespace:str|None=None,
                checkpoint_audience:str|None=None)->dict:
        """Atomically consume verified technical review metadata ONLY.

        Caller must first run full M50/M51 source and signature validation.
        This internal method does not itself assert signatures; the public
        backup_restore.record_witnessed_recovery_review calls them first.
        """
        if (type(expected_restore_request_id) is not str
            or not TOKEN.fullmatch(expected_restore_request_id)
            or type(expected_audience) is not str
            or not TOKEN.fullmatch(expected_audience)
            or type(as_of_utc) is not datetime or as_of_utc.tzinfo is None
            or len(witness_receipts)!=2):
            _reject("INVALID_CONSUMPTION_CONTEXT")
        if checkpoint is None and any(value is not None for value in (
            custodian_trust,journal_namespace,checkpoint_audience
        )):
            _reject("CHECKPOINT_CONTEXT_WITHOUT_SIGNED_CHECKPOINT")
        reviewed_at=as_of_utc.astimezone(timezone.utc).isoformat(
            timespec="seconds"
        ).replace("+00:00","Z")
        signed_info=[]
        for receipt in witness_receipts:
            payload=receipt["payload"]
            witness_id=payload["witness_id"]
            entry=trust_registry[witness_id]
            signed_info.append((
                payload["nonce_hex"],expected_restore_request_id,witness_id,
                payload["role"],
                sha256(bytes.fromhex(entry["public_key_hex"])).hexdigest(),
                sha256(signing_message(payload)).hexdigest(),
            ))
        from freight.contracts import canonical_hash
        signed_digest=canonical_hash([
            (r[2],r[3],r[0],r[4],r[5]) for r in sorted(
                signed_info,key=lambda row:row[3]
            )
        ])
        con=self._connect()
        try:
            con.execute("BEGIN IMMEDIATE")
            try:
                _validate(con)
                from freight.recovery_mode_m54 import (
                    require_safe_mode,advance_mode,
                )
                # The local-only path CANNOT downgrade a journal once a
                # checkpointed review raised its durable mode under this
                # same write lock. A client opened earlier also sees mode
                # after waiting for a concurrent checkpoint transaction.
                require_safe_mode(
                    con,has_signed_checkpoint=checkpoint is not None
                )
                # M53 high-assurance mode: verify a signed, off-journal
                # replay checkpoint UNDER THE SAME BEGIN IMMEDIATE LOCK as
                # the one-time request/nonce inserts. Validation before
                # acquiring this lock would leave a rollback/TOCTOU race.
                checkpoint_proof=None
                if checkpoint is not None:
                    from freight.recovery_checkpoint_m53 import verify_checkpoint_locked
                    checkpoint_proof=verify_checkpoint_locked(
                        con,checkpoint=checkpoint,
                        custodian_trust=custodian_trust,
                        journal_namespace=journal_namespace,
                        expected_audience=checkpoint_audience,
                        as_of_utc=as_of_utc,
                    )
                self._check_identity()
                if con.execute(
                    "SELECT 1 FROM review_consumptions "
                    "WHERE restore_request_id=?",
                    (expected_restore_request_id,),
                ).fetchone() is not None:
                    _reject("REQUEST_ALREADY_CONSUMED")
                if any(con.execute(
                    "SELECT 1 FROM witness_nonce_consumptions WHERE nonce_hex=?",
                    (row[0],),
                ).fetchone() is not None for row in signed_info):
                    _reject("WITNESS_NONCE_ALREADY_CONSUMED")
                con.execute(
                    "INSERT INTO review_consumptions VALUES (?,?,?,?,?,?,?,?,?)",
                    (expected_restore_request_id,manifest["manifest_sha256"],
                     result.proof_hash,result.buyer_id,result.business_unit,
                     expected_audience,reviewed_at,signed_digest,TECHNICAL_STATUS)
                )
                for row in signed_info:
                    con.execute(
                        "INSERT INTO witness_nonce_consumptions "
                        "VALUES (?,?,?,?,?,?)",row
                    )
                if checkpoint_proof is not None:
                    # Flip 0->54 in the SAME BEGIN IMMEDIATE revision.
                    # Rejections/rollback undo BOTH the new reviews and
                    # this mode. The successor M53 signature will include
                    # this committed one-way security-mode elevation.
                    advance_mode(con,verified_checkpoint=True)
                summary=_validate(con)
                successor=None
                if checkpoint_proof is not None:
                    from freight.recovery_checkpoint_m53 import journal_state
                    successor=journal_state(con)
                self._check_identity()
                con.commit()
                self._check_identity()
            except BaseException:
                con.rollback()
                raise
        except sqlite3.IntegrityError as exc:
            raise ValueError("M52_REPLAY_ATOMIC_DUPLICATE_RECORD") from exc
        except sqlite3.OperationalError as exc:
            raise ValueError("M52_REPLAY_LOCKED_OR_IO_FAILED") from exc
        finally:
            con.close()
        outcome={
            "scope":SCOPE,
            "state":TECHNICAL_STATUS,
            "review_attempt_recorded_once":True,
            "local_request_id_is_globally_unique":True,
            "two_ephemeral_review_nonces_consumed":2,
            "review_event_rows_in_journal":summary["technical_review_rows"],
            "separate_from_customer_recovery_sqlite":True,
            "source_sqlite_bytes_modified":False,
            "real_customer_restore_activation_authorized":False,
            "legal_customer_or_bank_permission_verified":False,
            "independent_first_customer_approvals_unmet":18,
            "original_historical_findings_closed":0,
            "replay_ledger_is_locally_mutable_not_external_trust_anchor":True,
        }
        if successor is not None:
            # The next state is deliberately UNSIGNED. An independent
            # custodian must sign/store it outside the journal before
            # the next checkpointed review. A crash in between leaves
            # higher-assurance verification fail closed, not falsely ready.
            outcome.update({
                "m53_prior_checkpoint_verified_under_write_lock":True,
                "m53_signed_prior_sequence":checkpoint_proof["prior_signed_sequence"],
                "m53_successor_sequence":successor["review_sequence"],
                "m53_successor_state_sha256":successor["journal_state_sha256"],
                "m53_successor_requires_independent_external_signature":True,
                "m53_external_checkpoint_updated_by_this_operation":False,
                "m53_customer_activation_authorized":False,
            })
        return outcome
