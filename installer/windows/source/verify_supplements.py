# Copyright 2026 Trieflow LLC. MIT. Scoped reuse of the original source Git-export verifier.
"""Verify two retained MSYS2 source inputs without importing repository configuration.
Only regular object-pack and packed-ref bytes are materialized in fresh bare repos;
no PKGBUILD, hook, repository config, worktree or source program is executed.
"""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,tarfile,tempfile
from datetime import datetime,timezone
SELECT={'mingw-w64-winpthreads':'mingw-w64'}
def zstd_program():
 path=shutil.which('zstd')
 if not path:raise ValueError('Source verification requires the zstd command on PATH')
 return path
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def inspect(entry):
 base=entry['pkgbase'][0];repo_name=SELECT[base];archive=Path(entry['path'])
 if digest(archive)!=entry['sha256']:raise ValueError('Original source archive hash mismatch')
 with tempfile.TemporaryDirectory(prefix='pixelquay-git-source-') as tmp:
  work=Path(tmp);bare=work/'source.git';empty=work/'empty';empty.mkdir()
  env={k:v for k,v in os.environ.items() if not k.startswith('GIT_')}
  env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull,GIT_ATTR_NOSYSTEM='1',GIT_NO_REPLACE_OBJECTS='1',GIT_TERMINAL_PROMPT='0')
  subprocess.run(['git','init','--bare','--template='+str(empty),'-q',str(bare)],check=True,env=env)
  materialized=[];srcinfo=None;prefix=f'{base}/{repo_name}/';total=0;seen=set()
  zstd=subprocess.Popen([zstd_program(),'-dc',str(archive)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  try:
   with tarfile.open(fileobj=zstd.stdout,mode='r|') as tar:
    for member in tar:
     if member.name in seen:raise ValueError('Duplicate source archive member')
     seen.add(member.name);total+=member.size
     if total>512*1024*1024 or member.size>256*1024*1024:raise ValueError('Source archive exceeds bounds')
     wanted=(member.name==f'{base}/.SRCINFO' or (member.name.startswith(prefix) and (member.name[len(prefix):]=='packed-refs' or re.fullmatch(r'objects/pack/pack-[0-9a-f]{40}\.(?:pack|idx)',member.name[len(prefix):]))))
     if not wanted:continue
     if not member.isfile() or member.linkname:raise ValueError('Selected source member is not regular')
     stream=tar.extractfile(member)
     if member.name==f'{base}/.SRCINFO':
      if member.size>2*1024*1024:raise ValueError('Oversized SRCINFO')
      srcinfo=stream.read().decode('utf-8');continue
     relative=member.name[len(prefix):];destination=bare/relative;destination.parent.mkdir(parents=True,exist_ok=True)
     h=hashlib.sha256();count=0
     with destination.open('xb') as out:
      while chunk:=stream.read(1024*1024):out.write(chunk);h.update(chunk);count+=len(chunk)
     if count!=member.size:raise ValueError('Truncated Git input')
     materialized.append(dict(path=relative,bytes=count,sha256=h.hexdigest()))
   if zstd.wait(timeout=15)!=0:raise ValueError(zstd.stderr.read().decode())
  finally:
   if zstd.poll() is None:zstd.kill();zstd.wait()
   zstd.stdout.close();zstd.stderr.close()
  if srcinfo is None:raise ValueError('Missing source declarations')
  fields={}
  for line in srcinfo.splitlines():
   if ' = ' in line:
    key,value=line.strip().split(' = ',1);fields.setdefault(key,[]).append(value)
  candidates=[(url,sha) for url,sha in zip(fields['source'],fields['sha256sums']) if '::git+' in url]
  if len(candidates)!=1:raise ValueError('Expected one pinned Git input')
  declaration,expected=candidates[0];fragment=declaration.split('#',1)[1];kind,ref=fragment.split('=',1)
  if kind not in ('tag','commit') or not re.fullmatch(r'[A-Za-z0-9._/-]+',ref) or ref.startswith('-'):raise ValueError('Unexpected Git ref')
  if not re.fullmatch(r'[0-9a-f]{64}',expected):raise ValueError('Expected SHA256')
  command=['git','-c','core.abbrev=no','-c','core.attributesFile='+os.devnull,'-c','core.hooksPath='+str(empty),'--git-dir='+str(bare)]
  revision=subprocess.check_output(command+['rev-parse','--verify',ref+'^{commit}'],env=env,text=True,timeout=30).strip()
  if not re.fullmatch(r'[0-9a-f]{40}',revision):raise ValueError('Invalid resolved commit')
  if kind=='commit' and revision!=ref:raise ValueError('Requested commit mismatch')
  exports=[]
  for repetition in range(2):
   process=subprocess.Popen(command+['archive','--format','tar',ref],stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
   h=hashlib.sha256();size=0
   try:
    while chunk:=process.stdout.read(1024*1024):
     size+=len(chunk)
     if size>512*1024*1024:raise ValueError('Export exceeds bound')
     h.update(chunk)
    if process.wait(timeout=30)!=0:raise ValueError(process.stderr.read().decode())
   finally:
    if process.poll() is None:process.kill();process.wait()
    process.stdout.close();process.stderr.close()
   actual=h.hexdigest()
   if actual!=expected:raise ValueError(f'{base}: Git export SHA256 mismatch: {actual} != {expected}')
   exports.append(dict(bytes=size,sha256=actual))
  notice=subprocess.check_output(command+['show',ref+':mingw-w64-libraries/winpthreads/COPYING'],env=env,timeout=30)
  return dict(notice=dict(bytes=len(notice),sha256=hashlib.sha256(notice).hexdigest()),packageBase=base,archive=entry['path'],archiveSha256=entry['sha256'],sourceDeclaration=declaration,requestedRef=ref,resolvedCommit=revision,declaredSha256=expected,exportChecks=exports,status='requested_ref_and_deterministic_export_sha256_verified',materializedInputs=materialized)


def collect(cache, native_path, hashes_path):
 import io
 cache=Path(cache);native=json.loads(Path(native_path).read_text(encoding='utf-8-sig'))
 owners={p['name']:p for row in native['files'] for p in row['packages']}
 binary_hashes={Path(line.split(maxsplit=1)[1].strip().lstrip('*')).name:line.split()[0] for line in Path(hashes_path).read_text().splitlines() if line.strip()}
 wanted=[('mingw-w64-clang-x86_64-gtk4','4.24.0-1','mingw-w64-gtk4-4.24.0-1.src.tar.zst',17262450,'9092701eae0abf0410e5709779613b3485a4849874294830d889ef86aa9268fb'),
         ('mingw-w64-clang-x86_64-libwinpthread','14.0.0.r375.g9c1abbbf5-1','mingw-w64-winpthreads-14.0.0.r375.g9c1abbbf5-1.src.tar.zst',54173752,'7bf513784ae0bc4f1a413e1f787f7a3ba2bd7ec0503980ea4d17ddf0e4796c87')]
 result=[]
 for package,version,filename,size,sha in wanted:
  archive=cache/filename
  if archive.is_symlink() or not archive.is_file() or archive.stat().st_size!=size or digest(archive)!=sha:raise ValueError('Exact supplemental archive mismatch')
  owner=owners[package]
  if owner['version']!=version:raise ValueError('Actual native owner version differs')
  members={};proc=subprocess.Popen([zstd_program(),'-dc',str(archive)],stdout=subprocess.PIPE)
  with tarfile.open(fileobj=proc.stdout,mode='r|') as tar:
   for m in tar:
    if m.isfile() and (m.name.endswith(('/PKGBUILD','/.SRCINFO','.patch','.tar.xz'))):
     if m.size>32*1024*1024 or m.name in members:raise ValueError('Duplicate/oversized selected source input')
     members[m.name]=tar.extractfile(m).read()
  if proc.wait(timeout=30)!=0:raise ValueError('Source decompression failed')
  base=filename.split('-'+version)[0];srcinfo=members[base+'/.SRCINFO'].decode();fields={}
  for line in srcinfo.splitlines():
   if ' = ' in line:
    key,value=line.strip().split(' = ',1);fields.setdefault(key,[]).append(value)
  if fields['pkgbase']!=[base] or fields['pkgver'][0]+'-'+fields['pkgrel'][0]!=version or fields['license']!=owner['licenses']:raise ValueError('Source recipe/version/license differs from installed owner')
  inputs=[];git_proof=None;notice=None
  for declaration,expected in zip(fields['source'],fields['sha256sums']):
   if '::git+' in declaration:
    git_proof=inspect(dict(pkgbase=[base],path=str(archive),sha256=sha));notice=git_proof['notice']
    continue
   name=declaration.rsplit('/',1)[-1];data=members[base+'/'+name]
   if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Declared upstream/patch checksum mismatch')
   inputs.append(dict(declaration=declaration,bytes=len(data),sha256=expected))
   if name=='gtk-4.24.0.tar.xz':
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:xz') as tar:
     item=tar.getmember('gtk-4.24.0/COPYING')
     if not item.isfile() or item.size>100000:raise ValueError('GTK notice is not bounded regular source')
     raw=tar.extractfile(item).read();notice=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
  included=owner['includedLicenseFiles']
  if len(included)!=1 or notice!={'bytes':included[0]['size'],'sha256':included[0]['sha256']}:raise ValueError('Current packaged notice differs from exact original source notice')
  binary=package+'-'+version+'-any.pkg.tar.zst'
  if binary not in binary_hashes:raise ValueError('Exact native binary archive binding absent')
  modules=[dict(path=row['path'],bytes=row['size'],sha256=row['sha256']) for row in native['files']
           if row['path'].lower().endswith(('.dll','.exe')) and any(p['name']==package for p in row['packages'])]
  result.append(dict(package=package,version=version,base=base,package_archive=binary,package_sha256=binary_hashes[binary],
      filename=filename,url='https://mirror.msys2.org/mingw/sources/'+filename,bytes=size,sha256=sha,
      declared_licenses=owner['licenses'],original_notice=notice,installed_notice=included[0],native_modules=modules,
      source_inputs=inputs,git_source=git_proof,recipe_sha256=hashlib.sha256(members[base+'/PKGBUILD']).hexdigest(),
      srcinfo_sha256=hashlib.sha256(members[base+'/.SRCINFO']).hexdigest()))
 return dict(schema_version=1,product='TintFable',original_windows_run='34684998708',
     original_source_commit='8556eb5e329d6fd857d13d1bfb561429f756a824',
     native_inventory_sha256=digest(Path(native_path)),binary_archive_hash_evidence_sha256=digest(Path(hashes_path)),
     scope='Exact two newer source inputs supplement the unchanged 63-archive original collection. Preferred-form inputs, declared checksums and copied original notices verified; no rebuild-parity claim.',
     executed_pkgbuild=False,imported_repository_configuration=False,imported_hooks=False,checked_out_source=False,
     supplements=result)


if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__)
 for name in ('cache','native-inventory','binary-hashes','output'):parser.add_argument('--'+name,required=True,type=Path)
 args=parser.parse_args();result=collect(args.cache,args.native_inventory,args.binary_hashes)
 with args.output.open('x',encoding='utf-8',newline='\n') as stream:json.dump(result,stream,indent=2);stream.write('\n')
 print('PASS: both exact source recipes, upstream/patch hashes, Winpthreads Git export, native module and original notice bindings.')
