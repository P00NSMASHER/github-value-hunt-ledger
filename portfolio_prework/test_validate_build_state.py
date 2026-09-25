import copy
import unittest

from portfolio_prework.validate_build_state import ValidationError, validate_state


BASE = {
    "schema_version":"1.0.0",
    "architecture_version":"test",
    "state_id":"test-state",
    "working_branch":"branch",
    "phase":"parallel_prework",
    "current_step":2,
    "completed_steps":[1],
    "repositories":{
        "REPO-001":{
            "full_name":"acme/demo",
            "last_inspected_sha":"a"*40,
            "inspection_status":"UNCHANGED",
            "last_observed_at":None,
            "notes":None
        }
    },
    "decisions":[
        {"decision_id":"DEC-001","summary":"x","status":"ACCEPTED","evidence_refs":[]}
    ],
    "artifacts":[
        {"path":"a.json","kind":"test","step":1,"commit_sha":"b"*40}
    ],
    "tests":[
        {"name":"test","status":"PASS","step":1,"evidence":"ok"}
    ],
    "blockers":[],
    "next_action":{"step":2,"summary":"continue","preconditions":[]},
    "updated_at":"2026-09-25T00:00:00Z"
}


class BuildStateValidationTests(unittest.TestCase):
    def test_valid_state(self):
        validate_state(copy.deepcopy(BASE))

    def test_rejects_duplicate_completed_steps(self):
        state=copy.deepcopy(BASE)
        state["completed_steps"]=[1,1]
        with self.assertRaises(ValidationError):
            validate_state(state)

    def test_rejects_bad_sha(self):
        state=copy.deepcopy(BASE)
        state["repositories"]["REPO-001"]["last_inspected_sha"]="nope"
        with self.assertRaises(ValidationError):
            validate_state(state)

    def test_rejects_future_completed_step(self):
        state=copy.deepcopy(BASE)
        state["completed_steps"]=[1,2]
        with self.assertRaises(ValidationError):
            validate_state(state)

    def test_next_action_must_match_current_step(self):
        state=copy.deepcopy(BASE)
        state["next_action"]["step"]=3
        with self.assertRaises(ValidationError):
            validate_state(state)


if __name__ == "__main__":
    unittest.main()
