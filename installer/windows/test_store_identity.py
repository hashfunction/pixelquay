# Copyright 2026 Trieflow LLC. MIT. Execute the existing package boundaries in both modes.
import json
import unittest
import xml.etree.ElementTree as ET

import msix_qualification as msix
import test_msix_qualification as fixtures


class StoreIdentityTests(fixtures.BuildFlowTests):

    def test_assigned_identity_is_explicit_and_default_is_disposable(self):
        self.assertEqual(msix.QUALIFICATION_IDENTITY, msix.identity_for_mode('qualification'))
        identity = msix.identity_for_mode('store')
        self.assertEqual(identity['packageName'], '1659hashfunction.PixelQuay')
        self.assertEqual(identity['publisher'], 'CN=B6A2631A-FD32-45CC-AE12-82466975F528')
        for key in ('version', 'architecture', 'applicationId', 'executable', 'minVersion'):
            self.assertEqual(identity[key], msix.QUALIFICATION_IDENTITY[key])
        with self.assertRaises(ValueError):
            msix.identity_for_mode('Store')
        for mode in ('qualification', 'store'):
            manifest = msix.create_manifest(mode)
            self.assertEqual(msix.identity_for_mode(mode), msix.validate_manifest(manifest, mode))
            root = ET.fromstring(manifest)
            publisher = root.find('{'+msix.APPX_NS+'}Properties/{'+msix.APPX_NS+'}PublisherDisplayName')
            self.assertEqual(publisher.text, 'hashfunction' if mode == 'store' else 'Trieflow LLC')
            with self.assertRaises(ValueError):
                msix.validate_manifest(manifest, 'store' if mode == 'qualification' else 'qualification')

    def test_store_runs_actual_stage_sdk_zip_unpack_and_record_rederivation(self):
        msix.build_qualification(self.release, self.artwork, self.commit, self.makeappx,
                                 '10.0.26100.0', self.output, self.fake_sdk, 'store')
        record_path = self.output / 'package-record.json'
        record = json.loads(record_path.read_text())
        self.assertFalse(record['qualificationIdentityOnly'])
        self.assertEqual('store', record['identityMode'])
        package = self.output / 'TintFable_1.0.1.0_x64.msix'
        self.assertEqual(record['containerVerification'], msix.verify_msix(package, record['payload'], 'store'))
        msix.verify_record_inputs(package, record_path, self.release, self.artwork, self.commit, 'store')
        with self.assertRaises(ValueError):
            msix.verify_msix(package, record['payload'])
        for mutation in ('stale-source', 'mode', 'payload', 'unpack', 'manifest-identity'):
            altered = json.loads(json.dumps(record))
            if mutation == 'stale-source': altered['sourceCommit'] = '0' * 40
            elif mutation == 'mode': altered['identityMode'] = 'qualification'
            elif mutation == 'payload': altered['payload']['bin/TintFable.exe']['sha256'] = '0' * 64
            elif mutation == 'unpack': altered['unpackedVerification']['verifiedPayloadFiles'] -= 1
            elif mutation == 'manifest-identity': altered['identity']['applicationId'] = 'TintFable'
            record_path.write_text(json.dumps(altered))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                msix.verify_record_inputs(package, record_path, self.release, self.artwork, self.commit, 'store')
        record_path.write_text(json.dumps(record))
        (self.release / 'bin/TintFable.exe').write_bytes(b'changed actual release')
        with self.assertRaises(ValueError):
            msix.verify_record_inputs(package, record_path, self.release, self.artwork, self.commit, 'store')


if __name__ == '__main__':
    unittest.main()
