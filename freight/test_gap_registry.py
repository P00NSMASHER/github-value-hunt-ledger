from pathlib import Path
from freight.gap_registry import active_search_gaps, authorize_search, load_register, validate_register

REGISTER = Path(__file__).with_name("GAP_REGISTER.json")

def test_canonical_gap_register_is_valid():
    register = load_register(REGISTER)
    assert validate_register(register) == []

def test_canonical_register_has_no_active_github_search_gap():
    register = load_register(REGISTER)
    assert active_search_gaps(register) == []

def test_invented_gap_id_is_rejected():
    decision = authorize_search(load_register(REGISTER), "FRT-MADE-UP-999", "EXP001_GAP")
    assert decision.allowed is False
    assert "gap_id_not_registered" in decision.reasons

def test_dormant_authority_gap_does_not_authorize_search():
    decision = authorize_search(load_register(REGISTER), "FRT-AUTH-001", "AUTHORITY_CONNECTOR")
    assert decision.allowed is False
    assert "gap_search_not_allowed" in decision.reasons

def test_search_allowed_requires_active_search_status():
    register = {
        "stage_gate": "EXP-001",
        "gaps": [{
            "gap_id": "FRT-X",
            "title": "x",
            "status": "ACTIVE_INTERNAL",
            "search_allowed": True,
            "allowed_triggers": ["EXP001_GAP"],
            "commercial_effect": "x",
            "evidence_to_close": ["x"],
            "stop_condition": "x",
        }],
    }
    errors = validate_register(register)
    assert any("search_allowed requires ACTIVE_SEARCH" in error for error in errors)
