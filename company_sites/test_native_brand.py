"""Transparent native logo integration: existing funnels must remain readable."""
from pathlib import Path
import hashlib,json,tempfile,unittest
from company_sites.build import build
R=Path(__file__).resolve().parents[1]
class NativeBrandTests(unittest.TestCase):
 def test_verified_emblem_bytes(self):
  m=json.loads((R/'company_sites/native-brand-assets.json').read_text())
  for key in ('freightrecovery','recoveryos','permitplate','capturebrief'):
   name=m[key]['emblem']
   data=(R/'freight/site/assets/brand'/name).read_bytes()
   self.assertEqual(hashlib.sha256(data).hexdigest(),m[key]['sizes'][name]['sha256'])
   self.assertLess(len(data),140000)
 def test_freight_homepage_is_restored_and_logo_integrated(self):
  html=(R/'freight/site/index.html').read_text()
  self.assertIn('id="auditForm"',html)
  self.assertIn('Find it.',html)
  self.assertIn('freightrecovery-emblem.webp',html)
  self.assertNotIn('freightrecovery-600-20261022.webp',html)
  self.assertIn('assets/brand/retally-wordmark-approved.png',html)
 def test_four_companies_and_shared_software_brand(self):
  html=(R/'company_sites/group/index.html').read_text()
  self.assertEqual(html.count('<article class="company-card '),4)
  for key in ('freightrecovery','permitplate','capturebrief','recoveryos'):self.assertIn(key+'-emblem.webp',html)
  self.assertIn('RETALLY RecoveryWorks',html)
  self.assertNotIn('freightrecovery-600-20261022.webp',html)
 def test_recoveryworks_card_uses_approved_native_identity(self):
  html=(R/'company_sites/group/index.html').read_text()
  card=html.split('<article class="company-card recoveryworks">',1)[1].split('</article>',1)[0]
  self.assertIn('class="approved-brand-image native-company-emblem"',card)
  self.assertIn('src="/assets/brand/recoveryos-emblem.webp"',card)
  self.assertIn('alt="RecoveryOS by RETALLY"',card)
  self.assertNotIn('/assets/recoveryworks.webp',card)
  css=(R/'company_sites/group/site.css').read_text()
  self.assertNotIn('.company-card.recoveryworks>img{height:228px;object-fit:cover}',css)
 def test_independent_allowlists_publish_emblems(self):
  for company,keys in [('group',('freightrecovery','permitplate','capturebrief','recoveryos')),('recoveryworks',('recoveryos',))]:
   with tempfile.TemporaryDirectory() as tmp:
    out=Path(tmp)/'out'
    build(company,out)
    for key in keys:self.assertTrue((out/'assets/brand'/f'{key}-emblem.webp').is_file())
    if company=='group':self.assertFalse((out/'assets/recoveryworks.webp').exists())
 def test_software_uses_transparent_emblem(self):
  self.assertIn('recoveryos-emblem.webp',(R/'recoveryworks/site/index.html').read_text())
if __name__=='__main__':unittest.main()
