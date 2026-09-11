"""Real-archive tests: unsafe inputs must never write outside/new owned output."""
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import libdatrie_source as source

ARCHIVE = ROOT / 'inputs/mingw-w64-libdatrie-0.2.14-1.src.tar.zst'


def tar_bytes(rows):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        for name, data, kind in rows:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(data) if kind == tarfile.REGTYPE else 0
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = '../../outside'
            archive.addfile(member, io.BytesIO(data))
    return stream.getvalue()


class SourceTests(unittest.TestCase):
    def test_real_patch_notices_every_modified_file_and_preserves_copying(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'source'
            source.materialize(ARCHIVE, output)
            tree = output / 'upstream/libdatrie-0.2.14'
            before = {p.relative_to(tree).as_posix(): p.read_bytes() for p in tree.rglob('*') if p.is_file()}
            subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', str(ROOT / '001-local-marker.patch')], cwd=tree, check=True, capture_output=True)
            after = {p.relative_to(tree).as_posix(): p.read_bytes() for p in tree.rglob('*') if p.is_file()}
            changed = {name for name in before if before[name] != after[name]}
            self.assertEqual(changed, {'datrie/trie.c', 'datrie/trie.h', 'datrie/libdatrie.def', 'datrie/libdatrie.map'})
            for name in changed:
                with self.subTest(name=name):
                    self.assertIn(b'Local modification, Trieflow LLC, 2026-09-11', after[name])
            self.assertEqual(before['COPYING'], after['COPYING'])
            self.assertIn(hashlib.sha256((ROOT / '001-local-marker.patch').read_bytes()).hexdigest(), (ROOT / 'recipes/modified/PKGBUILD').read_text())

    def test_windows_test_data_patch_uses_32_bit_alpha_literals_only_in_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'source'
            source.materialize(ARCHIVE, output)
            tree = output / 'upstream/libdatrie-0.2.14'
            before = {
                path.relative_to(tree).as_posix(): path.read_bytes()
                for path in tree.rglob('*')
                if path.is_file()
            }
            subprocess.run(
                [
                    'patch',
                    '--batch',
                    '--forward',
                    '--fuzz=0',
                    '-p1',
                    '-i',
                    str(ROOT / '002-windows-alpha-test-data.patch'),
                ],
                cwd=tree,
                check=True,
                capture_output=True,
            )
            after = {
                path.relative_to(tree).as_posix(): path.read_bytes()
                for path in tree.rglob('*')
                if path.is_file()
            }
            changed = {name for name in before if before[name] != after[name]}
            self.assertEqual(
                changed,
                {
                    'tests/test_nonalpha.c',
                    'tests/test_term_state.c',
                    'tests/test_walk.c',
                    'tests/utils.c',
                },
            )
            adapted = b''.join(after[name] for name in sorted(changed))
            self.assertEqual(adapted.count(b'(AlphaChar *)U"'), 49)
            self.assertNotIn(b'(AlphaChar *)L"', adapted)
            for name in changed:
                self.assertIn(b'Test-data portability modification, Trieflow LLC, 2026-09-11', after[name])
            self.assertEqual(before['COPYING'], after['COPYING'])
            patch_hash = hashlib.sha256(
                (ROOT / '002-windows-alpha-test-data.patch').read_bytes()
            ).hexdigest()
            for variant in ('original', 'modified'):
                recipe = (ROOT / 'recipes' / variant / 'PKGBUILD').read_text()
                self.assertIn('002-windows-alpha-test-data.patch', recipe)
                self.assertIn(patch_hash, recipe)

    def test_actual_source_materialized_with_exact_notices_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp).resolve() / 'source'
            receipt = source.materialize(ARCHIVE, output)
            self.assertIn('archive', receipt)
            self.assertEqual(receipt['archive']['bytes'], 327473)
            self.assertEqual(receipt['archive']['sha256'], 'da58ca439051a8cfb1d7f15cdd82af104e1ea1eeefdb090e608d2305a747df7d')
            notice = output / 'upstream/libdatrie-0.2.14/COPYING'
            self.assertEqual(hashlib.sha256(notice.read_bytes()).hexdigest(), 'a9bdde5616ecdd1e980b44f360600ee8783b1f99b8cc83a2beb163a0a390e861')
            self.assertTrue((output / 'recipe/PKGBUILD').is_file())
            self.assertTrue((output / 'upstream/libdatrie-0.2.14/datrie/trie.c').is_file())
            self.assertEqual(json.loads((output / 'source-receipt.json').read_text()), receipt)
            self.assertFalse(receipt['executedRecipe'])

    def test_wrong_archive_digest_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            changed = root / 'changed.zst'
            data = bytearray(ARCHIVE.read_bytes()); data[-1] ^= 1
            changed.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'hash'):
                source.materialize(changed, root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_existing_destination_or_link_preserved(self):
        for kind in ('directory', 'file', 'link'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp).resolve(); target = root / 'out'; outside = root / 'outside'
                outside.mkdir(); (outside / 'sentinel').write_bytes(b'preserve')
                if kind == 'directory': target.mkdir()
                elif kind == 'file': target.write_bytes(b'previous')
                else: target.symlink_to(outside, target_is_directory=True)
                with self.assertRaises((ValueError, FileExistsError)):
                    source.materialize(ARCHIVE, target)
                self.assertEqual((outside / 'sentinel').read_bytes(), b'preserve')
                if kind == 'file': self.assertEqual(target.read_bytes(), b'previous')
                if kind == 'directory': self.assertEqual(list(target.iterdir()), [])

    def test_linked_ancestor_and_archive_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); outside = root / 'outside'; outside.mkdir()
            link = root / 'link'; link.symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'link|reparse'):
                source.materialize(ARCHIVE, link / 'out')
            archive_link = root / 'source.zst'; archive_link.symlink_to(ARCHIVE)
            with self.assertRaisesRegex(ValueError, 'link|reparse'):
                source.materialize(archive_link, root / 'out')
            self.assertEqual(list(outside.iterdir()), [])

    def test_tar_rejects_traversal_aliases_duplicates_links_and_devices(self):
        valid = ('libdatrie-0.2.14/a', b'a', tarfile.REGTYPE)
        invalid = [
            [('libdatrie-0.2.14/../outside', b'x', tarfile.REGTYPE)],
            [('/libdatrie-0.2.14/a', b'x', tarfile.REGTYPE)],
            [('libdatrie-0.2.14/a\\b', b'x', tarfile.REGTYPE)],
            [('libdatrie-0.2.14/a:', b'x', tarfile.REGTYPE)],
            [('libdatrie-0.2.14/NUL', b'x', tarfile.REGTYPE)],
            [valid, valid],
            [valid, ('libdatrie-0.2.14/A', b'b', tarfile.REGTYPE)],
        ]
        invalid.extend([[('libdatrie-0.2.14/a', b'', kind)] for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.FIFOTYPE)])
        for rows in invalid:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                source.read_tar(tar_bytes(rows), 'libdatrie-0.2.14')

    def test_tar_file_directory_collision_and_size_limit(self):
        cases = [
            [('libdatrie-0.2.14/a', b'file', tarfile.REGTYPE), ('libdatrie-0.2.14/a/b', b'child', tarfile.REGTYPE)],
            [('libdatrie-0.2.14/a', b'12345', tarfile.REGTYPE)],
        ]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                source.read_tar(tar_bytes(rows), 'libdatrie-0.2.14', max_bytes=4)

    def test_outer_member_set_is_exact(self):
        with self.assertRaisesRegex(ValueError, 'member|set'):
            source.verify_recipe_members({'mingw-w64-libdatrie/PKGBUILD': b'only one'})

    def test_output_link_is_rejected_before_creating_descendant_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); outside = root / 'outside'; outside.mkdir()
            link = root / 'linked'; link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                source.write_new(link / 'must-not-create' / 'file', b'no')
            self.assertEqual(list(outside.iterdir()), [])

    def test_file_directory_collision_is_rejected_without_hitting_size_bound(self):
        rows = [('libdatrie-0.2.14/a', b'file', tarfile.REGTYPE), ('libdatrie-0.2.14/a/b', b'child', tarfile.REGTYPE)]
        with self.assertRaisesRegex(ValueError, 'collision'):
            source.read_tar(tar_bytes(rows), 'libdatrie-0.2.14')


if __name__ == '__main__':
    unittest.main()
