import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import proof_driver as driver


def archive_at(path, entries):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w') as tar:
        for name, body, kind in entries:
            member = tarfile.TarInfo(name); member.type = kind
            if kind == tarfile.LNKTYPE:
                member.linkname = body
                tar.addfile(member)
            else:
                member.size = len(body); tar.addfile(member, io.BytesIO(body))
    result = subprocess.run(['zstd', '-q', '-c'], input=data.getvalue(), capture_output=True, check=True)
    path.write_bytes(result.stdout)


class ArchiveInputsTests(unittest.TestCase):
    def test_post_test_hash_binds_build_library_not_stripped_package_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            built = root / 'build/libdatrie-1.dll'
            packaged = root / 'pkg/libdatrie-1.dll'
            built.parent.mkdir(); packaged.parent.mkdir()
            built.write_bytes(b'unstripped build library with linker symbols')
            packaged.write_bytes(b'stripped package library')
            retained = root / 'library-unchanged-by-tests.sha256'
            retained.write_bytes(hashlib.sha256(built.read_bytes()).hexdigest().encode('ascii') + b'\n')

            record = driver.verify_post_test_library(built, retained)

            self.assertEqual(record, driver.file_record(built))
            self.assertNotEqual(record, driver.file_record(packaged))
            retained.write_bytes(hashlib.sha256(packaged.read_bytes()).hexdigest().encode('ascii') + b'\n')
            with self.assertRaisesRegex(ValueError, 'built library'):
                driver.verify_post_test_library(built, retained)

    def test_failed_upstream_test_logs_are_preserved_individually_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            tests = root / 'build/tests'
            evidence = root / 'evidence'
            tests.mkdir(parents=True)
            evidence.mkdir()
            expected = ['test-suite.log']
            for name in driver.UPSTREAM_TESTS:
                expected.extend((name + '.log', name + '.trs'))
            for name in expected:
                (tests / name).write_text('exact ' + name, encoding='utf-8')

            result = driver.preserve_failed_test_logs(
                root / 'build', evidence, 'original'
            )

            self.assertEqual(result['files'], expected)
            for name in expected:
                self.assertEqual(
                    (evidence / ('original-' + name + '.txt')).read_text(),
                    'exact ' + name,
                )
            with self.assertRaises(FileExistsError):
                driver.preserve_failed_test_logs(root / 'build', evidence, 'original')

    def test_actual_archive_bytes_bind_regular_and_hardlinked_tool_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); archive = root / 'tools.pkg.tar.zst'
            archive_at(archive, [('clang64/bin/clang.exe', b'compiler', tarfile.REGTYPE),
                                 ('clang64/bin/cc.exe', 'clang64/bin/clang.exe', tarfile.LNKTYPE)])
            result = driver.archive_hashes(archive)
            expected = {'bytes': 8, 'sha256': hashlib.sha256(b'compiler').hexdigest()}
            self.assertEqual(result['clang64/bin/clang.exe'], expected)
            self.assertEqual(result['clang64/bin/cc.exe'], expected)

    def test_unknown_hardlink_target_and_duplicate_members_rejected(self):
        for entries in [
            [('clang64/bin/cc.exe', '../../outside', tarfile.LNKTYPE)],
            [('clang64/bin/a', b'a', tarfile.REGTYPE), ('clang64/bin/a', b'b', tarfile.REGTYPE)],
        ]:
            with tempfile.TemporaryDirectory() as tmp:
                archive = Path(tmp) / 'bad.zst'; archive_at(archive, entries)
                with self.assertRaises(ValueError): driver.archive_hashes(archive)

    def test_changed_or_absent_installed_tool_not_accepted_as_archive_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); path = root / 'clang64/bin/clang.exe'
            before = {'msysRoot': str(root), 'tools': {'clang': {'path': str(path), 'bytes': 8, 'sha256': hashlib.sha256(b'compiler').hexdigest()}},
                      'configs': {'etc/makepkg.conf': {'bytes': 4, 'sha256': hashlib.sha256(b'conf').hexdigest(), 'content': 'conf'}}}
            archives = {'clang64/bin/clang.exe': {'bytes': 8, 'sha256': hashlib.sha256(b'compiler').hexdigest()},
                        'etc/makepkg.conf': {'bytes': 4, 'sha256': hashlib.sha256(b'conf').hexdigest()}}
            self.assertTrue(driver.validate_archived_tools(before, archives))
            archives['clang64/bin/clang.exe']['sha256'] = '0'*64
            with self.assertRaises(ValueError): driver.validate_archived_tools(before, archives)
            del archives['clang64/bin/clang.exe']
            with self.assertRaises(ValueError): driver.validate_archived_tools(before, archives)


if __name__ == '__main__': unittest.main()
