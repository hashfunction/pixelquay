"""Behavioral tests for the disposable PixelQuay MSIX qualification package.

Copyright 2026 Trieflow LLC. MIT licensed.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

import msix_qualification as msix
import inventory_native


def sha(data):
	return hashlib.sha256(data).hexdigest()


def native_package(name, data):
	source = f'clang64/share/licenses/{name}/COPYING'
	return {'name': name, 'version': '1.0', 'licenses': ['MIT'],
		'upstream': 'https://example.invalid/' + name,
		'licenseFiles': [source],
		'includedLicenseFiles': [{'sourcePath': source,
			'path': f'licenses/native/{name}/{source}', 'size': len(data), 'sha256': sha(data)}]}


class QualificationFixture(unittest.TestCase):
	def setUp(self):
		self.temporary = tempfile.TemporaryDirectory()
		self.addCleanup(self.temporary.cleanup)
		self.root = Path(self.temporary.name)
		self.release = self.root / 'release'
		(self.release / 'bin/licenses/managed').mkdir(parents=True)
		(self.release / 'share/locale').mkdir(parents=True)
		files = {
			'bin/TintFable.exe': b'pixelquay executable',
			'bin/TintFable.dll': b'pixelquay assembly',
			'bin/TintFable.runtimeconfig.json': b'{"runtimeOptions":{}}',
			'bin/coreclr.dll': b'core clr',
			'bin/hostfxr.dll': b'host fxr',
			'bin/native.dll': b'native dependency',
			'bin/licenses/managed/example.txt': b'example notice',
			'bin/licenses/native/native-fixture/clang64/share/licenses/native-fixture/COPYING': b'native fixture notice',
			'share/locale/example.mo': b'locale',
		}
		for relative, data in files.items():
			path = self.release / relative
			path.parent.mkdir(parents=True, exist_ok=True)
			path.write_bytes(data)
		native = {
			'schemaVersion': 1,
			'provider': 'MSYS2',
			'status': 'inventoried-requires-release-license-review',
			'files': [{
				'path': 'bin/native.dll', 'size': len(files['bin/native.dll']),
				'sha256': sha(files['bin/native.dll']),
				'packages': [native_package('native-fixture', b'native fixture notice')],
				'provenanceInputs': ['bin/native.dll'],
			}],
		}
		managed = {
			'schemaVersion': 1,
			'status': 'restored-package-audit-not-release-clearance',
			'scope': 'fixture',
			'packages': [{
				'package': 'Fixture/1.0', 'packageSha256': 'a' * 64,
				'includedNoticeFiles': ['managed/example.txt'],
				'noticeReviewRequired': False,
			}],
		}
		(self.release / 'bin/native-files.json').write_text(json.dumps(native), encoding='utf-8')
		(self.release / 'bin/licenses/managed-packages.json').write_text(json.dumps(managed), encoding='utf-8')
		self.artwork = self.root / 'pixelquay.png'
		self.artwork.write_bytes((Path(__file__).resolve().parents[2] / 'branding/tintfable.png').read_bytes())
		self.commit = '1' * 40

	def stage(self):
		return msix.stage_release(self.release, self.artwork, self.root / 'stage', self.commit)


class ManifestTests(QualificationFixture):
	def test_tintfable_manifest_renames_visible_contract_and_preserves_identity(self):
		data=msix.create_manifest();root=ET.fromstring(data)
		ns={'a':msix.APPX_NS,'uap':msix.UAP_NS}
		self.assertEqual('TintFable',root.find('a:Properties/a:DisplayName',ns).text)
		identity=root.find('a:Identity',ns)
		self.assertEqual('Trieflow.PixelQuay.Qualification',identity.get('Name'))
		self.assertEqual('CN=PixelQuay-CI-Qualification',identity.get('Publisher'))
		self.assertEqual('1.0.1.0',identity.get('Version'))
		application=root.find('a:Applications/a:Application',ns)
		self.assertEqual('PixelQuay',application.get('Id'))
		self.assertEqual(r'bin\TintFable.exe',application.get('Executable'))
		self.assertEqual('TintFable',application.find('uap:VisualElements',ns).get('DisplayName'))
		for original,changed in [(b'<DisplayName>TintFable</DisplayName>',b'<DisplayName>PixelQuay</DisplayName>'),
				(b'DisplayName="TintFable"',b'DisplayName="PixelQuay"'),
				(b'bin\\TintFable.exe',b'bin\\PixelQuay.exe'),(b'1.0.1.0',b'1.0.0.0'),
				(b'Id="PixelQuay"',b'Id="TintFable"'),(b'Trieflow.PixelQuay.Qualification',b'Trieflow.TintFable.Qualification')]:
			with self.subTest(changed=changed),self.assertRaises(ValueError):msix.validate_manifest(data.replace(original,changed))

	def test_manifest_has_only_qualification_identity_and_required_capability(self):
		manifest = msix.validate_manifest(msix.create_manifest())
		self.assertEqual(msix.QUALIFICATION_IDENTITY, manifest)
		text = msix.create_manifest().decode('utf-8')
		for absent in ('Protocol', 'FileTypeAssociation', 'com:Extension', 'uap:Extension', 'Registry'):
			self.assertNotIn(absent, text)

	def test_manifest_rejects_extra_capability_and_wrong_executable(self):
		data = msix.create_manifest()
		with self.assertRaisesRegex(ValueError, 'capabilit'):
			msix.validate_manifest(data.replace(b'</Capabilities>', b'<rescap:Capability Name="internetClient"/></Capabilities>'))
		with self.assertRaisesRegex(ValueError, 'executable'):
			msix.validate_manifest(data.replace(b'bin\\TintFable.exe', b'other.exe'))
		with self.assertRaisesRegex(ValueError, 'properties'):
			msix.validate_manifest(data.replace(b'</Properties>', b'<DisplayName>PixelQuay</DisplayName></Properties>'))


class StageTests(QualificationFixture):
	def test_stage_copies_complete_release_and_records_assets_and_hashes(self):
		record = self.stage()
		stage = self.root / 'stage'
		self.assertEqual(self.commit, record['sourceCommit'])
		self.assertFalse(record['licenseClearanceClaimed'])
		self.assertFalse(record['publicRelease'])
		self.assertEqual((self.release / 'share/locale/example.mo').read_bytes(), (stage / 'share/locale/example.mo').read_bytes())
		self.assertEqual(record['releaseInput'], msix.inventory_tree(self.release))
		self.assertEqual(record['payload'], msix.inventory_tree(stage))
		for name, size in [('StoreLogo.png', 50), ('Square44x44Logo.png', 44), ('Square150x150Logo.png', 150)]:
			data = (stage / 'Assets' / name).read_bytes()
			self.assertEqual((size, size), msix.png_dimensions(data))
			self.assertEqual(sha(data), record['assets'][f'Assets/{name}']['sha256'])

	def test_stage_refuses_existing_output_and_does_not_change_it(self):
		stage = self.root / 'stage'
		stage.mkdir()
		marker = stage / 'owned.txt'
		marker.write_text('preserve')
		with self.assertRaisesRegex(ValueError, 'already exists'):
			msix.stage_release(self.release, self.artwork, stage, self.commit)
		self.assertEqual('preserve', marker.read_text())

	def test_stage_rejects_missing_runtime_and_inventory(self):
		(self.release / 'bin/coreclr.dll').unlink()
		with self.assertRaisesRegex(ValueError, 'coreclr'):
			self.stage()
		self.assertFalse((self.root / 'stage').exists())
		(self.release / 'bin/coreclr.dll').write_bytes(b'core clr')
		(self.release / 'bin/native-files.json').unlink()
		with self.assertRaisesRegex(ValueError, '(?i)native-files|native inventory'):
			self.stage()

	def test_stage_rejects_native_inventory_hash_mismatch(self):
		(self.release / 'bin/native.dll').write_bytes(b'changed')
		with self.assertRaisesRegex(ValueError, '(?i)native inventory'):
			self.stage()

	def test_stage_rejects_missing_native_notice(self):
		(self.release / 'bin/licenses/native/native-fixture/clang64/share/licenses/native-fixture/COPYING').unlink()
		with self.assertRaisesRegex(ValueError, '(?i)native.*notice'):
			self.stage()

	def test_stage_rejects_changed_native_notice_despite_nonempty_directory(self):
		path = self.release / 'bin/licenses/native/native-fixture/clang64/share/licenses/native-fixture/COPYING'
		path.write_bytes(b'replacement notice')
		with self.assertRaisesRegex(ValueError, '(?i)native.*notice'):
			self.stage()

	def test_stage_requires_complete_unambiguous_native_notice_mapping(self):
		path = self.release / 'bin/native-files.json'
		original = path.read_text()
		for corruption in ('missing-map', 'omitted-source', 'extra-source', 'duplicate-source', 'duplicate-map', 'wrong-source', 'flattened-path', 'wrong-hash', 'wrong-size', 'unsafe-source', 'case-alias'):
			with self.subTest(corruption=corruption):
				inventory = json.loads(original)
				package = inventory['files'][0]['packages'][0]
				mapping = package['includedLicenseFiles']
				if corruption == 'missing-map': del package['includedLicenseFiles']
				elif corruption == 'omitted-source': package['licenseFiles'] = []
				elif corruption == 'extra-source': package['licenseFiles'].append('clang64/share/licenses/native-fixture/nested/COPYING')
				elif corruption == 'duplicate-source': package['licenseFiles'].append(package['licenseFiles'][0])
				elif corruption == 'duplicate-map': mapping.append(dict(mapping[0]))
				elif corruption == 'wrong-source': mapping[0]['sourcePath'] = 'clang64/share/licenses/other/COPYING'
				elif corruption == 'flattened-path': mapping[0]['path'] = 'licenses/native/native-fixture/COPYING'
				elif corruption == 'wrong-hash': mapping[0]['sha256'] = '0' * 64
				elif corruption == 'wrong-size': mapping[0]['size'] += 1
				elif corruption == 'unsafe-source': package['licenseFiles'][0] = '../clang64/share/licenses/native-fixture/COPYING'
				elif corruption == 'case-alias':
					original_source = 'clang64/share/licenses/native-fixture/copying'
					package['licenseFiles'].append(original_source)
					mapping.append({**mapping[0], 'sourcePath': original_source, 'path': 'licenses/native/native-fixture/' + original_source})
				path.write_text(json.dumps(inventory))
				with self.assertRaisesRegex(ValueError, '(?i)native.*notice'):
					msix._validate_native_inventory(self.release, inventory)
		path.write_text(original)

	def test_stage_rejects_unmapped_native_notice_even_with_valid_required_copy(self):
		path = self.release / 'bin/licenses/native/native-fixture/extra-COPYING'
		path.write_bytes(b'unmapped leftover')
		with self.assertRaisesRegex(ValueError, '(?i)native.*notice'):
			self.stage()

	def test_generated_nested_notice_inventory_survives_complete_package_stage(self):
		msys = self.root / 'msys'
		entry = msys / 'var/lib/pacman/local/gettext-runtime-1.0-1'
		entry.mkdir(parents=True)
		name = 'mingw-w64-clang-x86_64-gettext-runtime'
		(entry / 'desc').write_text('%NAME%\n'+name+'\n\n%VERSION%\n1.0-1\n\n%LICENSE%\nGPL-3.0-or-later\nLGPL-2.1-or-later\n\n%URL%\nhttps://www.gnu.org/software/gettext/\n')
		sources = ('clang64/share/licenses/gettext-runtime/COPYING', 'clang64/share/licenses/gettext-runtime/libasprintf/COPYING')
		(entry / 'files').write_text('%FILES%\nclang64/bin/native.dll\n'+'\n'.join(sources)+'\n')
		binary = msys / 'clang64/bin/native.dll'
		binary.parent.mkdir(parents=True)
		binary.write_bytes((self.release / 'bin/native.dll').read_bytes())
		for relative in sources:
			path = msys / relative
			path.parent.mkdir(parents=True, exist_ok=True)
			path.write_bytes((Path(__file__).parent / 'test-fixtures/native-notices' / relative).read_bytes())
		listing = msys / 'inputs.txt'
		listing.write_text(str(binary)+'\n')
		shutil.rmtree(self.release / 'bin/licenses/native')
		(self.release / 'bin/native-files.json').unlink()
		inventory_native.build_inventory(msys / 'clang64', listing, self.release / 'bin/native-files.json')
		record = self.stage()
		for relative in sources:
			copied = f'bin/licenses/native/{name}/{relative}'
			self.assertEqual((self.root / 'stage' / copied).read_bytes(), (msys / relative).read_bytes())
			self.assertEqual(record['payload'][copied], {'bytes': (msys / relative).stat().st_size, 'sha256': sha((msys / relative).read_bytes())})
		# A still-nonempty directory cannot conceal either absent original notice.
		(self.release / f'bin/licenses/native/{name}/{sources[0]}').unlink()
		with self.assertRaisesRegex(ValueError, '(?i)native.*notice'):
			msix._validate_native_inventory(self.release, json.loads((self.release / 'bin/native-files.json').read_text()))

	def test_native_supplement_mapping_preserves_exact_source_choice_and_hash(self):
		inventory = json.loads((self.release / 'bin/native-files.json').read_text())
		package = inventory['files'][0]['packages'][0]
		old = self.release / 'bin' / package['includedLicenseFiles'][0]['path']
		data = old.read_bytes()
		shutil.rmtree(self.release / 'bin/licenses/native')
		path = self.release / 'bin/licenses/native/native-fixture/COPYING'
		path.parent.mkdir(parents=True)
		path.write_bytes(data)
		package['licenseFiles'] = []
		package['licenseSupplement'] = {**{key: package[key] for key in ('version', 'licenses', 'upstream')},
			'package': package['name'], 'licenseFile': 'reviewed-source/COPYING', 'licenseSha256': sha(data)}
		package['includedLicenseFiles'] = [{'sourcePath': 'reviewed-source/COPYING', 'path': 'licenses/native/native-fixture/COPYING', 'size': len(data), 'sha256': sha(data)}]
		msix._validate_native_inventory(self.release, inventory)
		# Coherently changing the copied bytes and its mapping must still fail
		# against the exact already-reviewed supplemental source digest.
		path.write_bytes(b'changed supplemental notice')
		package['includedLicenseFiles'][0].update(size=path.stat().st_size, sha256=sha(path.read_bytes()))
		with self.assertRaisesRegex(ValueError, '(?i)native.*notice'):
			msix._validate_native_inventory(self.release, inventory)

	def test_stage_rejects_fontconfig_dll_without_runtime_configuration(self):
		data = b'fontconfig dll'
		(self.release / 'bin/libfontconfig-1.dll').write_bytes(data)
		inventory_path = self.release / 'bin/native-files.json'
		inventory = json.loads(inventory_path.read_text())
		inventory['files'].append({
			'path': 'bin/libfontconfig-1.dll', 'size': len(data), 'sha256': sha(data),
			'packages': [native_package('fontconfig-fixture', b'fontconfig fixture notice')],
			'provenanceInputs': ['bin/libfontconfig-1.dll'],
		})
		inventory_path.write_text(json.dumps(inventory))
		notice = self.release / 'bin/licenses/native/fontconfig-fixture/clang64/share/licenses/fontconfig-fixture/COPYING'
		notice.parent.mkdir(parents=True)
		notice.write_bytes(b'fontconfig fixture notice')
		with self.assertRaisesRegex(ValueError, '(?i)fontconfig.*etc/fonts'):
			self.stage()

	def test_stage_retains_inventoried_fontconfig_configuration_tree(self):
		inventory_path = self.release / 'bin/native-files.json'
		inventory = json.loads(inventory_path.read_text())
		for relative in ('bin/libfontconfig-1.dll', 'etc/fonts/fonts.conf', 'etc/fonts/conf.d/10-rule.conf', 'share/fontconfig/conf.avail/10-rule.conf', 'share/xml/fontconfig/fonts.dtd'):
			data = ('verified fontconfig ' + relative).encode()
			path = self.release / relative
			path.parent.mkdir(parents=True, exist_ok=True)
			path.write_bytes(data)
			inventory['files'].append({'path': relative, 'size': len(data), 'sha256': sha(data),
				'packages': [native_package('native-fixture', b'native fixture notice')],
				'provenanceInputs': [relative]})
		inventory_path.write_text(json.dumps(inventory))
		record = self.stage()
		self.assertEqual(record['releaseInput']['etc/fonts/fonts.conf'], record['payload']['etc/fonts/fonts.conf'])

	def test_stage_rejects_links_case_aliases_and_unsafe_windows_names(self):
		link = self.release / 'bin/linked.dll'
		try:
			link.symlink_to(self.release / 'bin/native.dll')
		except OSError as error:
			self.skipTest(f'symlink unavailable: {error}')
		with self.assertRaisesRegex(ValueError, 'link|reparse'):
			self.stage()
		link.unlink()
		alias = self.release / 'bin/NATIVE.dll'
		alias.write_bytes(b'alias')
		if alias.samefile(self.release / 'bin/native.dll'):
			# The default macOS filesystem is case-insensitive; ZIP verification covers
			# the synthetic two-entry alias case independently.
			alias.unlink()
			(self.release / 'bin/native.dll').write_bytes(b'native dependency')
		else:
			with self.assertRaisesRegex(ValueError, 'alias'):
				self.stage()
			alias.unlink()
		(self.release / 'share/con.txt').write_bytes(b'unsafe')
		with self.assertRaisesRegex(ValueError, 'Windows path'):
			self.stage()

	@unittest.skipUnless(sys.platform == 'win32', 'native junction fixture requires Windows')
	def test_stage_rejects_windows_directory_reparse_point_without_symlink_privilege(self):
		target = self.root / 'junction-target'
		target.mkdir()
		junction = self.release / 'share/reparse-fixture'
		result = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(junction), str(target)], capture_output=True, text=True)
		if result.returncode:
			self.skipTest(f'junction creation unavailable: {result.stdout} {result.stderr}')
		self.addCleanup(lambda: junction.exists() and os.rmdir(junction))
		with self.assertRaisesRegex(ValueError, 'reparse'):
			self.stage()


class PackageVerificationTests(QualificationFixture):
	def package(self, mutate=None):
		record = self.stage()
		stage = self.root / 'stage'
		package = self.root / 'fixture.msix'
		with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
			for path in sorted(stage.rglob('*')):
				if path.is_file():
					data = path.read_bytes()
					relative = path.relative_to(stage).as_posix()
					if mutate and relative == mutate[0]: data = mutate[1]
					archive.writestr(relative, data)
			archive.writestr('[Content_Types].xml', '<Types/>')
			archive.writestr('AppxBlockMap.xml', '<BlockMap/>')
		return package, record

	def test_independent_zip_verifier_accepts_exact_package(self):
		package, record = self.package()
		result = msix.verify_msix(package, record['payload'])
		self.assertEqual(len(record['payload']), result['verifiedPayloadFiles'])

	def test_opc_encoded_names_match_exact_decoded_payload_bytes(self):
		package, record = self.package()
		# The Windows 10.0.26100.0 SDK encoded libc++.dll this way in run
		# 34596219976. A literal percent filename must be decoded only once.
		pairs = [('bin/libc%2B%2B.dll', 'bin/libc++.dll'),
			('share/R%C3%A9sum%C3%A9%20note.txt', 'share/Résumé note.txt'),
			('share/literal%2520.txt', 'share/literal%20.txt')]
		with zipfile.ZipFile(package, 'a') as archive:
			for encoded, decoded in pairs:
				data = ('owned bytes for ' + decoded).encode('utf-8')
				archive.writestr(encoded, data)
				record['payload'][decoded] = {'bytes': len(data), 'sha256': sha(data)}
		self.assertEqual(len(record['payload']), msix.verify_msix(package, record['payload'])['verifiedPayloadFiles'])

	def test_opc_decoding_rejects_aliases_traversal_and_malformed_names(self):
		package, record = self.package()
		for name in ('bin/%54intFable.exe', 'bin%2FTintFable.exe', 'bin%5cTintFable.exe',
			'bin/%2e%2e/escaped.txt', '%2Fabsolute.txt', 'share/bad%GG.txt',
			'share/bad%.txt', 'share/bad%FF.txt', 'share/bad%00.txt'):
			with self.subTest(name=name):
				changed = self.root / 'encoded-invalid.msix'
				shutil.copyfile(package, changed)
				with zipfile.ZipFile(changed, 'a') as archive:
					archive.writestr(name, b'unexpected')
				with self.assertRaises(ValueError):
					msix.verify_msix(changed, record['payload'])

	def test_independent_zip_verifier_rejects_tamper_and_manifest_semantics(self):
		package, record = self.package(('bin/TintFable.exe', b'tampered'))
		with self.assertRaisesRegex(ValueError, 'hash|size'):
			msix.verify_msix(package, record['payload'])
		shutil.rmtree(self.root / 'stage')
		bad = msix.create_manifest().replace(b'runFullTrust', b'internetClient')
		package, record = self.package(('AppxManifest.xml', bad))
		# Bind the tampered bytes to demonstrate that semantic checks are independent of hashes.
		record['payload']['AppxManifest.xml'] = {'bytes': len(bad), 'sha256': sha(bad)}
		with self.assertRaisesRegex(ValueError, 'capabilities'):
			msix.verify_msix(package, record['payload'])

	def test_independent_zip_verifier_rejects_case_alias(self):
		package, record = self.package()
		with zipfile.ZipFile(package, 'a') as archive:
			archive.writestr('BIN/TintFable.exe', b'alias')
		with self.assertRaisesRegex(ValueError, 'alias'):
			msix.verify_msix(package, record['payload'])

	def test_independent_zip_verifier_rejects_unexpected_empty_directory(self):
		package, record = self.package()
		with zipfile.ZipFile(package, 'a') as archive:
			archive.writestr('unreviewed-empty/', b'')
		with self.assertRaisesRegex(ValueError, 'directory'):
			msix.verify_msix(package, record['payload'])


class BuildFlowTests(QualificationFixture):
	def setUp(self):
		super().setUp()
		self.sdk = self.root / 'Windows Kits/10/bin/10.0.26100.0/x64'
		self.sdk.mkdir(parents=True)
		self.makeappx = self.sdk / 'makeappx.exe'
		self.makeappx.write_bytes(b'fixture makeappx')
		self.output = self.root / 'qualification-output'
		self.commands = []

	def fake_sdk(self, command):
		self.commands.append(command)
		if command[1] == 'pack':
			stage = Path(command[command.index('/d') + 1])
			package = Path(command[command.index('/p') + 1])
			with zipfile.ZipFile(package, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
				for path in sorted(stage.rglob('*')):
					if path.is_file(): archive.write(path, path.relative_to(stage).as_posix())
				archive.writestr('[Content_Types].xml', '<Types/>')
				archive.writestr('AppxBlockMap.xml', '<BlockMap/>')
		elif command[1] == 'unpack':
			package = Path(command[command.index('/p') + 1])
			destination = Path(command[command.index('/d') + 1])
			with zipfile.ZipFile(package) as archive: archive.extractall(destination)
		else:
			raise AssertionError(command)

	def test_build_uses_semantic_sdk_pack_unpack_and_writes_false_claims(self):
		result = msix.build_qualification(
			self.release, self.artwork, self.commit, self.makeappx,
			'10.0.26100.0', self.output, self.fake_sdk)
		self.assertEqual(self.output, result)
		self.assertEqual(['pack', 'unpack'], [command[1] for command in self.commands])
		self.assertIn('/v', self.commands[0])
		self.assertNotIn('/nv', self.commands[0])
		self.assertNotIn('/o', self.commands[0])
		record = json.loads((self.output / 'package-record.json').read_text())
		self.assertFalse(record['signed'])
		self.assertFalse(record['installationQualificationPassed'])
		self.assertFalse(record['publicRelease'])
		self.assertEqual(sha(self.makeappx.read_bytes()), record['makeAppx']['sha256'])
		package = self.output / 'TintFable.Qualification_1.0.1.0_x64.msix'
		self.assertEqual(sha(package.read_bytes()), record['containerVerification']['package']['sha256'])

	def test_build_rechecks_sdk_tool_and_refuses_existing_output(self):
		def changing_sdk(command):
			self.fake_sdk(command)
			if command[1] == 'pack': self.makeappx.write_bytes(b'changed makeappx')
		with self.assertRaisesRegex(ValueError, 'MakeAppx changed'):
			msix.build_qualification(
				self.release, self.artwork, self.commit, self.makeappx,
				'10.0.26100.0', self.output, changing_sdk)
		self.assertFalse(self.output.exists())
		self.output.mkdir()
		marker = self.output / 'owner.txt'
		marker.write_text('preserve')
		with self.assertRaisesRegex(ValueError, 'already exists'):
			msix.build_qualification(
				self.release, self.artwork, self.commit, self.makeappx,
				'10.0.26100.0', self.output, self.fake_sdk)
		self.assertEqual('preserve', marker.read_text())

	def test_build_rejects_makeappx_outside_exact_sdk_tail(self):
		wrong = self.root / '10.0.26100.0/x64/makeappx.exe'
		wrong.parent.mkdir(parents=True)
		wrong.write_bytes(b'fixture makeappx')
		with self.assertRaisesRegex(ValueError, 'SDK.*path'):
			msix.build_qualification(
				self.release, self.artwork, self.commit, wrong,
				'10.0.26100.0', self.output, self.fake_sdk)


if __name__ == '__main__':
	unittest.main()
