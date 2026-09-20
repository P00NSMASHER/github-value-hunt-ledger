from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/technology-intelligence.yml"


def test_technology_intelligence_actions_are_immutable_pins():
    text=WORKFLOW.read_text()
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in text
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in text
    assert "actions/checkout@v4" not in text
    assert "actions/setup-python@v5" not in text


def test_validation_is_read_only_and_write_is_main_only():
    text=WORKFLOW.read_text()
    assert "permissions:\n  contents: read" in text
    assert "validate:" in text
    assert "persist-generated:" in text
    assert "permissions:\n      contents: write" in text
    assert "github.event_name == 'push'" in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "needs: validate" in text


def test_workflow_has_race_and_runtime_bounds():
    text=WORKFLOW.read_text()
    assert "concurrency:" in text
    assert text.count("timeout-minutes: 15") >= 2
    assert "git pull --ff-only origin main" in text
