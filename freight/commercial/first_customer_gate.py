"""RETALLY first-customer gate evaluation. No network, credentials or client data.

The evidence register is a bounded, explicitly unapproved snapshot. A status is not
VERIFIED unless independent owner/reviewer/timestamp/source evidence is present.
Exit 2 on requested but blocked readiness. No tool can authorize a customer itself.
"""
from __future__ import annotations
import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

DEFAULT = Path(__file__).with_name("first_customer_acceptance_m2g.json")


def verified(item):
    if item.get("status") != "VERIFIED":
        return False
    for key in ("evidence_ref", "reviewed_by", "reviewed_at"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            return False
    try:
        date.fromisoformat(item["reviewed_at"][:10])
    except ValueError:
        return False
    return True


def evaluate(snapshot):
    f = snapshot["published_synthetic_sample"]
    D = lambda k: Decimal(f[k])
    if D("gross_recovered_usd")-D("reversals_usd") != D("net_recovered_usd"):
        raise ValueError("gross/net sample arithmetic inconsistent")
    if D("net_recovered_usd")-D("published_fee_eligible_usd") != D("unallocated_difference_usd"):
        raise ValueError("sample eligibility delta inconsistent")
    if f.get("customer_result") is not False:
        raise ValueError("synthetic example must not be designated customer proof")
    status = snapshot["requirements"]
    gates = {}
    for name, required in snapshot["readiness_gates"].items():
        unknown = [key for key in required if key not in status]
        if unknown:
            raise ValueError(f"unknown required evidence fields: {unknown}")
        missing = [key for key in required if not verified(status[key])]
        if name in ("claims_recovery",) and snapshot["founding_offer"]["actual_contingency_rate"] == "NOT_APPROVED":
            missing.append("approved_actual_contingency_terms")
        gates[name] = {"ready": not missing, "missing":missing}
    if snapshot["production"]["inquiry_get_body"].get("online") is False and snapshot["production"]["online_inquiry_status"] != "DISABLED_BY_POLICY":
        raise ValueError("inquiry readiness contradicts observed disabled capability")
    return {
        "as_of": snapshot["as_of"], "release_policy": snapshot["release_policy"],
        "sample_fee_eligibility_verified":verified(status["synthetic_fee_eligibility_reconciled"]),
        "gates": gates,
        "all_customer_pilot_gates_ready": gates["confidential_pilot"]["ready"] and gates["qualified_proposal"]["ready"],
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT)
    parser.add_argument("--require", choices=["contact","qualified_proposal","confidential_pilot","claims_recovery","sample_publication"])
    args=parser.parse_args()
    result=evaluate(json.loads(args.source.read_text(encoding="utf-8")))
    print(json.dumps(result,indent=2,sort_keys=True))
    if args.require and not result["gates"][args.require]["ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
