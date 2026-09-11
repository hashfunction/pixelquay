#!/usr/bin/env python3
"""Record restored packages, licenses and hashes. Does not assert license clearance."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
from managed_notices import include_notice

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--assets',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assets=json.loads(args.assets.read_text())
roots=[Path(p) for p in assets['packageFolders']]
rows=[]
for key,info in assets['libraries'].items():
    if info['type']!='package': continue
    package=next(p/info['path'] for p in roots if (p/info['path']).is_dir())
    nuspec=next(package.glob('*.nuspec'))
    metadata={e.tag.split('}')[-1]:e for e in ET.parse(nuspec).getroot().iter()}
    def value(name):
        element=metadata.get(name)
        return element.text if element is not None else None
    license_files=[]
    for source in package.rglob('*'):
        if source.is_file() and any(word in source.name.lower() for word in ('license','copying','notice')):
            rel=Path('managed')/info['path']/source.relative_to(package)
            target=args.output.parent/rel
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,target)
            license_files.append(rel.as_posix())
    repo=metadata.get('repository')
    nupkg=next(package.glob('*.nupkg'))
    row={'package':key,'authors':value('authors'),'copyright':value('copyright'),
        'license':value('license'),'licenseUrl':value('licenseUrl'),'projectUrl':value('projectUrl'),
        'repository':dict(repo.attrib) if repo is not None else None,
        'packageSha256':hashlib.sha256(nupkg.read_bytes()).hexdigest(),
        'includedNoticeFiles':license_files,
        'noticeReviewRequired':not license_files}
    supplement=include_notice(row,Path(__file__).resolve().parents[2]/'licenses/managed-source-notices',args.output.parent)
    if supplement:
        row['includedNoticeFiles'].append(supplement['file'])
        row['supplementalNoticeProvenance']=supplement
        row['noticeTextPresent']=True
        # Keep the explicit review flag: the package itself omitted its notice.
        # A copied source text is evidence, not clearance for all shipped contents.
    rows.append(row)
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps({'schemaVersion':1,'status':'restored-package-audit-not-release-clearance',
    'scope':'All packages in the supplied assets file, including build-only and RID alternatives; rerun after Windows restore.',
    'packages':rows},indent=2)+'\n')
print(f'Recorded {len(rows)} packages; {sum(r["noticeReviewRequired"] for r in rows)} lack packaged license files and require source-notice review.')
