"""Guard the real six-mode metamorphic test at low-cost CI smoke scale."""
from freight.lab.six_mode_metamorphic_probe import run


def test_six_mode_billing_mutations_keep_authority_and_variance_consistent():
    result = run(iterations=15, seed=90217)
    assert result["rated_calls"] == result["base_gold_cases"] * 15
    assert result["failure_count"] == 0, result["failures"]
    assert set(result["by_mode"]) == {
        "PARCEL", "LTL", "TL", "INTERMODAL", "AIR", "OCEAN"
    }
    assert result["scope"] == "REAL_ENGINE_SYNTHETIC_6_MODE_METAMORPHIC_ONLY"


def test_six_mode_probe_is_seed_reproducible():
    left = run(iterations=7,seed=16439)
    right = run(iterations=7,seed=16439)
    assert left["by_mode"] == right["by_mode"]
    assert left["failure_count"] == right["failure_count"] == 0
