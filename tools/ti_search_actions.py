#!/usr/bin/env python3
"""Reviewed action routing; retrieval terms must come from an explicit recipe."""
import copy
import hashlib
import json
import re
from pathlib import Path
from ti_common import INTEL, ROOT

ACTIONS = {'search', 'verify_artifact', 'execute_fixture', 'await_external'}
GATED_CAPABILITIES = {'CAP-014', 'CAP-015'}


def load_recipe_policy():
    return json.loads((INTEL / 'search_recipe_policy.json').read_text(encoding='utf-8'))


def parse_capability_ids(value):
    """Support the canonical compact form `CAP-002, 007, 008`."""
    return list(dict.fromkeys('CAP-' + x for x in re.findall(r'\b(?:CAP-)?(\d{3,})\b', value or '')))


def experiment_status(value):
    # Markdown punctuation and explanatory scope are not part of the state enum.
    match = re.match(r'\s*(READY|RUNNING|BLOCKED_EXTERNAL)\b', (value or '').replace('*', ''), re.I)
    return match.group(1).upper() if match else (value or '').replace('*', '').strip().upper()


def search_gate_open(plan, root=None):
    """Require an explicit reviewed, digest-bound execution receipt to reopen search."""
    root = (root or ROOT).resolve()
    gate = plan.get('search_gate') or {}
    state = gate.get('state', 'closed')
    if state == 'closed':
        return False
    if state != 'reopened':
        raise ValueError('search gate must be closed or reopened')
    evidence = gate.get('reopen_evidence') or {}
    if evidence.get('reviewed') is not True or not evidence.get('gap_id'):
        raise ValueError('reopened search gate requires reviewed evidence and a named gap')
    path = evidence.get('path')
    if not isinstance(path, str) or not path or Path(path).is_absolute():
        raise ValueError('reopen evidence must use a repository-relative path')
    receipt_path = (root / path).resolve()
    if not receipt_path.is_relative_to(root) or not receipt_path.is_file():
        raise ValueError('reopen evidence receipt is missing or outside the repository')
    raw = receipt_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != evidence.get('sha256'):
        raise ValueError('reopen evidence digest does not match the receipt')
    receipt = json.loads(raw)
    if (receipt.get('gate_id') != gate.get('gate_id') or
            receipt.get('gap_id') != evidence['gap_id'] or
            receipt.get('executed') is not True or
            receipt.get('result') != gate.get('required_evidence_result') or
            not receipt.get('next_search_question')):
        raise ValueError('reopen receipt does not establish the executed named gap')
    if (plan.get('work_action') != 'search' or not plan.get('query_templates') or
            not plan.get('next_action') or not plan.get('acceptance_target')):
        raise ValueError('reopened gate requires an explicit bounded search recipe')
    if any(not anchored_query(q, plan.get('query_anchors', [])) for q in plan['query_templates']):
        raise ValueError('reopened recipe lacks reviewed domain anchors')
    return True


def capability_recipe(cid, policy=None, root=None):
    policy = policy or load_recipe_policy()
    plan = copy.deepcopy(policy.get('capabilities', {}).get(cid) or {
        'work_action': 'await_external', 'query_anchors': [],
        'blocking_reason': 'recipe_review_required',
        'stop_conditions': ['No reviewed action/query recipe exists; record the missing hypothesis instead of synthesizing search words.']
    })
    plan.setdefault('query_templates', [])
    plan.setdefault('required_signatures', plan.get('query_anchors', []))
    plan['query_recipe_id'] = 'capability:' + cid.lower()
    if cid in GATED_CAPABILITIES:
        gate = plan.get('search_gate') or {}
        if not gate.get('closed_work_action') or not gate.get('required_evidence_result'):
            raise ValueError(f'{cid}: required search gate is missing')
        plan['search_gate_open'] = search_gate_open(plan, root)
        if not plan['search_gate_open']:
            plan['work_action'] = gate['closed_work_action']
            plan['query_templates'] = []
    return plan


def transfer_recipe(repository, policy=None):
    policy = policy or load_recipe_policy()
    for recipe in policy.get('transfer_recipes', []):
        if repository.lower() in {r.lower() for r in recipe.get('source_repositories', [])}:
            plan = copy.deepcopy(recipe)
            plan['query_recipe_id'] = plan['recipe_id']
            return plan
    return None


def anchored_query(query, anchors):
    return any(re.search(r'(?<![a-z0-9])' + re.escape(anchor.lower()) + r'(?![a-z0-9])', query.lower())
               for anchor in anchors if anchor)


def action_errors(row, policy=None):
    """Validate new packets; historical packets without work_action remain readable."""
    policy = policy or load_recipe_policy()
    instructions = row.get('instructions') or {}
    action = row.get('work_action', instructions.get('work_action', 'search'))
    queries = row.get('query_templates', instructions.get('queries', [])) or []
    errors = []
    if instructions.get('work_action') and instructions['work_action'] != action:
        errors.append('top-level action differs from instruction action')
    if action not in ACTIONS:
        errors.append('invalid work_action')
    if action != 'search' and queries:
        errors.append('non-search work must not carry discovery queries')
    for cid in row.get('capability_ids') or []:
        if cid in GATED_CAPABILITIES:
            recipe = capability_recipe(cid, policy)
            allowed = {recipe['search_gate']['closed_work_action'], 'await_external'}
            if recipe.get('search_gate_open'):
                allowed.add('search')
            if action not in allowed:
                errors.append(f'{cid} STOP gate forbids {action}')
            stops = row.get('stop_conditions', instructions.get('stop_conditions', []))
            for stop in capability_recipe(cid, policy)['stop_conditions']:
                if stop not in stops:
                    errors.append(f'{cid} STOP condition was not inherited')
    if action == 'search' and row.get('query_recipe_id'):
        anchors = row.get('query_anchors') or instructions.get('query_anchors') or []
        if not queries or not anchors:
            errors.append('recipe-backed search requires queries and domain anchors')
        elif any(not anchored_query(q, anchors) for q in queries):
            errors.append('query lacks its reviewed domain/protocol anchor')
    return errors


def inherited_fields(seed):
    """Coverage and measurement inherit both permission and query provenance."""
    return {key: copy.deepcopy(seed.get(key)) for key in
            ('work_action', 'query_recipe_id', 'query_anchors', 'action_gate', 'next_action', 'acceptance_target')}


def experiment_action(capability_ids):
    return 'verify_artifact' if 'CAP-015' in capability_ids else 'execute_fixture'


def capability_stops(capability_ids, policy=None):
    policy = policy or load_recipe_policy()
    return list(dict.fromkeys(stop for cid in capability_ids
                             for stop in capability_recipe(cid, policy).get('stop_conditions', [])))
