"""Offline tests for strict free-resource preflight and network sequencing."""
from __future__ import annotations
import importlib.util
import json
import subprocess
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


class CloudShellCliParsingTests(unittest.TestCase):
    @staticmethod
    def result(cmd, stdout='', stderr='', rc=0):
        return subprocess.CompletedProcess(cmd, rc, stdout=stdout, stderr=stderr)

    def test_successful_empty_list_is_independently_rechecked(self):
        commands=[]
        def respond(command, **kwargs):
            commands.append(command)
            return self.result(command)
        with patch.object(mod.subprocess, 'run', side_effect=respond):
            self.assertEqual(mod.cli('iam', 'compartment', 'list', '--all'), [])
        self.assertEqual(len(commands), 2)
        self.assertIn('--all', commands[0])
        self.assertNotIn('--all', commands[1])

    def test_empty_unpaginated_response_can_be_checked(self):
        with patch.object(mod.subprocess, 'run',
                          return_value=self.result(['oci'])) as called:
            self.assertEqual(mod.cli('bv', 'volume', 'list'), [])
        self.assertEqual(called.call_count, 2)

    def test_failed_or_warned_empty_list_still_fails_closed(self):
        for stderr, rc in [('WARNING: result may be incomplete', 0),
                           ('', 3)]:
            with self.subTest(stderr=stderr, rc=rc):
                with patch.object(mod.subprocess, 'run',
                                  return_value=self.result(['oci'], stderr=stderr, rc=rc)):
                    with self.assertRaises(mod.Stop):
                        mod.cli('network', 'vcn', 'list', '--all')

    def test_second_list_disagreement_is_not_silenced(self):
        empty=self.result(['oci'])
        nonempty=self.result(['oci'], stdout=json.dumps({'data':[{'id':'existing'}]}))
        with patch.object(mod.subprocess, 'run', side_effect=[empty, nonempty]):
            with self.assertRaisesRegex(mod.Stop, 'disagreed'):
                mod.cli('compute', 'instance', 'list', '--all')

    def test_second_check_can_return_explicit_empty_json(self):
        empty=self.result(['oci'])
        explicit=self.result(['oci'], stdout=json.dumps({'data':[]}))
        with patch.object(mod.subprocess, 'run', side_effect=[empty, explicit]):
            self.assertEqual(mod.cli('iam', 'compartment', 'list', '--all'), [])

    def test_blank_mutation_response_is_never_accepted(self):
        with patch.object(mod.subprocess, 'run',
                          return_value=self.result(['oci'])) as called:
            with self.assertRaisesRegex(mod.Stop, 'non-list'):
                mod.cli('network', 'vcn', 'create')
        self.assertEqual(called.call_count, 1)

    def test_malformed_json_response_is_never_accepted(self):
        with patch.object(mod.subprocess, 'run',
                          return_value=self.result(['oci'],stdout='not-json')):
            with self.assertRaisesRegex(mod.Stop, 'invalid JSON'):
                mod.cli('compute', 'instance', 'list')

    def test_valid_structured_response_preserved(self):
        value={'data':[{'shape':mod.SHAPE}]}
        with patch.object(mod.subprocess, 'run',
                          return_value=self.result(['oci'], stdout=json.dumps(value))) as called:
            self.assertEqual(mod.cli('compute', 'shape', 'list'), value['data'])
        self.assertEqual(called.call_count, 1)



class CloudShellFipsKeyTests(unittest.TestCase):
    def test_rsa4096_keypair_created_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            private = root / 'test_rsa4096'
            public = root / 'test_rsa4096.pub'
            captured = []
            def generate(args, **kwargs):
                captured.append(args)
                private.write_text('TEST ONLY PRIVATE KEY', encoding='ascii')
                public.write_text('ssh-rsa TEST-ONLY-NONKEY', encoding='ascii')
                return mod.subprocess.CompletedProcess(args, 0)
            with (patch.object(mod,'RESOURCE_DIR',root),
                  patch.object(mod,'PRIVATE_KEY',private),
                  patch.object(mod,'PUBLIC_KEY',public),
                  patch.object(mod.subprocess,'run',side_effect=generate)):
                self.assertEqual(mod.generate_keypair(),public)
            self.assertEqual(len(captured),1)
            self.assertEqual(captured[0][:6], ['ssh-keygen','-q','-t','rsa','-b','4096'])
            self.assertEqual(private.stat().st_mode & 0o777,0o600)
            self.assertEqual(public.stat().st_mode & 0o777,0o600)

    def test_ed25519_keys_cannot_be_reused_in_fips_profile(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            private=root / 'test_rsa4096'
            public=root / 'test_rsa4096.pub'
            private.write_text('TEST KEY ONLY',encoding='ascii')
            public.write_text('ssh-ed25519 TEST-ONLY',encoding='ascii')
            private.chmod(0o600)
            with (patch.object(mod,'RESOURCE_DIR',root),
                  patch.object(mod,'PRIVATE_KEY',private),
                  patch.object(mod,'PUBLIC_KEY',public)):
                with self.assertRaisesRegex(mod.Stop,'SSH key permissions/type'):
                    mod.generate_keypair()

    def test_fips_keygen_failure_prevents_any_cloud_creation(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with (patch.object(mod,'RESOURCE_DIR',root),
                  patch.object(mod,'PRIVATE_KEY',root/'test_rsa4096'),
                  patch.object(mod,'PUBLIC_KEY',root/'test_rsa4096.pub'),
                  patch.object(mod.subprocess,'run',
                               return_value=mod.subprocess.CompletedProcess(['ssh-keygen'],255)),
                  patch.object(mod,'make_network') as network):
                with self.assertRaisesRegex(mod.Stop,'Could not generate'):
                    mod.generate_keypair()
                network.assert_not_called()




class ResumePartialResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.partial=self.base/'partial.json'
        self.receipt=self.base/'final.json'
        self.private=self.base/'fake-rsa'
        self.public=self.base/'fake-rsa.pub'
        self.private.write_text('TEST-PRIVATE-KEY-FIXTURE',encoding='ascii')
        self.private.chmod(0o600)
        self.public.write_text('ssh-rsa TEST-ONLY',encoding='ascii')
        self.public.chmod(0o600)
        self.ids={name:'ocid1.'+kind+'.oc1.iad.fixture' for name,kind in [
            ('vcn_id','vcn'),('security_list_id','securitylist'),
            ('route_table_id','routetable'),('internet_gateway_id','internetgateway'),
            ('subnet_id','subnet')]}
        self.state={
            'schema':1,'phase':'subnet_created','tenancy_id':TENANCY,
            'home_region':REGION,'release_status':'HOLD',
            'no_customer_data':True,'no_open_ingress':True,
            'public_key_path':str(self.public),'key_private_path':str(self.private),
            **self.ids}
        self.partial.write_text(json.dumps(self.state),encoding='utf-8')
        self.partial.chmod(0o600)

    def patches(self):
        from contextlib import ExitStack
        stack=ExitStack()
        stack.enter_context(patch.object(mod,'PARTIAL',self.partial))
        stack.enter_context(patch.object(mod,'RECEIPT',self.receipt))
        stack.enter_context(patch.object(mod,'RESOURCE_DIR',self.base))
        stack.enter_context(patch.object(mod,'PRIVATE_KEY',self.private))
        stack.enter_context(patch.object(mod,'PUBLIC_KEY',self.public))
        return stack

    def fake_network(self,*args,region=None,timeout=90):
        op=' '.join(args[:3])
        if op == 'network vcn get':
            return {'id':self.ids['vcn_id'],'display-name':mod.VPC_NAME,
                    'lifecycle-state':'AVAILABLE','cidr-blocks':[str(mod.VPC_NETWORK)],
                    'default-security-list-id':self.ids['security_list_id'],
                    'default-route-table-id':self.ids['route_table_id']}
        if op == 'network security-list get':
            return {'id':self.ids['security_list_id'],
                    'vcn-id':self.ids['vcn_id'],'ingress-security-rules':[]}
        if op == 'network subnet get':
            return {'id':self.ids['subnet_id'],'vcn-id':self.ids['vcn_id'],
                    'lifecycle-state':'AVAILABLE','display-name':'retally-outbound-no-inbound',
                    'cidr-block':mod.SUBNET_NETWORK,
                    'security-list-ids':[self.ids['security_list_id']],
                    'prohibit-public-ip-on-vnic':False}
        if op == 'network internet-gateway get':
            return {'id':self.ids['internet_gateway_id'],
                    'vcn-id':self.ids['vcn_id'],
                    'is-enabled':True,'display-name':'retally-outbound-only'}
        if op == 'network route-table get':
            return {'id':self.ids['route_table_id'],'vcn-id':self.ids['vcn_id'],
                    'route-rules':[{'destination':'0.0.0.0/0',
                                    'network-entity-id':self.ids['internet_gateway_id']}]}
        raise AssertionError('unexpected OCI action '+op)

    def test_network_verified_read_only(self):
        with self.patches(), patch.object(mod,'cli',side_effect=self.fake_network) as checked:
            mod.verify_partial_network(self.state,TENANCY,REGION)
        self.assertEqual(checked.call_count,5)
        self.assertTrue(all(call.args[2]=='get' for call in checked.call_args_list))

    def test_unapproved_ingress_fails_closed(self):
        def unsafe(*args,**kwargs):
            result=self.fake_network(*args,**kwargs)
            if args[:3]==('network','security-list','get'):
                result['ingress-security-rules']=[{'source':'0.0.0.0/0'}]
            return result
        with self.patches(), patch.object(mod,'cli',side_effect=unsafe):
            with self.assertRaisesRegex(mod.Stop,'zero-ingress'):
                mod.verify_partial_network(self.state,TENANCY,REGION)

    def test_wrong_subnet_or_gateway_fails_closed(self):
        for name in ('subnet','internet-gateway'):
            def changed(*args,**kwargs):
                result=self.fake_network(*args,**kwargs)
                if args[1]==name:
                    result['vcn-id']='ocid1.vcn.oc1.iad.other'
                return result
            with self.subTest(name=name),self.patches(),patch.object(mod,'cli',side_effect=changed):
                with self.assertRaises(mod.Stop):
                    mod.verify_partial_network(self.state,TENANCY,REGION)

    def test_mismatched_receipt_cannot_resume(self):
        with self.patches(),patch.object(mod,'cli',side_effect=self.fake_network):
            for change in ({'release_status':'APPROVED'},
                           {'phase':'gateway_created'},
                           {'instance_id':'ocid1.instance.oc1.iad.existing'},
                           {'home_region':'us-phoenix-1'}):
                with self.subTest(change=change):
                    with self.assertRaises(mod.Stop):
                        mod.verify_partial_network({**self.state,**change},TENANCY,REGION)

    def test_resume_inventory_reuses_only_original_exact_vcn(self):
        def network_and_resources(*args,**kwargs):
            if args[:3]==('network','vcn','list'):
                return [{'id':self.ids['vcn_id'],'display-name':mod.VPC_NAME,
                         'cidr-blocks':[str(mod.VPC_NETWORK)],'lifecycle-state':'AVAILABLE'}]
            return fake_oci(*args,**kwargs)
        with self.patches(),patch.object(mod,'cli',side_effect=network_and_resources):
            inv=mod.read_inventory(TENANCY,REGION,
                                   existing_vcn_id=self.ids['vcn_id'])
        self.assertEqual(inv['vcn_count'],1)
        self.assertEqual(inv['a1_ocpus_in_use'],0)

    def test_changed_or_duplicate_vcn_rejected(self):
        for kind in ('wrong_cidr','other_duplicate'):
            def changed(*args,**kwargs):
                if args[:3]==('network','vcn','list'):
                    first={'id':self.ids['vcn_id'],'display-name':mod.VPC_NAME,
                           'cidr-blocks':[str(mod.VPC_NETWORK)],'lifecycle-state':'AVAILABLE'}
                    if kind=='wrong_cidr':
                        first['cidr-blocks']=['10.80.0.0/16']
                        return [first]
                    return [first,{'id':'ocid1.vcn.oc1.iad.other',
                                   'display-name':mod.VPC_NAME,'cidr-blocks':['10.82.0.0/16'],
                                   'lifecycle-state':'AVAILABLE'}]
                return fake_oci(*args,**kwargs)
            with self.subTest(kind=kind),self.patches(),patch.object(mod,'cli',side_effect=changed):
                with self.assertRaises(mod.Stop):
                    mod.read_inventory(TENANCY,REGION,
                                       existing_vcn_id=self.ids['vcn_id'])

    def test_partial_inspection_never_writes(self):
        inv={'existing_instances':0,'a1_ocpus_in_use':0,
             'block_volume_gb_in_use':0,'vcn_count':1}
        with (self.patches(),
              patch.object(mod,'read_tenancy',return_value=TENANCY),
              patch.object(mod,'home_region',return_value=REGION),
              patch.object(mod,'verify_partial_network') as checked,
              patch.object(mod,'read_inventory',return_value=inv),
              patch.object(mod,'launch_vm') as launch,
              patch.object(mod,'make_network') as network,
              patch('builtins.print')):
            self.assertEqual(mod.main(['--inspect-partial']),0)
        launch.assert_not_called()
        network.assert_not_called()
        checked.assert_called_once()
        self.assertTrue(self.partial.exists())
        self.assertFalse(self.receipt.exists())

    def test_resume_needs_tty_and_never_creates_network(self):
        inv={'existing_instances':0,'a1_ocpus_in_use':0,
             'block_volume_gb_in_use':0,'vcn_count':1}
        with (self.patches(),
              patch.object(mod,'read_tenancy',return_value=TENANCY),
              patch.object(mod,'home_region',return_value=REGION),
              patch.object(mod,'verify_partial_network'),
              patch.object(mod,'read_inventory',return_value=inv),
              patch.object(mod.sys.stdin,'isatty',return_value=False),
              patch.object(mod,'launch_vm') as launch,
              patch.object(mod,'make_network') as network,
              patch('builtins.print')):
            with self.assertRaisesRegex(mod.Stop,'interactive'):
                mod.main(['--resume'])
        launch.assert_not_called()
        network.assert_not_called()

    def test_successful_resume_finalizes_without_new_network(self):
        inv={'existing_instances':0,'a1_ocpus_in_use':0,
             'block_volume_gb_in_use':0,'vcn_count':1}
        def launch(inv,state,key):
            self.assertEqual(key,self.public)
            state['instance_id']='ocid1.instance.oc1.iad.synthetic'
        with (self.patches(),
              patch.object(mod,'read_tenancy',return_value=TENANCY),
              patch.object(mod,'home_region',return_value=REGION),
              patch.object(mod,'verify_partial_network') as checked,
              patch.object(mod,'read_inventory',return_value=inv),
              patch.object(mod.sys.stdin,'isatty',return_value=True),
              patch('builtins.input',return_value='RESUME RETALLY ALWAYS FREE'),
              patch.object(mod,'launch_vm',side_effect=launch) as called,
              patch.object(mod,'make_network') as network,
              patch('builtins.print')):
            self.assertEqual(mod.main(['--resume']),0)
        self.assertEqual(checked.call_count,2)
        called.assert_called_once()
        network.assert_not_called()
        self.assertFalse(self.partial.exists())
        self.assertTrue(self.receipt.exists())
        self.assertTrue(json.loads(self.receipt.read_text())['instance_id'].startswith('ocid1.instance.'))

    def test_unsafe_cli_error_does_not_leak_provider_stderr(self):
        message='ServiceError:\\n{"code": "InternalError", "message": "SECRET_ACCOUNT_REFERENCE"}'
        error=subprocess.CompletedProcess(['oci'],1,stdout='',stderr=message)
        with patch.object(mod.subprocess,'run',return_value=error):
            with self.assertRaises(mod.Stop) as caught:
                mod.cli('compute','instance','launch')
        self.assertIn('InternalError',str(caught.exception))
        self.assertNotIn('SECRET_ACCOUNT_REFERENCE',str(caught.exception))




class SingleAttemptCliSafetyTests(unittest.TestCase):
    def test_instance_launch_has_exactly_one_provider_attempt(self):
        result = subprocess.CompletedProcess(
            args=['oci'], returncode=1, stdout='',
            stderr='ServiceError: InternalError')
        with patch.object(mod.subprocess, 'run', return_value=result) as run:
            with self.assertRaisesRegex(mod.Stop, 'InternalError'):
                mod.cli('compute', 'instance', 'launch',
                        '--shape', 'VM.Standard.A1.Flex')
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0].count('--no-retry'), 1)

    def test_blank_list_verification_disables_automatic_retries(self):
        result = subprocess.CompletedProcess(
            args=['oci'], returncode=0, stdout='', stderr='')
        with patch.object(mod.subprocess, 'run', side_effect=[result,result]) as run:
            self.assertEqual(mod.cli('compute', 'instance', 'list', '--all'), [])
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertEqual(call.args[0].count('--no-retry'), 1)



if __name__=='__main__':
    unittest.main()
