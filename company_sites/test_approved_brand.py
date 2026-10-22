"""Owner-approved logo provenance, restrained web delivery and identity boundaries."""
import hashlib,json,tempfile,unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from company_sites.build import build
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'freight/site/assets/brand'
EXPECTED={
 'freightrecovery':'f69f384eac341d3457decf14ebea2a21feebfe22376640672151ef0c37ba7bd2',
 'recoveryos':'3bd1d9f547465764eaec49f4e1b5439fd6b4071ff1250d376a711a7263317112',
 'permitplate':'4c34118fca23f1743f6e34e71dc5e65366c61f612619fa5264a14cfc6861874f',
 'capturebrief':'b48b332918001972060bbabb0190ed577ca9ab6f1c2d49589fc273abc8b36b8c'}
class ApprovedBrandTests(unittest.TestCase):
 def test_provenance_and_delivery_budget(self):
  manifest=json.loads((ROOT/'company_sites/approved-brand-assets.json').read_text())
  for key,digest in EXPECTED.items():
   brand=manifest['brands'][key]
   self.assertEqual(brand['source_sha256'],digest)
   self.assertEqual(brand['source_dimensions'],[6144,4096])
   for name,meta in brand['files'].items():
    data=(ASSETS/name).read_bytes()
    self.assertEqual(hashlib.sha256(data).hexdigest(),meta['sha256'],name)
    self.assertEqual(len(data),meta['bytes'])
    if name.endswith('.webp'):self.assertLess(len(data),160000,name)
 def test_freight_brand_preserves_original_home_and_intake(self):
  html=(ROOT/'freight/site/index.html').read_text(encoding='utf-8')
  for token in ['freightrecovery-emblem.webp','native-brand-text','FreightRecovery by RETALLY','id="auditForm"','id="hero-title"','Find it.','Prove it.','Recover it.']:
   self.assertIn(token,html)
  self.assertIn('assets/brand/retally-wordmark-approved.png',html,'Parent footer identity remains intact')
 def test_four_companies_and_separate_software_identity(self):
  html=(ROOT/'company_sites/group/index.html').read_text(encoding='utf-8')
  self.assertEqual(html.count('<article class="company-card '),4)
  self.assertIn('RETALLY RecoveryWorks',html)
  self.assertIn('Shared recovery software',html)
  for key in EXPECTED:self.assertIn(key+'-emblem.webp',html)
  recovery=(ROOT/'company_sites/recoveryworks/index.html').read_text(encoding='utf-8')
  self.assertIn('recoveryos-emblem.webp',recovery)
  for token in ['RecoveryWorks','Vendor overpayment review','Missed-credit reconciliation','Supporting recovery software']:
   self.assertIn(token,recovery)
 def test_company_publication_includes_exact_image_bytes(self):
  for company,keys in [('group',EXPECTED),('recoveryworks',['recoveryos'])]:
   with self.subTest(company=company),tempfile.TemporaryDirectory() as tmp:
    out=Path(tmp)/'public';build(company,out)
    for key in keys:
     for width in ('emblem',):
      name=f'{key}-{width}.webp'
      self.assertEqual((out/'assets/brand'/name).read_bytes(),(ASSETS/name).read_bytes())
 def test_images_are_not_stretched_or_blended_into_dark_backdrops(self):
  for f in ['freight/site/foundry.css','company_sites/group/site.css','company_sites/recoveryworks/site.css']:
   css=(ROOT/f).read_text(encoding='utf-8')
   self.assertIn('object-fit:contain',css)
   self.assertIn('.approved-brand',css)
if __name__=='__main__':unittest.main()
