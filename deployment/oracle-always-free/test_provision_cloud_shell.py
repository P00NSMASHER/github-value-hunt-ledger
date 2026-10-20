"""Offline tests for strict free-resource preflight and network sequencing."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE_FILE = Path(__file__).with_name('provision-cloud-shell.py')
spec = importlib.util.spec_from_file_location('retally_free_cloud_shell', MODULE_FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
TENANCY = 'ocid1.tenancy.oc1..free-test'
REGION = 'us-ashburn-1'
AD = 'example:US-ASHBURN-AD-1'


def fake_oci(*args, region=None, timeout=90):
    op = ' '.join(args[:3])
    if op == 'iam region-subscription list':
        return [{'is-home-region':True,'region-name':REGION}]
    if op == 'iam availability-domain list':
        return [{'name':AD}]
    if op == 'iam compartment list':
        return []
    if op == 'compute instance list':
        return []
    if op == 'bv volume list':
        return []
    if op == 'bv boot-volume list':
        return []
    if op == 'network vcn list':
        return []
    if op == 'compute shape list':
        return [{'shape':mod.SHAPE}]
    if op == 'compute image list':
        return [{'id':'ocid1.image.oc1.iad.fixture',
                 'operating-system':'Canonical Ubuntu',
                 'operating-system-version':'24.04',
                 'lifecycle-state':'AVAILABLE','display-name':'Ubuntu 24.04 for A1'}]
    raise AssertionError('Unexpected OCI CLI: '+op)


class AlwaysFreePreflightTests(unittest.TestCase):
    def test_exact_expected_free_limits(self):
        self.assertEqual((mod.OCPUS,mod.RAM_GB,mod.BOOT_GB),(2,12,50))
        self.assertEqual(mod.SHAPE,'VM.Standard.A1.Flex')

    def test_home_region_and_clean_empty_account(self):
        with patch.object(mod,'cli',side_effect=fake_oci):
            self.assertEqual(mod.home_region(TENANCY),REGION)
            data=mod.read_inventory(TENANCY,REGION)
        self.assertEqual(data['ads'],[AD])
        self.assertEqual(data['a1_ocpus_in_use'],0)
        self.assertEqual(data['block_volume_gb_in_use'],0)

    def test_other_a1_instances_disqualify_shape(self):
        def used(*args,**kwargs):
            if args[:3] == ('compute','instance','list'):
                return [{'shape':mod.SHAPE,'lifecycle-state':'RUNNING',
                         'shape-config':{'ocpus':1,'memory-in-gbs':6}}]
            return fake_oci(*args,**kwargs)
        with patch.object(mod,'cli',side_effect=used),self.assertRaisesRegex(mod.Stop,'Always Free A1'):
            mod.read_inventory(TENANCY,REGION)

    def test_excess_storage_rejected(self):
        def used(*args,**kwargs):
            if args[:3] == ('bv','volume','list'):
                return [{'lifecycle-state':'AVAILABLE','size-in-gbs':151}]
            return fake_oci(*args,**kwargs)
        with patch.object(mod,'cli',side_effect=used),self.assertRaisesRegex(mod.Stop,'storage exhausted'):
            mod.read_inventory(TENANCY,REGION)

    def test_duplicate_target_is_rejected(self):
        def used(*args,**kwargs):
            if args[:3] == ('compute','instance','list'):
                return [{'shape':mod.SHAPE,'lifecycle-state':'RUNNING',
                         'display-name':mod.NAME,'id':'ocid1.instance...foo',
                         'shape-config':{'ocpus':0.5,'memory-in-gbs':1}}]
            return fake_oci(*args,**kwargs)
        with patch.object(mod,'cli',side_effect=used),self.assertRaisesRegex(mod.Stop,'already exists'):
            mod.read_inventory(TENANCY,REGION)

    def test_network_overlap_is_rejected(self):
        def used(*args,**kwargs):
            if args[:3] == ('network','vcn','list'):
                return [{'cidr-blocks':['10.76.1.0/24'],'lifecycle-state':'AVAILABLE','display-name':'different'}]
            return fake_oci(*args,**kwargs)
        with patch.object(mod,'cli',side_effect=used),self.assertRaisesRegex(mod.Stop,'overlaps'):
            mod.read_inventory(TENANCY,REGION)

    def test_no_images_fail_closed(self):
        def used(*args,**kwargs):
            if args[:3] == ('compute','image','list'):
                return []
            return fake_oci(*args,**kwargs)
        with patch.object(mod,'cli',side_effect=used),self.assertRaisesRegex(mod.Stop,'No official Ubuntu'):
            mod.read_inventory(TENANCY,REGION)

    def test_plan_does_not_mutate_anything(self):
        with tempfile.TemporaryDirectory() as td:
            with (patch.object(mod,'RECEIPT',Path(td)/'receipt'),
                  patch.object(mod,'PARTIAL',Path(td)/'partial'),
                  patch.object(mod,'read_tenancy',return_value=TENANCY),
                  patch.object(mod,'home_region',return_value=REGION),
                  patch.object(mod,'cli',side_effect=fake_oci),
                  patch.object(mod,'make_network') as made,
                  patch.object(mod,'generate_keypair') as key):
                self.assertEqual(mod.main([]),0)
                made.assert_not_called()
                key.assert_not_called()

    def test_reject_noninteractive_apply(self):
        with tempfile.TemporaryDirectory() as td:
            with (patch.object(mod,'RECEIPT',Path(td)/'receipt'),
                  patch.object(mod,'PARTIAL',Path(td)/'partial'),
                  patch.object(mod,'read_tenancy',return_value=TENANCY),
                  patch.object(mod,'home_region',return_value=REGION),
                  patch.object(mod,'cli',side_effect=fake_oci),
                  patch.object(mod.sys.stdin,'isatty',return_value=False),
                  patch.object(mod,'make_network') as made):
                with self.assertRaisesRegex(mod.Stop,'interactive'):
                    mod.main(['--apply'])
                made.assert_not_called()

    def test_security_list_hardened_before_subnet(self):
        calls=[]
        def network(*args,region=None,timeout=90):
            cmd=' '.join(args[:3]);calls.append(cmd)
            if cmd=='network vcn create':
                return {'id':'ocid1.vcn.fixture','default-security-list-id':'ocid1.securitylist.fixture',
                        'default-route-table-id':'ocid1.routetable.fixture'}
            if cmd=='network security-list update':
                self.assertEqual(args[args.index('--ingress-security-rules')+1],'[]')
                return {}
            if cmd=='network security-list get':
                return {'ingress-security-rules':[]}
            if cmd=='network internet-gateway create':
                return {'id':'ocid1.internetgateway.fixture'}
            if cmd=='network route-table update':
                return {}
            if cmd=='network subnet create':
                self.assertIn('--prohibit-public-ip-on-vnic',args)
                return {'id':'ocid1.subnet.fixture'}
            raise AssertionError(cmd)
        with tempfile.TemporaryDirectory() as td:
            state={}
            with patch.object(mod,'RESOURCE_DIR',Path(td)),patch.object(mod,'PARTIAL',Path(td)/'partial.json'),patch.object(mod,'cli',side_effect=network):
                mod.make_network(TENANCY,REGION,state)
                self.assertEqual(state['phase'],'subnet_created')
                self.assertTrue((Path(td)/'partial.json').exists())
        self.assertLess(calls.index('network security-list get'),calls.index('network subnet create'))

    def test_vm_launch_exact_shape_and_free_dimensions(self):
        def vm(*args,region=None,timeout=90):
            if args[:3] == ('compute','instance','launch'):
                self.assertEqual(args[args.index('--shape')+1],mod.SHAPE)
                self.assertEqual(args[args.index('--boot-volume-size-in-gbs')+1],'50')
                self.assertEqual(json.loads(args[args.index('--shape-config')+1]),
                                 {'ocpus':2,'memoryInGBs':12})
                return {'id':'ocid1.instance.fixture'}
            if args[:3] == ('compute','instance','get'):
                return {'shape':mod.SHAPE,'lifecycle-state':'RUNNING',
                        'shape-config':{'ocpus':2,'memory-in-gbs':12}}
            raise AssertionError(args)
        inventory={'home_region':REGION,'tenancy':TENANCY,'ads':[AD],
                   'image_id':'ocid1.image.fixture'}
        state={'subnet_id':'ocid1.subnet.fixture'}
        with patch.object(mod,'cli',side_effect=vm):
            result=mod.launch_vm(inventory,state,Path('/tmp/test-pub-key-do-not-use'))
        self.assertEqual(result['instance_id'],'ocid1.instance.fixture')
        self.assertEqual(result['actual_ocpus'],2)


if __name__=='__main__':
    unittest.main()
