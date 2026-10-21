"""Customer audit scope and exact-population review for the private workbench.

These attestations record authorized role decisions, not external identity proof.
They authorize analysis only; case-level claim authority remains separate.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
import hashlib
import json
from .cli import write_private_json
from .private_io import private_file_lock


def digest(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def population(intake, branch):
    return {'sources': {key: {field: value[field] for field in
                              ('id', 'rows', 'raw_sha256', 'normalized_sha256')}
                        for key, value in sorted(intake['sources'].items()) if value['branch'] == branch},
            'settings': intake['settings'].get(branch, {})}


class OnboardingMixin:
    def submit_onboarding(self, token, branch, scope):
        actor = self.require(token, ('customer',))
        from .workbench import SCHEMAS
        if branch not in SCHEMAS or not isinstance(scope, dict):
            raise ValueError('supported branch and audit scope required')
        required = {'period_start', 'period_end', 'currency', 'account_scope', 'source_system',
                    'exclusions', 'population_reconciliation', 'expected_rows', 'authorized_to_analyze'}
        if set(scope) != required or scope['authorized_to_analyze'] is not True:
            raise ValueError('complete scope and customer authorization to analyze required')
        for key in required - {'expected_rows', 'authorized_to_analyze'}:
            if not isinstance(scope[key], str) or not scope[key].strip() or len(scope[key]) > 4000:
                raise ValueError('scope text required: ' + key)
        start, end = date.fromisoformat(scope['period_start']), date.fromisoformat(scope['period_end'])
        if start > end or end > date.today():
            raise ValueError('invalid audit period')
        if scope['currency'] != self.meta.get('currency', 'USD'):
            raise ValueError('scope currency must match workspace currency')
        with private_file_lock(self.root / '.workspace.lock'):
            intake = self._intake()
            current = population(intake, branch)
            required_sources = {branch + '/' + source for source in SCHEMAS[branch]}
            if set(current['sources']) != required_sources:
                raise ValueError('upload the complete branch source set before authorizing analysis')
            counts = scope['expected_rows']
            if not isinstance(counts, dict) or set(counts) != required_sources:
                raise ValueError('independent exported row counts required for every source')
            for key, count in counts.items():
                if type(count) is not int or count < 0 or count != current['sources'][key]['rows']:
                    raise ValueError('exported row count does not reconcile: ' + key)
            record = {'scope': scope, 'population_hash': digest(current), 'customer_actor': actor['actor_id'],
                      'authorized_at': now(), 'simulation': self.meta['simulation']}
            record['scope_hash'] = digest(record)
            previous = intake.setdefault('onboarding', {}).get(branch)
            if previous:
                intake.setdefault('onboarding_history', []).append(previous)
            intake['onboarding'][branch] = {**record, 'review': None}
            write_private_json(self.root / 'intake.json', intake)
            return intake['onboarding'][branch]

    def review_onboarding(self, token, branch, expected_scope_hash, note):
        actor = self.require(token, ('reviewer', 'independent'))
        if not isinstance(note, str) or not note.strip() or len(note) > 4000:
            raise ValueError('scope review note required')
        with private_file_lock(self.root / '.workspace.lock'):
            intake = self._intake()
            record = intake.get('onboarding', {}).get(branch)
            if not record or record['scope_hash'] != expected_scope_hash:
                raise ValueError('stale or missing audit scope')
            if record['customer_actor'] == actor['actor_id']:
                raise PermissionError('customer cannot independently review audit scope')
            errors = self._onboarding_errors(intake, branch, require_review=False)
            if errors:
                raise ValueError('; '.join(errors))
            record['review'] = {'actor_id': actor['actor_id'], 'scope_hash': expected_scope_hash,
                                'note': note.strip(), 'reviewed_at': now()}
            write_private_json(self.root / 'intake.json', intake)
            return record

    def _onboarding_errors(self, intake, branch, *, require_review=True):
        record = intake.get('onboarding', {}).get(branch)
        if not record:
            return ['customer audit scope and population reconciliation required']
        unsigned = {k: v for k, v in record.items() if k not in {'scope_hash', 'review'}}
        errors = []
        if digest(unsigned) != record['scope_hash']:
            errors.append('audit scope changed')
        if record['population_hash'] != digest(population(intake, branch)):
            errors.append('sources or settings changed; renew customer scope and review')
        if require_review and (not record.get('review') or record['review']['scope_hash'] != record['scope_hash']):
            errors.append('independent audit scope review required')
        for source in intake['sources'].values():
            if source['branch'] != branch:
                continue
            review = source.get('review')
            if not review or review['sha256'] != source['normalized_sha256']:
                errors.append(source['source'] + ': source review required')
            path = self.root / source['path']
            original = self.root / ('sources/' + source['id'] + '.original')
            if (not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != source['normalized_sha256']
                    or not original.is_file() or hashlib.sha256(original.read_bytes()).hexdigest() != source['raw_sha256']):
                errors.append(source['source'] + ': source integrity failure')
        settings = intake['settings'].get(branch, {})
        if branch in {'ap', 'utility'}:
            try:
                date.fromisoformat(settings['default_effective_from'])
            except (KeyError, TypeError, ValueError):
                errors.append('evidence-supported default effective date required')
        if branch == 'utility' and not settings.get('utility_id', '').strip():
            errors.append('actual utility identity required')
        if branch == 'rebate':
            try:
                audit_date = date.fromisoformat(settings['as_of_date'])
                if audit_date > date.today():
                    raise ValueError('future audit date')
                receipt = intake['sources']['rebate/programs_json']
                programs = json.loads((self.root / receipt['path']).read_text())
                if not isinstance(programs, list) or not programs:
                    raise ValueError('program list required')
                for program in programs:
                    due = date.fromisoformat(program['payment_due_date'])
                    if due < date.fromisoformat(program['period_end']):
                        raise ValueError('payment due before earned period end')
            except (KeyError, TypeError, ValueError, OSError):
                errors.append('rebate requires explicit payment due dates and a nonfuture audit date')
        return errors

    def onboarding_status(self, intake=None):
        from .workbench import SCHEMAS
        intake = self._intake() if intake is None else intake
        return {branch: {'analysis_ready': not (errors := self._onboarding_errors(intake, branch)),
                         'blockers': errors, 'record': intake.get('onboarding', {}).get(branch)}
                for branch in SCHEMAS}
