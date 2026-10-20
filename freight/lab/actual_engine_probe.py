"""Reproducible blind-to-engine synthetic TL rerating probe.

Only rates supported TL/PER_MILE invoices against independently computed integer-
cent expectations. It does not test OCR, billing duplicates, carrier settlements,
real customers, or customer data. Never treat perfect synthetic scores as production.
Run: python -m freight.lab.actual_engine_probe --count 10000
"""
import argparse
import hashlib
import json
import random
import statistics
import time

from freight.canonical_schema import SourceArtifact, ShipmentFacts, ChargeLine, build_record
from freight.rate_authority import compile_authority, AuthorityBook
from freight.rating_engine import rate_record, RATED


def expected_tl(per_mile: int, minimum: int, fuel_bps: int, miles: int) -> tuple[int,int]:
    base = max(minimum, per_mile*miles)
    return base, (base*fuel_bps+5000)//10000


def probe(count: int = 10000, seed: int = 41037) -> dict:
    rng = random.Random(seed)
    totals = dict(count=count,seed=seed,tp=0,tn=0,fp=0,fn=0,abstentions=0,
                  exact_expected=0,exact_variance=0,traceable=0,errors=[])
    times = []
    run_start = time.perf_counter()
    for i in range(count):
        per_mile=rng.randint(90,650)
        minimum=rng.randint(10000,160000)
        fuel_bps=rng.randrange(0,2101,100)
        miles=rng.randint(40,1700)
        base,fuel=expected_tl(per_mile,minimum,fuel_bps,miles)
        if i%5==0:
            billed_base,billed_fuel=base+rng.randint(100,20000),fuel
        elif i%5==1:
            billed_base,billed_fuel=base,fuel+rng.randint(100,4500)
        elif i%5==2:
            billed_base,billed_fuel=max(0,base-rng.randint(100,min(base,5500))),fuel
        else:
            billed_base,billed_fuel=base,fuel
        variance=max(0,billed_base+billed_fuel-base-fuel)
        truth=variance>0
        common=dict(buyer_id='SYN-BUYER',business_unit='SYN-BU',customer_id='SYN-CUST',currency='USD')
        authority=compile_authority(
            dict(authority_id=f'A-{i}',**common,carrier_id='SYN-CARRIER',
                 mode='TL',effective_from='2024-01-01',priority=10,
                 terms=dict(pricing_model='PER_MILE',per_mile_cents=per_mile,
                            minimum_cents=minimum,fuel_bps=fuel_bps)),
            source_sha256=hashlib.sha256(f'contract-{i}'.encode()).hexdigest(),
            verified_controlling_authority=True)
        source=SourceArtifact(source_id=f'SRC-{i}',kind='SYNTHETIC_INVOICE',
            sha256=hashlib.sha256(f'invoice-{i}'.encode()).hexdigest(),
            observed_at='2026-10-07T00:00:00.000000Z',transport='BATCH',
            filename=f'synthetic-{i}.json')
        shipment=ShipmentFacts(shipment_id=f'SHIP-{i}',carrier_id='SYN-CARRIER',
            mode='TL',service_date='2026-10-06',origin_postal='17901',
            destination_postal='21224',actual_weight_grams=5000000,
            package_count=1,miles=miles)
        record=build_record(**common,invoice_id=f'INV-{i}',invoice_date='2026-10-07',
            shipment=shipment,charges=(ChargeLine(f'BASE-{i}','LINEHAUL',billed_base),
                                      ChargeLine(f'FUEL-{i}','FUEL',billed_fuel)),sources=(source,))
        start=time.perf_counter()
        result=rate_record(record,AuthorityBook((authority,)))
        times.append((time.perf_counter()-start)*1000)
        positive=result.status==RATED and (result.variance_cents or 0)>0
        if result.status!=RATED:
            totals['abstentions']+=1
        elif truth and positive:totals['tp']+=1
        elif truth:totals['fn']+=1
        elif positive:totals['fp']+=1
        else:totals['tn']+=1
        totals['exact_expected']+=int(result.expected_total_cents==base+fuel)
        totals['exact_variance']+=int(result.variance_cents==variance)
        totals['traceable']+=int(result.record_hash==record.record_hash
                                 and len(result.rating_hash)==64 and result.authority_id==f'A-{i}')
        if result.status!=RATED and len(totals['errors'])<10:
            totals['errors'].append({'i':i,'status':result.status,'blockers':result.blockers})
    totals['seconds']=round(time.perf_counter()-run_start,3)
    totals['p50_ms']=round(statistics.median(times),5)
    totals['p95_ms']=round(sorted(times)[int(count*.95)],5)
    totals['precision']=totals['tp']/max(totals['tp']+totals['fp'],1)
    totals['recall']=totals['tp']/max(totals['tp']+totals['fn'],1)
    totals['specificity']=totals['tn']/max(totals['tn']+totals['fp'],1)
    totals['claim_boundary']='SYNTHETIC SUPPORTED TL RERATING ONLY; NOT PRODUCTION ACCURACY'
    return totals


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--count',type=int,default=10000)
    parser.add_argument('--seed',type=int,default=41037)
    args=parser.parse_args()
    print(json.dumps(probe(count=args.count,seed=args.seed),indent=2))
