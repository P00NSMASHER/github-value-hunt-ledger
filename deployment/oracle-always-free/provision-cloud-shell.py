#!/usr/bin/env python3
"""Preflight and optionally provision one Oracle Always Free A1 RETALLY staging VM.

This is an OCI *Cloud Shell* tool. Cloud Shell is pre-authenticated as the signed-in
OCI user. No account password, API key, or private key is sent to ChatGPT.

Default: read-only plan. --apply: require interactive confirmation, then create an
isolated network with NO inbound rules and one Ubuntu Arm64 Always Free-sized VM.
No customer data, applications, HTTP listeners, SSH ingress, cloud tunneling,
paid add-ons or external services are installed or enabled.
"""
from __future__ import annotations

import argparse
import configparser
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import subprocess
import sys

NAME = 'retally-private-staging'
SHAPE = 'VM.Standard.A1.Flex'
OCPUS = 2
RAM_GB = 12
BOOT_GB = 50
MAX_A1_OCPUS = 2
MAX_A1_MEMORY_GB = 12
MAX_BLOCK_STORAGE_GB = 200
VPC_NAME = 'retally-private-vcn'
VPC_NETWORK = ipaddress.ip_network('10.76.0.0/16')
SUBNET_NETWORK = '10.76.1.0/24'
RESOURCE_DIR = Path.home() / '.retally-oracle'
RECEIPT = RESOURCE_DIR / 'always-free-staging-receipt.json'
PARTIAL = RESOURCE_DIR / 'partial-setup-receipt.json'
PUBLIC_KEY = RESOURCE_DIR / 'retally_oci_a1_rsa4096.pub'
PRIVATE_KEY = RESOURCE_DIR / 'retally_oci_a1_rsa4096'


class Stop(RuntimeError):
    """Fail closed rather than guessing about an OCI resource or paid service."""


def ensure(condition: bool, message: str) -> None:
    if not condition:
        raise Stop(message)


def cli(*args: str, region: str | None = None, timeout: int = 90):
    cmd = ['oci', *map(str, args), '--output', 'json']
    if region:
        cmd += ['--region', region]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                                check=False)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise Stop('OCI CLI unavailable or timed out; use the signed-in Oracle Cloud Shell.') from exc
    if result.returncode:
        # Do not expose provider response data or credentials in the chat.
        # Restrict errors to public provider code labels; never leak CLI stderr,
        # request IDs, account information or credentials into operator output.
        raw_error = result.stderr or ''
        labels = ('OutOfHostCapacity', 'ServiceLimitExceeded', 'LimitExceeded',
                  'NotAuthorizedOrNotFound', 'InvalidParameter', 'TooManyRequests',
                  'InternalError', 'ServiceError')
        label = next((tag for tag in labels if tag.lower() in raw_error.lower()), None)
        if re.search(r'out of host capacity', raw_error, re.IGNORECASE):
            label = 'OutOfHostCapacity'
        raise Stop(f'OCI {" ".join(args[:3])} failed ({label or "exit status "+str(result.returncode)}). No paid fallback.')
    if not result.stdout.strip():
        # OCI CLI 3.91 on signed-in Cloud Shell reports a successful EMPTY list
        # with zero stdout bytes. Requery without --all; only two consistent,
        # warning-free successful empty reads may be treated as an empty list.
        ensure(len(args) >= 3 and args[2] == 'list' and not result.stderr.strip(),
               'OCI returned no JSON for a non-list operation or with warnings.')
        verification_args = [str(a) for a in args if a != '--all']
        verification_cmd = ['oci', *verification_args, '--output', 'json']
        if region:
            verification_cmd += ['--region', region]
        try:
            verified = subprocess.run(
                verification_cmd, capture_output=True, text=True,
                timeout=timeout, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise Stop('Cannot independently confirm an empty OCI resource list.') from exc
        ensure(verified.returncode == 0 and not verified.stderr.strip(),
               'OCI empty-list check failed; no resources will be created.')
        if verified.stdout.strip():
            try:
                explicit = json.loads(verified.stdout)
            except json.JSONDecodeError as exc:
                raise Stop('OCI empty-list check returned invalid JSON.') from exc
            ensure(isinstance(explicit, dict) and explicit.get('data') == [],
                   'OCI empty-list check disagreed with original inventory.')
        return []
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise Stop('OCI returned invalid JSON; no further actions taken.') from exc
    ensure(isinstance(payload, dict) and 'data' in payload,
           'OCI JSON response did not contain a data field.')
    return payload['data']


def config_tenancy() -> str | None:
    candidate = os.environ.get('OCI_TENANCY_OCID') or os.environ.get('OCI_CLI_TENANCY')
    if candidate:
        return candidate
    path = Path(os.environ.get('OCI_CLI_CONFIG_FILE', str(Path.home() / '.oci' / 'config')))
    config = configparser.ConfigParser(interpolation=None)
    config.read(path)
    profile = os.environ.get('OCI_CLI_PROFILE', 'DEFAULT')
    if profile in config:
        return config[profile].get('tenancy')
    return None


def read_tenancy(explicit: str | None, *, interactive: bool = True) -> str:
    tenancy = explicit or config_tenancy()
    if not tenancy and interactive and sys.stdin.isatty():
        tenancy = input('Tenancy OCID from Oracle Console (not a secret): ').strip()
    ensure(bool(tenancy and re.fullmatch(r'ocid1\.tenancy\..+', tenancy)),
           'Tenancy OCID was not available. Supply --tenancy-id ocid1.tenancy...')
    return tenancy


def data_list(value, label: str) -> list[dict]:
    ensure(isinstance(value, list), f'Cannot verify complete {label} inventory: unexpected result.')
    ensure(all(isinstance(v, dict) for v in value), f'Invalid {label} inventory.')
    return value


def active(entry: dict) -> bool:
    return str(entry.get('lifecycle-state', '')).upper() not in {
        'TERMINATED', 'TERMINATING', 'DELETED', 'DELETING', 'INACTIVE'}


def home_region(tenancy: str) -> str:
    # Region subscriptions can derive tenancy from OCI config, but pass it explicitly.
    regions = data_list(cli('iam', 'region-subscription', 'list', '--tenancy-id', tenancy, '--all'),
                        'region subscription')
    homes = [r for r in regions if r.get('is-home-region') is True]
    ensure(len(homes) == 1 and isinstance(homes[0].get('region-name'), str),
           'Unable to uniquely identify OCI home region; fail closed.')
    return homes[0]['region-name']


def compartments(tenancy: str, region: str) -> list[str]:
    cs = data_list(cli('iam', 'compartment', 'list', '--compartment-id', tenancy,
                       '--compartment-id-in-subtree', 'true', '--access-level', 'ANY',
                       '--all', region=region), 'compartments')
    ids = [tenancy] + [c['id'] for c in cs if active(c) and c.get('id')]
    return list(dict.fromkeys(ids))


def read_inventory(tenancy: str, region: str, *, existing_vcn_id: str | None = None):
    ads = data_list(cli('iam', 'availability-domain', 'list', '--compartment-id', tenancy,
                        region=region), 'availability domains')
    ad_names = [a.get('name') for a in ads if a.get('name')]
    ensure(ad_names, 'No availability domains reported in the home region.')
    compartments_ids = compartments(tenancy, region)
    ocpus = ram = size_gb = 0.0
    instance_count = 0
    found_names = []
    vcns = []
    networks = []
    owned_vcn_count = 0
    for compartment in compartments_ids:
        instances = data_list(cli('compute', 'instance', 'list', '--compartment-id', compartment,
                                  '--all', region=region), 'compute instances')
        for inst in instances:
            if not active(inst):
                continue
            instance_count += 1
            if inst.get('display-name') == NAME:
                found_names.append(inst.get('id'))
            if inst.get('shape') == SHAPE:
                config = inst.get('shape-config') or {}
                ensure('ocpus' in config and 'memory-in-gbs' in config,
                       'Cannot verify existing Ampere A1 allocation.')
                ocpus += float(config['ocpus'])
                ram += float(config['memory-in-gbs'])
        block = data_list(cli('bv', 'volume', 'list', '--compartment-id', compartment,
                              '--all', region=region), 'block volumes')
        size_gb += sum(float(v.get('size-in-gbs') or 0) for v in block if active(v))
        for ad in ad_names:
            boot = data_list(cli('bv', 'boot-volume', 'list', '--compartment-id', compartment,
                                 '--availability-domain', ad, '--all', region=region),
                             'boot volumes')
            size_gb += sum(float(v.get('size-in-gbs') or 0) for v in boot if active(v))
        vs = data_list(cli('network', 'vcn', 'list', '--compartment-id', compartment,
                            '--all', region=region), 'VCNs')
        for v in vs:
            if active(v):
                vcns.append(v)
                blocks = v.get('cidr-blocks') or ([v['cidr-block']] if v.get('cidr-block') else [])
                if existing_vcn_id and v.get('id') == existing_vcn_id:
                    owned_vcn_count += 1
                    ensure(v.get('display-name') == VPC_NAME and blocks == [str(VPC_NETWORK)],
                           'Recorded staging VCN identity or CIDR changed; refusing resume.')
                else:
                    if v.get('display-name') == VPC_NAME:
                        found_names.append(v.get('id'))
                    networks.extend(blocks)
    ensure(not found_names, 'RETALLY instance/VCN already exists; refusing duplicate resources.')
    if existing_vcn_id:
        ensure(owned_vcn_count == 1, 'Exactly one original staging VCN must be visible for resume.')
    ensure(ocpus + OCPUS <= MAX_A1_OCPUS and ram + RAM_GB <= MAX_A1_MEMORY_GB,
           f'Always Free A1 allocation unavailable (in use: {ocpus} OCPU, {ram} GB RAM).')
    ensure(size_gb + BOOT_GB <= MAX_BLOCK_STORAGE_GB,
           f'Always Free storage exhausted (allocated: {size_gb:g} GB).')
    ensure(len(vcns) < 2, 'Existing VCNs occupy the Always Free VCN allowance.')
    for network in networks:
        try:
            if VPC_NETWORK.overlaps(ipaddress.ip_network(network, strict=False)):
                raise Stop('Planned private CIDR overlaps an existing VCN; refusing network creation.')
        except ValueError as exc:
            raise Stop('Existing VCN has an unrecognized CIDR; cannot establish isolation.') from exc
    # Available shape listing indicates supported AD, not actual free host capacity.
    supported_ads = []
    for ad in ad_names:
        shapes = data_list(cli('compute', 'shape', 'list', '--compartment-id', tenancy,
                               '--availability-domain', ad, '--shape', SHAPE,
                               region=region), 'A1 shape offerings')
        if any(s.get('shape') == SHAPE for s in shapes):
            supported_ads.append(ad)
    ensure(supported_ads, 'No Ampere A1 supported in OCI home-region availability domains.')
    images = data_list(cli('compute', 'image', 'list', '--compartment-id', tenancy,
                           '--operating-system', 'Canonical Ubuntu',
                           '--operating-system-version', '24.04', '--shape', SHAPE,
                           '--sort-by', 'TIMECREATED', '--sort-order', 'DESC',
                           region=region), 'official Ubuntu Arm64 images')
    eligible = [im for im in images if im.get('operating-system') == 'Canonical Ubuntu'
                and im.get('operating-system-version') == '24.04'
                and im.get('lifecycle-state') == 'AVAILABLE'
                and im.get('id', '').startswith('ocid1.image.')]
    ensure(eligible, 'No official Ubuntu 24.04 image compatible with Ampere A1; no paid fallback.')
    return {'tenancy':tenancy, 'home_region':region, 'ads':supported_ads,
            'image_id':eligible[0]['id'], 'image_name':eligible[0].get('display-name'),
            'existing_instances':instance_count, 'a1_ocpus_in_use':ocpus,
            'a1_ram_gb_in_use':ram, 'block_volume_gb_in_use':size_gb,
            'vcn_count':len(vcns)}


def safe_receipt(data: dict, *, partial: bool):
    RESOURCE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = PARTIAL if partial else RECEIPT
    # Preserve the previous receipt rather than overwriting evidence on retry.
    with path.open('x', encoding='utf-8') as fd:
        json.dump(data, fd, indent=2, sort_keys=True)
        fd.write('\n')
    os.chmod(path, 0o600)
    return path


def generate_keypair():
    # Oracle Cloud Shell enforces FIPS mode and rejects Ed25519. Use RSA-4096.
    RESOURCE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(RESOURCE_DIR, 0o700)
    ensure(PRIVATE_KEY.exists() == PUBLIC_KEY.exists(),
           'Found an incomplete SSH keypair; refusing to overwrite it.')
    if PRIVATE_KEY.exists():
        ensure(PRIVATE_KEY.is_file() and PUBLIC_KEY.is_file() and
               (PRIVATE_KEY.stat().st_mode & 0o077) == 0 and
               PUBLIC_KEY.read_text(encoding='ascii').startswith('ssh-rsa '),
               'Existing Cloud Shell SSH key permissions/type are not acceptable.')
        return PUBLIC_KEY
    ensure(subprocess.run(['ssh-keygen', '-q', '-t', 'rsa', '-b', '4096', '-N', '', '-f', str(PRIVATE_KEY)],
                          capture_output=True, check=False, timeout=30).returncode == 0,
           'Could not generate the SSH keypair in Cloud Shell.')
    os.chmod(PRIVATE_KEY, 0o600)
    os.chmod(PUBLIC_KEY, 0o600)
    return PUBLIC_KEY


def make_network(tenancy: str, region: str, state: dict):
    def save(*, phase):
        state['phase'] = phase
        if PARTIAL.exists():
            # Only modify a receipt created by this run; guard against other attempts.
            PARTIAL.write_text(json.dumps(state, indent=2, sort_keys=True) + '\n')
            os.chmod(PARTIAL, 0o600)
        else:
            safe_receipt(state, partial=True)

    vcn = cli('network','vcn','create','--compartment-id',tenancy,
              '--cidr-blocks',json.dumps([str(VPC_NETWORK)]), '--dns-label','retallyoci',
              '--display-name',VPC_NAME,'--wait-for-state','AVAILABLE',region=region)
    ensure(isinstance(vcn,dict) and vcn.get('id') and vcn.get('default-security-list-id')
           and vcn.get('default-route-table-id'), 'VCN response was incomplete.')
    state.update({'vcn_id':vcn['id'], 'security_list_id':vcn['default-security-list-id'],
                  'route_table_id':vcn['default-route-table-id']})
    save(phase='vcn_created')
    # OCI default security lists have general SSH ingress: remove it BEFORE subnet/VM.
    cli('network','security-list','update', '--security-list-id',state['security_list_id'],
        '--ingress-security-rules','[]',
        '--egress-security-rules',json.dumps([{'destination':'0.0.0.0/0',
                                               'destinationType':'CIDR_BLOCK',
                                               'protocol':'all','isStateless':False}]),
        '--force',region=region)
    sl = cli('network','security-list','get','--security-list-id',state['security_list_id'],
             region=region)
    ensure(isinstance(sl,dict) and sl.get('ingress-security-rules') == [],
           'Could not verify empty inbound security rules. No VM will be created.')
    save(phase='ingress_verified_closed')
    gw = cli('network','internet-gateway','create','--compartment-id',tenancy,
             '--vcn-id',state['vcn_id'],'--display-name','retally-outbound-only',
             '--is-enabled','true','--wait-for-state','AVAILABLE',region=region)
    ensure(gw.get('id'), 'Internet gateway was not returned by OCI.')
    state['internet_gateway_id'] = gw['id']
    save(phase='gateway_created')
    cli('network','route-table','update','--rt-id',state['route_table_id'],
        '--route-rules',json.dumps([{'cidrBlock':'0.0.0.0/0',
                                    'networkEntityId':gw['id']}]),
        '--force',region=region)
    save(phase='outbound_route_configured')
    subnet = cli('network','subnet','create', '--compartment-id',tenancy,
                 '--vcn-id',state['vcn_id'], '--cidr-block',SUBNET_NETWORK,
                 '--display-name','retally-outbound-no-inbound',
                 '--dns-label','retallynet',
                 '--prohibit-public-ip-on-vnic','false',
                 '--wait-for-state','AVAILABLE',region=region)
    ensure(subnet.get('id'), 'Subnet ID was not returned by OCI.')
    state['subnet_id'] = subnet['id']
    save(phase='subnet_created')
    return state


def verify_partial_network(state: dict, tenancy: str, region: str) -> None:
    """Read-only, exact-resource verification; never creates or edits any OCI object."""
    ensure(isinstance(state, dict) and state.get('schema') == 1 and
           state.get('phase') == 'subnet_created' and not state.get('instance_id'),
           'Only a fully-created network with no recorded VM may be inspected or resumed.')
    ensure(state.get('tenancy_id') == tenancy and state.get('home_region') == region,
           'Partial receipt belongs to a different tenancy or home region.')
    ensure(state.get('release_status') == 'HOLD' and
           state.get('no_customer_data') is True and state.get('no_open_ingress') is True,
           'Original safety holds cannot be verified.')
    ensure(PARTIAL.is_file() and not PARTIAL.is_symlink() and
           os.stat(PARTIAL).st_mode & 0o077 == 0 and
           os.stat(PARTIAL).st_uid == os.geteuid(),
           'Private partial receipt permissions/owner are not verified.')
    ensure(state.get('public_key_path') == str(PUBLIC_KEY) and
           state.get('key_private_path') == str(PRIVATE_KEY),
           'Recorded SSH key path does not match the original staging key.')
    ensure(PRIVATE_KEY.is_file() and PUBLIC_KEY.is_file() and
           not PRIVATE_KEY.is_symlink() and not PUBLIC_KEY.is_symlink() and
           os.stat(PRIVATE_KEY).st_mode & 0o077 == 0 and
           PUBLIC_KEY.read_text(encoding='ascii').startswith('ssh-rsa '),
           'Original owner-only RSA-4096 SSH keypair must remain present.')

    ids = ('vcn_id', 'security_list_id', 'route_table_id',
           'internet_gateway_id', 'subnet_id')
    ensure(all(isinstance(state.get(k), str) and
               re.fullmatch(r'ocid1\.[A-Za-z][A-Za-z0-9]*\.[A-Za-z0-9.]+', state[k])
               for k in ids), 'Partial receipt lacks exact OCI resource identifiers.')

    vcn = cli('network', 'vcn', 'get', '--vcn-id', state['vcn_id'], region=region)
    ensure(isinstance(vcn, dict) and vcn.get('id') == state['vcn_id'] and
           vcn.get('lifecycle-state') == 'AVAILABLE' and
           vcn.get('display-name') == VPC_NAME and
           vcn.get('cidr-blocks') == [str(VPC_NETWORK)] and
           vcn.get('default-security-list-id') == state['security_list_id'] and
           vcn.get('default-route-table-id') == state['route_table_id'],
           'Original VCN or its default security/route identities changed.')

    access = cli('network', 'security-list', 'get',
                 '--security-list-id', state['security_list_id'], region=region)
    ensure(isinstance(access, dict) and access.get('id') == state['security_list_id'] and
           access.get('vcn-id') == state['vcn_id'] and
           access.get('ingress-security-rules') == [],
           'Original VCN no longer has a zero-ingress security list.')

    subnet = cli('network', 'subnet', 'get', '--subnet-id', state['subnet_id'],
                 region=region)
    ensure(isinstance(subnet, dict) and subnet.get('id') == state['subnet_id'] and
           subnet.get('lifecycle-state') == 'AVAILABLE' and
           subnet.get('display-name') == 'retally-outbound-no-inbound' and
           subnet.get('vcn-id') == state['vcn_id'] and
           subnet.get('cidr-block') == SUBNET_NETWORK and
           subnet.get('security-list-ids') == [state['security_list_id']] and
           subnet.get('prohibit-public-ip-on-vnic') is False,
           'Original subnet isolation or source permissions cannot be verified.')

    gateway = cli('network', 'internet-gateway', 'get',
                  '--ig-id', state['internet_gateway_id'], region=region)
    ensure(isinstance(gateway, dict) and
           gateway.get('id') == state['internet_gateway_id'] and
           gateway.get('vcn-id') == state['vcn_id'] and
           gateway.get('is-enabled') is True and
           gateway.get('display-name') == 'retally-outbound-only',
           'Outbound-only gateway identity has changed.')

    route = cli('network', 'route-table', 'get',
                '--rt-id', state['route_table_id'], region=region)
    rules = route.get('route-rules') if isinstance(route, dict) else None
    ensure(isinstance(route, dict) and route.get('id') == state['route_table_id'] and
           route.get('vcn-id') == state['vcn_id'] and
           isinstance(rules, list) and len(rules) == 1 and
           (rules[0].get('destination') or rules[0].get('cidr-block')) == '0.0.0.0/0' and
           rules[0].get('network-entity-id') == state['internet_gateway_id'],
           'Outbound-only route no longer matches the recorded gateway.')


def launch_vm(inventory: dict, state: dict, ssh_public_key: Path):
    region = inventory['home_region']
    for ad in inventory['ads']:
        try:
            vm = cli('compute','instance','launch','--availability-domain',ad,
                     '--compartment-id',inventory['tenancy'],'--subnet-id',state['subnet_id'],
                     '--display-name',NAME,'--shape',SHAPE,
                     '--shape-config',json.dumps({'ocpus':OCPUS,'memoryInGBs':RAM_GB}),
                     '--image-id',inventory['image_id'],'--boot-volume-size-in-gbs',str(BOOT_GB),
                     '--ssh-authorized-keys-file',str(ssh_public_key),
                     '--assign-public-ip','true','--wait-for-state','RUNNING',
                     '--max-wait-seconds','900',region=region,timeout=1000)
        except Stop as exc:
            if 'OutOfHostCapacity' in str(exc) or 'out of host capacity' in str(exc).lower():
                print('Always Free A1 capacity unavailable in this AD; trying another free AD.')
                continue
            raise
        ensure(vm.get('id','').startswith('ocid1.instance.'), 'Instance launch not independently verified.')
        verify = cli('compute','instance','get','--instance-id',vm['id'],region=region)
        ensure(verify.get('shape') == SHAPE and verify.get('lifecycle-state') == 'RUNNING',
               'Created instance is not the exact Always Free A1 shape in RUNNING state.')
        config = verify.get('shape-config') or {}
        ensure(float(config.get('ocpus',-1)) == OCPUS and
               float(config.get('memory-in-gbs',-1)) == RAM_GB,
               'Created VM shape allocation is incorrect; inspect and terminate if needed.')
        state.update({'phase':'vm_running', 'instance_id':vm['id'],'availability_domain':ad,
                      'image_id':inventory['image_id'],'actual_shape':SHAPE,
                      'actual_ocpus':OCPUS,'actual_ram_gb':RAM_GB,
                      'boot_gb_requested':BOOT_GB})
        return state
    raise Stop('Out of host capacity in every supported home-region AD; no paid fallback.')


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenancy-id', help='OCI tenancy OCID, automatically read from Cloud Shell when available')
    parser.add_argument('--apply', action='store_true', help='Create an Always Free-sized VM after interactive confirmation')
    args = parser.parse_args(argv)
    os.umask(0o077)
    ensure(not RECEIPT.exists() and not PARTIAL.exists(),
           f'Prior OCI staging receipt exists in {RESOURCE_DIR}; refusing duplicate creation.')
    tenancy = read_tenancy(args.tenancy_id)
    region = home_region(tenancy)
    inventory = read_inventory(tenancy, region)
    print('\n=== Oracle Always Free RETALLY preflight ===')
    print(json.dumps({'region':region,'name':NAME,'shape':SHAPE,'ocpus':OCPUS,
                      'ram_gb':RAM_GB,'boot_gb':BOOT_GB,'image_name':inventory['image_name'],
                      'existing_a1_ocpus':inventory['a1_ocpus_in_use'],
                      'existing_a1_ram_gb':inventory['a1_ram_gb_in_use'],
                      'existing_block_gb':inventory['block_volume_gb_in_use'],
                      'existing_vcns':inventory['vcn_count'], 'availability_domains':inventory['ads'],
                      'ingress':'DENY ALL', 'public_website':'UNCHANGED',
                      'customer_data':'NONE', 'applications':'NOT INSTALLED',
                      'zero_cost_target':'ALWAYS FREE SIZED; not a hard billing cap'},indent=2))
    if not args.apply:
        print('\nREAD-ONLY preflight passed. Run with --apply to provision after checking costs.')
        return 0
    ensure(sys.stdin.isatty(), 'Provisioning requires an interactive Oracle Cloud Shell.')
    print('\nThis creates 1 Arm64 A1 instance, 50 GB boot volume and 1 network.')
    print('There will be no inbound firewall rules or running RETALLY software.')
    print('If your tenancy has billable upgrades or unrelated usage, OCI may still bill it.')
    phrase = input('Type CREATE RETALLY ALWAYS FREE to proceed: ').strip()
    ensure(phrase == 'CREATE RETALLY ALWAYS FREE', 'Confirmation not received; nothing created.')
    key = generate_keypair()
    state = {'schema':1, 'created_utc':datetime.now(timezone.utc).isoformat(),
             'tenancy_id':tenancy, 'home_region':region, 'public_key_path':str(key),
             'key_private_path':str(PRIVATE_KEY), 'no_customer_data':True,
             'no_open_ingress':True, 'release_status':'HOLD', 'phase':'preparing_network'}
    try:
        make_network(tenancy,region,state)
        launch_vm(inventory,state,key)
    except Exception:
        if PARTIAL.exists():
            print(f'Partial resources recorded at {PARTIAL}. Inspect before any retry.',file=sys.stderr)
        raise
    ensure(PARTIAL.exists(), 'Expected durable provisioning receipt missing.')
    RECEIPT.write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    os.chmod(RECEIPT,0o600)
    PARTIAL.unlink()
    print('\nOCI Always Free-sized instance created and verified. NO workbench deployed.')
    print(f'Instance OCID: {state["instance_id"]}')
    print(f'Receipt: {RECEIPT}')
    print('Inbound: DENY ALL; public website unchanged; no real customer files.')
    print('Next: independent PR reviews, staged synthetic install, Cloudflare Access, private backups.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Stop, ValueError) as exc:
        print(f'STOP (no paid fallback): {exc}',file=sys.stderr)
        sys.exit(2)
