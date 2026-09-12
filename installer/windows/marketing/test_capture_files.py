# Copyright 2026 Trieflow LLC. MIT. Actual demo bytes and separate capture oracle.
import tempfile,unittest,json
from pathlib import Path
import capture_files as c

class Files(unittest.TestCase):
    def test_known_clockwise_pixel_mapping(self):
        image=(3,2,[b'aaaabbbbcccc',b'ddddeeeeffff'])
        self.assertEqual((2,3,[b'ddddaaaa',b'eeeebbbb',b'ffffcccc']),c.clockwise(image))
    def test_real_artwork_create_edit_export_reopen_recipe_and_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();state=c.create(root/'Cedar Coast',root/'profile')
            self.assertEqual((1200,1800),c.decode((Path(state['root'])/c.DRAFT).read_bytes())[:2])
            (Path(state['root'])/c.EDITED).write_bytes(c.ARTWORK.read_bytes())
            self.assertEqual(2160000,c.stage(state,'edited')['checked_pixels'])
            width,height,rows=c.decode(c.ARTWORK.read_bytes())
            reduced=(1200,800,[b''.join(rows[int(y*1.5)][int(x*1.5)*4:int(x*1.5)*4+4] for x in range(1200)) for y in range(800)])
            (Path(state['root'])/c.EXPORTED).write_bytes(c.encode(reduced))
            self.assertGreater(c.stage(state,'exported')['checked_pixels'],700000)
            (Path(state['root'])/c.WITNESS).write_bytes(c.encode(c.clockwise(reduced)))
            self.assertEqual(960000,c.stage(state,'reopened')['checked_pixels'])
            recipe=dict(c.RECIPE,Id='a'*32)
            import xml.etree.ElementTree as ET
            settings=ET.Element('settings');node=ET.SubElement(settings,'setting',name='pixelquay.export-recipes.v1',type='System.String');node.text=json.dumps(dict(Version=1,Recipes=[recipe]))
            (root/'profile/settings.xml').write_bytes(ET.tostring(settings))
            self.assertEqual(recipe,c.finish(state,True)['recipe'])
            c.owner.cleanup(state,True)
            self.assertFalse((root/'profile').exists());self.assertFalse((root/'Cedar Coast').exists())
    def test_existing_foreign_changed_and_incomplete_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();profile=root/'profile';profile.mkdir();(profile/'foreign').write_text('keep')
            with self.assertRaises(ValueError):c.create(root/'demo',profile)
            self.assertEqual('keep',(profile/'foreign').read_text())
            state=c.create(root/'demo',root/'fresh')
            with self.assertRaises(ValueError):c.finish(state,True)
            with self.assertRaises(ValueError):c.owner.cleanup(state,False)
            (root/'demo'/c.DRAFT).write_bytes(b'changed')
            with self.assertRaises(ValueError):c.owner.cleanup(state,True)
    def test_changed_artwork_and_wrong_export_refused(self):
        image=c.decode(c.ARTWORK.read_bytes())
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve();state=c.create(root/'demo',root/'profile')
            bad=list(image[2]);bad[0]=b'\x00\x00\x00\xff'+bad[0][4:]
            (root/'demo'/c.EDITED).write_bytes(c.encode((image[0],image[1],bad)))
            with self.assertRaises(ValueError):c.stage(state,'edited')
            (root/'demo'/c.EDITED).write_bytes(c.ARTWORK.read_bytes());c.stage(state,'edited')
            (root/'demo'/c.EXPORTED).write_bytes(c.ARTWORK.read_bytes())
            with self.assertRaises(ValueError):c.stage(state,'exported')

if __name__=='__main__':unittest.main()
