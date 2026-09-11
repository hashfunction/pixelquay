#!/usr/bin/env python3
"""Audit exactly the native inputs copied by MSBuild, using installed MSYS2 metadata.

No guessed versions or blanket license mapping. Unknown/generated provenance fails
closed unless its concrete package-owned inputs can be identified below.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


def fields(path):
    result, key = {}, None
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('%') and line.endswith('%'):
            key=line.strip('%')
            result[key]=[]
        elif line and key:
            result[key].append(line)
    return result


def build_inventory(mingw, file_list, output):
    mingw, output = Path(mingw).resolve(), Path(output)
    msys = mingw.parent
    database = msys/'var/lib/pacman/local'
    if not database.is_dir():
        raise ValueError(f'Missing installed MSYS2 ownership database: {database}')
    owners, packages = {}, {}
    for entry in database.iterdir():
        if not (entry/'desc').is_file() or not (entry/'files').is_file(): continue
        meta = fields(entry/'desc')
        name = (meta.get('NAME') or [''])[0]
        files = fields(entry/'files').get('FILES', [])
        packages[name] = {
            'name': name, 'version': (meta.get('VERSION') or [''])[0],
            'licenses': meta.get('LICENSE', []), 'upstream': (meta.get('URL') or [''])[0],
            'packageSource': 'MSYS2 CLANG64 installed pacman database',
            'licenseFiles': [f for f in files if '/share/licenses/' in f and not f.endswith('/')]
        }
        for filename in files: owners[filename.rstrip('/')] = name

    rows, used = [], set()
    paths = sorted(set(Path(p.strip()).resolve() for p in Path(file_list).read_text(encoding='utf-8-sig').splitlines() if p.strip()))
    for path in paths:
        if not path.is_file(): raise ValueError(f'Missing native input: {path}')
        rel = path.relative_to(msys).as_posix()
        provenance = [rel] if rel in owners else []
        if not provenance and path.name == 'gschemas.compiled':
            provenance = [p.relative_to(msys).as_posix() for p in path.parent.glob('*.xml')]
        elif not provenance and path.name == 'loaders.cache':
            provenance = [p.relative_to(msys).as_posix() for p in path.parent.rglob('*.dll')]
        elif not provenance and path.name == 'icon-theme.cache':
            provenance = [(path.parent/'index.theme').relative_to(msys).as_posix()]
        if not provenance or any(p not in owners for p in provenance):
            raise ValueError(f'No complete package ownership for native input: {rel}')
        names = sorted({owners[p] for p in provenance})
        for name in names:
            package = packages[name]
            if not package['name'] or not package['version'] or not package['licenses'] or not package['upstream']:
                raise ValueError(f'Missing version/license/source metadata: {name}')
            license_files = [msys/f for f in package['licenseFiles']]
            if not license_files or any(not f.is_file() for f in license_files):
                raise ValueError(f'Missing installed package license text: {name}')
        used.update(names)
        rows.append({'path': path.relative_to(mingw).as_posix(), 'size': path.stat().st_size,
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'packages': [packages[name] for name in names], 'provenanceInputs': provenance})
    if not rows: raise ValueError('Empty native inventory is not a release inventory')
    output.parent.mkdir(parents=True, exist_ok=True)
    for name in used:
        for rel in packages[name]['licenseFiles']:
            destination=output.parent/'licenses/native'/name/Path(rel).name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(msys/rel, destination)
    payload = {'schemaVersion': 1, 'verifiedAt': datetime.now(timezone.utc).isoformat(),
               'provider': 'MSYS2', 'status': 'inventoried-requires-release-license-review', 'files': rows}
    stage=output.with_suffix('.json.tmp')
    stage.write_text(json.dumps(payload, indent=2)+'\n', encoding='utf-8')
    stage.replace(output)

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mingw', type=Path, required=True)
    parser.add_argument('--file-list', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    build_inventory(args.mingw, args.file_list, args.output)
