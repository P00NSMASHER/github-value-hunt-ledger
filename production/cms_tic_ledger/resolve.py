#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import date
from pathlib import Path

import duckdb


def parquet_glob(root: Path, table: str) -> str:
    return str(root / "*" / "*" / table / "*.parquet")


def catalog_context(conn: sqlite3.Connection, file_key: str) -> dict:
    row=conn.execute(
        """SELECT url,last_updated_on,first_seen_at,last_seen_at
           FROM files WHERE file_key=?""",
        (file_key,),
    ).fetchone()
    plans=conn.execute(
        """SELECT p.plan_name,p.issuer_name,p.plan_id_type,p.plan_id,p.plan_market_type,
                  re.reporting_entity_name,re.reporting_entity_type
           FROM file_plans fp
           JOIN plans p ON p.plan_key=fp.plan_key
           LEFT JOIN reporting_entities re ON re.id=p.reporting_entity_id
           WHERE fp.file_key=?""",
        (file_key,),
    ).fetchall()
    return {
        "file": {
            "url": row[0] if row else None,
            "last_updated_on": row[1] if row else None,
            "first_seen_at": row[2] if row else None,
            "last_seen_at": row[3] if row else None,
        },
        "plans": [
            {
                "plan_name":p[0],"issuer_name":p[1],"plan_id_type":p[2],"plan_id":p[3],
                "plan_market_type":p[4],"reporting_entity_name":p[5],"reporting_entity_type":p[6],
            } for p in plans
        ],
    }


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--normalized-root", required=True)
    p.add_argument("--billing-code", required=True)
    p.add_argument("--service-date", required=True)
    p.add_argument("--npi")
    p.add_argument("--tin")
    p.add_argument("--billing-class")
    p.add_argument("--setting")
    p.add_argument("--service-code")
    p.add_argument("--modifier")
    p.add_argument("--limit", type=int, default=500)
    args=p.parse_args()

    service_date=date.fromisoformat(args.service_date).isoformat()
    root=Path(args.normalized_root).resolve()
    d=duckdb.connect()
    paths={name:parquet_glob(root,name) for name in (
        "items","rates","rate_provider_refs","prices","provider_groups","provider_npis"
    )}
    for path in paths.values():
        if not list(Path(root).glob(path.replace(str(root)+"/",""))):
            raise SystemExit(f"missing normalized parquet for query: {path}")

    provider_sql=""
    params=[]
    if args.npi:
        provider_sql = """
          AND EXISTS (
            SELECT 1 FROM read_parquet(?) pn
            WHERE pn.source_file_id=rpr.source_file_id
              AND pn.provider_group_id=rpr.provider_group_id
              AND pn.npi=?
          )
        """
        params += [paths["provider_npis"], args.npi]
    if args.tin:
        provider_sql += """
          AND EXISTS (
            SELECT 1 FROM read_parquet(?) pg
            WHERE pg.source_file_id=rpr.source_file_id
              AND pg.provider_group_id=rpr.provider_group_id
              AND replace(pg.tin_value,'-','')=replace(?,'-','')
          )
        """
        params += [paths["provider_groups"], args.tin]

    extra=[]
    if args.billing_class:
        extra.append("lower(p.billing_class)=lower(?)"); params.append(args.billing_class)
    if args.setting:
        extra.append("lower(p.setting)=lower(?)"); params.append(args.setting)
    if args.service_code:
        extra.append("list_contains(p.service_codes, ?)"); params.append(args.service_code)
    if args.modifier:
        extra.append("list_contains(p.billing_code_modifiers, ?)"); params.append(args.modifier)

    extra_sql=(" AND "+" AND ".join(extra)) if extra else ""
    sql=f"""
      SELECT DISTINCT
        i.source_file_id,
        i.source_sha256,
        i.billing_code_type,
        i.billing_code_type_version,
        i.billing_code,
        i.description,
        i.negotiation_arrangement,
        rpr.provider_group_id,
        p.negotiated_type,
        p.negotiated_rate,
        p.expiration_date,
        p.billing_class,
        p.setting,
        p.service_codes,
        p.billing_code_modifiers,
        p.additional_information
      FROM read_parquet(?) i
      JOIN read_parquet(?) r ON r.item_id=i.item_id
      JOIN read_parquet(?) rpr ON rpr.rate_id=r.rate_id
      JOIN read_parquet(?) p ON p.rate_id=r.rate_id
      WHERE i.billing_code=?
        {provider_sql}
        {extra_sql}
        AND (
          p.expiration_date IS NULL OR p.expiration_date='' OR
          p.expiration_date='9999-12-31' OR p.expiration_date>=?
        )
      LIMIT ?
    """
    base_params=[paths["items"],paths["rates"],paths["rate_provider_refs"],paths["prices"],args.billing_code]
    query_params=base_params+params+[service_date,args.limit]
    rows=d.execute(sql,query_params).fetchall()
    cols=[x[0] for x in d.description]

    cat=sqlite3.connect(args.catalog)
    evidence=[]
    for row in rows:
        item=dict(zip(cols,row))
        ctx=catalog_context(cat,item["source_file_id"])
        last_updated=ctx["file"].get("last_updated_on")
        if last_updated and service_date < last_updated:
            status="PRE_SNAPSHOT_NO_AUTHORITY"
        else:
            status="EVIDENCE_ONLY_NOT_CONTRACT_AUTHORITY"
        item["authority_status"]=status
        item["date_basis"]="payer_snapshot_last_updated_on"
        item["catalog"]=ctx
        evidence.append(item)

    distinct_semantics={
        (
            x["source_file_id"],x["provider_group_id"],x["negotiated_type"],
            x["negotiated_rate"],x["billing_class"],x["setting"],
            tuple(x["service_codes"] or []),tuple(x["billing_code_modifiers"] or [])
        ) for x in evidence if x["authority_status"]!="PRE_SNAPSHOT_NO_AUTHORITY"
    }
    if not evidence:
        overall="NO_RATE_EVIDENCE"
    elif all(x["authority_status"]=="PRE_SNAPSHOT_NO_AUTHORITY" for x in evidence):
        overall="PRE_SNAPSHOT_NO_AUTHORITY"
    elif len(distinct_semantics)>1:
        overall="REQUIRES_CLAIM_CONTEXT"
    else:
        overall="EVIDENCE_ONLY_NOT_CONTRACT_AUTHORITY"

    result={
        "status":overall,
        "billing_code":args.billing_code,
        "service_date":service_date,
        "npi":args.npi,
        "tin":args.tin,
        "result_count":len(evidence),
        "results":evidence,
        "rules":{
            "expiration_date_used_as_end_evidence":True,
            "payer_mrf_has_no_contract_effective_start":True,
            "service_date_before_snapshot_fails_closed":True,
            "contract_or_claim_context_required_for_money_bearing_recovery":True,
        },
    }
    print(json.dumps(result,indent=2,default=str))
    cat.close()
    d.close()
    return 0

if __name__=="__main__":
    raise SystemExit(main())
