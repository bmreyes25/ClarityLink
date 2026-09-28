import json
from pathlib import Path
import unittest
from catalog_services import catalog, parse_activity, parse_audio, parse_display, manifest_facts, OWNER_PACKAGES


class ServiceEvidenceTests(unittest.TestCase):
    def test_bindings_require_service_block_and_connection_arrow(self):
        cp = OWNER_PACKAGES['CarPlayApService']
        nav = OWNER_PACKAGES['NavigationApService']
        text = f'''  * ServiceRecord{{abc {nav}/.NavigationApService}}
    app=ProcessRecord{{abc 123:{nav}/1000}}
    Connections:
      act=synthetic -> 123:{cp}/1000
  * ServiceRecord{{abc other.package/.Other}}
      act=synthetic -> 123:{cp}/1000
'''
        facts = parse_activity(text)
        self.assertTrue(facts['servicesPresent']['NavigationApService'])
        self.assertEqual(facts['bindings'], [{'client': 'CarPlayApService', 'service': 'NavigationApService'}])
        self.assertNotIn('abc', json.dumps(facts))

    def test_missing_unrecognized_snapshots_are_unknown(self):
        for parser in (parse_activity, parse_audio, parse_display):
            self.assertEqual(parser(None)['availability'], 'unavailable')
            self.assertEqual(parser('permission denied')['availability'], 'unrecognized')

    def test_audio_focus_not_media_player_package(self):
        av = OWNER_PACKAGES['AvApService']
        facts = parse_audio(f'Audio Focus stack entries:\n source:synthetic -- pack: {av} -- stream: 12\nRemote Control stack entries:\npack: other.package')
        self.assertEqual(facts['focusOwners'], ['AvApService'])
        self.assertEqual(facts['focusStreams'], [12])
        self.assertEqual(parse_audio(f'Remote Control stack entries:\npack: {av}')['focusOwners'], [])

    def test_display_dimensions_are_allowlisted(self):
        facts = parse_display('Display Devices:\nDisplayDeviceInfo{"synthetic": 800 x 480, modeId 1}\nDisplayDeviceInfo{"private": 1024 x 600}')
        self.assertEqual(facts['dimensionsObserved'], [[800, 480]])
        self.assertNotIn('private', json.dumps(facts))

    def test_manifest_outputs_only_known_services(self):
        xml = '<manifest package="com.mitsubishielectric.ada.appservice.navigation" xmlns:android="http://schemas.android.com/apk/res/android"><application><service android:name=".NavigationApService"/><service android:name="private.RouteService"/></application></manifest>'
        self.assertEqual(manifest_facts(xml), ['NavigationApService'])

    def test_original_dataset_rejected(self):
        with self.assertRaises(ValueError):
            catalog(Path('CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL'), Path('.'))

    def test_saved_catalog_provenance_and_privacy(self):
        data = json.loads(Path(__file__).with_name('service-evidence.json').read_text())
        self.assertEqual(data['schemaVersion'], 1)
        self.assertEqual(len(data['runtimeSnapshots']), 8)
        self.assertEqual(len(data['firmwareOwnership']), 4)
        for row in data['firmwareOwnership']:
            self.assertRegex(row['apkSha256'], '^[0-9a-f]{64}$')
            self.assertTrue(row['originalManifestMatchesCurrentApk'])
            self.assertIn(row['ownerComponent'], row['declaredAllowlistedServices'])
            self.assertRegex(row['manifestSha256'], '^[0-9a-f]{64}$')
            self.assertRegex(row['decodedSha256'], '^[0-9a-f]{64}$')
        for snapshot in data['runtimeSnapshots']:
            self.assertIn('activity.stdout.txt', snapshot['sources'])
            self.assertIn('services.stdout.txt', snapshot['sources'])
            self.assertEqual(set(snapshot['activity']['servicesPresent']), set(OWNER_PACKAGES))
            self.assertTrue(all(set(edge) == {'client', 'service'} for edge in snapshot['activity']['bindings']))
            self.assertEqual(snapshot['audio']['focusOwners'], ['AvApService'])
            self.assertEqual(snapshot['audio']['focusStreams'], [12])
            self.assertEqual(snapshot['display']['dimensionsObserved'], [[800, 480]])
            for target in ('NavigationApService', 'ExternalDisplayApService'):
                self.assertIn({'client': 'CarPlayApService', 'service': target}, snapshot['activity']['bindings'])
