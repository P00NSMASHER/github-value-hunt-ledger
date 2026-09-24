from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from recoveryworks.customer_data_governance import (
    CustomerDataAccessHistory,
    CustomerDataPurpose,
    CustomerLegalHold,
    build_customer_data_inventory,
    delete_customer_data_object,
    export_customer_data,
)
from recoveryworks.models import canonical_hash
from recoveryworks.private_io import private_permissions_verified


class CustomerDataGovernanceTests(unittest.TestCase):
    def setup(self, root: Path):
        customer=root/"customers"/"cust-1"
        customer.mkdir(parents=True)
        if os.name!="nt":
            customer.chmod(0o700)
        billing=customer/"billing.csv"
        contract=customer/"contract.csv"
        billing.write_text("billing-data\n",encoding="utf-8")
        contract.write_text("contract-data\n",encoding="utf-8")
        if os.name!="nt":
            billing.chmod(0o600); contract.chmod(0o600)
        inventory=build_customer_data_inventory(
            customer_id="cust-1",customer_root=customer,
            object_specs=(
                {
                    "relative_path":"billing.csv",
                    "classification":"FINANCIAL_EVIDENCE",
                    "allowed_purposes":["CLOUD_BILLING_AUDIT","RECOVERY_EVIDENCE","CUSTOMER_EXPORT"],
                    "collected_at":"2026-09-01T00:00:00Z",
                    "retention_until":"2026-09-30T00:00:00Z",
                    "source_kind":"authorized billing export",
                },
                {
                    "relative_path":"contract.csv",
                    "classification":"CUSTOMER_CONFIDENTIAL",
                    "allowed_purposes":["RECOVERY_EVIDENCE","CUSTOMER_EXPORT"],
                    "collected_at":"2026-09-01T00:00:00Z",
                    "retention_until":"2026-09-30T00:00:00Z",
                    "source_kind":"reviewed contract authority",
                },
            ),
            generated_at="2026-09-24T12:00:00Z")
        return customer,inventory

    def test_customer_isolation_purpose_limitation_and_access_history(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); customer,inventory=self.setup(root)
            history=CustomerDataAccessHistory(root/"private"/"access.json")
            billing=next(x for x in inventory.objects if x.relative_path=="billing.csv")
            event=history.record(
                billing,actor_id="reviewer",purpose=CustomerDataPurpose.CLOUD_BILLING_AUDIT,
                accessed_at="2026-09-24T12:05:00Z")
            self.assertTrue(event.allowed)
            with self.assertRaises(PermissionError):
                history.record(
                    billing,actor_id="reviewer",
                    purpose=CustomerDataPurpose.OPERATIONS,
                    accessed_at="2026-09-24T12:06:00Z")
            self.assertEqual(len(history.events()),2)
            outside=root/"outside.csv"; outside.write_text("x",encoding="utf-8")
            if os.name!="nt": outside.chmod(0o600)
            with self.assertRaisesRegex(ValueError,"inside customer_root"):
                build_customer_data_inventory(
                    customer_id="cust-1",customer_root=customer,
                    object_specs=({
                        "relative_path":"../../outside.csv",
                        "classification":"FINANCIAL_EVIDENCE",
                        "allowed_purposes":["RECOVERY_EVIDENCE"],
                        "collected_at":"2026-09-01T00:00:00Z",
                        "retention_until":"2026-09-30T00:00:00Z",
                        "source_kind":"bad",
                    },),generated_at="2026-09-24T12:00:00Z")

    def test_private_export_and_legal_hold_block_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); customer,inventory=self.setup(root)
            archive=root/"private"/"export.zip"
            export=export_customer_data(
                inventory,customer_root=customer,archive_path=archive,
                exported_at="2026-09-24T12:10:00Z")
            self.assertTrue(private_permissions_verified(archive))
            self.assertEqual(len(export.object_ids),2)
            obj=inventory.objects[0]
            hold_ident={
                "schema":1,"customer_id":"cust-1","object_ids":[obj.object_id],
                "reason":"litigation hold","imposed_by":"legal",
                "imposed_at":"2026-09-24T12:11:00Z","released_at":None}
            hold=CustomerLegalHold(
                hold_id="customer-legal-hold:"+canonical_hash(hold_ident),
                customer_id="cust-1",object_ids=(obj.object_id,),
                reason="litigation hold",imposed_by="legal",
                imposed_at="2026-09-24T12:11:00Z")
            with self.assertRaisesRegex(ValueError,"legal hold"):
                delete_customer_data_object(
                    obj,customer_root=customer,holds=(hold,),
                    deleted_at="2026-10-01T00:00:00Z",
                    authorized_by="privacy-owner",reason="retention expiry")

    def test_logical_deletion_receipt_does_not_claim_forensic_wipe(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); customer,inventory=self.setup(root)
            obj=inventory.objects[0]
            receipt=delete_customer_data_object(
                obj,customer_root=customer,holds=(),
                deleted_at="2026-10-01T00:00:00Z",
                authorized_by="privacy-owner",reason="retention expiry")
            self.assertFalse((customer/obj.relative_path).exists())
            self.assertTrue(receipt.logical_deletion_only)
            self.assertFalse(receipt.forensic_wipe_claimed)

    def test_early_deletion_requires_explicit_approval(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); customer,inventory=self.setup(root)
            obj=inventory.objects[0]
            with self.assertRaisesRegex(ValueError,"retention period"):
                delete_customer_data_object(
                    obj,customer_root=customer,holds=(),
                    deleted_at="2026-09-24T13:00:00Z",
                    authorized_by="privacy-owner",reason="request")


if __name__=="__main__":
    unittest.main()
