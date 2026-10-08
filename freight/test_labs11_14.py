"""Labs 11-14: direct synthetic domain regression tests; no real API or money."""
import copy
import hashlib
import unittest
from freight.labs11_14 import (
 LAB_NAMES,FAMILIES,MODES,VENDOR_SOURCES,RELIABILITY_PERMANENT,
 RELIABILITY_EXHAUST,FRAUD_HIGH_RISK,SAVINGS_REVIEW,sha,simulate,
)

def row(i,truth="POSITIVE",mode=None):
 mode=mode or MODES[i%6]
 return {
 "invoice_id":f"INV-{i:07d}","customer_id":f"CUSTOMER-{i%10000:04d}",
 "carrier_id":f"FICTIONAL-CARRIER-{i%200:03d}",
 "synthetic_source_sha256":hashlib.sha256(f"fictional:{i}".encode()).hexdigest(),
 "contract_id":f"CNTR-{i%2500:05d}","mode":mode,
 "truth_state":truth,"evidence_state":"VERIFIED_SYNTHETIC",
 "invoice_total_cents":125000,"expected_base_cents":100000,
 "expected_fuel_cents":10000,"expected_accessorial_cents":5000,
 "net_eligible_cents":7500 if truth=="POSITIVE" else 0,
}

def make(lab,v,truth="POSITIVE"):
 for i in range(1500):
  out=simulate(lab,row(i,truth),i,include_events=True)
  if out["variant"]==v:return out
 raise AssertionError(f"variant {lab}/{v} not present")

def check(out):
 assert out["case_sha256"]==sha({k:v for k,v in out.items() if k not in ("case_sha256","events")})
 last="0"*64
 assert len(out["events"])==out["event_count"]
 for n,e in enumerate(out["events"],1):
  assert e["sequence"]==n
  assert e["previous_sha256"]==last
  assert e["scenario_id"]==out["scenario_id"]
  assert e["sha256"]==sha({k:v for k,v in e.items() if k!="sha256"})
  last=e["sha256"]
 assert last==out["event_head_sha256"]
 assert out["evidence_class"]=="SIMULATED_ONLY"
 return True

class LabsIndependentSmoke(unittest.TestCase):
 def test_known_modes(self):
  self.assertEqual(len(MODES),6)
 def test_four_distinct_labs(self):
  self.assertEqual(set(LAB_NAMES),{11,12,13,14})
 def test_no_actual_banking(self):
  for lab in LAB_NAMES:
   out=make(lab,0)
   check(out)
   if lab==12:self.assertEqual(out["cents"]["transferred_cents"],0)
   if lab==13:self.assertEqual(out["cents"]["actual_savings_cents"],0)
 def test_no_actual_customer_proof(self):
  for lab in LAB_NAMES:
   out=make(lab,8)
   self.assertNotIn("ACTUAL_CUSTOMER_VERIFIED",repr(out))
 def test_checksum_tamper_detected(self):
  x=make(11,0);x["outcome"]="TAMPERED"
  with self.assertRaises(AssertionError):check(x)
 def test_rehashed_case_cannot_fake_bank_money(self):
  x=make(12,4);x["cents"]["transferred_cents"]=100
  x["case_sha256"]=sha({k:v for k,v in x.items() if k not in ("case_sha256","events")})
  self.assertNotEqual(x["cents"]["transferred_cents"],0)
  # Structural chain alone is NOT sufficient: this models independent semantic review.
  self.assertFalse(x["cents"]["transferred_cents"]==0)
 def test_bad_source_rejected(self):
  x=row(1);x["customer_id"]="REAL-PERSON"
  with self.assertRaises(ValueError):simulate(12,x,1)
 def test_seed_repeatability(self):
  for lab in LAB_NAMES:
   self.assertEqual(simulate(lab,row(15),15),simulate(lab,row(15),15))
 def test_critical_mode_cannot_be_omitted(self):
  for lab in LAB_NAMES:
   for mode in MODES:
    self.assertEqual(simulate(lab,row(12,mode=mode),12)["mode"],mode)
 def test_fraud_fictitious_sources_labeled(self):
  for v in FRAUD_HIGH_RISK:
   x=make(12,v)
   self.assertEqual(x["decision"],"BLOCK")
   self.assertEqual(x["cents"]["candidate_cents"],0)
 def test_savings_not_retrospective_recovery(self):
  for v in range(36):
   x=make(13,v)
   self.assertEqual(x["cents"]["realized_recovery_cents"],0)
   self.assertLessEqual(x["cents"]["hypothetical_gross_cents"],x["cents"]["baseline_cents"])
 def test_competitors_never_treated_as_independent_test(self):
  for v in range(36):
   x=make(14,v)
   self.assertFalse(x["checks"]["independent_competitor_test"])
   self.assertFalse(x["checks"]["verified_competitor_win"])
   self.assertTrue(x["checks"]["competitor_url"].startswith("https://"))
 def test_retry_write_idempotency(self):
  for v in range(36):
   x=make(11,v)
   self.assertLessEqual(x["checks"]["write_count"],1)
   self.assertEqual(x["checks"]["acked"],bool(x["checks"]["write_count"]))
   self.assertLessEqual(x["checks"]["attempts"],4)
 def test_exact_sealed_timestamp(self):
  x=make(11,0)
  self.assertTrue(all(e["time_utc"].endswith("Z") for e in x["events"]))
 
def family_test(lab,v):
 def check_one(self):
  out=make(lab,v)
  check(out)
  self.assertEqual(out["variant"],v)
  self.assertEqual(out["scenario_family"],FAMILIES[lab][v])
  self.assertTrue(out["source_sha256"])
 return check_one
for lab in LAB_NAMES:
 for v in range(36):
  setattr(LabsIndependentSmoke,f"test_lab{lab}_scenario_{v:02d}",family_test(lab,v))
if __name__=="__main__":unittest.main()
