# Copyright 2026 Trieflow LLC. MIT.
"""Bind reviewed native sources and the exact current public application tree."""
import hashlib
import json
import re
import subprocess
import tarfile
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from msix_qualification import file_record, _regular_stream

SOURCE_PAGE = 'https://tintfable.trieflow.com/source'
RELEASE_URL = 'https://github.com/hashfunction/pixelquay/releases/tag/native-sources-2026-09-12-tintfable'
DOWNLOAD_ROOT = RELEASE_URL.replace('/tag/', '/download/') + '/'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def utc(value):
    require(isinstance(value, str), 'Missing UTC publication verification time')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0, 'Verification time must be UTC')
    except ValueError as error:
        raise ValueError('Invalid UTC publication verification time') from error



def download(url, destination, limit):
    """Unauthenticated HTTPS bytes, bounded in size and time; never reuse HEAD metadata."""
    require(urlsplit(url).scheme == 'https', 'Source download requires HTTPS')
    started = time.monotonic()
    digest = hashlib.sha256(); size = 0
    with urlopen(Request(url, headers={'User-Agent': 'TintFable-source-verification'}), timeout=30) as response:
        require(response.status == 200 and urlsplit(response.url).scheme == 'https', 'Anonymous source download failed')
        with destination.open('xb') as target:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                require(size <= limit and time.monotonic() - started < 180, 'Source download exceeded bound')
                target.write(chunk); digest.update(chunk)
        final_url = response.url
    return dict(url=url, final_url=final_url, bytes=size, sha256=digest.hexdigest(),
                verified_at_utc=datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))


def git(source, *arguments):
    return subprocess.check_output(['git', '-C', str(source), *arguments], timeout=30)


def verify_application_archive(archive, source, commit):
    require(re.fullmatch('[0-9a-f]{40}', commit or ''), 'Current source needs an exact Git commit')
    expected = {}
    for row in git(source, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0'):
        if not row: continue
        metadata, raw_name = row.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split(' ')
        require(kind == 'blob' and mode in ('100644', '100755', '120000'), 'Unsupported source tree entry')
        expected[raw_name.decode('utf-8')] = (mode, blob)
    seen = set(); prefix = None; total = 0
    with tarfile.open(archive, 'r:gz') as stream:
        for member in stream:
            parts = PurePosixPath(member.name).parts
            require(parts and not member.name.startswith('/') and '..' not in parts, 'Unsafe source archive path')
            prefix = prefix or parts[0]
            require(parts[0] == prefix, 'Source archive has multiple roots')
            if member.isdir(): continue
            name = '/'.join(parts[1:])
            require(name in expected and name not in seen, 'Missing, extra or duplicate source archive member')
            mode, blob = expected[name]
            if mode == '120000':
                require(member.issym(), 'Source archive symlink mode changed')
                data = member.linkname.encode('utf-8')
            else:
                require(member.isfile() and bool(member.mode & 0o111) == (mode == '100755'), 'Source file mode changed')
                require(0 <= member.size <= 64 * 1024 * 1024, 'Oversized application source member')
                data = stream.extractfile(member).read()
            total += len(data)
            require(total <= 256 * 1024 * 1024, 'Application source archive is too large')
            actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            require(actual == blob, 'Public application source bytes differ from Git: ' + name)
            seen.add(name)
    require(seen == set(expected) and bool(seen), 'Public application archive omits tracked source')
    return dict(source_commit=commit, git_tree=git(source, 'rev-parse', commit+'^{tree}').decode().strip(),
                verified_tracked_files=len(seen), verified_source_bytes=total)


def load(path):
    with _regular_stream(path) as stream:
        return json.load(stream)


def validate_publication(record, plan_path):
    plan = load(plan_path)
    require(record.get('schema_version') == 1 and record.get('product') == 'TintFable'
            and record.get('publication_verified') is True and record.get('source_page') == SOURCE_PAGE
            and record.get('release_url') == RELEASE_URL, 'Supplemental source publication is missing or unverified')
    utc(record.get('verified_at_utc'))
    expected = {row['filename']: {key: row[key] for key in ('bytes', 'sha256')} for row in plan['supplements']}
    require(len(expected) == len(plan['supplements']) == 2, 'Expected exact two reviewed source supplements')
    expected['source-supplements.json'] = file_record(plan_path)
    items = [record.get('manifest', {})] + record.get('assets', [])
    require(len(items) == 3 and {row.get('filename') for row in items} == set(expected), 'Missing/duplicate published source supplement')
    for row in items:
        name = row['filename']; final = urlsplit(row.get('final_url', ''))
        require(row.get('url') == DOWNLOAD_ROOT + name and all(row.get(key) == value for key, value in expected[name].items())
                and final.scheme == 'https' and bool(final.hostname) and not final.username and not final.password,
                'Supplement publication URL or bytes differ: ' + name)
        utc(row.get('verified_at_utc'))
    return plan


def validate_native_sources(source, evidence, record):
    """Reconcile actual current MSYS2 owners with retained exact source packages."""
    folder = source / 'installer/windows/source'
    delivery = load(folder / 'native-source-delivery.json'); baseline = load(folder / 'native-source-evidence.json')
    manifest = load(folder / 'source-manifest.json'); supplements = load(folder / 'source-supplements.json')
    original_url = 'https://github.com/hashfunction/pixelquay/releases/tag/native-sources-2026-09-11-c9f4add'
    require(delivery.get('releaseUrl') == original_url and delivery.get('sourceArchiveCount') == 63
            and delivery.get('sourceArchiveBytes') == 524235576 and baseline.get('binaryPackageOwners') == 64
            and file_record(folder / 'native-source-evidence.json')['sha256'] == delivery.get('sourceEvidenceSha256') == manifest.get('sourceEvidenceSha256'),
            'Original source collection binding differs')
    published = {row['name']: row for row in delivery['artifacts']}
    for name in ('pixelquay-native-sources-c9f4add.tar', 'source-manifest.json', 'SHA256SUMS'):
        row = published[name]
        require(row.get('unauthenticatedDownloadVerified') is True and row.get('url') == original_url.replace('/tag/', '/download/') + '/' + name,
                'Original source collection lacks exact public delivery evidence')
    require(file_record(folder / 'source-manifest.json') == {key: published['source-manifest.json'][key] for key in ('bytes', 'sha256')},
            'Original public source manifest changed')
    archive_rows = {row['filename']: row for row in baseline['sourceArchives']}
    require(len(archive_rows) == len(manifest['archives']) == 63, 'Original source archive set differs')
    for row in manifest['archives']:
        prior = archive_rows[PurePosixPath(row['archive']).name]
        require(all(row[key] == prior[key] for key in ('bytes', 'sha256', 'version')) and row['sourceUrl'] == prior['url'], 'Original source member changed')
    expected = {row['package']: dict(version=row['version'], licenses=row['declaredLicenses'],
                binary=PurePosixPath(row['packageArchive']).name, binary_sha256=row['packageSha256']) for row in baseline['packages']}
    for row in supplements['supplements']:
        require(row['package'] in expected and row['version'] != expected[row['package']]['version'], 'Supplement must replace an exact older source version')
        expected[row['package']] = dict(version=row['version'], licenses=row['declared_licenses'], binary=row['package_archive'], binary_sha256=row['package_sha256'])
        for module in row['native_modules']:
            require(record['releaseInput'].get(module['path']) == {key: module[key] for key in ('bytes', 'sha256')}, 'Supplement native module differs from reviewed current input')
        notice = row['installed_notice']; path = 'bin/' + notice['path']
        require(record['releaseInput'].get(path) == row['original_notice'] == dict(bytes=notice['size'], sha256=notice['sha256']), 'Exact source license notice differs from final package')
    native = load(source / 'release/bin/native-files.json')
    actual = {owner['name']: owner for row in native['files'] for owner in row['packages']}
    require(set(actual) == set(expected) and len(actual) == 64, 'Current native source owners are not completely covered')
    hashes = {}
    for line in (evidence / 'msys2-cache-sha256.txt').read_text(encoding='utf-8-sig').splitlines():
        fields = line.split(maxsplit=1)
        require(len(fields) == 2 and re.fullmatch('[0-9a-f]{64}', fields[0]), 'Invalid current binary archive hash evidence')
        name = PurePosixPath(fields[1].lstrip('*')).name
        require(name not in hashes, 'Duplicate binary archive hash evidence'); hashes[name] = fields[0]
    for name, wanted in expected.items():
        require(actual[name]['version'] == wanted['version'] and actual[name]['licenses'] == wanted['licenses']
                and hashes.get(wanted['binary']) == wanted['binary_sha256'], 'Native owner/version/archive is not covered by published sources: ' + name)
    return dict(owners=len(actual), original_collection=delivery['artifacts'][0], original_manifest=published['source-manifest.json'], supplemental_sources=2)


def verify_public_sources(source, evidence, record, commit):
    folder = source / 'installer/windows/source'
    publication = load(folder / 'native-source-supplement-publication.json')
    validate_publication(publication, folder / 'source-supplements.json')
    native = validate_native_sources(source, evidence, record)
    inputs = {path.name: file_record(path) for path in folder.glob('*.json')}
    with tempfile.TemporaryDirectory(prefix='tintfable-public-source-') as temporary:
        temporary = Path(temporary).resolve()
        fetched = []
        for filename, url in (('source-manifest.json', native['original_manifest']['url']), ('source-supplements.json', publication['manifest']['url'])):
            target = temporary / filename
            result = download(url, target, 1024 * 1024)
            require(file_record(target) == file_record(folder / filename), 'Public source manifest bytes changed: ' + filename)
            fetched.append(result)
        archive = temporary / 'current-app.tar.gz'
        current = download('https://github.com/hashfunction/pixelquay/archive/' + commit + '.tar.gz', archive, 64 * 1024 * 1024)
        current.update(verify_application_archive(archive, source, commit))
    require(inputs == {path.name: file_record(path) for path in folder.glob('*.json')}, 'Source publication inputs changed during verification')
    return dict(application_source=current, source_page=SOURCE_PAGE, source_publication_inputs=inputs,
                native_source_coverage=native, current_public_manifests=fetched, supplemental_release=RELEASE_URL)
