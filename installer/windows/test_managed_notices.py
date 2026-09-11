"""Exact package/notice binding tests. Copyright 2026 Trieflow LLC; MIT."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from managed_notices import include_notice


class ManagedNoticeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        self.destination = self.root / 'licenses'
        self.data = b'Copyright Test Author\nPermission granted for this test fixture.\n'
        (self.source / 'example.txt').write_bytes(self.data)
        self.entry = {'package': 'Example/1.2.3', 'packageSha256': 'a' * 64,
            'noticeFile': 'example.txt', 'noticeSha256': hashlib.sha256(self.data).hexdigest(),
            'noticeSourceUrl': 'https://example.test/license'}
        self.record = {'package': 'Example/1.2.3', 'packageSha256': 'a' * 64}

    def call(self):
        (self.source / 'package-bindings.json').write_text(json.dumps({'schemaVersion': 1, 'entries': [self.entry]}))
        return include_notice(self.record, self.source, self.destination)

    def test_exact_package_copies_exact_notice_and_provenance(self):
        result = self.call()
        self.assertEqual(self.data, (self.destination / result['file']).read_bytes())
        self.assertEqual(self.entry['noticeSha256'], result['sha256'])
        self.assertEqual(self.entry['noticeSourceUrl'], result['sourceUrl'])
        self.assertEqual(result, self.call())

    def test_new_version_is_unmatched_and_does_not_receive_old_notice(self):
        self.record['package'] = 'Example/2.0.0'
        self.assertIsNone(self.call())
        self.assertFalse(self.destination.exists())

    def test_changed_package_bytes_fail_without_writing(self):
        self.record['packageSha256'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'package hash'):
            self.call()
        self.assertFalse(self.destination.exists())

    def test_changed_notice_bytes_fail_without_writing(self):
        (self.source / 'example.txt').write_bytes(b'incorrect notice')
        with self.assertRaisesRegex(ValueError, 'notice hash'):
            self.call()
        self.assertFalse(self.destination.exists())

    def test_path_escape_cannot_read_or_publish_unrelated_file(self):
        self.entry['noticeFile'] = '../private.txt'
        (self.root / 'private.txt').write_bytes(self.data)
        with self.assertRaisesRegex(ValueError, 'notice filename'):
            self.call()
        self.assertFalse(self.destination.exists())

    def test_existing_conflicting_destination_is_preserved(self):
        self.call()
        output = self.destination / 'managed-source-notices/example.txt'
        output.write_bytes(b'prior retained data')
        with self.assertRaisesRegex(ValueError, 'destination'):
            self.call()
        self.assertEqual(b'prior retained data', output.read_bytes())


if __name__ == '__main__':
    unittest.main()
