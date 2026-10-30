"""Golden Goose #032: ensure the research fixture runs in Technology Intelligence CI."""
from pathlib import Path
import subprocess
import sys
import unittest

RESEARCH = Path(__file__).resolve().parents[1] / "research" / "golden_goose" / "deadline_conflict_032"

class TestGoldenGooseDeadlineConflict(unittest.TestCase):
    def test_research_negative_controls(self):
        p=subprocess.run([sys.executable,"-m","unittest","-q","test_deadline_conflict_gate"],
                         cwd=RESEARCH,capture_output=True,text=True,timeout=30,check=False)
        self.assertEqual(p.returncode,0,p.stdout+"\n"+p.stderr)
