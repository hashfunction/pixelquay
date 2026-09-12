"""Independent file, image, recipe, and ownership boundaries."""
import json
import stat
from types import SimpleNamespace
from unittest import mock
from pathlib import Path
import tempfile
import struct
import zlib
import unittest
import xml.etree.ElementTree as ET

import consumer_workflow as workflow


class ConsumerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.state = workflow.create(self.base / 'fixture', self.base / 'profile')

    def output(self, name, image):
        (Path(self.state['root']) / name).write_bytes(workflow.encode_png(image))

    def prepare_images(self):
        self.output('edited.png', workflow.rotate_clockwise(workflow.fixture_image()))
        workflow.verify_stage(self.state, 'edited')
        image = workflow.fixture_image(48, 32)
        image = workflow.rotate_clockwise(image)
        self.output('edited-proof.png', image)
        workflow.verify_stage(self.state, 'exported')
        self.output('reopened.png', workflow.rotate_clockwise(image))
        workflow.verify_stage(self.state, 'reopened')

    def test_fixture_coordinates_and_rotation(self):
        w, h, rows = workflow.fixture_image()
        self.assertEqual((w, h), (96, 64))
        self.assertEqual(rows[0][0], (255, 0, 0, 255))
        self.assertEqual(rows[0][-1], (0, 255, 0, 255))
        self.assertEqual(rows[-1][0], (0, 0, 255, 255))
        rotated = workflow.rotate_clockwise((w, h, rows))
        self.assertEqual(rotated[:2], (64, 96))
        self.assertEqual(rotated[2][0][0], (0, 0, 255, 255))
        self.assertEqual(rotated[2][0][-1], (255, 0, 0, 255))

    def test_full_export_and_reopen_sequence(self):
        self.prepare_images()
        self.assertEqual(set(self.state['files']), {workflow.MARKER, 'source.png', 'edited.png', 'edited-proof.png', 'reopened.png'})

    def test_wrong_rotation_refused(self):
        self.output('edited.png', workflow.fixture_image(64, 96))
        with self.assertRaisesRegex(ValueError, 'pixels'):
            workflow.verify_stage(self.state, 'edited')

    def test_wrong_dimensions_refused(self):
        self.output('edited.png', workflow.fixture_image())
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            workflow.verify_stage(self.state, 'edited')

    def test_export_wrong_orientation_refused(self):
        self.output('edited.png', workflow.rotate_clockwise(workflow.fixture_image()))
        workflow.verify_stage(self.state, 'edited')
        self.output('edited-proof.png', workflow.fixture_image(32, 48))
        with self.assertRaisesRegex(ValueError, 'pixels'):
            workflow.verify_stage(self.state, 'exported')

    def test_original_changed_refused(self):
        self.output('source.png', workflow.fixture_image(32, 48))
        self.output('edited.png', workflow.rotate_clockwise(workflow.fixture_image()))
        with self.assertRaisesRegex(ValueError, 'changed'):
            workflow.verify_stage(self.state, 'edited')

    def test_staging_leftovers_refused(self):
        self.output('edited.png', workflow.rotate_clockwise(workflow.fixture_image()))
        (Path(self.state['root']) / '.output.stage.png').write_bytes(b'partial')
        with self.assertRaisesRegex(ValueError, '(?i)unexpected'):
            workflow.verify_stage(self.state, 'edited')

    def test_corrupt_png_refused(self):
        data = bytearray(workflow.encode_png(workflow.fixture_image()))
        data[-8] ^= 1
        with self.assertRaises(ValueError):
            workflow.decode_png(bytes(data))

    def test_rgb_decoder(self):
        image = workflow.fixture_image()
        self.assertEqual(workflow.decode_png(workflow.encode_png(image, rgb=True)), image)

    def test_reopen_wrong_pixels_refused(self):
        self.prepare_images()
        self.output('reopened.png', workflow.fixture_image(48, 32))
        with self.assertRaises(ValueError):
            workflow.verify_stage(self.state, 'reopened')

    def test_all_png_filters_decode_independently_encoded_rows(self):
        # Two known RGB rows, encoded with each PNG prediction method.
        rows = [bytes((3, 10, 30, 60, 90, 120)), bytes((4, 11, 31, 61, 91, 121))]
        for mode in range(5):
            encoded = bytearray()
            prior = bytes(6)
            for row in rows:
                encoded.append(mode)
                for index, value in enumerate(row):
                    left = row[index-3] if index >= 3 else 0
                    up = prior[index]
                    corner = prior[index-3] if index >= 3 else 0
                    candidate = left + up - corner
                    distances = [abs(candidate-v) for v in (left, up, corner)]
                    prediction = (0, left, up, (left+up)//2, (left, up, corner)[distances.index(min(distances))])[mode]
                    encoded.append((value-prediction) % 256)
                prior = row
            data = b'\x89PNG\r\n\x1a\n' + workflow._chunk(b'IHDR', struct.pack('>IIBBBBB', 2, 2, 8, 2, 0, 0, 0)) + workflow._chunk(b'IDAT', zlib.compress(encoded)) + workflow._chunk(b'IEND', b'')
            image = workflow.decode_png(data)
            self.assertEqual(image, (2, 2, [[(3,10,30,255),(60,90,120,255)],[(4,11,31,255),(61,91,121,255)]]))

    def test_unexpected_empty_directory_is_preserved(self):
        extra = Path(self.state['root']) / 'foreign-directory'
        extra.mkdir()
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            workflow.cleanup(self.state, stopped=True)
        self.assertTrue(extra.is_dir())

    def test_cleanup_refuses_changed_profile_after_successful_seal(self):
        self.prepare_images()
        self.write_settings()
        workflow.finish(self.state, stopped=True)
        settings = Path(self.state['profile']) / 'settings.xml'
        settings.write_text('foreign replacement')
        with self.assertRaisesRegex(ValueError, 'changed'):
            workflow.cleanup(self.state, stopped=True)
        self.assertEqual(settings.read_text(), 'foreign replacement')
        self.assertTrue((Path(self.state['root']) / 'source.png').is_file())

    def test_fixture_profile_nesting_refused(self):
        root = self.base / 'nested'
        with self.assertRaisesRegex(ValueError, 'separate'):
            workflow.create(root, root / 'profile')
        self.assertFalse(root.exists())

    def test_existing_profile_preserved(self):
        (self.base / 'other-profile').mkdir()
        protected = self.base / 'other-profile' / 'keep.txt'
        protected.write_text('preserve')
        with self.assertRaises(ValueError):
            workflow.create(self.base / 'other-fixture', protected.parent)
        self.assertEqual(protected.read_text(), 'preserve')
        self.assertFalse((self.base / 'other-fixture').exists())

    def test_cleanup_requires_stopped_processes(self):
        with self.assertRaisesRegex(ValueError, 'stopped'):
            workflow.cleanup(self.state, stopped=False)
        self.assertTrue(Path(self.state['root']).exists())

    def test_changed_marker_preserves_everything(self):
        (Path(self.state['profile']) / workflow.MARKER).write_text('different owner')
        with self.assertRaises(ValueError):
            workflow.cleanup(self.state, stopped=True)
        self.assertTrue((Path(self.state['root']) / 'source.png').exists())

    def test_unexpected_cleanup_file_preserved(self):
        extra = Path(self.state['root']) / 'foreign.txt'
        extra.write_text('keep')
        with self.assertRaisesRegex(ValueError, '(?i)unexpected'):
            workflow.cleanup(self.state, stopped=True)
        self.assertEqual(extra.read_text(), 'keep')

    def test_changed_cleanup_file_preserved(self):
        protected = Path(self.state['root']) / 'source.png'
        protected.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            workflow.cleanup(self.state, stopped=True)
        self.assertEqual(protected.read_bytes(), b'changed')

    def test_symlink_cleanup_preserves_target(self):
        protected = self.base / 'outside.txt'
        protected.write_text('keep')
        link = Path(self.state['root']) / 'foreign'
        try:
            link.symlink_to(protected)
        except OSError:
            # Exercise the Windows reparse observation without requiring the
            # account privilege needed to create symbolic links.
            link.write_text('reparse fixture')
            original = Path.lstat
            def observed(path, *args, **kwargs):
                info = original(path, *args, **kwargs)
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=1024) if path == link else info
            with mock.patch.object(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 1024, create=True), mock.patch.object(Path, 'lstat', observed):
                with self.assertRaisesRegex(ValueError, 'reparse'):
                    workflow.cleanup(self.state, stopped=True)
            self.assertEqual(protected.read_text(), 'keep')
            return
        with self.assertRaisesRegex(ValueError, 'link|reparse'):
            workflow.cleanup(self.state, stopped=True)
        self.assertEqual(protected.read_text(), 'keep')

    def write_settings(self, recipe=None):
        recipe = recipe or dict(Id='a'*32, Name=workflow.RECIPE_NAME, Width=32, Height=48, Extension='png', Quality=None, Suffix='-proof', Overwrite=False)
        xml = ET.Element('settings')
        item = ET.SubElement(xml, 'setting', name='pixelquay.export-recipes.v1', type='System.String')
        item.text = json.dumps(dict(Version=1, Recipes=[recipe]))
        ET.ElementTree(xml).write(Path(self.state['profile']) / 'settings.xml', encoding='utf-8')

    def test_exact_recipe_and_cleanup(self):
        self.prepare_images()
        self.write_settings()
        result = workflow.finish(self.state, stopped=True)
        self.assertEqual(result['recipe']['Name'], workflow.RECIPE_NAME)
        workflow.cleanup(self.state, stopped=True)
        self.assertFalse(Path(self.state['root']).exists())
        self.assertFalse(Path(self.state['profile']).exists())

    def test_recipe_not_read_before_stop(self):
        with self.assertRaisesRegex(ValueError, 'stopped'):
            workflow.finish(self.state, stopped=False)

    def test_wrong_recipe_refused(self):
        self.prepare_images()
        self.write_settings(dict(Id='a', Name='wrong', Width=32, Height=48, Extension='png', Quality=None, Suffix='-proof', Overwrite=False))
        with self.assertRaisesRegex(ValueError, 'recipe'):
            workflow.finish(self.state, stopped=True)

    def test_foreign_profile_file_refused_before_sealing(self):
        self.prepare_images()
        self.write_settings()
        (Path(self.state['profile']) / 'foreign.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError, '(?i)unexpected'):
            workflow.finish(self.state, stopped=True)


if __name__ == '__main__':
    unittest.main()
