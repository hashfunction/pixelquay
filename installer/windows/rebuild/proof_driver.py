#!/usr/bin/env python3
"""Build preparation/evidence for the isolated Windows libdatrie proof. MIT."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile

from libdatrie_source import materialize, digest, checked_parents, write_new, write_json, _regular_stream, _checked_path
from library_receipt import SELECTED_ARCHIVE_HASHES, SELECTED_PACKAGES, COPYING_SHA, UPSTREAM_TESTS, pe_inventory, read_upstream_tests, validate_environment, validate_pair

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2]


def capture(*args):
    return subprocess.run([str(a) for a in args], check=True, capture_output=True, text=True, encoding='utf-8', timeout=120).stdout.strip()


def file_record(path):
    with _regular_stream(path) as stream:
        value = stream.read()
    return digest(value)


def verify_post_test_library(library, retained_hash):
    """Bind the check() receipt to the same pre-package build DLL it hashed."""
    with _regular_stream(retained_hash) as stream:
        tested_hash_bytes = stream.read(66)
    if len(tested_hash_bytes) > 65:
        raise ValueError('Oversized post-test library hash evidence')
    try:
        tested_library_hash = tested_hash_bytes.decode('ascii').strip()
    except UnicodeDecodeError as error:
        raise ValueError('Non-ASCII post-test library hash evidence') from error
    if not re.fullmatch(r'[0-9a-f]{64}', tested_library_hash):
        raise ValueError('Malformed post-test library hash evidence')
    record = file_record(library)
    if tested_library_hash != record['sha256']:
        raise ValueError('Retained post-test hash differs from the built library')
    return record


def source_state():
    sha = capture('git', '-C', SOURCE, 'rev-parse', 'HEAD')
    if capture('git', '-C', SOURCE, 'status', '--porcelain', '--untracked-files=all'):
        raise ValueError('Proof source must be a clean committed checkout')
    if os.environ.get('GITHUB_SHA') and sha != os.environ['GITHUB_SHA']:
        raise ValueError('Workflow source commit does not match checkout')
    return sha


def tracked_inputs():
    rows = {}
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            rows[path.relative_to(SOURCE).as_posix()] = file_record(path)
    return rows


def prepare(work, evidence):
    work, evidence = checked_parents(work), checked_parents(evidence)
    if os.path.lexists(work) or os.path.lexists(evidence):
        raise FileExistsError('Fresh work and evidence directories required')
    commit = source_state()
    inputs = tracked_inputs()
    work.mkdir(); evidence.mkdir()
    original_source = materialize(HERE / 'inputs/mingw-w64-libdatrie-0.2.14-1.src.tar.zst', work / 'source')
    for variant in ('original', 'modified'):
        root = work / variant
        root.mkdir()
        write_new(root / 'PKGBUILD', (HERE / 'recipes' / variant / 'PKGBUILD').read_bytes())
        write_new(root / 'libdatrie-0.2.14.tar.xz', (work / 'source/recipe/libdatrie-0.2.14.tar.xz').read_bytes())
        write_new(root / '002-windows-alpha-test-data.patch', (HERE / '002-windows-alpha-test-data.patch').read_bytes())
        if variant == 'modified': write_new(root / '001-local-marker.patch', (HERE / '001-local-marker.patch').read_bytes())
        (root / 'packages').mkdir(); (root / 'probe-work').mkdir(); (root / 'negative-probe-work').mkdir()
    write_json(evidence / 'inputs.json', {'sourceCommit': commit, 'inputs': inputs, 'sourceReceipt': original_source})


def preserve_failed_test_logs(build_root, evidence, variant):
    """Copy exact Automake test diagnostics before a failed runner is discarded."""
    if variant not in ('original', 'modified'):
        raise ValueError('Unknown libdatrie proof variant')
    tests = Path(build_root) / 'tests'
    names = ['test-suite.log']
    for name in UPSTREAM_TESTS:
        names.extend((name + '.log', name + '.trs'))
    bodies = {}
    for name in names:
        with _regular_stream(tests / name) as stream:
            body = stream.read(2 * 1024 * 1024 + 1)
        if len(body) > 2 * 1024 * 1024:
            raise ValueError(f'Oversized failed test diagnostic: {name}')
        bodies[name] = body
    outputs = {
        name: checked_parents(Path(evidence) / f'{variant}-{name}.txt') for name in names
    }
    if any(os.path.lexists(path) for path in outputs.values()):
        raise FileExistsError('Failed test evidence already exists and will not be replaced')
    for name in names:
        write_new(outputs[name], bodies[name])
    return {'variant': variant, 'files': names}


def package_versions(text):
    result = {}
    for line in text.splitlines():
        name, version = line.split()
        if name in result: raise ValueError('Duplicate installed package')
        result[name] = version
    return result


def environment(msys, output):
    msys = Path(msys).resolve()
    prefix = msys / 'clang64'
    tools = {}
    names = {
        'clang': prefix / 'bin/clang.exe', 'lld': prefix / 'bin/ld.lld.exe',
        'llvm-readobj': prefix / 'bin/llvm-readobj.exe', 'python': Path(sys.executable),
        'make': msys / 'usr/bin/make.exe', 'makepkg': msys / 'usr/bin/makepkg',
        'makepkg-mingw': msys / 'usr/bin/makepkg-mingw', 'bash': msys / 'usr/bin/bash.exe',
        'patch': msys / 'usr/bin/patch.exe', 'zstd': msys / 'usr/bin/zstd.exe',
    }
    for name, path in names.items():
        if not path.is_file(): raise ValueError(f'Missing build tool: {path}')
        tools[name] = {'path': str(path), **file_record(path)}
    packages = package_versions(capture(msys / 'usr/bin/pacman.exe', '-Q'))
    configs = {}
    for candidate in sorted((msys / 'etc').glob('makepkg*')):
        files = candidate.rglob('*') if candidate.is_dir() else [candidate]
        for path in files:
            if path.is_file():
                key = path.relative_to(msys).as_posix()
                with _regular_stream(path) as stream: body = stream.read()
                configs[key] = {'content': body.decode('utf-8'), **digest(body)}
    if not {'etc/makepkg.conf', 'etc/makepkg_mingw.conf'} <= set(configs):
        raise ValueError('Required makepkg configurations not recorded')
    value = {'packages': packages, 'tools': tools, 'configs': configs,
             'compilerVersion': capture(names['clang'], '--version'),
             'compilerSearch': capture(names['clang'], '-print-search-dirs'),
             'compilerResources': capture(names['clang'], '-print-resource-dir'),
             'msystem': os.environ.get('MSYSTEM'), 'mingwPrefix': str(prefix), 'msysRoot': str(msys),
             'configuredEnvironment': {k: os.environ.get(k) for k in ('CFLAGS', 'CPPFLAGS', 'CXXFLAGS', 'LDFLAGS', 'LANG', 'LC_ALL', 'SOURCE_DATE_EPOCH')}}
    if value['msystem'] != 'CLANG64': raise ValueError('Requires current CLANG64 environment')
    validate_environment(value, value)
    write_json(output, value)


def verify_archive_inputs(cache, before, output):
    packages, rows, contents = {}, [], {}
    msys = Path(before['msysRoot'])
    required = {Path(row['path']).relative_to(msys).as_posix() for row in before['tools'].values()} | set(before['configs'])
    for path in sorted(Path(cache).glob('*.pkg.tar.zst')):
        identity = capture('pacman', '-Qp', path).split()
        if len(identity) != 2 or identity[0] in packages: raise ValueError('Duplicate/malformed cached package')
        name, version = identity
        record = file_record(path)
        if name in SELECTED_ARCHIVE_HASHES and record['sha256'] != SELECTED_ARCHIVE_HASHES[name]:
            raise ValueError(f'Selected package archive hash mismatch: {name}')
        packages[name] = version
        rows.append({'name': name, 'version': version, 'archive': path.name, **record})
        for member, value in archive_hashes(path).items():
            if member not in required: continue
            # Different packages can carry matching directory metadata; regular
            # file ownership must not conflict in the recorded build inputs.
            if member in contents and contents[member] != value:
                raise ValueError(f'Conflicting cached package file: {member}')
            contents[member] = value
    if packages != before['packages']:
        raise ValueError('Downloaded package archive set/versions differ from recorded environment')
    validate_archived_tools(before, contents)
    result = {'schemaVersion': 1, 'packages': rows, 'allInstalledPackageArchivesRecorded': True,
              'actualToolAndConfigurationBytesMatchedArchives': True,
              'matchedToolAndConfigurationFiles': {name: contents[name] for name in sorted(required)}}
    write_json(output, result)
    return result


def archive_hashes(path):
    """Hash archive data without extracting/executing, consuming zstd to EOF."""
    process = subprocess.Popen(['zstd', '-dc', str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    values, links, seen = {}, {}, set()
    total = 0
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            for index, member in enumerate(archive):
                name = member.name.rstrip('/')
                _checked_path(name)
                if index > 500000 or name in seen: raise ValueError('Duplicate/unbounded input archive')
                seen.add(name); total += member.size
                if member.size < 0 or total > 2 * 1024**3: raise ValueError('Input archive expanded byte bound')
                if member.isreg():
                    hasher = hashlib.sha256(); size = 0
                    with archive.extractfile(member) as stream:
                        while chunk := stream.read(1024 * 1024): hasher.update(chunk); size += len(chunk)
                    if size != member.size: raise ValueError('Truncated input archive member')
                    values[name] = {'bytes': size, 'sha256': hasher.hexdigest()}
                elif member.islnk():
                    _checked_path(member.linkname)
                    links[name] = member.linkname
                # Symbolic links and directories are never materialized and
                # cannot establish a regular tool/configuration byte match.
        drain_padding(process.stdout)
        process.stdout.close(); stderr = process.stderr.read()
        if process.wait(timeout=30): raise ValueError(f'Input archive decode failed: {stderr.decode(errors="replace")}')
    finally:
        if process.poll() is None: process.kill(); process.wait()
        process.stdout.close(); process.stderr.close()
    while links:
        resolved = [name for name, target in links.items() if target in values]
        if not resolved: raise ValueError('Unresolved/cyclic archive hardlink')
        for name in resolved: values[name] = values[links.pop(name)]
    return values


def drain_padding(stream):
    # tarfile stops at its end marker. Consume bounded tar padding so an early
    # pipe close cannot be mistaken for a zstd/archive failure (SIGPIPE).
    total = 0
    while chunk := stream.read(65536):
        total += len(chunk)
        if total > 1024 * 1024 or any(chunk):
            raise ValueError('Unexpected bytes after tar end marker')


def validate_archived_tools(before, archive_files):
    root = Path(before['msysRoot'])
    expected = {Path(row['path']).relative_to(root).as_posix(): row for row in before['tools'].values()}
    expected.update(before['configs'])
    for name, row in expected.items():
        if archive_files.get(name) != {key: row[key] for key in ('bytes', 'sha256')}:
            raise ValueError(f'Installed tool/configuration differs from package archive: {name}')
    return True


def read_package(path, dll_path):
    process = subprocess.Popen(['zstd', '-dc', str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wanted = {'.PKGINFO', '.BUILDINFO', 'clang64/bin/libdatrie-1.dll', 'clang64/share/licenses/libdatrie/COPYING'}
    found = {}; seen = set(); total = 0
    try:
        with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
            for index, member in enumerate(archive):
                name = member.name.rstrip('/')
                _checked_path(name)
                if index > 4096 or name in seen: raise ValueError('Unbounded/duplicate package entries')
                seen.add(name); total += member.size
                if total > 64 * 1024 * 1024: raise ValueError('Package exceeds proof bound')
                if name in wanted:
                    if not member.isreg() or member.size > 8 * 1024 * 1024: raise ValueError('Expected regular bounded package member')
                    found[name] = archive.extractfile(member).read()
        drain_padding(process.stdout)
        process.stdout.close()
        error = process.stderr.read()
        if process.wait(timeout=30): raise ValueError(f'Package decompression failed: {error.decode(errors="replace")}')
    finally:
        if process.poll() is None: process.kill(); process.wait()
        process.stdout.close(); process.stderr.close()
    if set(found) != wanted: raise ValueError('Missing package metadata/DLL/COPYING')
    if digest(found['clang64/bin/libdatrie-1.dll']) != file_record(dll_path):
        raise ValueError('Staged DLL differs from actual package archive')
    if hashlib.sha256(found['clang64/share/licenses/libdatrie/COPYING']).hexdigest() != COPYING_SHA:
        raise ValueError('Packaged original COPYING differs')
    return found


def verify(work, evidence):
    inputs = json.loads((evidence / 'inputs.json').read_text())
    if inputs['sourceCommit'] != source_state() or inputs['inputs'] != tracked_inputs():
        raise ValueError('Proof source or tracked inputs changed during builds')
    before = json.loads((evidence / 'environment-before.json').read_text())
    after = json.loads((evidence / 'environment-after.json').read_text())
    validate_environment(before, after)
    final_archives = verify_archive_inputs(work / 'package-cache', before, evidence / 'package-inputs.json')
    if final_archives != json.loads((evidence / 'package-inputs-before.json').read_text()):
        raise ValueError('Cached package archive inputs changed during builds')
    results = {}
    for variant, version in [('original', '0.2.14-1'), ('modified', '0.2.14-1.1')]:
        root = work / variant
        package_name = 'mingw-w64-clang-x86_64-libdatrie'
        packages = list((root / 'packages').glob(package_name + '-[0-9]*.pkg.tar.zst'))
        if len(packages) != 1: raise ValueError('Expected one exact runtime package per variant')
        dll = root / 'pkg' / package_name / 'clang64/bin/libdatrie-1.dll'
        members = read_package(packages[0], dll)
        pkginfo = members['.PKGINFO'].decode(); buildinfo = members['.BUILDINFO'].decode()
        for line in [f'pkgname = {package_name}', f'pkgver = {version}', 'license = LGPL']:
            if line not in pkginfo.splitlines(): raise ValueError(f'Wrong runtime package identity: {line}')
        if 'pkgbuild_sha256sum = ' + file_record(root / 'PKGBUILD')['sha256'] not in buildinfo.splitlines():
            raise ValueError('Actual package does not bind the local build recipe')
        probe = json.loads((evidence / (variant + '-probe.json')).read_text())
        build = root / 'src/build-CLANG64'
        tested_build_library = verify_post_test_library(
            build / 'datrie/.libs/libdatrie-1.dll',
            build / 'library-unchanged-by-tests.sha256',
        )
        results[variant] = {
            **file_record(dll), **pe_inventory(dll.read_bytes()), 'upstreamTests': read_upstream_tests(build / 'tests'),
            'probe': probe, 'copyingSha256': hashlib.sha256(members['clang64/share/licenses/libdatrie/COPYING']).hexdigest(),
            'libraryUnchangedByTests': True, 'testedBuildLibrary': tested_build_library,
            'package': {'name': packages[0].name, **file_record(packages[0])},
            'sourceFiles': {p.relative_to(root / 'src/libdatrie-0.2.14').as_posix(): file_record(p) for p in sorted((root / 'src/libdatrie-0.2.14').rglob('*')) if p.is_file()},
        }
        for name, content in [('.PKGINFO', pkginfo), ('.BUILDINFO', buildinfo)]:
            write_new(evidence / (variant + '-' + name[1:] + '.txt'), content.encode())
        for name in ('config.log', 'libdatrie-link.map'):
            write_new(evidence / (variant + '-' + name + '.txt'), (build / name).read_bytes())
        for path in sorted((build / 'tests').glob('*.trs')):
            write_new(evidence / (variant + '-' + path.name + '.txt'), path.read_bytes())
    expected = (work / 'source/upstream/libdatrie-0.2.14/datrie/libdatrie.def').read_text().split()
    validate_pair(results['original'], results['modified'], expected)
    write_json(evidence / 'library-proof.json', {
        'schemaVersion': 1, 'sourceCommit': inputs['sourceCommit'], 'variants': results,
        'environmentUnchanged': True, 'nativeLibraryReplacementProof': True,
        'historicalBinaryParityClaimed': False, 'licenseConversionApplied': False,
        'applicationReplacementVerified': False, 'msixBuilt': False, 'licenseClearanceClaimed': False,
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'operation',
        choices=['prepare', 'environment', 'archives', 'preserve-failed-tests', 'verify'],
    )
    parser.add_argument('--work', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--msys', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--variant')
    args = parser.parse_args()
    if sys.platform != 'win32': parser.error('Native Windows proof requires Windows; portable source/tests use separate entry points')
    if args.operation == 'prepare': prepare(args.work, args.evidence)
    elif args.operation == 'environment': environment(args.msys, args.output)
    elif args.operation == 'archives':
        before = json.loads((args.evidence / 'environment-before.json').read_text())
        verify_archive_inputs(args.work / 'package-cache', before, args.evidence / 'package-inputs-before.json')
    elif args.operation == 'preserve-failed-tests':
        preserve_failed_test_logs(args.work, args.evidence, args.variant)
    else: verify(args.work, args.evidence)


if __name__ == '__main__': main()
