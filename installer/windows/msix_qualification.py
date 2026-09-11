#!/usr/bin/env python3
"""Build and independently verify a disposable PixelQuay qualification MSIX.

Copyright 2026 Trieflow LLC. MIT licensed. The installation-flow design retains
attribution for the MIT ReticleQuay helper in RETICLEQUAY-MIT.txt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import unquote
import xml.etree.ElementTree as ET
import zipfile
import zlib


APPX_NS = 'http://schemas.microsoft.com/appx/manifest/foundation/windows10'
UAP_NS = 'http://schemas.microsoft.com/appx/manifest/uap/windows10'
RESCAP_NS = 'http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities'
ET.register_namespace('', APPX_NS)
ET.register_namespace('uap', UAP_NS)
ET.register_namespace('rescap', RESCAP_NS)

QUALIFICATION_IDENTITY = {
	'packageName': 'Trieflow.PixelQuay.Qualification',
	'publisher': 'CN=PixelQuay-CI-Qualification',
	'version': '1.0.0.0',
	'architecture': 'x64',
	'applicationId': 'PixelQuay',
	'executable': r'bin\PixelQuay.exe',
	'deviceFamily': 'Windows.Desktop',
	'minVersion': '10.0.19041.0',
	'maxVersionTested': '10.0.26100.0',
	'capability': 'runFullTrust',
}
REQUIRED_RELEASE_FILES = (
	'bin/PixelQuay.exe',
	'bin/PixelQuay.dll',
	'bin/PixelQuay.runtimeconfig.json',
	'bin/coreclr.dll',
	'bin/hostfxr.dll',
	'bin/native-files.json',
	'bin/licenses/managed-packages.json',
)
PACKAGE_METADATA = {'[Content_Types].xml', 'AppxBlockMap.xml', 'AppxMetadata/CodeIntegrity.cat'}


def _canonical_json(value):
	return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def _digest(stream):
	hasher = hashlib.sha256()
	size = 0
	while block := stream.read(1024 * 1024):
		hasher.update(block)
		size += len(block)
	return {'bytes': size, 'sha256': hasher.hexdigest()}


def _reject_link(path):
	path = Path(path)
	info = path.lstat()
	if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
		raise ValueError(f'Symlink/reparse point refused: {path}')
	return info


def _regular_stream(path):
	path = Path(path)
	before = _reject_link(path)
	if not stat.S_ISREG(before.st_mode):
		raise ValueError(f'Expected regular file: {path}')
	flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
	fd = os.open(path, flags)
	stream = os.fdopen(fd, 'rb')
	after = os.fstat(fd)
	if not stat.S_ISREG(after.st_mode) or (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
		stream.close()
		raise ValueError(f'File identity changed while opening: {path}')
	return stream


def _checked_path(value):
	if not isinstance(value, str) or not value or '\\' in value or ':' in value or value.startswith('/'):
		raise ValueError(f'Unsafe Windows path: {value!r}')
	parts = value.split('/')
	if any(
		not part or part in ('.', '..') or part.endswith(('.', ' '))
		or re.search(r'[<>"|?*\x00-\x1f\x7f]', part)
		or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I)
		for part in parts
	):
		raise ValueError(f'Unsafe Windows path: {value!r}')
	return value


def _register_path(value, seen):
	_checked_path(value)
	parts = value.split('/')
	for count in range(1, len(parts) + 1):
		prefix = '/'.join(parts[:count])
		key = unicodedata.normalize('NFC', prefix).casefold()
		if ('file', key) in seen:
			raise ValueError(f'File/directory or case/Unicode alias: {value}')
		prior = seen.get(('component', key))
		if prior is not None and prior != prefix:
			raise ValueError(f'Case/Unicode path alias: {value}')
		if count == len(parts) and ('directory', key) in seen:
			raise ValueError(f'File/directory path alias: {value}')
		seen[('component', key)] = prefix
		seen[('file' if count == len(parts) else 'directory', key)] = prefix


def inventory_tree(root):
	root = Path(root)
	root_info = _reject_link(root)
	if not stat.S_ISDIR(root_info.st_mode):
		raise ValueError(f'Expected directory: {root}')
	result = {}
	seen = {}

	def walk(directory):
		for path in sorted(directory.iterdir(), key=lambda item: item.name):
			info = _reject_link(path)
			relative = path.relative_to(root).as_posix()
			_checked_path(relative)
			if stat.S_ISDIR(info.st_mode):
				walk(path)
			elif stat.S_ISREG(info.st_mode):
				_register_path(relative, seen)
				with _regular_stream(path) as stream:
					result[relative] = _digest(stream)
			else:
				raise ValueError(f'Special file refused: {relative}')

	walk(root)
	if not result:
		raise ValueError('Empty tree refused')
	return result


def _load_json(path, label):
	try:
		with _regular_stream(path) as stream:
			raw = stream.read(16 * 1024 * 1024 + 1)
		if len(raw) > 16 * 1024 * 1024:
			raise ValueError(f'Oversized {label}')
		return json.loads(raw.decode('utf-8-sig'))
	except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
		raise ValueError(f'Invalid {label}: {error}') from error


def _validate_native_inventory(release, inventory):
	if not isinstance(inventory, dict) or inventory.get('schemaVersion') != 1 \
		or inventory.get('provider') != 'MSYS2' \
		or inventory.get('status') != 'inventoried-requires-release-license-review' \
		or not isinstance(inventory.get('files'), list) or not inventory['files']:
		raise ValueError('Invalid native inventory')
	seen = set()
	package_records = {}
	for row in inventory['files']:
		if not isinstance(row, dict) or not isinstance(row.get('path'), str):
			raise ValueError('Invalid native inventory row')
		relative = _checked_path(row['path'])
		key = unicodedata.normalize('NFC', relative).casefold()
		if key in seen:
			raise ValueError('Duplicate native inventory path')
		seen.add(key)
		if relative.split('/')[0] not in ('bin', 'etc', 'lib', 'share'):
			raise ValueError(f'Native inventory path is outside release layout: {relative}')
		path = release / relative
		if not path.is_file():
			raise ValueError(f'Native inventory file missing from release: {relative}')
		with _regular_stream(path) as stream:
			measured = _digest(stream)
		if measured != {'bytes': row.get('size'), 'sha256': row.get('sha256')}:
			raise ValueError(f'Native inventory hash/size mismatch: {relative}')
		packages = row.get('packages')
		if not isinstance(packages, list) or not packages:
			raise ValueError(f'Native inventory package provenance missing: {relative}')
		for package in packages:
			if not isinstance(package, dict) or any(not package.get(field) for field in ('name', 'version', 'licenses', 'upstream')):
				raise ValueError(f'Native inventory package metadata missing: {relative}')
			name = package['name']
			if '/' in name or _checked_path(name) != name:
				raise ValueError(f'Invalid native inventory package name: {name!r}')
			if name in package_records and package_records[name] != package:
				raise ValueError(f'Conflicting native package notice metadata: {name}')
			package_records[name] = package
	try:
		expected_notices = {}
		seen_notices = {}
		for name, package in package_records.items():
			originals = package.get('licenseFiles')
			if not isinstance(originals, list):
				raise ValueError(f'Missing original license paths for {name}')
			expected_sources = {}
			for original in originals:
				_checked_path(original)
				if '/share/licenses/' not in original or original in expected_sources:
					raise ValueError(f'Invalid or duplicate original license path for {name}')
				expected_sources[original] = f'licenses/native/{name}/{original}'
			supplement = package.get('licenseSupplement')
			if not originals:
				if not isinstance(supplement, dict) or supplement.get('package') != name \
					or any(supplement.get(key) != package[key] for key in ('version', 'licenses', 'upstream')):
					raise ValueError(f'Missing or inconsistent license supplement for {name}')
				original = _checked_path(supplement.get('licenseFile'))
				expected_sources[original] = f'licenses/native/{name}/{PurePosixPath(original).name}'
			elif supplement is not None:
				raise ValueError(f'Supplement cannot replace installed license files for {name}')
			included = package.get('includedLicenseFiles')
			if not isinstance(included, list) or len(included) != len(expected_sources):
				raise ValueError(f'Incomplete included license mapping for {name}')
			mapped_sources = set()
			for notice in included:
				if not isinstance(notice, dict):
					raise ValueError(f'Invalid included license mapping for {name}')
				original = _checked_path(notice.get('sourcePath'))
				relative = _checked_path(notice.get('path'))
				if original in mapped_sources or expected_sources.get(original) != relative:
					raise ValueError(f'Incorrect or duplicate included license mapping for {name}')
				mapped_sources.add(original)
				_register_path(relative, seen_notices)
				if type(notice.get('size')) is not int or notice['size'] <= 0 \
					or not isinstance(notice.get('sha256'), str) or not re.fullmatch('[0-9a-f]{64}', notice['sha256']):
					raise ValueError(f'Invalid included license hash/size for {name}')
				if supplement is not None and notice['sha256'] != supplement.get('licenseSha256'):
					raise ValueError(f'Included license differs from exact source supplement for {name}')
				expected_notices[relative.removeprefix('licenses/native/')] = {'bytes': notice['size'], 'sha256': notice['sha256']}
		if inventory_tree(release / 'bin/licenses/native') != expected_notices:
			raise ValueError('Copied license files differ from complete source-to-package mapping')
	except (OSError, ValueError) as error:
		raise ValueError(f'Native package notice verification failed: {error}') from error
	return hashlib.sha256(_canonical_json(inventory)).hexdigest()


def _validate_managed_inventory(release, inventory):
	if not isinstance(inventory, dict) or inventory.get('schemaVersion') != 1 \
		or inventory.get('status') != 'restored-package-audit-not-release-clearance' \
		or not isinstance(inventory.get('packages'), list) or not inventory['packages']:
		raise ValueError('Invalid managed inventory')
	seen = set()
	for package in inventory['packages']:
		if not isinstance(package, dict) or not isinstance(package.get('package'), str) \
			or not re.fullmatch(r'[0-9a-f]{64}', package.get('packageSha256', '')):
			raise ValueError('Invalid managed inventory package')
		key = package['package'].casefold()
		if key in seen:
			raise ValueError('Duplicate managed inventory package')
		seen.add(key)
		notices = package.get('includedNoticeFiles')
		if not isinstance(notices, list) or not notices:
			raise ValueError(f'Managed inventory notice missing: {package["package"]}')
		for notice in notices:
			relative = _checked_path(notice)
			if not (release / 'bin/licenses' / relative).is_file():
				raise ValueError(f'Managed inventory notice missing: {relative}')
	return hashlib.sha256(_canonical_json(inventory)).hexdigest()


def create_manifest():
	identity = QUALIFICATION_IDENTITY
	package = ET.Element(f'{{{APPX_NS}}}Package', {'IgnorableNamespaces': 'uap rescap'})
	ET.SubElement(package, f'{{{APPX_NS}}}Identity', {
		'Name': identity['packageName'], 'Publisher': identity['publisher'],
		'Version': identity['version'], 'ProcessorArchitecture': identity['architecture'],
	})
	properties = ET.SubElement(package, f'{{{APPX_NS}}}Properties')
	for name, value in (
		('DisplayName', 'PixelQuay'), ('PublisherDisplayName', 'Trieflow LLC'),
		('Description', 'PixelQuay qualification package'), ('Logo', r'Assets\StoreLogo.png'),
	):
		ET.SubElement(properties, f'{{{APPX_NS}}}{name}').text = value
	resources = ET.SubElement(package, f'{{{APPX_NS}}}Resources')
	ET.SubElement(resources, f'{{{APPX_NS}}}Resource', {'Language': 'en-US'})
	dependencies = ET.SubElement(package, f'{{{APPX_NS}}}Dependencies')
	ET.SubElement(dependencies, f'{{{APPX_NS}}}TargetDeviceFamily', {
		'Name': identity['deviceFamily'], 'MinVersion': identity['minVersion'],
		'MaxVersionTested': identity['maxVersionTested'],
	})
	applications = ET.SubElement(package, f'{{{APPX_NS}}}Applications')
	application = ET.SubElement(applications, f'{{{APPX_NS}}}Application', {
		'Id': identity['applicationId'], 'Executable': identity['executable'],
		'EntryPoint': 'Windows.FullTrustApplication',
	})
	ET.SubElement(application, f'{{{UAP_NS}}}VisualElements', {
		'DisplayName': 'PixelQuay', 'Description': 'PixelQuay qualification package',
		'BackgroundColor': '#142e38', 'Square150x150Logo': r'Assets\Square150x150Logo.png',
		'Square44x44Logo': r'Assets\Square44x44Logo.png',
	})
	capabilities = ET.SubElement(package, f'{{{APPX_NS}}}Capabilities')
	ET.SubElement(capabilities, f'{{{RESCAP_NS}}}Capability', {'Name': identity['capability']})
	ET.indent(package, space='  ')
	return ET.tostring(package, encoding='utf-8', xml_declaration=True)


def _one(parent, tag, label):
	items = parent.findall(tag)
	if len(items) != 1:
		raise ValueError(f'Manifest requires exactly one {label}')
	return items[0]


def validate_manifest(data):
	try:
		root = ET.fromstring(data)
	except ET.ParseError as error:
		raise ValueError(f'Invalid manifest XML: {error}') from error
	if root.tag != f'{{{APPX_NS}}}Package' or root.attrib != {'IgnorableNamespaces': 'uap rescap'}:
		raise ValueError('Invalid manifest package root')
	expected_children = [
		f'{{{APPX_NS}}}Identity', f'{{{APPX_NS}}}Properties', f'{{{APPX_NS}}}Resources',
		f'{{{APPX_NS}}}Dependencies', f'{{{APPX_NS}}}Applications', f'{{{APPX_NS}}}Capabilities',
	]
	if [child.tag for child in root] != expected_children:
		raise ValueError('Unexpected manifest sections or extensions')
	identity_node = _one(root, f'{{{APPX_NS}}}Identity', 'identity')
	identity = QUALIFICATION_IDENTITY
	if identity_node.attrib != {
		'Name': identity['packageName'], 'Publisher': identity['publisher'],
		'Version': identity['version'], 'ProcessorArchitecture': identity['architecture'],
	}:
		raise ValueError('Unexpected qualification identity')
	properties = _one(root, f'{{{APPX_NS}}}Properties', 'properties')
	expected_properties = {
		'DisplayName': 'PixelQuay', 'PublisherDisplayName': 'Trieflow LLC',
		'Description': 'PixelQuay qualification package', 'Logo': r'Assets\StoreLogo.png',
	}
	if len(properties) != len(expected_properties) \
		or {child.tag.rsplit('}', 1)[-1]: child.text for child in properties} != expected_properties \
		or any(child.attrib or len(child) for child in properties):
		raise ValueError('Unexpected manifest properties')
	resources = _one(root, f'{{{APPX_NS}}}Resources', 'resources')
	resource = _one(resources, f'{{{APPX_NS}}}Resource', 'resource')
	if len(resources) != 1 or resource.attrib != {'Language': 'en-US'} or len(resource):
		raise ValueError('Unexpected manifest resources')
	dependencies = _one(root, f'{{{APPX_NS}}}Dependencies', 'dependencies')
	family = _one(dependencies, f'{{{APPX_NS}}}TargetDeviceFamily', 'target device family')
	if len(dependencies) != 1 or family.attrib != {'Name': identity['deviceFamily'], 'MinVersion': identity['minVersion'], 'MaxVersionTested': identity['maxVersionTested']} or len(family):
		raise ValueError('Unexpected target device family')
	applications = _one(root, f'{{{APPX_NS}}}Applications', 'applications')
	application = _one(applications, f'{{{APPX_NS}}}Application', 'application')
	if len(applications) != 1 or application.attrib != {'Id': identity['applicationId'], 'Executable': identity['executable'], 'EntryPoint': 'Windows.FullTrustApplication'}:
		raise ValueError('Unexpected manifest executable/application')
	visual = _one(application, f'{{{UAP_NS}}}VisualElements', 'visual elements')
	if len(application) != 1 or visual.attrib != {
		'DisplayName': 'PixelQuay', 'Description': 'PixelQuay qualification package',
		'BackgroundColor': '#142e38', 'Square150x150Logo': r'Assets\Square150x150Logo.png',
		'Square44x44Logo': r'Assets\Square44x44Logo.png',
	} or len(visual):
		raise ValueError('Unexpected manifest visual elements')
	capabilities = _one(root, f'{{{APPX_NS}}}Capabilities', 'capabilities')
	capability = _one(capabilities, f'{{{RESCAP_NS}}}Capability', 'capability')
	if len(capabilities) != 1 or capability.attrib != {'Name': identity['capability']} or len(capability):
		raise ValueError('Unexpected manifest capabilities')
	return dict(identity)


def _png_chunks(data):
	if not data.startswith(b'\x89PNG\r\n\x1a\n'):
		raise ValueError('Artwork is not PNG')
	position = 8
	while position < len(data):
		if position + 12 > len(data):
			raise ValueError('Truncated PNG')
		length = struct.unpack('>I', data[position:position + 4])[0]
		kind = data[position + 4:position + 8]
		body = data[position + 8:position + 8 + length]
		crc = data[position + 8 + length:position + 12 + length]
		if len(body) != length or len(crc) != 4 or zlib.crc32(kind + body) & 0xffffffff != struct.unpack('>I', crc)[0]:
			raise ValueError('Invalid PNG chunk')
		position += 12 + length
		yield kind, body
		if kind == b'IEND':
			if position != len(data):
				raise ValueError('Trailing PNG data')
			return
	raise ValueError('PNG is missing IEND')


def png_dimensions(data):
	chunks = list(_png_chunks(data))
	if not chunks or chunks[0][0] != b'IHDR' or len(chunks[0][1]) != 13:
		raise ValueError('PNG is missing IHDR')
	return struct.unpack('>II', chunks[0][1][:8])


def _decode_rgba_png(data):
	chunks = list(_png_chunks(data))
	if chunks[0][0] != b'IHDR':
		raise ValueError('PNG is missing IHDR')
	width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', chunks[0][1])
	if not (0 < width <= 4096 and 0 < height <= 4096 and depth == 8 and color == 6 and compression == filtering == interlace == 0):
		raise ValueError('Artwork must be bounded noninterlaced 8-bit RGBA PNG')
	compressed = b''.join(body for kind, body in chunks if kind == b'IDAT')
	try:
		raw = zlib.decompress(compressed)
	except zlib.error as error:
		raise ValueError(f'Invalid compressed PNG: {error}') from error
	stride = width * 4
	if len(raw) != (stride + 1) * height:
		raise ValueError('Unexpected PNG data size')
	rows = []
	prior = bytearray(stride)
	for row_number in range(height):
		start = row_number * (stride + 1)
		filter_type = raw[start]
		encoded = raw[start + 1:start + stride + 1]
		if filter_type > 4:
			raise ValueError('Unsupported PNG filter')
		row = bytearray(stride)
		for index, value in enumerate(encoded):
			left = row[index - 4] if index >= 4 else 0
			up = prior[index]
			upper_left = prior[index - 4] if index >= 4 else 0
			if filter_type == 0:
				prediction = 0
			elif filter_type == 1:
				prediction = left
			elif filter_type == 2:
				prediction = up
			elif filter_type == 3:
				prediction = (left + up) // 2
			else:
				candidate = left + up - upper_left
				dl, du, dul = abs(candidate - left), abs(candidate - up), abs(candidate - upper_left)
				prediction = left if dl <= du and dl <= dul else up if du <= dul else upper_left
			row[index] = (value + prediction) & 0xff
		rows.append(bytes(row))
		prior = row
	return width, height, rows


def _chunk(kind, body):
	return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)


def resize_png(data, target):
	if target not in (44, 50, 150):
		raise ValueError('Unreviewed qualification asset size')
	width, height, rows = _decode_rgba_png(data)
	output = bytearray()
	for y in range(target):
		source_row = rows[min(height - 1, y * height // target)]
		output.append(0)
		for x in range(target):
			start = min(width - 1, x * width // target) * 4
			output.extend(source_row[start:start + 4])
	header = struct.pack('>IIBBBBB', target, target, 8, 6, 0, 0, 0)
	return b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', header) + _chunk(b'IDAT', zlib.compress(bytes(output), 9)) + _chunk(b'IEND', b'')


def _write_new(path, data):
	path = Path(path)
	path.parent.mkdir(parents=True, exist_ok=True)
	with path.open('xb') as output:
		output.write(data)
		output.flush()
		os.fsync(output.fileno())


def stage_release(release, artwork, stage, source_commit):
	release, artwork, stage = Path(release), Path(artwork), Path(stage)
	if not re.fullmatch(r'[0-9a-f]{40}', source_commit or ''):
		raise ValueError('Exact 40-character source commit is required')
	if os.path.lexists(stage):
		raise ValueError(f'Stage already exists and will not be replaced: {stage}')
	input_inventory = inventory_tree(release)
	for relative in REQUIRED_RELEASE_FILES:
		if relative not in input_inventory:
			raise ValueError(f'Required release file missing: {relative}')
	if 'AppxManifest.xml' in input_inventory or any(name.casefold().startswith('assets/') for name in input_inventory):
		raise ValueError('Release collides with qualification-owned manifest/assets')
	if 'bin/libfontconfig-1.dll' in input_inventory:
		if 'etc/fonts/fonts.conf' not in input_inventory:
			raise ValueError('Fontconfig runtime requires etc/fonts/fonts.conf in the release stage')
		for directory in ('share/fontconfig', 'share/xml/fontconfig'):
			prefix = directory + '/'
			if not any(name.startswith(prefix) for name in input_inventory):
				raise ValueError(f'Fontconfig runtime requires nonempty {directory} resources')
	native = _load_json(release / 'bin/native-files.json', 'native inventory')
	managed = _load_json(release / 'bin/licenses/managed-packages.json', 'managed inventory')
	native_digest = _validate_native_inventory(release, native)
	managed_digest = _validate_managed_inventory(release, managed)
	with _regular_stream(artwork) as stream:
		artwork_data = stream.read()
	artwork_record = {'bytes': len(artwork_data), 'sha256': hashlib.sha256(artwork_data).hexdigest()}
	assets = {}
	stage.mkdir(parents=False)
	try:
		for relative in sorted(input_inventory):
			target = stage / relative
			target.parent.mkdir(parents=True, exist_ok=True)
			with _regular_stream(release / relative) as source, target.open('xb') as output:
				shutil.copyfileobj(source, output, 1024 * 1024)
		for name, size in (('StoreLogo.png', 50), ('Square44x44Logo.png', 44), ('Square150x150Logo.png', 150)):
			data = resize_png(artwork_data, size)
			relative = f'Assets/{name}'
			_write_new(stage / relative, data)
			assets[relative] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'pixels': [size, size]}
		manifest = create_manifest()
		validate_manifest(manifest)
		_write_new(stage / 'AppxManifest.xml', manifest)
		if inventory_tree(release) != input_inventory:
			raise ValueError('Release input changed while staging')
		payload = inventory_tree(stage)
		for relative, record in input_inventory.items():
			if payload.get(relative) != record:
				raise ValueError(f'Staged release differs from input: {relative}')
		return {
			'schemaVersion': 1,
			'sourceCommit': source_commit,
			'qualificationIdentityOnly': True,
			'identity': dict(QUALIFICATION_IDENTITY),
			'releaseInput': input_inventory,
			'payload': payload,
			'nativeInventoryCanonicalSha256': native_digest,
			'managedInventoryCanonicalSha256': managed_digest,
			'artworkSource': artwork_record,
			'assets': assets,
			'licenseClearanceClaimed': False,
			'publicRelease': False,
			'signed': False,
			'installationQualificationPassed': False,
		}
	except Exception:
		shutil.rmtree(stage, ignore_errors=True)
		raise


def _decode_opc_path(value):
	# MakeAppx stores OPC URI names in the ZIP, e.g. libc++.dll becomes
	# libc%2B%2B.dll. Decode once before payload/hash and alias comparison.
	# Escaped separators cannot change the archive's directory hierarchy.
	if re.search(r'%(?![0-9A-Fa-f]{2})|%(?:2f|5c)', value, re.I):
		raise ValueError(f'Malformed or hierarchy-changing OPC path: {value!r}')
	return _checked_path(unquote(value, encoding='utf-8', errors='strict'))


def verify_msix(path, expected):
	if not isinstance(expected, dict) or 'AppxManifest.xml' not in expected:
		raise ValueError('Invalid expected package payload')
	allowed_directories = {
		str(parent) for name in set(expected) | PACKAGE_METADATA
		for parent in PurePosixPath(name).parents if str(parent) != '.'
	}
	seen = {}
	actual = {}
	metadata = set()
	directories = set()
	manifest_data = None
	with zipfile.ZipFile(path) as archive:
		for info in archive.infolist():
			name = _decode_opc_path(info.filename.rstrip('/') if info.is_dir() else info.filename)
			mode = info.external_attr >> 16
			if info.flag_bits & 1:
				raise ValueError(f'Encrypted package entry: {info.filename}')
			if info.is_dir():
				key = unicodedata.normalize('NFC', name).casefold()
				if stat.S_IFMT(mode) not in (0, stat.S_IFDIR) or name not in allowed_directories or key in directories:
					raise ValueError(f'Unexpected/special package directory: {info.filename}')
				directories.add(key)
				continue
			_register_path(name, seen)
			if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
				raise ValueError(f'Special package entry: {name}')
			if name in PACKAGE_METADATA:
				if info.file_size > 32 * 1024 * 1024:
					raise ValueError(f'Oversized package metadata: {name}')
				metadata.add(name)
				continue
			record = expected.get(name)
			if not record or info.file_size != record['bytes']:
				raise ValueError(f'Unexpected package entry or size: {name}')
			with archive.open(info) as stream:
				measured = _digest(stream)
			if measured != record:
				raise ValueError(f'Package hash mismatch: {name}')
			actual[name] = measured
			if name == 'AppxManifest.xml':
				manifest_data = archive.read(info)
	if set(actual) != set(expected):
		raise ValueError('Package payload is missing expected files')
	if not {'[Content_Types].xml', 'AppxBlockMap.xml'}.issubset(metadata):
		raise ValueError('Package metadata is incomplete')
	validate_manifest(manifest_data)
	with _regular_stream(path) as stream:
		package = _digest(stream)
	return {'verifiedPayloadFiles': len(actual), 'metadata': sorted(metadata), 'package': package}


def verify_unpacked(root, expected):
	actual = inventory_tree(root)
	for metadata in PACKAGE_METADATA:
		actual.pop(metadata, None)
	if actual != expected:
		raise ValueError('SDK-unpacked payload differs from staged payload')
	validate_manifest((Path(root) / 'AppxManifest.xml').read_bytes())
	return {'verifiedPayloadFiles': len(actual)}


def _tool_record(path, sdk_version):
	path = Path(path)
	if not path.is_absolute() or path.name.casefold() != 'makeappx.exe':
		raise ValueError('Absolute MakeAppx.exe path is required')
	if not re.fullmatch(r'10\.0\.\d+\.0', sdk_version or ''):
		raise ValueError('Exact Windows SDK version is required')
	normalized = [part.casefold() for part in path.parts]
	expected_tail = ['windows kits', '10', 'bin', sdk_version.casefold(), 'x64', 'makeappx.exe']
	if normalized[-6:] != expected_tail:
		raise ValueError('MakeAppx SDK path must end with Windows Kits/10/bin/<exact-version>/x64/makeappx.exe')
	with _regular_stream(path) as stream:
		record = _digest(stream)
	record.update({'path': str(path), 'sdkVersion': sdk_version})
	return record


def _run(command):
	subprocess.run(command, check=True, shell=False, timeout=900)


def build_qualification(release, artwork, source_commit, makeappx, sdk_version, output, runner=_run):
	output = Path(output).absolute()
	if os.path.lexists(output):
		raise ValueError(f'Output already exists and will not be replaced: {output}')
	output.parent.mkdir(parents=True, exist_ok=True)
	temporary = Path(tempfile.mkdtemp(prefix='.pixelquay-msix-', dir=output.parent))
	try:
		tool = _tool_record(makeappx, sdk_version)
		stage = temporary / 'stage'
		record = stage_release(release, artwork, stage, source_commit)
		package = temporary / 'PixelQuay.Qualification_1.0.0.0_x64.msix'
		unpacked = temporary / 'unpacked'
		commands = [
			[str(makeappx), 'pack', '/d', str(stage), '/p', str(package), '/v', '/h', 'SHA256'],
			[str(makeappx), 'unpack', '/p', str(package), '/d', str(unpacked), '/v'],
		]
		for command in commands:
			if _tool_record(makeappx, sdk_version) != tool:
				raise ValueError('MakeAppx changed during qualification build')
			runner(command)
			if inventory_tree(stage) != record['payload']:
				raise ValueError('Package stage changed during SDK execution')
		container = verify_msix(package, record['payload'])
		unpacked_result = verify_unpacked(unpacked, record['payload'])
		if _tool_record(makeappx, sdk_version) != tool:
			raise ValueError('MakeAppx changed during qualification build')
		record.update({
			'makeAppx': tool,
			'containerVerification': container,
			'unpackedVerification': unpacked_result,
		})
		output.mkdir()
		try:
			with _regular_stream(package) as source, (output / package.name).open('xb') as destination:
				shutil.copyfileobj(source, destination, 1024 * 1024)
			_write_new(output / 'package-record.json', _canonical_json(record))
		except Exception:
			# This directory was created by this invocation; retain it as explicit incomplete evidence.
			_write_new(output / 'INCOMPLETE.txt', b'Packaging output is incomplete and must not be consumed.\n')
			raise
		shutil.rmtree(temporary)
		return output
	except Exception as error:
		raise ValueError(f'Qualification packaging failed; evidence retained at {temporary}: {error}') from error


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument('--release', type=Path, required=True)
	parser.add_argument('--artwork', type=Path, required=True)
	parser.add_argument('--source-root', type=Path, required=True)
	parser.add_argument('--source-commit', required=True)
	parser.add_argument('--makeappx', type=Path, required=True)
	parser.add_argument('--sdk-version', required=True)
	parser.add_argument('--output', type=Path, required=True)
	args = parser.parse_args()
	if sys.platform != 'win32' or os.environ.get('CI') != 'true':
		parser.error('Qualification package builds require disposable Windows CI')
	try:
		actual = subprocess.run(
			['git', '-C', str(args.source_root), 'rev-parse', 'HEAD'], check=True,
			capture_output=True, text=True, timeout=30,
		).stdout.strip()
		if actual != args.source_commit:
			raise ValueError(f'Source commit mismatch: expected {args.source_commit}, found {actual}')
		dirty = subprocess.run(
			['git', '-C', str(args.source_root), 'status', '--porcelain', '--untracked-files=all'], check=True,
			capture_output=True, text=True, timeout=30,
		).stdout.strip()
		if dirty:
			raise ValueError('Source checkout must be clean so the recorded commit identifies every packaging input')
		print(build_qualification(args.release, args.artwork, args.source_commit, args.makeappx, args.sdk_version, args.output))
	except (OSError, ValueError, subprocess.SubprocessError) as error:
		parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
	main()
