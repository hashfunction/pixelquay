"""Reject incomplete native proofs, missing exports, and changed environment."""
import copy
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import library_receipt as receipt

EXPECTED_TESTS = ['test_walk', 'test_iterator', 'test_store-retrieve', 'test_file', 'test_serialization', 'test_nonalpha', 'test_null_trie', 'test_term_state', 'test_byte_alpha', 'test_byte_list']


def example_pe(machine=0x8664):
    # A hand-built PE32+ fixture with one .rdata section, two named exports,
    # and one import descriptor. Not produced by the parser under test.
    data = bytearray(1536)
    data[:2] = b'MZ'; struct.pack_into('<I', data, 0x3c, 0x80)
    data[0x80:0x84] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', data, 0x84, machine, 1, 0, 0, 0, 240, 0x2022)
    struct.pack_into('<H', data, 0x98, 0x20b)
    struct.pack_into('<I', data, 0x98 + 60, 512)
    struct.pack_into('<I', data, 0x98 + 108, 16)
    struct.pack_into('<IIII', data, 0x98 + 112, 0x1000, 128, 0x1080, 40)
    section = 0x98 + 240
    data[section:section+8] = b'.rdata\0\0'
    struct.pack_into('<IIII', data, section+8, 1024, 0x1000, 1024, 512)
    struct.pack_into('<IIIII', data, 512+20, 2, 2, 0x1040, 0x1048, 0x1050)
    struct.pack_into('<II', data, 512+0x48, 0x1120, 0x1130)
    data[512+0x120:512+0x129] = b'trie_new\0'
    data[512+0x130:512+0x13a] = b'trie_free\0'
    struct.pack_into('<IIIII', data, 512+0x80, 0, 0, 0, 0x1140, 0)
    data[512+0x140:512+0x14d] = b'KERNEL32.dll\0'
    return bytes(data)


def proof_pair():
    original = {'sha256': '1'*64, 'machine': 'x64', 'exports': ['trie_free', 'trie_new'], 'imports': ['kernel32.dll'],
                'upstreamTests': {name: 'PASS' for name in EXPECTED_TESTS},
                'probe': {'mode': 'original', 'apiChecks': 21, 'libraryPathMatched': True, 'markerPresent': False},
                'copyingSha256': 'a9bdde5616ecdd1e980b44f360600ee8783b1f99b8cc83a2beb163a0a390e861'}
    modified = copy.deepcopy(original)
    modified.update(sha256='2'*64, exports=['pixelquay_rebuild_marker', 'trie_free', 'trie_new'])
    modified['probe'].update(mode='modified', markerPresent=True)
    return original, modified


class ReceiptTests(unittest.TestCase):
    def test_actual_pe_tables_are_read(self):
        value = receipt.pe_inventory(example_pe())
        self.assertEqual(value, {'machine': 'x64', 'exports': ['trie_free', 'trie_new'], 'imports': ['kernel32.dll']})

    def test_wrong_architecture_bad_ranges_and_truncation_rejected(self):
        bad_rva = bytearray(example_pe()); struct.pack_into('<I', bad_rva, 512+0x48, 0x7fffffff)
        huge_count = bytearray(example_pe()); struct.pack_into('<I', huge_count, 512+24, 999999)
        for data in [b'', example_pe()[:300], example_pe(0x14c), bytes(bad_rva), bytes(huge_count)]:
            with self.subTest(length=len(data)), self.assertRaises(ValueError): receipt.pe_inventory(data)

    def test_pair_requires_all_ten_tests_real_probe_and_only_one_added_export(self):
        original, modified = proof_pair()
        self.assertTrue(receipt.validate_pair(original, modified, ['trie_free', 'trie_new']))
        changes = [
            ('exports', ['trie_new', 'pixelquay_rebuild_marker']),
            ('exports', ['trie_new', 'trie_free', 'pixelquay_rebuild_marker', 'extra']),
            ('imports', ['kernel32.dll', 'unrecorded.dll']),
            ('machine', 'x86'), ('sha256', '1'*64),
            ('upstreamTests', {'test_walk': 'PASS'}),
            ('probe', {'mode': 'modified', 'apiChecks': 0, 'libraryPathMatched': True, 'markerPresent': True}),
            ('probe', {'mode': 'modified', 'apiChecks': 21, 'libraryPathMatched': False, 'markerPresent': True}),
            ('copyingSha256', '0'*64),
        ]
        for field, value in changes:
            bad = copy.deepcopy(modified); bad[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                receipt.validate_pair(original, bad, ['trie_free', 'trie_new'])
        bad = copy.deepcopy(original); bad['upstreamTests']['test_walk'] = 'SKIP'
        with self.assertRaises(ValueError): receipt.validate_pair(bad, modified, ['trie_free', 'trie_new'])

    def test_read_automake_results_rejects_skip_and_missing_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in EXPECTED_TESTS:
                (root / (name+'.trs')).write_text(':test-result: PASS\n:global-test-result: PASS\n')
            self.assertEqual(len(receipt.read_upstream_tests(root)), 10)
            (root / 'test_walk.trs').write_text(':test-result: SKIP\n:global-test-result: SKIP\n')
            with self.assertRaises(ValueError): receipt.read_upstream_tests(root)

    def test_environment_drift_and_wrong_selected_versions_rejected(self):
        value = {'packages': {'mingw-w64-clang-x86_64-clang': '22.1.8-2', 'mingw-w64-clang-x86_64-libiconv': '1.19-1',
                 'mingw-w64-clang-x86_64-autotools': '2026.08.04-1', 'mingw-w64-clang-x86_64-doxygen': '1.18.0-3'},
                 'tools': {'clang': {'sha256': '1'*64}}, 'configs': {'makepkg.conf': {'sha256': '2'*64}}}
        self.assertTrue(receipt.validate_environment(value, value))
        for field in ('packages', 'tools', 'configs'):
            changed = copy.deepcopy(value); changed[field] = {}
            with self.subTest(field=field), self.assertRaises(ValueError): receipt.validate_environment(value, changed)
        changed = copy.deepcopy(value); changed['configuredEnvironment'] = {'CFLAGS': '-ffast-math'}
        with self.assertRaises(ValueError): receipt.validate_environment(value, changed)
        value['packages']['mingw-w64-clang-x86_64-clang'] = '21.1.5-1'
        with self.assertRaises(ValueError): receipt.validate_environment(value, value)


if __name__ == '__main__': unittest.main()
