"""Standard RecoveryWorks adapters for branch engines.

These adapters intentionally do not calculate domain money. A vertical engine must
first produce a BranchInput with deterministic expected/actual cents and proof refs.
RecoveryOS then applies the common branch recovery mode and evidence gates.
"""
from __future__ import annotations

from .base import RuleBackedAdapter
from recoveryworks.models import Branch


class FreightAdapter(RuleBackedAdapter):
    branch = Branch.FREIGHT


class PayerAdapter(RuleBackedAdapter):
    branch = Branch.PAYER


class UtilityAdapter(RuleBackedAdapter):
    branch = Branch.UTILITY


class APAdapter(RuleBackedAdapter):
    branch = Branch.AP


class ConstructionAdapter(RuleBackedAdapter):
    branch = Branch.CONSTRUCTION


class DutyAdapter(RuleBackedAdapter):
    branch = Branch.DUTY


ADAPTERS: dict[Branch, RuleBackedAdapter] = {
    Branch.FREIGHT: FreightAdapter(),
    Branch.PAYER: PayerAdapter(),
    Branch.UTILITY: UtilityAdapter(),
    Branch.AP: APAdapter(),
    Branch.CONSTRUCTION: ConstructionAdapter(),
    Branch.DUTY: DutyAdapter(),
}


def adapter_for(branch: Branch) -> RuleBackedAdapter:
    try:
        return ADAPTERS[branch]
    except KeyError as exc:
        raise ValueError(f"unsupported recovery branch: {branch!r}") from exc
