"""Offline adversarial tests for the ONE approved Always Free E2 Micro fallback."""
from __future__ import annotations

from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "retally_micro_cli", Path(__file__).with_name("provision-micro-cloud-shell.py"))
micro = importlib.util.module_from_spec(spec)
spec.loader.exec_module(micro)

TENANCY = "ocid1.tenancy.oc1..synthetic"
REGION = "us-ashburn-1"
AD1 = "example:US-ASHBURN-AD-1"
AD2 = "example:US-ASHBURN-AD-2"


class MicroResourceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="test-retally-micro-")
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.partial = self.root / "original-partial.json"
        self.complete = self.root / "final.json"
        self.archive = self.root / "original-partial-after-micro.json"
        self.attempt = self.root / "micro-launch-attempt.json"
        self.public = self.root / "test_key.pub"
        self.public.write_text("ssh-rsa SYNTHETIC_FIXTURE_DO_NOT_USE", encoding="ascii")
        self.original = {
            "schema": 1, "phase": "subnet_created",
            "tenancy_id": TENANCY, "home_region": REGION,
            "subnet_id": "ocid1.subnet.oc1.iad.fake",
            "vcn_id": "ocid1.vcn.oc1.iad.fake",
            "no_open_ingress": True, "release_status": "HOLD",
        }
        self.partial.write_text(json.dumps(self.original), encoding="ascii")
        self.partial.chmod(0o600)
        self.inv = {
            "existing_instances": 0, "a1_ocpus_in_use": 0,
            "block_volume_gb_in_use": 0, "vcn_count": 1,
        }

    def bridge(self):
        stack = ExitStack()
        stack.enter_context(patch.object(micro.BASE, "RESOURCE_DIR", self.root))
        stack.enter_context(patch.object(micro.BASE, "PARTIAL", self.partial))
        stack.enter_context(patch.object(micro.BASE, "RECEIPT", self.complete))
        stack.enter_context(patch.object(micro.BASE, "PUBLIC_KEY", self.public))
        stack.enter_context(patch.object(micro, "MICRO_RECEIPT_ARCHIVE", self.archive))
        stack.enter_context(patch.object(micro, "MICRO_ATTEMPT_MARKER", self.attempt))
        stack.enter_context(patch.object(micro.BASE, "verify_partial_network"))
        stack.enter_context(patch.object(micro.BASE, "read_inventory", return_value=self.inv))
        stack.enter_context(patch.object(micro.BASE, "compartments", return_value=[TENANCY]))
        return stack

    def fake_cli(self, *args, region=None, timeout=90):
        cmd = " ".join(args[:3])
        if cmd == "compute instance list":
            return []
        if cmd == "iam availability-domain list":
            return [{"name": AD1}, {"name": AD2}]
        if cmd == "compute shape list":
            if args[args.index("--availability-domain")+1] == AD1:
                return [{"shape": micro.MICRO_SHAPE}]
            return []
        if cmd == "compute image list":
            return [{"id":"ocid1.image.oc1.iad.synthetic", "operating-system":"Canonical Ubuntu",
                     "operating-system-version":"24.04", "lifecycle-state":"AVAILABLE",
                     "display-name":"Canonical-Ubuntu-24.04-amd64-SYNTHETIC"}]
        raise AssertionError("Unexpected OCI API call (may be a write): " + cmd)

    def test_fixed_micro_dimensions_and_isolation(self):
        self.assertEqual(micro.MICRO_SHAPE, "VM.Standard.E2.1.Micro")
        self.assertEqual(micro.MICRO_MEMORY_GB, 1)
        self.assertEqual(micro.MICRO_BOOT_GB, 50)
        self.assertEqual(micro.MAX_FREE_MICRO_INSTANCES, 2)

    def test_no_write_preflight_with_exact_one_ad(self):
        with self.bridge(),patch.object(micro.BASE, "cli", side_effect=self.fake_cli) as req:
            result = micro.inventory(TENANCY, REGION, self.original)
        self.assertEqual(result["ad"],AD1)
        self.assertEqual(result["micro_instances_in_use"],0)
        self.assertEqual(result["image_name"],"Canonical-Ubuntu-24.04-amd64-SYNTHETIC")
        self.assertTrue(all(c.args[2] == "list" for c in req.call_args_list))

    def test_micro_only_in_one_eligible_ad(self):
        def alternate(*args,**kwargs):
            if args[:3]==("compute","shape","list"):
                return [{"shape":micro.MICRO_SHAPE}]
            return self.fake_cli(*args,**kwargs)
        with self.bridge(),patch.object(micro.BASE, "cli", side_effect=alternate):
            with self.assertRaisesRegex(micro.BASE.Stop,"exactly one"):
                micro.inventory(TENANCY,REGION,self.original)

    def test_two_used_micro_vm_instances_exhaust_allowance(self):
        def existing(*args,**kwargs):
            if args[:3]==("compute","instance","list"):
                return [{"shape":micro.MICRO_SHAPE,"lifecycle-state":"RUNNING",
                         "display-name":"another-micro-"+str(x)} for x in (1,2)]
            return self.fake_cli(*args,**kwargs)
        with self.bridge(),patch.object(micro.BASE,"cli",side_effect=existing):
            with self.assertRaisesRegex(micro.BASE.Stop,"allowance"):
                micro.inventory(TENANCY,REGION,self.original)

    def test_one_used_micro_with_room_is_allowed(self):
        def existing(*args,**kwargs):
            if args[:3]==("compute","instance","list"):
                return [{"shape":micro.MICRO_SHAPE,"lifecycle-state":"RUNNING",
                         "display-name":"other-micro"}]
            return self.fake_cli(*args,**kwargs)
        self.inv["existing_instances"] = 1
        with self.bridge(),patch.object(micro.BASE,"cli",side_effect=existing):
            self.assertEqual(micro.inventory(TENANCY,REGION,self.original)["micro_instances_in_use"],1)

    def test_duplicate_retally_name_never_provisioned(self):
        def existing(*args,**kwargs):
            if args[:3]==("compute","instance","list"):
                return [{"shape":micro.MICRO_SHAPE,"lifecycle-state":"RUNNING",
                         "display-name":micro.BASE.NAME}]
            return self.fake_cli(*args,**kwargs)
        with self.bridge(),patch.object(micro.BASE,"cli",side_effect=existing):
            with self.assertRaisesRegex(micro.BASE.Stop,"already exists"):
                micro.inventory(TENANCY,REGION,self.original)

    def test_high_block_storage_refused(self):
        self.inv["block_volume_gb_in_use"] = 175
        with self.bridge(),patch.object(micro.BASE,"cli",side_effect=self.fake_cli):
            with self.assertRaisesRegex(micro.BASE.Stop,"storage allowance"):
                micro.inventory(TENANCY,REGION,self.original)

    def test_unavailable_micro_image_fails_closed(self):
        def missing(*args,**kwargs):
            if args[:3]==("compute","image","list"):
                return []
            return self.fake_cli(*args,**kwargs)
        with self.bridge(),patch.object(micro.BASE,"cli",side_effect=missing):
            with self.assertRaisesRegex(micro.BASE.Stop,"No approved official Ubuntu"):
                micro.inventory(TENANCY,REGION,self.original)

    def test_missing_original_partial_never_provisions(self):
        self.partial.unlink()
        with self.bridge(),patch.object(micro,"launch_single_micro") as launch:
            with self.assertRaises(micro.BASE.Stop):
                micro.main([])
        launch.assert_not_called()

    def test_wrong_micro_confirmation_never_provisions(self):
        with (self.bridge(),
              patch.object(micro.BASE,"read_tenancy",return_value=TENANCY),
              patch.object(micro.BASE,"home_region",return_value=REGION),
              patch.object(micro,"inventory",return_value={"ad":AD1,"image_id":"fake","image_name":"fake",
                      "micro_instances_in_use":0,"block_gb_in_use":0}) as preflight,
              patch.object(micro.sys.stdin,"isatty",return_value=True),
              patch("builtins.input",return_value="CREATE RETALLY ALWAYS FREE"),
              patch.object(micro,"launch_single_micro") as launch,
              patch("builtins.print")):
            with self.assertRaisesRegex(micro.BASE.Stop,"Confirmation not received"):
                micro.main(["--create"])
        preflight.assert_called_once()
        launch.assert_not_called()

    def test_never_provisions_without_interactive_tty(self):
        with (self.bridge(),
              patch.object(micro.BASE,"read_tenancy",return_value=TENANCY),
              patch.object(micro.BASE,"home_region",return_value=REGION),
              patch.object(micro,"inventory",return_value={"ad":AD1,"image_name":"fake",
                      "micro_instances_in_use":0,"block_gb_in_use":0}),
              patch.object(micro.sys.stdin,"isatty",return_value=False),
              patch.object(micro,"launch_single_micro") as launch,
              patch("builtins.print")):
            with self.assertRaisesRegex(micro.BASE.Stop,"interactive"):
                micro.main(["--create"])
        launch.assert_not_called()

    def test_real_launch_command_is_fixed_free_micro_only(self):
        planned={"ad":AD1,"tenancy":TENANCY,"image_id":"ocid1.image.oc1.iad.fake",
                 "home_region":REGION}
        calls=[]
        def api(*args,**kwargs):
            calls.append(args)
            cmd=" ".join(args[:3])
            if cmd=="compute instance launch":
                self.assertEqual(args[args.index("--shape")+1],micro.MICRO_SHAPE)
                self.assertNotIn("--shape-config",args)
                self.assertEqual(args[args.index("--boot-volume-size-in-gbs")+1],"50")
                self.assertEqual(args[args.index("--subnet-id")+1],self.original["subnet_id"])
                self.assertEqual(args[args.index("--ssh-authorized-keys-file")+1],str(self.public))
                return {"id":"ocid1.instance.oc1.iad.synthetic"}
            if cmd=="compute instance get":
                return {"id":"ocid1.instance.oc1.iad.synthetic","display-name":micro.BASE.NAME,
                        "shape":micro.MICRO_SHAPE,"lifecycle-state":"RUNNING",
                        "availability-domain":AD1,"compartment-id":TENANCY,
                        "shape-config":{"memory-in-gbs":1}}
            raise AssertionError("Wrong OCI API call: "+cmd)
        with self.bridge(),patch.object(micro.BASE,"cli",side_effect=api):
            self.assertEqual(micro.launch_single_micro(planned,self.original)["actual_shape"],
                             micro.MICRO_SHAPE)
        self.assertEqual([a[:3] for a in calls],
                         [("compute","instance","launch"),("compute","instance","get")])
        self.assertTrue(self.attempt.is_file())
        self.assertEqual(self.attempt.stat().st_mode & 0o777, 0o600)
        marker = json.loads(self.attempt.read_text(encoding="utf-8"))
        self.assertEqual(marker["status"], "LAUNCH_UNCERTAIN_UNTIL_VERIFIED")
        self.assertEqual(marker["shape"], micro.MICRO_SHAPE)
        self.assertEqual(marker["subnet_id"], self.original["subnet_id"])

    def test_wrong_shape_never_marked_verified(self):
        plan={"ad":AD1,"tenancy":TENANCY,"image_id":"ocid1.image.oc1.iad.fake",
              "home_region":REGION}
        def wrong(*args,**kwargs):
            if args[:3]==("compute","instance","launch"):
                return {"id":"ocid1.instance.oc1.iad.fake"}
            if args[:3]==("compute","instance","get"):
                return {"id":"ocid1.instance.oc1.iad.fake","display-name":micro.BASE.NAME,
                        "shape":"VM.Standard.E4.Flex","lifecycle-state":"RUNNING",
                        "availability-domain":AD1,"compartment-id":TENANCY}
        with self.bridge(),patch.object(micro.BASE,"cli",side_effect=wrong):
            with self.assertRaisesRegex(micro.BASE.Stop,"verification failed"):
                micro.launch_single_micro(plan,self.original)
        self.assertNotIn("instance_id",self.original)

    @unittest.skipUnless(os.name == "posix",
                         "OCI owner/mode or FIPS key-permission fixture requires POSIX; verified on Linux")
    def test_successful_resume_preserves_original_partial_evidence(self):
        plan={"ad":AD1,"tenancy":TENANCY,"image_id":"ocid1.image.oc1.iad.fake",
              "home_region":REGION,"image_name":"Synthetic Ubuntu",
              "micro_instances_in_use":0,"block_gb_in_use":0}
        def launched(x, state):
            state["instance_id"]="ocid1.instance.oc1.iad.synthetic"
            state["phase"]="vm_running"
            return state
        with (self.bridge(),
              patch.object(micro.BASE,"read_tenancy",return_value=TENANCY),
              patch.object(micro.BASE,"home_region",return_value=REGION),
              patch.object(micro,"inventory",return_value=plan) as read,
              patch.object(micro.sys.stdin,"isatty",return_value=True),
              patch("builtins.input",return_value="CREATE ONE RETALLY FREE MICRO"),
              patch.object(micro,"launch_single_micro",side_effect=launched) as launch,
              patch("builtins.print")):
            # This uses the original safe_receipt implementation to confirm file mode.
            self.assertEqual(micro.main(["--create"]),0)
        self.assertEqual(read.call_count,2)
        launch.assert_called_once()
        self.assertTrue(self.complete.exists())
        self.assertTrue(self.archive.exists())
        self.assertFalse(self.partial.exists())
        self.assertEqual(self.complete.stat().st_mode & 0o777,0o600)
        self.assertEqual(self.archive.stat().st_mode & 0o777,0o600)


    def test_ambiguous_api_error_leaves_persistent_exclusive_retry_lock(self):
        plan = {"ad": AD1, "tenancy": TENANCY,
                "image_id": "ocid1.image.oc1.iad.synthetic", "home_region": REGION}
        attempts = []
        def failed_api(*args, **kwargs):
            attempts.append(args[:3])
            raise micro.BASE.Stop("OCI launch failed (InternalError)")
        with self.bridge(), patch.object(micro.BASE, "cli", side_effect=failed_api):
            with self.assertRaisesRegex(micro.BASE.Stop, "InternalError"):
                micro.launch_single_micro(plan, self.original)
            self.assertTrue(self.attempt.is_file())
            self.assertEqual(self.attempt.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(self.attempt.read_text())["status"],
                             "LAUNCH_UNCERTAIN_UNTIL_VERIFIED")
            with self.assertRaisesRegex(micro.BASE.Stop, "prior Micro launch attempt"):
                micro.launch_single_micro(plan, self.original)
        self.assertEqual(attempts, [("compute", "instance", "launch")])

    def test_readonly_inventory_still_works_after_ambiguous_launch(self):
        self.attempt.write_text('{"status":"LAUNCH_UNCERTAIN_UNTIL_VERIFIED"}')
        self.attempt.chmod(0o600)
        plan = {"ad": AD1, "image_name": "Synthetic Ubuntu",
                "micro_instances_in_use": 0, "block_gb_in_use": 0}
        with (self.bridge(),
              patch.object(micro.BASE, "read_tenancy", return_value=TENANCY),
              patch.object(micro.BASE, "home_region", return_value=REGION),
              patch.object(micro, "inventory", return_value=plan),
              patch.object(micro, "launch_single_micro") as launch,
              patch("builtins.print") as printer):
            self.assertEqual(micro.main([]), 0)
        self.assertTrue(any("RETRY LOCKED" in str(c) for c in printer.call_args_list))
        launch.assert_not_called()

    def test_prior_attempt_fails_before_new_confirmation_or_launch(self):
        self.attempt.write_text('{"status":"LAUNCH_UNCERTAIN_UNTIL_VERIFIED"}')
        self.attempt.chmod(0o600)
        plan = {"ad": AD1, "image_name": "Synthetic Ubuntu",
                "micro_instances_in_use": 0, "block_gb_in_use": 0}
        with (self.bridge(),
              patch.object(micro.BASE, "read_tenancy", return_value=TENANCY),
              patch.object(micro.BASE, "home_region", return_value=REGION),
              patch.object(micro, "inventory", return_value=plan),
              patch.object(micro.sys.stdin, "isatty", return_value=True),
              patch("builtins.input") as prompt,
              patch.object(micro, "launch_single_micro") as launch,
              patch("builtins.print")):
            with self.assertRaisesRegex(micro.BASE.Stop, "Prior Micro launch attempt"):
                micro.main(["--create"])
        prompt.assert_not_called()
        launch.assert_not_called()


if __name__=="__main__":
    unittest.main()
