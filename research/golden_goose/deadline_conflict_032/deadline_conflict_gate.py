"""Research-only deadline disagreement gate: never certifies a current bid deadline."""
from datetime import datetime
from decimal import Decimal

TYPES = {"third_party_headline", "third_party_embedded_description", "third_party_raw_snapshot", "official_agency_portal_link"}

def parse_local(value):
    if not isinstance(value, str) or len(value) != 16:
        raise ValueError("noncanonical datetime")
    dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
    if dt.strftime("%Y-%m-%d %H:%M") != value:
        raise ValueError("noncanonical datetime")
    return dt

def evaluate(record):
    if not isinstance(record, dict) or not isinstance(record.get("solicitation_id"), str) or not record["solicitation_id"].strip():
        raise ValueError("missing solicitation identity")
    obs = record.get("observations")
    if not isinstance(obs, list) or not obs:
        raise ValueError("missing observations")
    claims = []
    seen = set()
    for o in obs:
        if not isinstance(o, dict) or o.get("kind") not in TYPES or not isinstance(o.get("url"), str) or not o["url"].startswith("https://"):
            raise ValueError("missing provenance")
        if o["kind"] == "official_agency_portal_link":
            if o.get("close_local") is not None:
                raise ValueError("unfetched official portal cannot assert deadline")
            continue
        if o.get("tz") != "America/Los_Angeles":
            raise ValueError("unverified timezone")
        dt = parse_local(o.get("close_local"))
        key = (o["url"], o["kind"], str(dt))
        if key not in seen:
            seen.add(key)
            claims.append(dt)
    if not claims:
        return {"status":"SOURCE_INSUFFICIENT", "distinct_deadlines":0, "local_calendar_gap_days":0, "decision_deadline":None, "claim_count":0, "requires_official_review":True}
    distinct = sorted(set(claims))
    return {"status":"CONFLICT_REVIEW" if len(distinct)>1 else "UNCONFIRMED_SINGLE_DATE",
            "distinct_deadlines":len(distinct),
            "local_calendar_gap_days":(distinct[-1].date()-distinct[0].date()).days,
            "decision_deadline":None, "claim_count":len(claims), "requires_official_review":True}

def fictional_unit_economics(price="49", review_minutes=20, labor_hourly="45", fixed_cost="5"):
    p,m,h,f = map(Decimal, (str(price), str(review_minutes), str(labor_hourly), str(fixed_cost)))
    if min(p,m,h,f) < 0: raise ValueError("negative money/time")
    return {"assumed_fee":str(p),"assumed_contribution_per_paid_audit":str(p-f-m*h/Decimal(60)),
            "verified_sales":0,"verified_revenue":"0"}
