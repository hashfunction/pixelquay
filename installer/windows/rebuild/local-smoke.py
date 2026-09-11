#!/usr/bin/env python3
"""Repeat the actual macOS source/patch/API checks; does not qualify Windows.

Copyright 2026 Trieflow LLC. MIT licensed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from libdatrie_source import materialize, checked_parents, write_new, write_json, digest, COPYING_SHA
from library_receipt import read_upstream_tests

HERE = Path(__file__).resolve().parent


def run(args, cwd, log):
    with log.open('xb') as stream:
        subprocess.run([str(a) for a in args], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=600)


def smoke(work, evidence):
    if sys.platform != 'darwin': raise ValueError('This host smoke uses macOS clang/nm; Windows uses prove-windows.sh')
    work, evidence = checked_parents(work), checked_parents(evidence)
    if os.path.lexists(work) or os.path.lexists(evidence): raise FileExistsError('New work/evidence directories required')
    work.mkdir(); evidence.mkdir()
    source = materialize(HERE / 'inputs/mingw-w64-libdatrie-0.2.14-1.src.tar.zst', work / 'source')
    upstream = work / 'source/upstream/libdatrie-0.2.14'
    expected_exports = set((upstream / 'datrie/libdatrie.def').read_text().split())
    probe = work / 'datrie_probe'
    run(['/usr/bin/clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I'+str(upstream), HERE / 'datrie_probe.c', '-o', probe], work, evidence / 'probe-compile.txt')
    results = {}
    for variant in ('original', 'modified'):
        root = work / variant; root.mkdir()
        tree, build = root / 'source', root / 'build'
        shutil.copytree(upstream, tree); build.mkdir()
        if variant == 'modified':
            run(['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i', HERE / '001-local-marker.patch'], tree, evidence / 'patch.txt')
        # Darwin libtool prefixes every raw -export-symbols line with '_'; it
        # cannot consume Windows DEF semicolon comments. Preserve the noticed
        # source, and derive an owned symbol-only host linker input explicitly.
        names = [line.strip() for line in (tree / 'datrie/libdatrie.def').read_text().splitlines() if line.strip() and not line.lstrip().startswith(';')]
        if any(not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name) for name in names):
            raise ValueError('Unsupported DEF export syntax in host adapter')
        if len(names) != len(set(names)): raise ValueError('Duplicate DEF export in host adapter')
        host_exports = build / 'host-export-symbols.txt'
        write_new(host_exports, ('\n'.join(names) + '\n').encode())
        make_exports = 'EXPORTS_FLAGS=-export-symbols ' + str(host_exports)
        run(['sh', tree / 'configure', '--disable-doxygen-doc', '--prefix='+str(root / 'install')], build, evidence / (variant+'-configure.txt'))
        run(['make', '-j2', make_exports], build, evidence / (variant+'-build.txt'))
        run(['make', 'check', make_exports], build, evidence / (variant+'-tests.txt'))
        # The real Mach-O target behind its version symlinks is supplied to dlopen.
        libraries = {path.resolve() for path in (build / 'datrie/.libs').glob('libdatrie.*.dylib')}
        if len(libraries) != 1: raise ValueError('Expected one built dylib')
        library = libraries.pop()
        symbols = subprocess.check_output(['/usr/bin/nm', '-gUj', library], text=True).split()
        exports = {name.removeprefix('_') for name in symbols}
        expected = expected_exports | ({'pixelquay_rebuild_marker'} if variant == 'modified' else set())
        if exports != expected: raise ValueError('Actual Mach-O exports differ from source ABI')
        proof_work = root / 'probe-work'; proof_work.mkdir()
        positive = subprocess.run([probe, library, variant, proof_work], capture_output=True, text=True, timeout=30)
        if positive.returncode: raise ValueError(positive.stderr)
        value = json.loads(positive.stdout)
        if value != {'schemaVersion': 1, 'mode': variant, 'apiChecks': 21, 'libraryPathMatched': True, 'markerPresent': variant == 'modified'}:
            raise ValueError('Probe result incomplete')
        wrong = 'original' if variant == 'modified' else 'modified'
        negative = subprocess.run([probe, library, wrong, proof_work], capture_output=True, text=True, timeout=30)
        if negative.returncode != 4: raise ValueError('Wrong-variant marker rejection did not occur')
        sentinel = root / 'sentinel'; sentinel.mkdir(); (sentinel / 'probe.trie').write_bytes(b'previous output')
        existing = subprocess.run([probe, library, variant, sentinel], capture_output=True, text=True, timeout=30)
        if existing.returncode != 5 or (sentinel / 'probe.trie').read_bytes() != b'previous output':
            raise ValueError('Probe overwrote an existing output')
        if hashlib.sha256((tree / 'COPYING').read_bytes()).hexdigest() != COPYING_SHA: raise ValueError('COPYING changed')
        results[variant] = {**digest(library.read_bytes()), 'exports': sorted(exports), 'probe': value,
                            'hostExportSymbols': digest(host_exports.read_bytes()),
                            'upstreamTests': read_upstream_tests(build / 'tests'),
                            'wrongVariantExit': negative.returncode, 'existingOutputExit': existing.returncode}
    if results['original']['sha256'] == results['modified']['sha256']: raise ValueError('Modification did not change library bytes')
    write_json(evidence / 'local-smoke.json', {'schemaVersion': 1, 'host': 'macOS', 'variants': results,
               'sourceArchive': source['archive'], 'windowsProof': False, 'applicationReplacementVerified': False,
               'licenseConversionApplied': False, 'msixBuilt': False})
    print('Both host libraries: 10 upstream tests and 21 API checks each; negative controls passed. Windows proof pending.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    smoke(args.work, args.evidence)
