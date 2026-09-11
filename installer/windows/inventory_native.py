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
import stat

# Use the same Windows-safe path and regular-file primitives as final packaging.
from msix_qualification import _checked_path, _digest, _register_path, _regular_stream, _reject_link



def _output_directory(path):
    """Create a missing directory, never follow an existing output link."""
    try:
        info = _reject_link(path)
    except FileNotFoundError:
        path.mkdir()
        info = _reject_link(path)
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(f'Expected output directory: {path}')


def _exclusive_output(root, relative):
    """The caller supplies the build root; every child component is checked."""
    _checked_path(relative)
    _output_directory(root)
    parts = relative.split('/')
    parent = root
    for part in parts[:-1]:
        parent = parent/part
        _output_directory(parent)
    # Exclusive creation also refuses a file/link appearing after the checks.
    # Never truncate a pre-existing notice, including a hard-link alias.
    return (parent/parts[-1]).open('xb')


def fields(path):
    result, key = {}, None
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('%') and line.endswith('%'):
            key=line.strip('%')
            result[key]=[]
        elif line and key:
            result[key].append(line)
    return result


def source_license(package, manifest):
    """Use a reviewed source notice only for the exact split package recorded."""
    if not manifest.is_file():
        raise ValueError(f"Missing installed package license text: {package['name']}")
    data = json.loads(manifest.read_text(encoding='utf-8'))
    matches = [p for p in data['packages'] if p['package'] == package['name']]
    if len(matches) != 1:
        raise ValueError(f"Missing installed package license text: {package['name']}")
    record = matches[0]
    if data.get('schemaVersion') != 1 or any(record[k] != package[k] for k in ('version', 'licenses', 'upstream')):
        raise ValueError(f"License supplement metadata mismatch: {package['name']}")
    relative = Path(record['licenseFile'])
    path = (manifest.parent/relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(manifest.parent.resolve()):
        raise ValueError(f"Invalid license supplement path: {package['name']}")
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['licenseSha256']:
        raise ValueError(f"License supplement hash mismatch: {package['name']}")
    package['licenseSupplement'] = record
    return path


def build_inventory(mingw, file_list, output, supplements=None):
    mingw, output = Path(mingw).resolve(), Path(output)
    supplements = Path(supplements) if supplements is not None else Path(__file__).resolve().parents[2]/'licenses/native-supplements/sources.json'
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

    rows, used, supplemental_files = [], set(), {}
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
            if any(not f.is_file() for f in license_files):
                raise ValueError(f'Missing installed package license text: {name}')
            if not license_files:
                supplemental_files[name] = source_license(package, supplements)
        used.update(names)
        rows.append({'path': path.relative_to(mingw).as_posix(), 'size': path.stat().st_size,
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                     'packages': [packages[name] for name in names], 'provenanceInputs': provenance})
    if not rows: raise ValueError('Empty native inventory is not a release inventory')
    # Build output may be reused accidentally; refuse existing inventory bytes.
    if output.exists() or output.is_symlink():
        raise ValueError(f'Native inventory already exists; use a fresh output: {output}')
    if not output.parent.exists() and not output.parent.is_symlink():
        output.parent.parent.mkdir(parents=True, exist_ok=True)
    _output_directory(output.parent)
    notice_paths = {}
    for name in sorted(used):
        _checked_path(name)
        if '/' in name:
            raise ValueError(f'Invalid native package name: {name}')
        package = packages[name]
        copies = []
        if name in supplemental_files:
            source = supplemental_files[name]
            copies.append((package['licenseSupplement']['licenseFile'], source,
                           f'licenses/native/{name}/{source.name}'))
        for rel in package['licenseFiles']:
            _checked_path(rel)
            copies.append((rel, msys/rel, f'licenses/native/{name}/{rel}'))
        package['includedLicenseFiles'] = []
        for original, source, relative in copies:
            _register_path(relative, notice_paths)
            destination = output.parent/relative
            with _regular_stream(source) as stream:
                record = _digest(stream)
                stream.seek(0)
                with _exclusive_output(output.parent, relative) as target:
                    shutil.copyfileobj(stream, target)
            with _regular_stream(destination) as stream:
                if _digest(stream) != record:
                    raise ValueError(f'Copied native notice hash mismatch: {relative}')
            package['includedLicenseFiles'].append({'sourcePath': original, 'path': relative,
                                                   'size': record['bytes'], 'sha256': record['sha256']})
    payload = {'schemaVersion': 1, 'verifiedAt': datetime.now(timezone.utc).isoformat(),
               'provider': 'MSYS2', 'status': 'inventoried-requires-release-license-review', 'files': rows}
    with _exclusive_output(output.parent, output.name) as stream:
        stream.write((json.dumps(payload, indent=2)+'\n').encode('utf-8'))

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mingw', type=Path, required=True)
    parser.add_argument('--file-list', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args=parser.parse_args()
    build_inventory(args.mingw, args.file_list, args.output)
