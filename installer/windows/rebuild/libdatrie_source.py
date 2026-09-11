"""Verify and materialize only the exact published libdatrie 0.2.14 source.

Copyright 2026 Trieflow LLC. MIT licensed; upstream sources retain LGPL-2.1+.
No recipe execution, archive extractall, network access, or overwrite.
"""
import argparse
import hashlib
import io
import json
import lzma
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tarfile
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from msix_qualification import _checked_path, _regular_stream, _reject_link

ARCHIVE_SHA = 'da58ca439051a8cfb1d7f15cdd82af104e1ea1eeefdb090e608d2305a747df7d'
ARCHIVE_SIZE = 327473
MEMBERS = {
    'mingw-w64-libdatrie/PKGBUILD': (2293, '5b6a0eae66edab8c902ae4668b31859a00ac09d78ff7b9dfe6cb044ea4be5af6'),
    'mingw-w64-libdatrie/.SRCINFO': (949, 'd806220181cd0ca3c58db206701386051aeae42b22ddaa635e06d3b480f1156b'),
    'mingw-w64-libdatrie/libdatrie-0.2.14.tar.xz': (325696, 'f04095010518635b51c2313efa4f290b7db828d6273e39b2b8858f859dfe81d5'),
}
COPYING_SHA = 'a9bdde5616ecdd1e980b44f360600ee8783b1f99b8cc83a2beb163a0a390e861'


def digest(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def checked_parents(path):
    """Call with an absolute path; preexisting ancestors must be real directories."""
    path = Path(os.path.abspath(path))
    for parent in reversed(path.parents):
        info = _reject_link(parent)
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError(f'Non-directory ancestor: {parent}')
    return path


def read_tar(data, root, max_bytes=16 * 1024 * 1024):
    if len(data) > max_bytes + 2 * 1024 * 1024:
        raise ValueError('Archive expanded byte limit exceeded')
    files, directories, seen = {}, set(), {}
    total = 0
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
        for index, member in enumerate(archive):
            if index >= 1024 or member.pax_headers:
                raise ValueError('Unreviewed archive member count or extension')
            name = member.name.rstrip('/') if member.isdir() else member.name
            _checked_path(name)
            if name != root and not name.startswith(root + '/'):
                raise ValueError(f'Archive member outside expected root: {name}')
            parts = name.split('/')
            for count in range(1, len(parts) + 1):
                prefix = '/'.join(parts[:count])
                key = unicodedata.normalize('NFC', prefix).casefold()
                if key in seen and seen[key] != prefix:
                    raise ValueError(f'Case/Unicode archive alias: {name}')
                seen[key] = prefix
            if name in files or name in directories:
                raise ValueError(f'Duplicate archive member: {name}')
            if member.isdir():
                if member.size != 0:
                    raise ValueError('Directory member has data')
                directories.add(name)
            elif member.isreg():
                total += member.size
                if member.size < 0 or total > max_bytes:
                    raise ValueError('Archive declared byte limit exceeded')
                stream = archive.extractfile(member)
                body = stream.read(member.size + 1)
                if len(body) != member.size:
                    raise ValueError('Truncated archive member')
                files[name] = body
            else:
                raise ValueError(f'Archive links/devices refused: {name}')
    for name in set(files) | directories:
        if any(str(parent) in files for parent in PurePosixPath(name).parents):
            raise ValueError(f'Archive file/directory collision: {name}')
    if not files:
        raise ValueError('Empty archive')
    return files


def verify_recipe_members(members):
    if set(members) != set(MEMBERS):
        raise ValueError('Source archive member set differs from the three approved files')
    for name, (size, sha) in MEMBERS.items():
        if digest(members[name]) != {'bytes': size, 'sha256': sha}:
            raise ValueError(f'Source member hash mismatch: {name}')


def write_new(path, data):
    path = Path(os.path.abspath(path))
    # Check each ancestor before creating descendants, including on failure.
    for parent in reversed(path.parents):
        if not os.path.lexists(parent):
            parent.mkdir()
        if not stat.S_ISDIR(_reject_link(parent).st_mode):
            raise ValueError(f'Non-directory output ancestor: {parent}')
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, value):
    write_new(path, (json.dumps(value, indent=2, sort_keys=True) + '\n').encode())


def materialize(archive, output, zstd='zstd'):
    archive, output = checked_parents(archive), checked_parents(output)
    if os.path.lexists(output):
        raise FileExistsError(f'Output already exists: {output}')
    with _regular_stream(archive) as stream:
        compressed = stream.read(ARCHIVE_SIZE + 1)
    if digest(compressed) != {'bytes': ARCHIVE_SIZE, 'sha256': ARCHIVE_SHA}:
        raise ValueError('Exact libdatrie source archive hash/size mismatch')
    # Digest is checked before invoking the decoder. Its input is the bounded
    # in-memory verified snapshot, never a subsequently replaceable pathname.
    decoded = subprocess.run([zstd, '-dc'], input=compressed, capture_output=True, check=True, timeout=30).stdout
    recipe = read_tar(decoded, 'mingw-w64-libdatrie', max_bytes=512 * 1024)
    verify_recipe_members(recipe)
    decoder = lzma.LZMADecompressor(memlimit=64 * 1024 * 1024)
    upstream_tar = decoder.decompress(recipe['mingw-w64-libdatrie/libdatrie-0.2.14.tar.xz'], max_length=16 * 1024 * 1024 + 1)
    if not decoder.eof or decoder.unused_data or len(upstream_tar) > 16 * 1024 * 1024:
        raise ValueError('Upstream decompression bound/trailing data')
    upstream = read_tar(upstream_tar, 'libdatrie-0.2.14')
    if hashlib.sha256(upstream['libdatrie-0.2.14/COPYING']).hexdigest() != COPYING_SHA:
        raise ValueError('Original COPYING differs')
    outputs = {'recipe/' + name.split('/', 1)[1]: data for name, data in recipe.items()}
    outputs.update({'upstream/' + name: data for name, data in upstream.items()})
    receipt = {
        'schemaVersion': 1,
        'purpose': 'libdatrie-source-rebuild-proof',
        'archive': digest(compressed),
        'sourceUrl': 'https://mirror.msys2.org/mingw/sources/mingw-w64-libdatrie-0.2.14-1.src.tar.zst',
        'publishedCollection': 'https://github.com/hashfunction/pixelquay/releases/tag/native-sources-2026-09-11-c9f4add',
        'files': {name: digest(body) for name, body in sorted(outputs.items())},
        'executedRecipe': False,
        'licenseConversionApplied': False,
    }
    output.mkdir()
    # On interruption, preserve the owned partial tree for diagnosis; never
    # recursively remove a path that could since have been replaced by a caller.
    for name, body in outputs.items():
        write_new(output / name, body)
    write_json(output / 'source-receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--zstd', default='zstd')
    args = parser.parse_args()
    materialize(args.archive, args.output, args.zstd)
    print('Verified libdatrie source and original COPYING; no recipe executed.')


if __name__ == '__main__':
    main()
