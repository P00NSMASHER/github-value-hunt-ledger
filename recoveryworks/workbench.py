"""Private, single-client operator workspace. No outbound claim transport."""
from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
from pathlib import Path
import secrets
from datetime import datetime, timezone

from .cli import write_private_json
from .durable_ledger import DurableRecoveryLedger
from .expansion_pilot import SOURCES
from .financial_events import CashEvent
from .journal import finding_from_payload
from .assurance import case_bundle_from_payload, authorization_from_payload, external_action_from_payload, verify_external_action
from .private_io import atomic_private_write, private_file_lock
from .runner import run_scan360_config
from .store import LocalBundleStore

SCHEMAS = {**SOURCES, 'freight': {'truth_manifest_json': (None, None)}}
ROLES = ('customer', 'reviewer', 'independent', 'operator')
MAX_UPLOAD = 5 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


class Workspace:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.meta = json.loads((self.root / 'workspace.json').read_text())
        self.store = LocalBundleStore(self.root / 'ledger.json')

    @classmethod
    def create(cls, root, client_id, *, simulation=True):
        root = Path(root)
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValueError('client_id required')
        if type(simulation) is not bool:
            raise ValueError('simulation must be boolean')
        root.mkdir(parents=True, mode=0o700, exist_ok=False)
        tokens = {role: secrets.token_urlsafe(32) for role in ROLES}
        write_private_json(root / 'workspace.json', {
            'schema': 1, 'client_id': client_id.strip(), 'simulation': simulation,
            'created_at': timestamp(), 'tokens': {
                sha(token.encode()): {'role': role, 'actor_id': ('SIMULATED/' if simulation else '') + role}
                for role, token in tokens.items()}})
        write_private_json(root / 'credentials.json', tokens)
        write_private_json(root / 'intake.json', {'sources': {}, 'settings': {}})
        return cls(root), tokens

    def principal(self, token):
        digest = sha(str(token).encode())
        # Constant-time digest comparisons; random bearer tokens never appear in logs.
        for stored, identity in self.meta['tokens'].items():
            if hmac.compare_digest(stored, digest):
                return identity
        raise PermissionError('invalid workspace credential')

    def require(self, token, roles):
        identity = self.principal(token)
        if identity['role'] not in roles:
            raise PermissionError('role cannot perform this action')
        return identity

    def _intake(self):
        return json.loads((self.root / 'intake.json').read_text())

    def upload(self, token, branch, source, content, mapping=None):
        identity = self.require(token, ('customer', 'operator'))
        if branch not in SCHEMAS or source not in SCHEMAS[branch]:
            raise ValueError('unsupported branch/source')
        if not isinstance(content, str) or not content or len(content.encode()) > MAX_UPLOAD:
            raise ValueError('upload empty or exceeds 5 MiB')
        raw = content.encode()
        headers, _ = SCHEMAS[branch][source]
        if headers:
            reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')), strict=True)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError('missing or duplicate input columns')
            required = headers.split(',')
            mapping = mapping or {column: column for column in required}
            if not isinstance(mapping, dict) or set(mapping) != set(required):
                raise ValueError('mapping must cover every required target column exactly once')
            if len(set(mapping.values())) != len(mapping) or not set(mapping.values()) <= set(reader.fieldnames):
                raise ValueError('mapping is ambiguous or references absent columns')
            # Preserve supported reversal/return columns when present, without guessing.
            optional = [c for c in ('Reverses_ID', 'Return_Of_Purchase_ID', 'Price_Unit', 'Quantity_Unit', 'Price_Units_Per_Quantity_Unit', 'Conversion_Basis', 'Conversion_Reviewer_ID') if c in reader.fieldnames and c not in required]
            output = io.StringIO(newline='')
            writer = csv.DictWriter(output, fieldnames=required + optional, lineterminator='\n')
            writer.writeheader()
            count = 0
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError('ragged CSV row')
                writer.writerow({**{target: row[origin] for target, origin in mapping.items()},
                                 **{key: row[key] for key in optional}})
                count += 1
            if count == 0:
                raise ValueError('source has no records')
            normalized = output.getvalue().encode()
        else:
            payload = json.loads(content)
            if not isinstance(payload, (list, dict)) or not payload:
                raise ValueError('JSON source must contain records')
            normalized = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
            count = len(payload) if isinstance(payload, list) else len(payload.get('findings', []))
        receipt_id = sha((branch + ':' + source + ':' + sha(normalized)).encode())
        extension = 'csv' if headers else 'json'
        path = 'sources/' + receipt_id + '.' + extension
        receipt = {'id': receipt_id, 'branch': branch, 'source': source, 'path': path,
                   'raw_sha256': sha(raw), 'normalized_sha256': sha(normalized), 'rows': count,
                   'mapping': mapping or {}, 'uploaded_by': identity['actor_id'], 'review': None,
                   'simulation': self.meta['simulation']}
        with private_file_lock(self.root / '.workspace.lock'):
            intake = self._intake()
            key = branch + '/' + source
            previous = intake['sources'].get(key)
            if previous and previous['id'] == receipt_id:
                return previous
            atomic_private_write(self.root / path, normalized)
            atomic_private_write(self.root / ('sources/' + receipt_id + '.original'), raw)
            intake['sources'][key] = receipt
            write_private_json(self.root / 'intake.json', intake)
        return receipt

    def upload_document(self, token, finding_id, kind, content):
        roles = {'case_bundle': ('reviewer', 'independent'), 'authorization': ('customer',),
                 'external_action': ('operator',), 'cash_event': ('operator',)}
        if kind not in roles:
            raise ValueError("unsupported case document")
        actor = self.require(token, roles[kind])
        if not isinstance(content, str) or len(content.encode()) > MAX_UPLOAD:
            raise ValueError("invalid document size")
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise ValueError("case document must be a JSON object")
        raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        with private_file_lock(self.root / '.workspace.lock'):
            ledger = self.store.load()
            if ledger is None or ledger.get(finding_id).finding.client_id != self.meta['client_id']:
                raise PermissionError("case outside workspace")
            digest = sha(raw)
            receipt_id = sha((finding_id + '/' + kind + '/' + digest).encode())
            record = {'id': receipt_id, 'finding_id': finding_id, 'kind': kind,
                      'path': 'sources/'+receipt_id+'.json', 'normalized_sha256': digest,
                      'raw_sha256': sha(content.encode()), 'uploaded_by': actor['actor_id'],
                      'review': None, 'simulation': self.meta['simulation']}
            intake = self._intake()
            documents = intake.setdefault('documents', {})
            if receipt_id in documents:
                return documents[receipt_id]
            atomic_private_write(self.root/record['path'], raw)
            atomic_private_write(self.root/('sources/'+receipt_id+'.original'), content.encode())
            documents[receipt_id] = record
            write_private_json(self.root/'intake.json', intake)
            return record

    def review_document(self, token, receipt_id, expected_sha256, note):
        actor = self.require(token, ('reviewer', 'independent'))
        if not isinstance(note, str) or not note.strip():
            raise ValueError("document review note required")
        with private_file_lock(self.root/'.workspace.lock'):
            intake = self._intake()
            record = intake.get('documents', {}).get(receipt_id)
            if record is None or record['uploaded_by'] == actor['actor_id']:
                raise ValueError("distinct document reviewer required")
            digest = sha((self.root/record['path']).read_bytes())
            if digest != expected_sha256 or digest != record['normalized_sha256']:
                raise ValueError("document changed since review")
            record['review'] = {'actor_id': actor['actor_id'], 'sha256': digest,
                               'note': note, 'at': timestamp(), 'simulation': self.meta['simulation']}
            write_private_json(self.root/'intake.json', intake)
            return record

    def _reviewed_document(self, receipt_id, finding_id, kind):
        record = self._intake().get('documents', {}).get(receipt_id)
        if not record or record['finding_id'] != finding_id or record['kind'] != kind or not record['review']:
            raise ValueError("reviewed in-scope " + kind + " document required")
        raw = (self.root/record['path']).read_bytes()
        if sha(raw) != record['normalized_sha256'] or sha(raw) != record['review']['sha256']:
            raise ValueError("reviewed document bytes changed")
        return json.loads(raw)

    def read_source(self, token, receipt_id):
        self.principal(token)
        intake = self._intake()
        record = next((r for r in list(intake['sources'].values()) + list(intake.get('documents', {}).values()) if r['id'] == receipt_id), None)
        if record is None:
            raise ValueError("source is not in this workspace")
        raw = (self.root / record['path']).read_bytes()
        if sha(raw) != record['normalized_sha256']:
            raise ValueError("source bytes changed")
        return {'content': raw.decode(), 'sha256': sha(raw)}

    def review_source(self, token, branch, source, expected_sha256, note):
        actor = self.require(token, ('reviewer', 'independent'))
        if not isinstance(note, str) or not note.strip():
            raise ValueError('review note required')
        with private_file_lock(self.root / '.workspace.lock'):
            intake = self._intake()
            record = intake['sources'][branch + '/' + source]
            digest = sha((self.root / record['path']).read_bytes())
            if digest != expected_sha256 or digest != record['normalized_sha256']:
                raise ValueError('source changed since review began')
            if actor['actor_id'] == record['uploaded_by']:
                raise ValueError('uploader cannot verify own source')
            record['review'] = {'actor_id': actor['actor_id'], 'sha256': digest,
                                'note': note.strip(), 'at': timestamp(), 'simulation': self.meta['simulation']}
            write_private_json(self.root / 'intake.json', intake)
        return record

    def configure(self, token, branch, settings):
        self.require(token, ('operator',))
        allowed = {'ap': {'default_effective_from'}, 'utility': {'default_effective_from', 'utility_id'},
                   'rebate': {'as_of_date'}}.get(branch, set())
        if branch not in SCHEMAS or not isinstance(settings, dict) or not set(settings) <= allowed:
            raise ValueError('unsupported settings')
        for key, value in settings.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError('setting requires text')
            if key != 'utility_id':
                from datetime import date
                date.fromisoformat(value)
        with private_file_lock(self.root / '.workspace.lock'):
            intake = self._intake()
            intake['settings'][branch] = settings
            write_private_json(self.root / 'intake.json', intake)

    def scan(self, token):
        self.require(token, ('operator',))
        with private_file_lock(self.root / '.workspace.lock'):
            intake = self._intake()
            config = {'client_id': self.meta['client_id'], 'currency': 'USD'}
            active = {item['branch'] for item in intake['sources'].values()}
            if not active:
                raise ValueError('upload branch sources first')
            for branch in sorted(active):
                job = dict(intake['settings'].get(branch, {}))
                for source, (_, flag) in SCHEMAS[branch].items():
                    record = intake['sources'].get(branch + '/' + source)
                    if not record or not record['review']:
                        raise ValueError(branch + '/' + source + ': source review required')
                    digest = sha((self.root / record['path']).read_bytes())
                    if digest != record['normalized_sha256'] or digest != record['review']['sha256']:
                        raise ValueError('reviewed source bytes changed')
                    job[source] = record['path']
                    if flag:
                        job[flag] = True
                config[branch] = job
            result = run_scan360_config(config, state_path=self.store.path, base_dir=self.root).as_dict()
            result['simulation'] = self.meta['simulation']
            result['commercially_validated'] = False
            write_private_json(self.root / 'scan-report.json', result)
            return result

    def cases(self, token):
        actor = self.principal(token)
        ledger = self.store.load() or DurableRecoveryLedger()
        holds = ledger.reconciliation_holds()
        scan = json.loads((self.root / 'scan-report.json').read_text()) if (self.root / 'scan-report.json').exists() else {}
        return {'client_id': self.meta['client_id'], 'simulation': self.meta['simulation'], 'actor': actor,
                'head_hash': ledger.journal.head_hash, 'sources': self._intake()['sources'],
                'documents': self._intake().get('documents', {}),
                'schemas': SCHEMAS, 'conflicts': [e for e in scan.get('exceptions', []) if e.get('code') == 'ECONOMIC_LOSS_CONFLICT'], 'cases': [{
                    'finding_id': r.finding.finding_id, 'branch': r.finding.branch.value,
                    'counterparty': r.finding.counterparty_id, 'reference': r.finding.reference,
                    'state': r.case_state.value, 'potential_cents': r.finding.potential_recovery_cents,
                    'recovered_cents': r.recovered_cents, 'fee_cents': r.fee_cents,
                    'remaining_cents': r.finding.potential_recovery_cents - r.recovered_cents,
                    'hold': holds.get(r.finding.finding_id), 'record_hash': r.record_hash,
                    'primary_reviewer': r.reviewer_id, 'independent_reviewer': r.independent_reviewer_id,
                    'evidence': [{'kind': e.kind, 'locator': e.locator, 'sha256': e.source_hash} for e in r.finding.evidence]
                } for r in ledger.active_records() if r.finding.client_id == self.meta['client_id']]}

    def action(self, token, action, finding_id, expected_head, data):
        roles = {'approve': ('reviewer',), 'independent': ('independent',),
                 'authorize': ('customer',), 'claim': ('operator',), 'cash': ('operator',),
                 'hold': ('reviewer', 'independent'), 'resolve': ('independent',), 'revise': ('independent',)}
        if action not in roles:
            raise ValueError('unsupported case action')
        actor = self.require(token, roles[action])
        with private_file_lock(self.root / '.workspace.lock'):
            ledger = self.store.load()
            if ledger is None or ledger.journal.head_hash != expected_head:
                raise ValueError('stale workspace; refresh before acting')
            record = ledger.get(finding_id)
            if record.finding.client_id != self.meta['client_id']:
                raise PermissionError('case outside workspace')
            note = data.get('note', '')
            if action == 'approve':
                ledger.approve(finding_id, actor['actor_id'], note)
            elif action == 'independent':
                ledger.independent_approve(finding_id, actor['actor_id'], note)
            elif action == 'authorize':
                if not record.independent_reviewer_id:
                    raise ValueError('two independent reviews required before customer authorization')
                if not isinstance(note, str) or not note.strip():
                    raise ValueError('authorization scope note required')
                if self.meta['simulation']:
                    ledger.authorize(finding_id, 'SIMULATED/customer-authorization:' + sha((finding_id + expected_head + note).encode()))
                else:
                    bundle = case_bundle_from_payload(self._reviewed_document(data.get('bundle_document_id'), finding_id, 'case_bundle'))
                    authorization = authorization_from_payload(self._reviewed_document(data.get('authorization_document_id'), finding_id, 'authorization'))
                    if authorization.client_actor_id != actor['actor_id']:
                        raise ValueError('authorization actor differs from signed-in customer')
                    ledger.authorize_with_case(finding_id, bundle, authorization)
            elif action == 'claim':
                # Local bookkeeping only. This endpoint never contacts a counterparty.
                envelope = None
                if not self.meta['simulation']:
                    document = self._reviewed_document(data.get('document_id'), finding_id, 'external_action')
                    envelope = external_action_from_payload(document['envelope'])
                    bundle = case_bundle_from_payload(self._reviewed_document(data.get('bundle_document_id'), finding_id, 'case_bundle'))
                    authorization = authorization_from_payload(self._reviewed_document(data.get('authorization_document_id'), finding_id, 'authorization'))
                    verify_external_action(envelope, bundle, authorization, artifact_bytes=document['artifact_text'].encode())
                    from .models import normalize_utc_timestamp
                    submitted = normalize_utc_timestamp('submitted_at', document['submitted_at'])
                    if not isinstance(document.get('submission_reference'), str) or not document['submission_reference'].strip():
                        raise ValueError('external submission reference required')
                    if submitted < envelope.prepared_at or submitted > timestamp():
                        raise ValueError('invalid externally submitted time')
                    if authorization.expires_at and submitted > authorization.expires_at:
                        raise ValueError('submission occurred after customer authorization expired')
                    if any(d.deadline_at and submitted > d.deadline_at for d in bundle.deadlines):
                        raise ValueError('submission occurred after assessed deadline')
                ledger.mark_claimed(finding_id, envelope)
            elif action == 'cash':
                if not self.meta['simulation']:
                    payload = self._reviewed_document(data.get('document_id'), finding_id, 'cash_event')
                    event = CashEvent(**{**payload, 'verified': True})
                    if event.finding_id != finding_id:
                        raise ValueError('cash event case mismatch')
                else:
                    previous = ledger._cash_events.get((record.finding.client_id, data['event_id']))
                    event = CashEvent(event_id=data['event_id'], finding_id=finding_id,
                                      amount_cents=data['amount_cents'], fee_cents=data.get('fee_cents', 0),
                                      currency=record.finding.currency, source_hash=data['source_hash'],
                                      source_locator='simulation://' + data['event_id'],
                                      observed_at=previous.observed_at if previous else timestamp(),
                                      verified=True, reverses_id=data.get('reverses_id'))
                ledger.post_cash_event(event)
            elif action == 'hold':
                if not isinstance(note, str) or not note.strip():
                    raise ValueError('hold reason required')
                ledger.hold_for_reconciliation(finding_id, actor['actor_id'] + ': ' + note)
            elif action in {'resolve', 'revise'}:
                primary = ledger.reconciliation_holds().get(finding_id, '').split(': ', 1)[0]
                if primary != ('SIMULATED/' if self.meta['simulation'] else '') + 'reviewer':
                    raise ValueError('primary reviewer must record their reconciliation hold before release')
                review = dict(reviewer_id=primary, independent_reviewer_id=actor['actor_id'],
                              evidence_hash=data['evidence_hash'], expected_record_hash=data['expected_record_hash'],
                              expected_hold_hash=ledger.reconciliation_hold_hash(finding_id), note=note)
                if action == 'resolve':
                    ledger.resolve_reconciliation(finding_id, **review)
                else:
                    scan = json.loads((self.root / 'scan-report.json').read_text())
                    pending = [e['replacement'] for e in scan['exceptions']
                               if e.get('code') == 'ECONOMIC_LOSS_CONFLICT' and e.get('existing_finding_id') == finding_id
                               and e['replacement']['finding_id'] == data.get('replacement_id')]
                    if len(pending) != 1:
                        raise ValueError('select exactly one stored replacement candidate')
                    ledger.revise_held_case(finding_id, finding_from_payload(pending[0]), **review)
            self.store.save(ledger, expected_head_hash=expected_head, enforce_expected=True)
            return {'head_hash': ledger.journal.head_hash, 'simulation': self.meta['simulation'],
                    'external_action_sent': False}

    def backup(self, token):
        self.require(token, ('operator',))
        with private_file_lock(self.root / '.workspace.lock'):
            ledger = self.store.load() or DurableRecoveryLedger()
            bundle = ledger.export_bundle()
            restored = DurableRecoveryLedger.from_bundle(bundle)
            if restored.journal.head_hash != ledger.journal.head_hash:
                raise ValueError('restore rehearsal failed')
            names = ['workspace.json', 'intake.json']
            names += [p.name for p in (self.root/'ledger.json', self.root/'scan-report.json') if p.exists()]
            names += ['sources/'+p.name for p in (self.root/'sources').glob('*') if p.is_file()]
            files = {name: {'content': (self.root/name).read_text(),
                            'sha256': sha((self.root/name).read_bytes())} for name in sorted(names)}
            snapshot = {'schema': 1, 'simulation': self.meta['simulation'],
                        'journal_head': ledger.journal.head_hash, 'files': files}
            identity = sha(json.dumps(snapshot, sort_keys=True).encode())
            write_private_json(self.root/('backups/'+identity+'.json'), snapshot)
            # Restore every captured file into a new isolated temporary workspace, then replay it.
            import tempfile
            with tempfile.TemporaryDirectory() as directory:
                check = self.restore_snapshot(snapshot, Path(directory)/'restore')
                replay = check.store.load()
                actual = replay.journal.head_hash if replay else None
                if actual != ledger.journal.head_hash:
                    raise ValueError('snapshot restore head mismatch')
            return {'snapshot_id': identity, 'journal_head': ledger.journal.head_hash,
                    'restore_verified': True, 'files_verified': len(files),
                    'simulation': self.meta['simulation']}

    @classmethod
    def restore_snapshot(cls, snapshot, destination):
        import re
        if snapshot.get('schema') != 1 or not isinstance(snapshot.get('files'), dict):
            raise ValueError('unsupported snapshot')
        files = snapshot['files']
        if not {'workspace.json', 'intake.json'} <= files.keys():
            raise ValueError('incomplete workspace snapshot')
        for name, item in files.items():
            if name not in {'workspace.json', 'intake.json', 'ledger.json', 'scan-report.json'} and not re.fullmatch(r'sources/[a-f0-9]{64}\.(csv|json|original)', name):
                raise ValueError('invalid snapshot path')
            if not isinstance(item, dict) or not isinstance(item.get('content'), str) or sha(item['content'].encode()) != item.get('sha256'):
                raise ValueError('snapshot file integrity failure')
        intake = json.loads(files['intake.json']['content'])
        for record in list(intake['sources'].values()) + list(intake.get('documents', {}).values()):
            item = files.get(record['path'])
            if item is None or item['sha256'] != record['normalized_sha256']:
                raise ValueError('snapshot source missing or changed')
            original = files.get('sources/'+record['id']+'.original')
            if original is None or original['sha256'] != record['raw_sha256']:
                raise ValueError('snapshot original evidence missing or changed')
        root = Path(destination)
        root.mkdir(mode=0o700, parents=True, exist_ok=False)
        for name,item in files.items():
            atomic_private_write(root/name,item['content'].encode())
        workspace=cls(root)
        ledger=workspace.store.load()
        if (ledger.journal.head_hash if ledger else None) != snapshot['journal_head']:
            raise ValueError('snapshot journal mismatch')
        if workspace.meta['simulation'] != snapshot['simulation']:
            raise ValueError('snapshot environment mismatch')
        return workspace
