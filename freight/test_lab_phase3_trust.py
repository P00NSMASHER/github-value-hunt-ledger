import base64
import hashlib
import unittest
from dataclasses import replace
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
except ImportError:
    # General freight release suite has only stdlib dependencies.
    # The dedicated Phase 3 gate installs pinned cryptography and executes
    # every cryptographic test. Runtime verification still FAILS CLOSED.
    Ed25519PrivateKey = None
    serialization = None
from freight.lab_phase3_trust import ExternalTrustGateway, SignedRecord, TrustRoot, TrustRejected, canonical_bytes

@unittest.skipIf(Ed25519PrivateKey is None, 'cryptography runs in dedicated pinned Phase 3 CI')
class TrustTests(unittest.TestCase):
    def setUp(self):
        self.private = Ed25519PrivateKey.generate()  # Ephemeral, NEVER stored in source or disk.
        pub = self.private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.root=TrustRoot('simulated-buyer','v1','BUYER','SIM-TENANT',base64.b64encode(pub).decode(),
                            '2026-10-01T00:00:00Z')
        self.gateway=ExternalTrustGateway([self.root],as_of='2026-10-31T00:00:00Z')
        obj=SignedRecord('sim-owner-001','BUYER_SOURCE_ENTITLEMENT','simulated-buyer','v1',
                         'SIM-TENANT','USD',hashlib.sha256(b'fake-invoice').hexdigest(),1000,
                         '2026-10-08T00:00:00Z','')
        sig=base64.b64encode(self.private.sign(canonical_bytes(obj.signed_body()))).decode()
        self.record=replace(obj,signature_b64=sig)

    def rejects(self,code,records=None,gateway=None,tenant='SIM-TENANT'):
        with self.assertRaises(TrustRejected) as cm:
            (gateway or self.gateway).admit([self.record] if records is None else records,tenant_id=tenant,
                                            required_kinds=frozenset(['BUYER_SOURCE_ENTITLEMENT']))
        self.assertEqual(cm.exception.code,code)

    def test_positive_ephemeral_ed25519_and_scope(self):
        r=self.gateway.admit([self.record],tenant_id='SIM-TENANT',
                             required_kinds=frozenset(['BUYER_SOURCE_ENTITLEMENT']))
        self.assertEqual(r['scope'],'PUBLIC_KEY_CRYPTOGRAPHY_SIMULATED_ISSUERS')
        self.assertFalse(r['actual_buyer_bank_carrier_authority_proven'])

    def test_changed_amount_with_same_signature(self):
        self.rejects('INVALID_SIGNATURE',records=[replace(self.record,amount_cents=99999)])
    def test_changed_tenant(self):
        self.rejects('WRONG_ISSUER_OR_TENANT',tenant='OTHER')
    def test_untrusted_key(self):
        self.rejects('WRONG_ISSUER_OR_TENANT',records=[replace(self.record,key_id='v2')])
    def test_duplicate_claim_proof(self):
        self.rejects('DUPLICATE_OR_MISSING_RECORD',records=[self.record,self.record])
    def test_wrong_role(self):
        self.rejects('WRONG_ISSUER_OR_TENANT',records=[replace(self.record,kind='CARRIER_CREDIT')])
    def test_bad_signature(self):
        self.rejects('INVALID_SIGNATURE',records=[replace(self.record,signature_b64=base64.b64encode(b'0'*64).decode())])
    def test_late_source_signed_with_expired_authority(self):
        root=replace(self.root,disabled_at='2026-10-05T00:00:00Z')
        self.rejects('REVOKED_SIGNER',gateway=ExternalTrustGateway([root],as_of='2026-10-31T00:00:00Z'))
    def test_currency_type(self):
        self.rejects('INVALID_EVIDENCE_CURRENCY',records=[replace(self.record,currency='usd')])
    def test_missing_required_document(self):
        self.rejects('MISSING_ENTITLEMENT',records=[])
    def test_boolean_amount_rejected(self):
        self.rejects('INVALID_EVIDENCE_AMOUNT',records=[replace(self.record,amount_cents=True)])
    def test_future_attestation(self):
        obj=replace(self.record,occurred_at='2027-01-01T00:00:00Z',signature_b64='')
        obj=replace(obj,signature_b64=base64.b64encode(self.private.sign(canonical_bytes(obj.signed_body()))).decode())
        self.rejects('OUTSIDE_SIGNER_WINDOW',records=[obj])

if __name__=='__main__': unittest.main()
