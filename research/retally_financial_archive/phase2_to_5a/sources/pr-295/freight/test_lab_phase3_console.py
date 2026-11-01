import json
import tempfile
import unittest
from pathlib import Path
from freight.lab_phase3_console import generate
class ConsoleTests(unittest.TestCase):
 def test_self_contained_browser_report(self):
  with tempfile.TemporaryDirectory() as d:
   p=generate(Path(d))
   html=(Path(d)/'index.html').read_text()
   self.assertIn('RETALLY | Laboratory Control Center',html)
   self.assertIn('SIMULATED DATA',html)
   self.assertNotIn('__DATA__',html)
   self.assertIn(p['receipt_sha256'],html)
   self.assertEqual(len(p['labs']),14)
   self.assertEqual(p['routed_tasks_not_executed'],49)
   self.assertEqual(json.loads((Path(d)/'phase3_dashboard.json').read_text())['actual_company_revenue_cents'],0)
   self.assertIn('Simulated founding pilot',(Path(d)/'phase3_executive_report.md').read_text())
if __name__=='__main__':unittest.main()
