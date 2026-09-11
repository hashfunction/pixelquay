import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
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
            self.assertTrue((output.parent/'licenses/native/gtk4/COPYING').is_file())

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

if __name__ == '__main__': unittest.main()
