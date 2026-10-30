"""Recover only orphaned lab host veths identified by an existing collection.

Used for pre-fix teardown failures that removed the ownership marker before the
namespace's final process exited. Never remove a bridge, a named namespace,
an attached link, a non-veth interface, or a link bearing a foreign owner alias.
"""
import json
from pathlib import Path
import subprocess


def recover_orphans(kit, collection):
    kit, collection = Path(kit).resolve(), Path(collection).resolve()
    root = collection.parent
    if (not root.is_relative_to(kit / 'data') or root.parent.name not in
            ('v2_development', 'v2_holdout','v3_holdout') or root.parent.parent != kit / 'data'
            or collection.name != 'COLLECTION.json'):
        raise ValueError('Recovery requires an existing v2 collection in this kit')
    from lab.collect_v2 import plan
    record = json.loads(collection.read_text())
    profile=record.get('protocol_profile','v2')
    if (root.parent.name=='v3_holdout') != (profile=='hybrid-v3'):
        raise ValueError('Collection profile/root mismatch')
    expected_root, commands = plan(record['phase'], root.name,profile)
    if (root != kit / 'data' / expected_root or record.get('format') != 1
            or record.get('plan') != commands or record.get('capture_ids') != [r['capture_id'] for r in commands]
            or record.get('reset_owned_lab_each_session') is not True):
        raise ValueError('Collection does not establish ownership of this lab')
    if (kit / 'build/lab.created').exists():
        raise ValueError('Ownership marker exists: use the normal owned-lab teardown')
    names = set(subprocess.check_output(['ip', 'netns', 'list'], text=True).splitlines())
    if any(line.split()[0] in ('p2broker', 'p2sensor', 'p2source') for line in names if line.split()):
        raise ValueError('Named lab namespaces remain; refusing orphan-only recovery')
    links = json.loads(subprocess.check_output(['ip', '-j', '-d', 'link', 'show'], text=True))
    if any(row['ifname'] == 'p2br' for row in links):
        raise ValueError('Lab bridge remains without marker; inspect before recovery')
    owned_names = {'p2brokerh', 'p2sensorh', 'p2sourceh'}
    candidates = [row for row in links if row['ifname'] in owned_names]
    # Validate every candidate before the first mutation.
    for row in candidates:
        if (row.get('linkinfo', {}).get('info_kind') != 'veth' or row.get('master')
                or row.get('ifalias', '') not in ('', f'ai_part2:{kit}')):
            raise ValueError('Link is not an unattached lab veth: ' + row['ifname'])
    removed = []
    for row in candidates:
        try:
            subprocess.run(['ip', 'link', 'del', row['ifname']], check=True)
        except subprocess.CalledProcessError:
            # The final old namespace process may exit between inspection and
            # deletion. Accept only a confirmed disappearance, not other errors.
            current = json.loads(subprocess.check_output(['ip', '-j', '-d', 'link', 'show'], text=True))
            if any(link['ifname'] == row['ifname'] for link in current):
                raise
        removed.append(row['ifname'])
    return removed
