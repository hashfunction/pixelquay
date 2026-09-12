"""Verify ordinary installed image/recipe operations without loading product code.

Copyright 2026 Trieflow LLC. MIT licensed. Only the qualification process writes
fixtures; application outputs and settings are always read independently.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat
import re
import struct
import uuid
import xml.etree.ElementTree as ET
import zlib

from msix_qualification import _png_chunks, _chunk

MARKER = '.pixelquay-consumer-owner'
RECIPE_NAME = 'Consumer proof 32x48'
COLORS = ((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255), (255, 255, 0, 255))


def fixture_image(width=96, height=64):
    return width, height, [[COLORS[(y >= height // 2) * 2 + (x >= width // 2)] for x in range(width)] for y in range(height)]


def encode_png(image, rgb=False):
    width, height, rows = image
    raw = b''.join(b'\0' + bytes(channel for pixel in row for channel in pixel[:3 if rgb else 4]) for row in rows)
    return b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2 if rgb else 6, 0, 0, 0)) + _chunk(b'IDAT', zlib.compress(raw)) + _chunk(b'IEND', b'')


def decode_png(data):
    if len(data) > 1024 * 1024:
        raise ValueError('PNG exceeds fixture byte bound')
    chunks = list(_png_chunks(data))
    if not chunks or chunks[0][0] != b'IHDR' or len(chunks[0][1]) != 13 or sum(k == b'IHDR' for k, _ in chunks) != 1:
        raise ValueError('Invalid PNG header')
    w, h, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', chunks[0][1])
    if not (0 < w <= 128 and 0 < h <= 128 and depth == 8 and color in (2, 6) and compression == filtering == interlace == 0):
        raise ValueError('Unexpected PNG dimensions or encoding')
    channels = 3 if color == 2 else 4
    stride = w * channels
    limit = (stride + 1) * h
    decoder = zlib.decompressobj()
    raw = decoder.decompress(b''.join(body for kind, body in chunks if kind == b'IDAT'), limit + 1)
    if len(raw) != limit or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError('Unexpected PNG decompression size or tail')
    result, prior = [], bytearray(stride)
    for y in range(h):
        start = y * (stride + 1)
        mode = raw[start]
        if mode > 4:
            raise ValueError('Invalid PNG filter')
        row = bytearray(stride)
        for x, value in enumerate(raw[start + 1:start + stride + 1]):
            a = row[x - channels] if x >= channels else 0
            b = prior[x]
            c = prior[x - channels] if x >= channels else 0
            p = a + b - c
            da, db, dc = abs(p-a), abs(p-b), abs(p-c)
            paeth = a if da <= db and da <= dc else b if db <= dc else c
            prediction = (0, a, b, (a+b)//2, paeth)[mode]
            row[x] = (value + prediction) & 255
        result.append([tuple(row[x:x+channels]) + (() if channels == 4 else (255,)) for x in range(0, stride, channels)])
        prior = row
    return w, h, result


def rotate_clockwise(image):
    w, h, rows = image
    return h, w, [[rows[h-1-x][y] for x in range(h)] for y in range(w)]


def no_links(path):
    path = Path(path)
    for candidate in (path, *path.parents):
        if candidate.exists() or candidate.is_symlink():
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                raise ValueError('Refused link or reparse point')


def snapshot(root):
    root = Path(root)
    no_links(root)
    result = {}
    total = 0
    paths = []
    for path in root.rglob('*'):
        paths.append(path)
        if len(paths) > 512:
            raise ValueError('Owned tree exceeds bounded inventory')
    for path in paths:
        no_links(path)
        if path.is_dir():
            result[path.relative_to(root).as_posix() + '/'] = dict(directory=True)
            continue
        if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
            raise ValueError('Owned tree has an unsupported file')
        total += path.stat().st_size
        if total > 32 * 1024 * 1024:
            raise ValueError('Owned tree exceeds total byte bound')
        data = path.read_bytes()
        result[path.relative_to(root).as_posix()] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    return result


def require_snapshot(root, expected):
    actual = snapshot(root)
    if set(actual) != set(expected):
        unexpected = sorted(set(actual) ^ set(expected))[:16]
        raise ValueError('Owned tree has unexpected or missing files: ' + repr(unexpected))
    if actual != expected:
        raise ValueError('Owned file bytes changed')


def create(root, profile):
    root, profile = Path(root).absolute(), Path(profile).absolute()
    for path in (root, profile):
        no_links(path)
        if path.exists():
            raise ValueError('Existing fixture/profile must be preserved')
    if root == profile or root in profile.parents or profile in root.parents:
        raise ValueError('Fixture and profile must be separate owned trees')
    token = uuid.uuid4().hex
    made = []
    try:
        for path in (root, profile):
            path.mkdir()
            made.append(path)
            with (path / MARKER).open('x', encoding='ascii') as marker:
                marker.write(token)
        with (root / 'source.png').open('xb') as source:
            source.write(encode_png(fixture_image()))
        return dict(root=str(root), profile=str(profile), token=token, files=snapshot(root), profile_files=snapshot(profile), stages={})
    except Exception:
        for path in reversed(made):
            children = list(path.iterdir())
            if children == [path / MARKER] and children[0].read_text() == token:
                children[0].unlink()
                path.rmdir()
        raise


def verify_stage(state, stage):
    if stage not in ('edited', 'exported', 'reopened'):
        raise ValueError('Unknown consumer stage')
    root = Path(state['root'])
    name = dict(edited='edited.png', exported='edited-proof.png', reopened='reopened.png')[stage]
    known = {k: v for k, v in state['files'].items() if k != name}
    actual = snapshot(root)
    if set(actual) != set(known) | {name}:
        raise ValueError('Unexpected files, missing output, or staging leftovers')
    if {k: actual[k] for k in known} != known:
        raise ValueError('Previously verified source/output bytes changed')
    image = decode_png((root / name).read_bytes())
    if stage == 'edited':
        expected = rotate_clockwise(fixture_image())
    elif stage == 'reopened':
        if 'exported' not in state['stages']:
            raise ValueError('Export must be verified before reopening')
        expected = rotate_clockwise(decode_png((root / 'edited-proof.png').read_bytes()))
    else:
        if 'edited' not in state['stages']:
            raise ValueError('Edited image must be verified before exporting')
        expected = rotate_clockwise(fixture_image(48, 32))
    if image[:2] != expected[:2]:
        raise ValueError('Output dimensions differ')
    checked = 0
    for y in range(image[1]):
        for x in range(image[0]):
            pixel = image[2][y][x]
            if pixel[3] != 255:
                raise ValueError('Output unexpectedly contains transparency')
            # Bilinear resizing may mix the two adjacent rows/columns at a
            # quadrant boundary. Every other pixel must keep its exact color.
            if stage == 'exported' and (abs(x - image[0]//2) <= 1 or abs(y - image[1]//2) <= 1):
                continue
            if pixel != expected[2][y][x]:
                raise ValueError('Output pixels differ from the independent operation')
            checked += 1
    state['files'][name] = actual[name]
    state['stages'][stage] = dict(width=image[0], height=image[1], checked_pixels=checked, **actual[name])
    return state['stages'][stage]


def seal_profile(state, initial=False):
    profile = Path(state['profile'])
    no_links(profile / MARKER)
    if (profile / MARKER).stat().st_size != 32 or (profile / MARKER).read_text(encoding='ascii') != state['token']:
        raise ValueError('Profile marker changed')
    actual = snapshot(profile)
    for relative in actual:
        if relative not in (MARKER, 'settings.xml', 'palette.txt') and not relative.startswith('addins/'):
            raise ValueError('Profile has unexpected files')
    if not initial:
        baseline = state['profile_files']
        for relative in set(actual) | set(baseline):
            if relative not in ('settings.xml', 'palette.txt') and actual.get(relative) != baseline.get(relative):
                raise ValueError('Baseline profile bytes changed unexpectedly')
    state['profile_files'] = actual


def finish(state, stopped):
    if not stopped:
        raise ValueError('All owned processes must be proven normally stopped before settings are read')
    if set(state['stages']) != {'edited', 'exported', 'reopened'}:
        raise ValueError('Consumer image stages are incomplete')
    require_snapshot(state['root'], state['files'])
    profile = Path(state['profile'])
    no_links(profile / 'settings.xml')
    if (profile / 'settings.xml').stat().st_size > 1024 * 1024:
        raise ValueError('Settings exceed bound')
    settings = ET.fromstring((profile / 'settings.xml').read_bytes())
    if settings.tag != 'settings':
        raise ValueError('Unexpected settings document')
    values = settings.findall("setting[@name='pixelquay.export-recipes.v1']")
    if len(values) != 1 or values[0].get('type') != 'System.String':
        raise ValueError('Saved recipe setting is missing or ambiguous')
    envelope = json.loads(values[0].text or '')
    recipes = envelope.get('Recipes')
    if set(envelope) != {'Version', 'Recipes'} or type(envelope.get('Version')) is not int or envelope['Version'] != 1 or not isinstance(recipes, list) or len(recipes) != 1:
        raise ValueError('Saved recipe envelope differs')
    recipe = recipes[0]
    expected = dict(Name=RECIPE_NAME, Width=32, Height=48, Extension='png', Quality=None, Suffix='-proof', Overwrite=False)
    if not isinstance(recipe, dict) or set(recipe) != set(expected) | {'Id'} or not isinstance(recipe['Id'], str) or not re.fullmatch(r'[0-9a-f]{32}', recipe['Id']) or any(type(recipe[k]) is not type(v) or recipe[k] != v for k, v in expected.items()):
        raise ValueError('Saved recipe fields differ')
    seal_profile(state)
    return dict(recipe=recipe, images=state['stages'], source_unchanged=True, profile_files=state['profile_files'])


def cleanup(state, stopped):
    if not stopped:
        raise ValueError('All owned processes must be proven stopped before cleanup')
    for root, expected in ((state['root'], state['files']), (state['profile'], state['profile_files'])):
        require_snapshot(root, expected)
        if (Path(root) / MARKER).read_text(encoding='ascii') != state['token']:
            raise ValueError('Ownership marker changed')
    # Validate both complete trees before deleting either. Recheck each file
    # immediately before removal; refuse changed/unexpected entries.
    for root, expected in ((state['root'], state['files']), (state['profile'], state['profile_files'])):
        root = Path(root)
        require_snapshot(root, expected)
        for relative in expected:
            if relative.endswith('/'):
                continue
            path = root / relative
            no_links(path)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected[relative]['sha256']:
                raise ValueError('Owned file changed during cleanup')
            path.unlink()
        for directory in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            no_links(directory)
            directory.rmdir()
        root.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('create', 'baseline', 'edited', 'exported', 'reopened', 'finish', 'cleanup'))
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--root', type=Path)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--stopped', action='store_true')
    args = parser.parse_args()
    if args.operation == 'create':
        if args.state.exists() or not args.root or not args.profile:
            raise ValueError('New state and explicit fixture/profile paths are required')
        state = create(args.root, args.profile)
        result = state
    else:
        state = json.loads(args.state.read_text(encoding='utf-8'))
        if args.operation == 'cleanup':
            cleanup(state, args.stopped)
            state['cleanup_removed'] = True
            result = dict(removed=True)
        elif args.operation == 'finish':
            result = finish(state, args.stopped)
        elif args.operation == 'baseline':
            if not args.stopped:
                raise ValueError('Diagnostic process must be normally stopped before profile baseline')
            seal_profile(state, initial=True)
            result = dict(profile_baseline=state['profile_files'])
        else:
            result = verify_stage(state, args.operation)
    with args.state.open('x' if args.operation == 'create' else 'w', encoding='utf-8') as output:
        output.write(json.dumps(state, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
