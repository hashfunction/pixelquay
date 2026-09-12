# Copyright 2026 Trieflow LLC. MIT. Real package and original native-record replay.
import copy,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
import capture_checks as c
import test_store_export as fixtures

class Checks(unittest.TestCase):
    def test_unbound_candidate_and_invalid_bindings_refuse_before_execution(self):
        with self.assertRaisesRegex(ValueError,'no reviewed'):c.validate_binding({'schema_version':1,'product':'TintFable','qualified':None})
        bound=dict(source_commit='a'*40,workflow_run_id='12',workflow_run_attempt='1',package={'bytes':3,'sha256':'b'*64},readiness_receipt={'bytes':4,'sha256':'c'*64},store_artifact_id=5,metadata_artifact_id=6)
        c.validate_binding(dict(schema_version=1,product='TintFable',qualified=bound))
        for field,value in [('source_commit','main'),('workflow_run_id','0'),('package',{}),('metadata_artifact_id',False)]:
            altered=copy.deepcopy(bound);altered[field]=value
            with self.assertRaises((ValueError,KeyError)):c.validate_binding(dict(schema_version=1,product='TintFable',qualified=altered))
    def test_actual_container_both_original_lifecycles_and_input_tampering(self):
        f=fixtures.ExportTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        native=f.source/'installer/windows/source';shutil.copytree(c.BINDING.parents[1]/'source',native)
        subprocess.run(['git','-C',str(f.source),'add','.'],check=True,capture_output=True)
        subprocess.run(['git','-C',str(f.source),'commit','-qm','Fixture public source records'],check=True,capture_output=True)
        commit=c.git(f.source,'rev-parse','HEAD').decode().strip();context=dict(f.context,source_commit=commit)
        for mode in ('qualification','store'):
            prefix='msix-store' if mode=='store' else 'msix';record=f.records[mode];record['sourceCommit']=commit
            fixtures.write(f.evidence/(prefix+'-package-record.json'),record)
            path=f.evidence/(prefix+'-install/installation-qualification.json');r=c.read_json(path);r.update(context);fixtures.write(path,r)
        (f.evidence/'msys2-cache-sha256.txt').write_text('a'*64+' *build-evidence/package-cache/fixture.pkg.tar.zst\n'+'b'*64+' *build-evidence/package-cache/fixture.pkg.tar.zst.sig\n')
        ready=dict(context,store_upload_ready=True,signed=False,identity=c.msix.STORE_IDENTITY,qualified_identity_modes=['qualification','store'],
                   package=dict(filename=c.PACKAGE_NAME,**c.digest(f.packages['store'])),qualification_evidence=c.msix.inventory_tree(f.evidence),
                   public_sources={'source_publication_inputs':{p.name:c.digest(p) for p in native.glob('*.json')}})
        ready['qualification_evidence'].update({'package-cache/fixture.pkg.tar.zst':{'bytes':50,'sha256':'a'*64},'package-cache/fixture.pkg.tar.zst.sig':{'bytes':5,'sha256':'b'*64}})
        path=f.root/'release-ready.json';fixtures.write(path,ready)
        bound=dict(context,package=c.digest(f.packages['store']),readiness_receipt=c.digest(path),store_artifact_id=1,metadata_artifact_id=2)
        run=dict(id=int(bound['workflow_run_id']),head_sha=commit,run_attempt=1,conclusion='success',repository={'full_name':'hashfunction/pixelquay'},path='.github/workflows/windows.yml')
        verify=lambda:c.verify_inputs(f.packages['store'],path,f.evidence,f.source,run,bound)
        self.assertEqual('store',verify()['identityMode'])
        original_ready=path.read_bytes();original_binding=dict(bound['readiness_receipt'])
        for mutation in ('missing-signature','unrecorded-cache'):
            altered=copy.deepcopy(ready)
            if mutation=='missing-signature':altered['qualification_evidence'].pop('package-cache/fixture.pkg.tar.zst.sig')
            else:altered['qualification_evidence']['package-cache/foreign.pkg.tar.zst']={'bytes':2,'sha256':'d'*64}
            fixtures.write(path,altered);bound['readiness_receipt']=c.digest(path)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):verify()
        path.write_bytes(original_ready);bound['readiness_receipt']=original_binding
        for field,value in [('conclusion','failure'),('head_sha','0'*40),('run_attempt',2),('path','capture.yml')]:
            old=run[field];run[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):verify()
            run[field]=old
        original=f.packages['store'].read_bytes();f.packages['store'].write_bytes(b'changed')
        with self.assertRaises(ValueError):verify()
        f.packages['store'].write_bytes(original)
        evidence=f.evidence/'msix-store-install/consumer-opened.png';evidence.write_bytes(b'changed actual evidence')
        with self.assertRaises(ValueError):verify()
    def test_archive_paths_and_ambiguous_metadata(self):
        for path in ('../x','C:/x','/x','x\\y','x//y','x/./y',''):
            with self.assertRaises(ValueError):c.relative_path(path)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            with self.assertRaises(ValueError):c.metadata_root(root)
            for name in ('one','two'):(root/name).mkdir();(root/name/'msix-store-package-record.json').write_text('{}')
            with self.assertRaises(ValueError):c.metadata_root(root)

if __name__=='__main__':unittest.main()
