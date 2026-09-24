from pathlib import Path
import re


ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/technology-intelligence.yml"
WORKFLOWS=ROOT/".github/workflows"
PAGES_WORKFLOW=WORKFLOWS/"freight-site-pages.yml"
IMMUTABLE_ACTION=re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}$")


def test_technology_intelligence_actions_are_immutable_pins():
    text=WORKFLOW.read_text()
    assert "actions/checkout@11d5960a326750d5838078e36cf38b85af677262" in text
    assert "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065" in text
    assert "actions/checkout@v4" not in text
    assert "actions/setup-python@v5" not in text


def test_every_repository_workflow_action_is_immutably_pinned():
    floating=[]
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        for line_number,line in enumerate(path.read_text().splitlines(),start=1):
            match=re.search(r"\buses:\s*([^\s#]+)",line)
            if not match:
                continue
            reference=match.group(1)
            if reference.startswith(("./","docker://")):
                continue
            if not IMMUTABLE_ACTION.fullmatch(reference):
                floating.append(f"{path.name}:{line_number}:{reference}")
    assert floating==[]


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


def test_freight_deployment_gates_use_the_real_workflow_date():
    text=(WORKFLOWS/"freight-contracts.yml").read_text()
    assert text.count('"$(date -u +%F)"') >= 7
    assert "--as-of-date 2026-09-20" not in text
    assert "--as-of-date 2026-09-21" not in text


def test_freight_pages_deployment_is_main_only_verified_and_config_gated():
    text=PAGES_WORKFLOW.read_text()
    assert "permissions:\n  contents: read" in text
    assert "needs: verify" in text
    assert "github.event_name != 'pull_request'" in text
    assert "github.ref == 'refs/heads/main'" in text
    assert "vars.FREIGHT_CONTACT_VERIFIED == '1'" in text
    assert "vars.FREIGHT_CONTACT_EMAIL != ''" in text
    assert "FREIGHT_CONTINGENCY_RECOVERY_RATE" in text
    assert "FREIGHT_CHECKOUT_VERIFIED" not in text
    assert "FREIGHT_READINESS_CHECKOUT_URL" not in text
    assert "FREIGHT_AUDIT_CHECKOUT_URL" not in text
    assert "pages: write" in text
    assert "id-token: write" in text
    assert "python freight/site/build.py --output /tmp/freight-recovery-public" in text
    assert "path: /tmp/freight-recovery-public" in text
