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

import msix_qualification as msix


def sha(data):
	return hashlib.sha256(data).hexdigest()


class QualificationFixture(unittest.TestCase):
	def setUp(self):
		self.temporary = tempfile.TemporaryDirectory()
		self.addCleanup(self.temporary.cleanup)
		self.root = Path(self.temporary.name)
		self.release = self.root / 'release'
		(self.release / 'bin/licenses/managed').mkdir(parents=True)
		(self.release / 'share/locale').mkdir(parents=True)
		files = {
			'bin/PixelQuay.exe': b'pixelquay executable',
			'bin/PixelQuay.dll': b'pixelquay assembly',
			'bin/PixelQuay.runtimeconfig.json': b'{"runtimeOptions":{}}',
			'bin/coreclr.dll': b'core clr',
			'bin/hostfxr.dll': b'host fxr',
			'bin/native.dll': b'native dependency',
			'bin/licenses/managed/example.txt': b'example notice',
			'bin/licenses/native/native-fixture/COPYING': b'native fixture notice',
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
				'packages': [{'name': 'native-fixture', 'version': '1.0',
					'licenses': ['MIT'], 'upstream': 'https://example.invalid/native'}],
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
		self.artwork.write_bytes((Path(__file__).resolve().parents[2] / 'branding/pixelquay.png').read_bytes())
		self.commit = '1' * 40

	def stage(self):
		return msix.stage_release(self.release, self.artwork, self.root / 'stage', self.commit)


class ManifestTests(QualificationFixture):
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
			msix.validate_manifest(data.replace(b'bin\\PixelQuay.exe', b'other.exe'))
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
		(self.release / 'bin/licenses/native/native-fixture/COPYING').unlink()
		with self.assertRaisesRegex(ValueError, '(?i)native.*notice'):
			self.stage()

	def test_stage_rejects_fontconfig_dll_without_runtime_configuration(self):
		data = b'fontconfig dll'
		(self.release / 'bin/libfontconfig-1.dll').write_bytes(data)
		inventory_path = self.release / 'bin/native-files.json'
		inventory = json.loads(inventory_path.read_text())
		inventory['files'].append({
			'path': 'bin/libfontconfig-1.dll', 'size': len(data), 'sha256': sha(data),
			'packages': [{'name': 'fontconfig-fixture', 'version': '1.0',
				'licenses': ['MIT'], 'upstream': 'https://example.invalid/fontconfig'}],
			'provenanceInputs': ['bin/libfontconfig-1.dll'],
		})
		inventory_path.write_text(json.dumps(inventory))
		notice = self.release / 'bin/licenses/native/fontconfig-fixture/COPYING'
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
				'packages': [{'name': 'native-fixture', 'version': '1.0', 'licenses': ['MIT'], 'upstream': 'https://example.invalid/native'}],
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

	def test_independent_zip_verifier_rejects_tamper_and_manifest_semantics(self):
		package, record = self.package(('bin/PixelQuay.exe', b'tampered'))
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
			archive.writestr('BIN/PixelQuay.exe', b'alias')
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
		package = self.output / 'PixelQuay.Qualification_1.0.0.0_x64.msix'
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
