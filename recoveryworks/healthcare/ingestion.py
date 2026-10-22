"""Strict authorized JSON intake. No file discovery, network I/O or silent skips."""
from dataclasses import fields, asdict
import hashlib
import json
from .models import (ScopeKey, SourceRef, ApprovedScope, Hold, ImportBatch,
                     CanonicalBatch, TABLE_TYPES, InvoiceLine)

MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 50000


def canonical_bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('utf-8')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def _reject_float(_value):
    raise ValueError('FLOAT_INPUT_FORBIDDEN')


def _depth(value, depth=0):
    if depth > 12:
        raise ValueError('EXCESSIVE_NESTING')
    if isinstance(value, dict):
        for item in value.values():
            _depth(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _depth(item, depth + 1)


def _record(cls, raw):
    if type(raw) is not dict:
        raise ValueError('INVALID_RECORD')
    allowed = {f.name for f in fields(cls)}
    if set(raw) - allowed:
        raise ValueError('UNKNOWN_FIELD')
    values = dict(raw)
    for key in ('source', 'authority_source', 'receipt_source', 'notice_source'):
        if key in values and values[key] is not None:
            if type(values[key]) is not dict:
                raise ValueError('INVALID_SOURCE')
            values[key] = SourceRef(**values[key])
    if type(values.get('scope')) is not dict:
        raise ValueError('MISSING_SCOPE')
    values['scope'] = ScopeKey(**values['scope'])
    if 'unsupported_components' in values:
        if type(values['unsupported_components']) is not list:
            raise ValueError('INVALID_COMPONENTS')
        values['unsupported_components'] = tuple(values['unsupported_components'])
    return cls(**values)


def import_json(data: bytes, scope: ApprovedScope) -> ImportBatch:
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise ValueError('INVALID_INPUT_SIZE')
    if type(scope) is not ApprovedScope:
        raise ValueError('APPROVED_SCOPE_REQUIRED')
    digest = hashlib.sha256(data).hexdigest()
    if digest != scope.source_hash:
        raise ValueError('SOURCE_HASH_MISMATCH')
    try:
        raw = json.loads(data.decode('utf-8'), object_pairs_hook=_pairs,
                         parse_float=_reject_float, parse_constant=_reject_float)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError('INVALID_JSON') from None
    _depth(raw)
    if type(raw) is not dict or type(raw.get('schema_version')) is not int or raw['schema_version'] != 1:
        raise ValueError('UNSUPPORTED_SCHEMA')
    if set(raw) - set(TABLE_TYPES) - {'schema_version'}:
        raise ValueError('UNKNOWN_FIELD')
    records, holds = [], []
    declared = dict(scope.declared_counts)
    observed = rejected = missing = 0
    for table, cls in TABLE_TYPES.items():
        rows = raw.get(table, [])
        if type(rows) is not list:
            raise ValueError('INVALID_RECORD_COLLECTION')
        observed += len(rows)
        if observed > MAX_ROWS:
            raise ValueError('ROW_LIMIT_EXCEEDED')
        expected = declared.get(table, 0)
        if len(rows) != expected:
            holds.append(Hold('INCOMPLETE_POPULATION', table))
            missing += max(expected - len(rows), 0)
        for i, row in enumerate(rows, 1):
            locator = f'{table}:{i}'
            try:
                record = _record(cls, row)
                if record.scope not in scope.scopes:
                    raise ValueError('SCOPE_NOT_AUTHORIZED')
                if cls is InvoiceLine and not scope.period_start <= record.invoice_date <= scope.as_of:
                    raise ValueError('INVOICE_OUTSIDE_APPROVED_PERIOD')
                records.append(record)
            except (ValueError, TypeError, KeyError) as exc:
                code = str(exc) if type(exc) is ValueError and str(exc).isupper() and ' ' not in str(exc) else 'INVALID_RECORD'
                holds.append(Hold(code, locator))
                rejected += 1
    if not raw.get('invoices'):
        holds.append(Hold('EMPTY_POPULATION', 'invoices'))
    normalized = hashlib.sha256(canonical_bytes(raw)).hexdigest()
    return ImportBatch(tuple(records), scope, tuple(holds), sum(declared.values()), observed,
                       len(records), rejected, missing, digest, normalized)


def validate_batch(batch: ImportBatch, scope: ApprovedScope) -> CanonicalBatch:
    if type(batch) is not ImportBatch or batch.scope != scope:
        raise ValueError('SCOPE_BINDING_MISMATCH')
    groups = {}
    for record in batch.records:
        groups.setdefault((type(record).__name__, record.scope, record.id), []).append(record)
    selected, holds, duplicates = [], list(batch.holds), 0
    for _, group in groups.items():
        signatures = set()
        for record in group:
            content = asdict(record)
            content.pop('source')
            signatures.add(canonical_bytes(content))
        if len(signatures) != 1:
            holds.append(Hold('CONFLICTING_RECORD_ID', type(group[0]).__name__, tuple(x.source for x in group)))
        else:
            selected.append(min(group, key=lambda x: (x.source.sha256, x.source.locator)))
            duplicates += len(group) - 1
    selected.sort(key=lambda x: (type(x).__name__, canonical_bytes(asdict(x))))
    return CanonicalBatch(tuple(selected), scope, tuple(holds), duplicates, batch)
