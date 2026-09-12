"""Exact existing Store package verification for a separate native capture run.
Copyright 2026 Trieflow LLC. MIT. An unbound candidate refuses execution.
"""
import argparse,json,os,re,subprocess,sys
from pathlib import Path,PurePosixPath
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import msix_qualification as msix
import store_export as release
from source_publication import git
PACKAGE_NAME='TintFable_1.0.1.0_x64.msix'
FULL_NAME='1659hashfunction.PixelQuay_1.0.1.0_x64__r3hxytd7jt6c4'
BINDING=Path(__file__).resolve().parent/'binding.json'
require=release.require;read_json=release.load;digest=msix.file_record

def relative_path(name):
    require(isinstance(name,str) and name and '\\' not in name and ':' not in name and not name.startswith('/') and all(p not in ('','.','..') for p in name.split('/')) and str(PurePosixPath(name))==name,'Unsafe artifact/evidence path')
    return name

def validate_binding(value):
    require(value.get('schema_version')==1 and value.get('product')=='TintFable' and isinstance(value.get('qualified'),dict),'Capture has no reviewed successful Store package binding')
    bound=value['qualified']
    require(set(bound)=={'source_commit','workflow_run_id','workflow_run_attempt','package','readiness_receipt','store_artifact_id','metadata_artifact_id'},'Capture binding fields differ')
    require(re.fullmatch('[0-9a-f]{40}',bound['source_commit']) and all(re.fullmatch('[1-9][0-9]*',bound[k]) for k in ('workflow_run_id','workflow_run_attempt')),'Invalid exact source/run binding')
    for key in ('package','readiness_receipt'):
        row=bound[key];require(set(row)=={'bytes','sha256'} and type(row['bytes']) is int and row['bytes']>0 and re.fullmatch('[0-9a-f]{64}',row['sha256']),'Invalid exact package/receipt binding')
    for key in ('store_artifact_id','metadata_artifact_id'):require(type(bound[key]) is int and bound[key]>0,'Missing exact artifact binding')
    return bound

def binding():return validate_binding(read_json(BINDING))

def assert_capture_checkout():
    root=BINDING.parents[3]
    require(git(root,'rev-parse','HEAD').decode().strip()==os.environ.get('GITHUB_SHA'),'Current capture helper commit differs')
    require(not git(root,'status','--porcelain=v1','--untracked-files=all').strip(),'Current capture helper checkout changed')

def assert_qualified_checkout(source,bound):
    require(git(source,'rev-parse','HEAD').decode().strip()==bound['source_commit'],'Qualified source checkout differs')
    require(not git(source,'status','--porcelain=v1','--untracked-files=all').strip(),'Qualified source checkout changed')

def validate_receipts(ready,run,bound):
    require(run.get('id')==int(bound['workflow_run_id']) and run.get('head_sha')==bound['source_commit'] and type(run.get('run_attempt')) is int and run['run_attempt']==int(bound['workflow_run_attempt']) and run.get('conclusion')=='success' and run.get('repository',{}).get('full_name')=='hashfunction/pixelquay' and run.get('path')=='.github/workflows/windows.yml','Pinned successful native run differs')
    require(ready.get('store_upload_ready') is True and ready.get('signed') is False and ready.get('identity')==msix.STORE_IDENTITY and ready.get('package')==dict(bound['package'],filename=PACKAGE_NAME) and ready.get('qualified_identity_modes')==['qualification','store'],'Exact original Store readiness differs')
    require(all(ready.get(k)==bound[k] for k in ('source_commit','workflow_run_id','workflow_run_attempt')),'Original readiness source/run differs')
    require(isinstance(ready.get('qualification_evidence'),dict) and ready['qualification_evidence'],'Original evidence hashes absent')

def metadata_root(path):
    matches=list(Path(path).rglob('msix-store-package-record.json'))
    require(len(matches)==1,'Original Store record missing or ambiguous in metadata artifact')
    return matches[0].parent

def verify_inputs(package,ready_path,metadata,source,run,bound):
    assert_qualified_checkout(source,bound)
    require(digest(package)==bound['package'] and digest(ready_path)==bound['readiness_receipt'],'Pinned original package/readiness bytes differ')
    ready=read_json(ready_path);validate_receipts(ready,run,bound);metadata=metadata_root(metadata)
    evidence=ready['qualification_evidence']
    require(digest(metadata/'msys2-cache-sha256.txt')==evidence['msys2-cache-sha256.txt'],'Original package-cache hash list changed')
    cache={}
    for line in (metadata/'msys2-cache-sha256.txt').read_text(encoding='utf-8-sig').splitlines():
        fields=line.split(maxsplit=1);require(len(fields)==2 and re.fullmatch('[0-9a-f]{64}',fields[0]),'Invalid original package-cache hash row')
        path=fields[1].lstrip('*');require(path.startswith('build-evidence/package-cache/'),'Unexpected package-cache hash path')
        name=relative_path(path.removeprefix('build-evidence/'))
        require(name.endswith(('.pkg.tar.zst','.pkg.tar.zst.sig')) and name not in cache,'Unexpected/duplicate cached package or signature')
        cache[name]=fields[0]
    require(set(cache)=={name for name in evidence if name.startswith('package-cache/')},'Original unretained cache inventory differs')
    for name,expected in evidence.items():
        relative_path(name)
        # Actual run34684998708 records both .pkg.tar.zst archives and detached
        # signatures, but its artifact retains neither. Permit exactly the set
        # in the separately hash-bound original cache list, never arbitrary gaps.
        if name in cache:
            require(expected['sha256']==cache[name] and type(expected['bytes']) is int and expected['bytes']>0,'Original unretained cache record differs')
            continue
        require(digest(metadata/name)==expected,'Original retained qualification evidence changed: '+name)
    source_inputs=ready['public_sources']['source_publication_inputs']
    require(set(source_inputs)=={'native-source-delivery.json','native-source-evidence.json','source-manifest.json','source-supplements.json','native-source-supplement-publication.json'},'Original public source record set differs')
    for name,expected in source_inputs.items():
        relative_path(name);require(digest(Path(source)/'installer/windows/source'/name)==expected,'Original public source record changed')
    context={k:bound[k] for k in ('source_commit','workflow_run_id','workflow_run_attempt')}
    for mode in ('qualification','store'):
        prefix='msix-store' if mode=='store' else 'msix';record=read_json(metadata/(prefix+'-package-record.json'))
        require(record['sourceCommit']==bound['source_commit'] and record['identityMode']==mode and record['identity']==msix.identity_for_mode(mode),'Original package record source/identity differs')
        release.validate_installation(metadata/(prefix+'-install'),record,Path(source),context,mode)
    require(msix.verify_msix(package,record['payload'],'store')==record['containerVerification'],'Original unsigned payload differs')
    return record

def main():
    p=argparse.ArgumentParser();p.add_argument('--binding-output',type=Path);p.add_argument('--inputs',type=Path);p.add_argument('--qualified-source',type=Path);a=p.parse_args();bound=binding()
    if a.binding_output:
        with a.binding_output.open('a',encoding='utf-8') as f:f.write('qualified_source='+bound['source_commit']+'\n')
    else:
        assert_capture_checkout()
        require(a.inputs and a.qualified_source,'Exact prepared inputs and qualified source required')
        verify_inputs(a.inputs/'store'/PACKAGE_NAME,a.inputs/'store/release-ready.json',a.inputs/'metadata',a.qualified_source,read_json(a.inputs/'qualified-run.json'),bound)
        print('Verified unchanged qualified Store package and both original native lifecycles; capture only.')
if __name__=='__main__':main()
