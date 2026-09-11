import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import os
import subprocess
from unittest.mock import patch
import unittest

spec = importlib.util.spec_from_file_location('inventory_native', Path(__file__).with_name('inventory_native.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class NativeInventoryTests(unittest.TestCase):
    def fixture(self, root):
        package = root / 'var/lib/pacman/local/gtk4-1.2-1'
        package.mkdir(parents=True)
        (package / 'desc').write_text('%NAME%\ngtk4\n\n%VERSION%\n1.2-1\n\n%LICENSE%\nLGPL-2.1-or-later\n\n%URL%\nhttps://gtk.org\n')
        (package / 'files').write_text('%FILES%\nclang64/bin/libgtk.dll\nclang64/share/licenses/gtk4/COPYING\n')
        dll = root / 'clang64/bin/libgtk.dll'
        dll.parent.mkdir(parents=True)
        dll.write_bytes(b'actual binary')
        license_file = root / 'clang64/share/licenses/gtk4/COPYING'
        license_file.parent.mkdir(parents=True)
        license_file.write_text('real package license fixture')
        listing = root / 'files.txt'
        listing.write_text(str(dll)+'\n')
        return listing, dll

    def test_inventory_records_actual_hash_version_owner_and_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, dll = self.fixture(root)
            output = root / 'release/native-files.json'
            module.build_inventory(root/'clang64', listing, output)
            data = json.loads(output.read_text())
            row = data['files'][0]
            self.assertEqual(row['sha256'], hashlib.sha256(dll.read_bytes()).hexdigest())
            self.assertEqual(row['packages'][0]['version'], '1.2-1')
            self.assertEqual(row['packages'][0]['licenses'], ['LGPL-2.1-or-later'])
            self.assertTrue((output.parent/'licenses/native/gtk4/clang64/share/licenses/gtk4/COPYING').is_file())

    def test_nested_same_basename_notices_preserve_exact_archive_bytes_and_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, _ = self.fixture(root)
            name = 'mingw-w64-clang-x86_64-gettext-runtime'
            entry = root/'var/lib/pacman/local/gtk4-1.2-1'
            (entry/'desc').write_text('%NAME%\n'+name+'\n\n%VERSION%\n1.0-1\n\n%LICENSE%\nGPL-3.0-or-later\nLGPL-2.1-or-later\n\n%URL%\nhttps://www.gnu.org/software/gettext/\n')
            sources = {
                'clang64/share/licenses/gettext-runtime/COPYING': (495, '7ef2cdfe58e0c0460657b6598b49af29d4e03c1e41cbaf0e1da1eb8ad74b95d0'),
                'clang64/share/licenses/gettext-runtime/libasprintf/COPYING': (65, '03133addae5b99a6148c538300e6d97074453089be1423b741bd081f18e2b298'),
            }
            (entry/'files').write_text('%FILES%\nclang64/bin/libgtk.dll\n'+'\n'.join(sources)+'\n')
            for relative in sources:
                original = Path(__file__).parent/'test-fixtures/native-notices'/relative
                target = root/relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(original.read_bytes())
            output = root/'release/native-files.json'
            module.build_inventory(root/'clang64', listing, output)
            actual_paths = {p.relative_to(output.parent).as_posix() for p in (output.parent/'licenses/native').rglob('*') if p.is_file()}
            expected_paths = {f'licenses/native/{name}/{relative}' for relative in sources}
            self.assertEqual(actual_paths, expected_paths)
            records = json.loads(output.read_text())['files'][0]['packages'][0]['includedLicenseFiles']
            self.assertEqual(len(records), 2)
            for relative, (size, digest) in sources.items():
                destination = f'licenses/native/{name}/{relative}'
                self.assertEqual((output.parent/destination).read_bytes(), (root/relative).read_bytes())
                self.assertIn({'sourcePath': relative, 'path': destination, 'size': size, 'sha256': digest}, records)

    def test_original_notice_bytes_survive_windows_style_git_checkout(self):
        source = Path(__file__).resolve().parents[2]
        relatives = (
            'installer/windows/test-fixtures/native-notices/clang64/share/licenses/gettext-runtime/COPYING',
            'installer/windows/test-fixtures/native-notices/clang64/share/licenses/gettext-runtime/libasprintf/COPYING')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); repo = root/'repo'; repo.mkdir(); checkout = root/'checkout'; checkout.mkdir()
            (repo/'.gitattributes').write_bytes((source/'.gitattributes').read_bytes())
            for relative in relatives:
                path = repo/relative; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((source/relative).read_bytes())
            def git(*args):
                subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
            git('init', '-q')
            git('-c', 'core.autocrlf=false', 'add', '.')
            git('-c', 'core.autocrlf=true', 'checkout-index', '--all', '--prefix='+checkout.as_posix()+'/')
            for relative in relatives:
                self.assertEqual((checkout/relative).read_bytes(), (source/relative).read_bytes())

    def test_existing_notice_outputs_are_preserved_before_any_write(self):
        for kind in ('file-link', 'directory-link', 'regular-file', 'hard-link'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                listing, _ = self.fixture(root)
                output = root/'release/native-files.json'
                destination = output.parent/'licenses/native/gtk4/clang64/share/licenses/gtk4/COPYING'
                outside = root/'outside'; outside.mkdir()
                sentinel = outside/'COPYING'; sentinel.write_bytes(b'preserve outside')
                if kind == 'directory-link':
                    destination.parent.parent.mkdir(parents=True)
                    destination.parent.symlink_to(outside, target_is_directory=True)
                else:
                    destination.parent.mkdir(parents=True)
                    if kind == 'file-link': destination.symlink_to(sentinel)
                    elif kind == 'hard-link': os.link(sentinel, destination)
                    else: destination.write_bytes(b'preserve existing')
                with self.assertRaises((ValueError, FileExistsError)):
                    module.build_inventory(root/'clang64', listing, output)
                self.assertEqual(sentinel.read_bytes(), b'preserve outside')
                if kind == 'regular-file': self.assertEqual(destination.read_bytes(), b'preserve existing')
                self.assertFalse(output.exists())

    def test_existing_inventory_is_preserved_without_copying_notices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); listing, _ = self.fixture(root)
            output = root/'release/native-files.json'; output.parent.mkdir()
            output.write_bytes(b'previous evidence')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                module.build_inventory(root/'clang64', listing, output)
            self.assertEqual(output.read_bytes(), b'previous evidence')
            self.assertFalse((output.parent/'licenses').exists())

    def test_late_notice_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); listing, _ = self.fixture(root)
            output = root/'release/native-files.json'
            destination = output.parent/'licenses/native/gtk4/clang64/share/licenses/gtk4/COPYING'
            original_open = Path.open
            def late_owner(path, mode='r', *args, **kwargs):
                if path == destination and mode in ('wb', 'xb'):
                    with original_open(path, 'wb') as stream: stream.write(b'late owner')
                return original_open(path, mode, *args, **kwargs)
            with patch.object(Path, 'open', late_owner):
                with self.assertRaises((ValueError, FileExistsError)):
                    module.build_inventory(root/'clang64', listing, output)
            self.assertEqual(destination.read_bytes(), b'late owner')
            self.assertFalse(output.exists())

    def test_missing_package_owner_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            listing, dll=self.fixture(root)
            unowned=dll.with_name('unknown.dll')
            unowned.write_bytes(b'unknown')
            listing.write_text(str(unowned)+'\n')
            with self.assertRaisesRegex(ValueError, 'ownership'):
                module.build_inventory(root/'clang64',listing,root/'out.json')
            self.assertFalse((root/'out.json').exists())

    def test_missing_license_text_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            listing, dll=self.fixture(root)
            (root/'clang64/share/licenses/gtk4/COPYING').unlink()
            with self.assertRaisesRegex(ValueError, 'license text'):
                module.build_inventory(root/'clang64',listing,root/'out.json')

    def test_unused_package_with_empty_metadata_does_not_break_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            listing, dll=self.fixture(root)
            other=root/'var/lib/pacman/local/unrelated'
            other.mkdir()
            (other/'desc').write_text('%NAME%\nunrelated\n\n%VERSION%\n\n%URL%\n\n')
            (other/'files').write_text('%FILES%\nusr/bin/unrelated.exe\n')
            output=root/'out.json'
            module.build_inventory(root/'clang64',listing,output)
            self.assertEqual(len(json.loads(output.read_text())['files']),1)

    def test_used_package_with_empty_url_fails_closed_with_metadata_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            listing, dll=self.fixture(root)
            desc=root/'var/lib/pacman/local/gtk4-1.2-1/desc'
            desc.write_text(desc.read_text().replace('https://gtk.org',''))
            with self.assertRaisesRegex(ValueError, 'version/license/source metadata'):
                module.build_inventory(root/'clang64',listing,root/'out.json')
            self.assertFalse((root/'out.json').exists())

    def supplement_fixture(self, root):
        listing, dll = self.fixture(root)
        (root/'var/lib/pacman/local/gtk4-1.2-1/files').write_text('%FILES%\nclang64/bin/libgtk.dll\n')
        directory = root/'source-notices'
        directory.mkdir()
        license_file = directory/'COPYING'
        license_file.write_bytes(b'exact upstream license bytes\r\n')
        record = {'package': 'gtk4', 'version': '1.2-1',
                  'licenses': ['LGPL-2.1-or-later'], 'upstream': 'https://gtk.org',
                  'licenseFile': 'COPYING',
                  'licenseSha256': hashlib.sha256(license_file.read_bytes()).hexdigest(),
                  'sourceArchive': {'url': 'https://gtk.org/fixture.tar.xz', 'sha256': 'a'*64}}
        manifest = directory/'sources.json'
        manifest.write_text(json.dumps({'schemaVersion': 1, 'packages': [record]}))
        return listing, manifest, record

    def test_split_package_uses_exact_version_hash_verified_source_license(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, manifest, record = self.supplement_fixture(root)
            output = root/'release/native-files.json'
            module.build_inventory(root/'clang64', listing, output, supplements=manifest)
            package = json.loads(output.read_text())['files'][0]['packages'][0]
            self.assertEqual(package['licenseSupplement'], record)
            copied = output.parent/'licenses/native/gtk4/COPYING'
            self.assertEqual(copied.read_bytes(), (manifest.parent/'COPYING').read_bytes())

    def test_source_license_rejects_version_or_metadata_mismatch(self):
        for field, changed in [('version', '9.0-1'), ('upstream', 'https://unrelated.org'),
                               ('licenses', ['MIT'])]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                listing, manifest, record = self.supplement_fixture(root)
                record[field] = changed
                manifest.write_text(json.dumps({'schemaVersion': 1, 'packages': [record]}))
                with self.assertRaisesRegex(ValueError, 'supplement metadata'):
                    module.build_inventory(root/'clang64', listing, root/'out.json', supplements=manifest)
                self.assertFalse((root/'out.json').exists())

    def test_source_license_rejects_modified_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, manifest, record = self.supplement_fixture(root)
            (manifest.parent/'COPYING').write_text('different license')
            with self.assertRaisesRegex(ValueError, 'supplement hash'):
                module.build_inventory(root/'clang64', listing, root/'out.json', supplements=manifest)
            self.assertFalse((root/'out.json').exists())

    def test_source_license_cannot_hide_missing_installed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, manifest, record = self.supplement_fixture(root)
            (root/'var/lib/pacman/local/gtk4-1.2-1/files').write_text('%FILES%\nclang64/bin/libgtk.dll\nclang64/share/licenses/gtk4/MISSING\n')
            with self.assertRaisesRegex(ValueError, 'installed package license text'):
                module.build_inventory(root/'clang64', listing, root/'out.json', supplements=manifest)

    def test_source_license_cannot_read_outside_manifest_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            listing, manifest, record = self.supplement_fixture(root)
            record['licenseFile'] = '../outside.txt'
            (root/'outside.txt').write_bytes((manifest.parent/'COPYING').read_bytes())
            manifest.write_text(json.dumps({'schemaVersion': 1, 'packages': [record]}))
            with self.assertRaisesRegex(ValueError, 'supplement path'):
                module.build_inventory(root/'clang64', listing, root/'out.json', supplements=manifest)

if __name__ == '__main__': unittest.main()
