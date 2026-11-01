#!/usr/bin/env python3
"""Fail-closed, standard-library-only bounds for read-only public ledger crawlers."""
from __future__ import annotations
import argparse
from pathlib import Path
import re

LIMITS={"tic":("max_indexes",60),"urdb":("history_limit",100)}
MAX_RETENTION_DAYS=90

def bounded_integer(value:str,*,label:str,maximum:int)->int:
    if not isinstance(value,str) or re.fullmatch(r"[1-9][0-9]{0,2}",value) is None:
        raise ValueError(f"{label} must be canonical positive decimal")
    result=int(value)
    if result>maximum:
        raise ValueError(f"{label} exceeds approved limit {maximum}")
    return result

def run_now_value(path:Path,key:str)->str:
    lines=path.read_text(encoding="utf-8").splitlines()
    matches=[line.split("=",1)[1] for line in lines if line.startswith(key+"=")]
    if len(matches)!=1:
        raise ValueError(f"RUN_NOW must contain exactly one {key} marker")
    return matches[0]

def reviewed_parameters(*,lane:str,event:str,requested:str,retention:str,run_now:Path)->dict[str,int]:
    if lane not in LIMITS: raise ValueError("Unapproved ledger")
    if event not in ("push","workflow_dispatch"): raise ValueError("Unapproved event")
    key,cap=LIMITS[lane]
    actual=run_now_value(run_now,key) if event=="push" else requested
    return {key:bounded_integer(actual,label=key,maximum=cap),
            "retention_days":bounded_integer(retention,label="retention_days",maximum=MAX_RETENTION_DAYS)}

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--lane",choices=LIMITS,required=True)
    p.add_argument("--event",required=True)
    p.add_argument("--value",required=True)
    p.add_argument("--retention",required=True)
    p.add_argument("--run-now",type=Path,required=True)
    args=p.parse_args()
    output=reviewed_parameters(lane=args.lane,event=args.event,requested=args.value,
                               retention=args.retention,run_now=args.run_now)
    for key,value in output.items(): print(f"{key}={value}")

if __name__=="__main__": main()
