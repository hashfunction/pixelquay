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
