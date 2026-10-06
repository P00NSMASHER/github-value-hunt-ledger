import json
from pathlib import Path
import pytest
from freight.client_status_dashboard import render_html, validate

FIXTURE=Path("freight/fixtures/client_status_dashboard_synthetic.json")

def payload():
    return json.loads(FIXTURE.read_text())

def test_dashboard_validates_and_renders():
    p=validate(payload())
    assert p["net_recovered_cents"] == 1345000
    html=render_html(p)
    assert "FICTIONAL / SYNTHETIC EXAMPLE" in html
    assert "Net actual recovered" in html
    assert "$13,450.00" in html

def test_counts_cannot_increase_downstream():
    p=payload()
    p["claims_approved"]=20
    with pytest.raises(ValueError, match="cannot increase downstream"):
        validate(p)

def test_net_recovery_must_reconcile():
    p=payload()
    p["net_recovered_cents"]=999
    with pytest.raises(ValueError, match="net recovered"):
        validate(p)

def test_fee_eligible_cannot_exceed_net():
    p=payload()
    p["fee_eligible_recovered_cents"]=p["net_recovered_cents"]+1
    with pytest.raises(ValueError, match="fee-eligible"):
        validate(p)
