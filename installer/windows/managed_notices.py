"""Bundle hash-bound upstream notices. Copyright 2026 Trieflow LLC; MIT."""
import hashlib
import json
from pathlib import Path
import re


def include_notice(record, source, destination):
    source, destination = Path(source), Path(destination)
    manifest = json.loads((source / 'package-bindings.json').read_text(encoding='utf-8'))
    if manifest.get('schemaVersion') != 1:
        raise ValueError('Unknown supplemental notice manifest schema')
    matches = [entry for entry in manifest['entries'] if entry['package'] == record['package']]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError('Ambiguous supplemental package mapping')
    entry = matches[0]
    if record['packageSha256'] != entry['packageSha256']:
        raise ValueError('Supplemental notice package hash differs from reviewed input')
    name = entry['noticeFile']
    if not isinstance(name, str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]*\.txt', name):
        raise ValueError('Invalid supplemental notice filename')
    origin = source / name
    if origin.is_symlink() or not origin.is_file():
        raise ValueError('Supplemental notice must be a regular source file')
    data = origin.read_bytes()
    if hashlib.sha256(data).hexdigest() != entry['noticeSha256']:
        raise ValueError('Supplemental notice hash differs from reviewed source text')
    relative = Path('managed-source-notices') / name
    target = destination / relative
    if target.is_symlink() or target.parent.is_symlink() or destination.is_symlink():
        raise ValueError('Supplemental notice destination must not be a link')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open('xb') as output:
            output.write(data)
    except FileExistsError:
        if not target.is_file() or target.read_bytes() != data:
            raise ValueError('Conflicting supplemental notice destination is preserved')
    return {'file': relative.as_posix(), 'sha256': entry['noticeSha256'],
            'sourceUrl': entry['noticeSourceUrl'], 'packageSha256': entry['packageSha256']}
