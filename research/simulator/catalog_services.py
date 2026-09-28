#!/usr/bin/env python3
"""Offline allowlisted service evidence; never emits firmware or runtime contents."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from catalog_firmware import STATES

OWNER_PACKAGES = {
    'NavigationApService': 'com.mitsubishielectric.ada.appservice.navigation',
    'CarPlayApService': 'com.mitsubishielectric.ada.appservice.carplayapservice',
    'ExternalDisplayApService': 'com.mitsubishielectric.ada.appservice.externaldisplay',
    'ExternalDisplayOutService': 'com.mitsubishielectric.ada.app.externaldisplay',
    'AvApService': 'com.mitsubishielectric.ada.appservice.avapservice',
}
APK_NAMES = {'Navigation': 'NavigationApService', 'CarPlayService': 'CarPlayApService',
             'ExternalDisplayApService': 'ExternalDisplayApService',
             'ExternalDisplayOutService': 'ExternalDisplayOutService'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def availability(text, recognized):
    return 'unavailable' if text is None else 'available' if recognized else 'unrecognized'


def parse_activity(text):
    value = text or ''
    present = {name: False for name in OWNER_PACKAGES}
    edges = set()
    service = None
    in_connections = False
    for line in value.splitlines():
        if re.match(r'^\s*\* ServiceRecord\{', line):
            in_connections = False
            service = next((name for name, package in OWNER_PACKAGES.items()
                            if re.search(re.escape(package) + r'/\.' + name + r'[}\s]', line)), None)
            if service:
                present[service] = True
        elif service and line.strip() == 'Connections:':
            in_connections = True
        elif service and in_connections and '->' in line and len(line) - len(line.lstrip()) >= 6:
            client_part = line.split('->', 1)[1]
            for name, package in OWNER_PACKAGES.items():
                if re.search(r':' + re.escape(package) + r'(?:/|:)', client_part):
                    edges.add((name, service))
    return {'availability': availability(text, '* ServiceRecord{' in value),
            'servicesPresent': present,
            'bindings': [{'client': client, 'service': service} for client, service in sorted(edges)],
            'evidence': 'observed dumpsys activity service records and connection clients; binding is not a decoded route'}


def parse_audio(text):
    value = text or ''
    owners, streams = set(), set()
    focus = False
    for line in value.splitlines():
        if 'Audio Focus stack entries' in line:
            focus = True
        elif re.match(r'^\S', line) and line.strip():
            focus = False
        if focus and 'pack:' in line:
            for name, package in OWNER_PACKAGES.items():
                if re.search(r'pack:\s*' + re.escape(package) + r'(?:\s|$)', line):
                    owners.add(name)
                    stream = re.search(r'\bstream:\s*(\d+)\b', line)
                    if stream and int(stream[1]) in range(16):
                        streams.add(int(stream[1]))
    return {'availability': availability(text, 'Audio Focus stack entries' in value),
            'focusOwners': sorted(owners), 'focusStreams': sorted(streams),
            'evidence': 'observed focus snapshot; no per-event voice or sample continuity proved'}


def parse_display(text):
    value = text or ''
    dimensions = [[800, 480]] if re.search(r'DisplayDeviceInfo\{[^\n]*\b800\s*x\s*480\b', value) else []
    return {'availability': availability(text, 'DisplayDeviceInfo{' in value),
            'dimensionsObserved': dimensions,
            'physicalNavigationBounds': 'unknown; logical display dimensions do not calibrate physical Navigation rectangle',
            'evidence': 'observed display-device dimensions; no pixel producer ownership asserted'}


def manifest_facts(xml):
    root = ET.fromstring(xml)
    declared = set()
    for element in root.iter('service'):
        value = element.attrib.get('{http://schemas.android.com/apk/res/android}name', '')
        package = root.attrib.get('package', '')
        qualified = package + value if value.startswith('.') else package + '.' + value if '.' not in value else value
        for name, owner in OWNER_PACKAGES.items():
            if qualified == owner + '.' + name:
                declared.add(name)
    return sorted(declared)


def catalog(root, repo):
    if root.name != 'CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING':
        raise ValueError('Use only the complete working acquisition')
    firmware = []
    archive_path = root / 'filesystems/system-vendor.tar'
    with tarfile.open(archive_path) as archive:
        for apk_name, component in APK_NAMES.items():
            member = f'system/vendor/app/{apk_name}.apk'
            item = archive.getmember(member)
            if not item.isfile():
                raise ValueError('Expected regular APK member')
            with archive.extractfile(item) as stream:
                apk = stream.read()
            with zipfile.ZipFile(io.BytesIO(apk)) as package:
                manifest = package.read('AndroidManifest.xml')
            derived = repo / 'research/resources' / apk_name
            original = derived / 'original/AndroidManifest.xml'
            decoded = derived / 'AndroidManifest.xml'
            matches = original.exists() and original.read_bytes() == manifest
            row = {'archive': 'filesystems/system-vendor.tar', 'member': member, 'apkSha256': sha(apk),
                   'manifestSha256': sha(manifest), 'ownerComponent': component,
                   'originalManifestMatchesCurrentApk': matches,
                   'evidence': 'observed APK manifest declaration through previously decoded manifest; current binary manifest matched decoder input'}
            if matches and decoded.exists():
                decoded_bytes = decoded.read_bytes()
                row.update({'decodedSource': f'research/resources/{apk_name}/AndroidManifest.xml',
                            'decodedSha256': sha(decoded_bytes),
                            'declaredAllowlistedServices': manifest_facts(decoded_bytes)})
            else:
                row.update({'declaredAllowlistedServices': [], 'evidence': 'unknown; current manifest did not match existing decoder input'})
            firmware.append(row)
    snapshots = []
    for state in STATES:
        sources, contents = {}, {}
        for name in ('activity', 'services', 'audio', 'display'):
            path = root / 'runtime' / state / f'{name}.stdout.txt'
            data = path.read_bytes() if path.exists() else None
            sources[path.name] = {'source': f'runtime/{state}/{path.name}', 'sha256': sha(data), 'bytes': len(data)} if data is not None else {'availability': 'unavailable'}
            contents[name] = data.decode(errors='replace') if data is not None else None
        snapshots.append({'state': state, 'sources': sources, 'activity': parse_activity(contents['activity']),
                          'audio': parse_audio(contents['audio']), 'display': parse_display(contents['display']),
                          'servicesRegistry': {'availability': availability(contents['services'], bool(contents['services'])),
                                               'evidence': 'service-manager registry hashed separately; not the activity-service connection graph'}})
    return {'schemaVersion': 1, 'source': root.name, 'firmwareOwnership': firmware, 'runtimeSnapshots': snapshots,
            'limitations': ['Allowlisted ownership only; not exhaustive service reverse engineering',
                            'Binding does not establish route metadata delivery or independent video',
                            'No ARM receiver, Android Binder, USB/MFi or vehicle bus execution',
                            'Runtime focus is snapshot evidence, not per-event audio continuity']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('working', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = catalog(args.working, Path(__file__).resolve().parents[2])
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(f"Cataloged {len(result['firmwareOwnership'])} APK owners and {len(result['runtimeSnapshots'])} sanitized runtime snapshots")
