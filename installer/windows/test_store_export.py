# Copyright 2026 Trieflow LLC. MIT. Production export boundaries with a tiny real package/Git tree.
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import tarfile
import unittest
from unittest import mock

import msix_qualification as msix
import source_publication as publication
import store_export as export
import test_msix_qualification as fixtures

HERE = Path(__file__).resolve().parent
NATIVE = json.loads((HERE / 'test-fixtures/store-export/34684998708-consumer-success.json').read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(msix._canonical_json(value))


class ExportTests(fixtures.QualificationFixture):
    def setUp(self):
        super().setUp()
        self.root = self.root.resolve()
        self.source = self.root / 'source'; self.source.mkdir()
        self.release = self.release.rename(self.source / 'release')
        (self.source / 'branding').mkdir()
        self.artwork = self.artwork.rename(self.source / 'branding/tintfable.png')
        for name in export.SOURCE_INPUTS:
            target = self.source / 'installer/windows' / name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((HERE / name).read_bytes())
        (self.source / '.gitignore').write_text('release/\n')
        (self.source / '.gitattributes').write_text('* -text\n')
        for arguments in (('init', '-q'), ('config', 'user.email', 'fixture@example.invalid'), ('config', 'user.name', 'Fixture'), ('add', '.'), ('commit', '-qm', 'Exact source fixture')):
            subprocess.run(['git', '-C', str(self.source), *arguments], check=True, capture_output=True)
        self.commit = publication.git(self.source, 'rev-parse', 'HEAD').decode().strip()
        self.context = dict(source_commit=self.commit, workflow_run_id='34684998708', workflow_run_attempt='1')
        sdk = self.root / 'Windows Kits/10/bin/10.0.26100.0/x64'; sdk.mkdir(parents=True)
        self.makeappx = sdk / 'makeappx.exe'; self.makeappx.write_bytes(b'fixture original SDK')
        self.archive = self.root / 'application.tar.gz'
        subprocess.run(['git', '-C', str(self.source), 'archive', '--format=tar.gz', '--prefix=fixture/', '-o', str(self.archive), self.commit], check=True)
        self.evidence = self.root / 'evidence'; self.evidence.mkdir(); self.packages = {}; self.records = {}
        for mode in ('qualification', 'store'):
            stage = self.root / ('stage-' + mode)
            record = msix.stage_release(self.release, self.artwork, stage, self.commit, mode)
            package = self.root / msix.package_name(mode)
            fixtures.BuildFlowTests.fake_sdk(self, ['makeappx', 'pack', '/d', str(stage), '/p', str(package)])
            record.update(makeAppx=msix._tool_record(self.makeappx, '10.0.26100.0'), containerVerification=msix.verify_msix(package, record['payload'], mode),
                          unpackedVerification={'verifiedPayloadFiles': len(record['payload'])})
            self.packages[mode] = package; self.records[mode] = record
            write(self.evidence / ('msix-store-package-record.json' if mode == 'store' else 'msix-package-record.json'), record)
            self.installation(mode, record)
        write(self.evidence / 'windows-startup.json', dict(source_commit=self.commit, windows_native_startup=True,
              executable_sha256=self.records['store']['payload']['bin/TintFable.exe']['sha256']))
        write(self.evidence / 'unpackaged-profile-cleanup.json', dict(retained_process_owned=True, process_stopped=True,
              normal_close_verified=True, owned_profile_and_fixture_removed=True, primary_error=None, cleanup_errors=[]))
        self.public_reads = 0

    @property
    def commands(self):
        return []

    def installation(self, mode, record):
        folder = self.evidence / ('msix-store-install' if mode == 'store' else 'msix-install'); folder.mkdir()
        facts = copy.deepcopy(NATIVE)
        workflow = facts['consumer-workflow.json']
        # Fixture PNG bytes exercise real filesystem hashing; these are not product screenshots.
        for row in workflow['observations']:
            png = b'fixture native observation:' + row['stage'].encode()
            (folder / row['screenshot']).write_bytes(png); row['sha256'] = export.digest(png)['sha256']
        install = facts['installation-qualification.json']; identity = msix.identity_for_mode(mode)
        package = identity['packageName'] + '_1.0.1.0_x64__' + ('r3hxytd7jt6c4' if mode == 'store' else 'zdhxetmajqhn8')
        install.update(self.context, identity=identity, identity_mode=mode, qualification_identity_only=mode == 'qualification', store_identity_used=mode == 'store',
                       consumer_workflow=workflow, normal_process_exit_code=0, unsigned_package_sha256=record['containerVerification']['package']['sha256'],
                       aumid=identity['packageName'] + '_' + package.rsplit('__', 1)[1] + '!PixelQuay',
                       qualification_source_inputs={name: msix.file_record(self.source / 'installer/windows' / name)['sha256'] for name in export.SOURCE_INPUTS})
        for field in ('package_full_name', 'owned_package_full_name', 'activated_process_package_full_name', 'diagnostic_process_package_full_name'): install[field] = package
        modules = []
        for field, filename in (('executable_sha256', 'TintFable.exe'), ('coreclr_sha256', 'coreclr.dll'), ('hostfxr_sha256', 'hostfxr.dll')):
            relative = 'bin/' + filename; install[field] = record['payload'][relative]['sha256']
            modules.append(dict(name=filename, path='C:\\Program Files\\WindowsApps\\' + package + '\\bin\\' + filename,
                                origin='package', relative_path=relative, sha256=install[field]))
        install['loaded_module_count'] = len(modules)
        write(folder / 'loaded-modules.json', modules)
        for name, value in facts.items(): write(folder / name, value)

    def public_read(self, source, evidence, record, commit):
        self.public_reads += 1
        return publication.verify_application_archive(self.archive, source, commit)

    def run_export(self):
        with mock.patch.object(publication, 'verify_public_sources', side_effect=self.public_read):
            return export.export_store(self.source, self.evidence, self.packages['qualification'], self.packages['store'], self.evidence / 'store-upload', self.context)

    def test_exact_both_lifecycles_package_source_and_receipt_retained(self):
        result = self.run_export(); output = self.evidence / 'store-upload'
        self.assertEqual(1, self.public_reads)
        self.assertEqual({msix.package_name('store'), 'release-ready.json'}, {p.name for p in output.iterdir()})
        self.assertEqual(self.packages['store'].read_bytes(), (output / msix.package_name('store')).read_bytes())
        self.assertTrue(result['store_upload_ready']); self.assertFalse(result['signed']); self.assertFalse(result['submitted'])
        self.assertEqual(['qualification', 'store'], result['qualified_identity_modes'])

    def test_actual_lifecycle_wrong_identity_stale_context_module_and_cleanup_refusals(self):
        for mode in ('qualification', 'store'):
            folder = self.evidence / ('msix-store-install' if mode == 'store' else 'msix-install')
            path = folder / 'installation-qualification.json'; baseline = export.load(path)
            for key, value in (('workflow_acceptance', False), ('clean_close_verified', False), ('uninstall_verified', False),
                    ('all_owned_processes_stopped', False), ('consumer_fixture_removed', False), ('normal_process_exit_code', -1),
                    ('normal_process_exit_code', False), ('workflow_run_id', '1'), ('source_commit', '0' * 40),
                    ('identity_mode', 'store' if mode == 'qualification' else 'qualification'), ('residual_package_full_names', ['foreign'])):
                bad = copy.deepcopy(baseline); bad[key] = value; write(path, bad)
                with self.subTest(mode=mode, key=key, value=value), self.assertRaises(ValueError): self.run_export()
                self.assertFalse((self.evidence / 'store-upload').exists())
            write(path, baseline)
            modules_path = folder / 'loaded-modules.json'; modules = export.load(modules_path)
            for field, value in (('sha256', '0' * 64), ('path', 'C:\\foreign\\TintFable.exe'), ('origin', 'external')):
                bad = copy.deepcopy(modules); bad[0][field] = value; write(modules_path, bad)
                with self.subTest(mode=mode, module=field), self.assertRaises(ValueError): self.run_export()
            write(modules_path, modules)
        self.assertEqual(0, self.public_reads)

    def test_pixel_recipe_screenshot_and_source_tampering_refused(self):
        folder = self.evidence / 'msix-store-install'
        for filename in ('consumer-workflow.json', 'consumer-verified-files.json', 'consumer-fixture-state.json'):
            path = folder / filename; baseline = path.read_bytes(); value = export.load(path)
            if filename == 'consumer-workflow.json': value['ui_actions_completed'] = False
            elif filename == 'consumer-verified-files.json': value['images']['exported']['checked_pixels'] = 0
            else: value['cleanup_removed'] = False
            write(path, value)
            with self.subTest(filename=filename), self.assertRaises(ValueError): self.run_export()
            path.write_bytes(baseline)
        png = folder / 'consumer-opened.png'; png.write_bytes(b'changed evidence')
        with self.assertRaises(ValueError): self.run_export()
        self.assertEqual(0, self.public_reads)

    def test_public_failure_or_concurrent_evidence_change_cannot_retain_package(self):
        with mock.patch.object(publication, 'verify_public_sources', side_effect=ValueError('unpublished source')):
            with self.assertRaisesRegex(ValueError, 'unpublished'):
                export.export_store(self.source, self.evidence, self.packages['qualification'], self.packages['store'], self.evidence / 'store-upload', self.context)
        original = self.public_read
        def race(*args):
            result = original(*args); (self.evidence / 'changed.txt').write_bytes(b'late change'); return result
        self.public_read = race
        with self.assertRaisesRegex(ValueError, 'evidence changed'): self.run_export()
        self.assertFalse((self.evidence / 'store-upload').exists())

    def test_dirty_source_and_existing_output_are_preserved(self):
        path = self.source / 'untracked.txt'; path.write_bytes(b'uncommitted source')
        with self.assertRaisesRegex(ValueError, 'not clean'): self.run_export()
        path.unlink(); output = self.evidence / 'store-upload'; output.mkdir(); (output / 'foreign').write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError, 'new evidence'): self.run_export()
        self.assertEqual(b'preserve', (output / 'foreign').read_bytes())


class PublicationTests(unittest.TestCase):
    def test_all_actual_owner_versions_and_binary_archives_need_source_coverage(self):
        baseline = publication.load(HERE / 'source/native-source-evidence.json')
        supplement = publication.load(HERE / 'source/source-supplements.json')
        owners = {row['package']: dict(name=row['package'], version=row['version'], licenses=row['declaredLicenses']) for row in baseline['packages']}
        hashes = {Path(row['packageArchive']).name: row['packageSha256'] for row in baseline['packages']}
        record = {'releaseInput': {}}
        for row in supplement['supplements']:
            owners[row['package']] = dict(name=row['package'], version=row['version'], licenses=row['declared_licenses'])
            hashes[row['package_archive']] = row['package_sha256']
            for module in row['native_modules']: record['releaseInput'][module['path']] = {key: module[key] for key in ('bytes', 'sha256')}
            record['releaseInput']['bin/' + row['installed_notice']['path']] = row['original_notice']
        native = {'files': [{'packages': [owner]} for owner in owners.values()]}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); shutil.copytree(HERE / 'source', root / 'installer/windows/source')
            evidence = root / 'evidence'; evidence.mkdir()
            hashfile = evidence / 'msys2-cache-sha256.txt'
            original_hashes = ''.join(value+' *build-evidence/package-cache/'+name+'\n' for name, value in hashes.items())
            hashfile.write_text(original_hashes)
            native_path = root / 'release/bin/native-files.json'; write(native_path, native)
            self.assertEqual(64, publication.validate_native_sources(root, evidence, record)['owners'])
            for change in ('new-version', 'missing-owner', 'wrong-license', 'changed-archive', 'changed-module', 'changed-notice'):
                bad = copy.deepcopy(native); changed_record = copy.deepcopy(record)
                if change == 'new-version': bad['files'][0]['packages'][0]['version'] = '999.0-1'
                elif change == 'missing-owner': bad['files'].pop()
                elif change == 'wrong-license': bad['files'][0]['packages'][0]['licenses'] = ['unreviewed']
                elif change == 'changed-archive': hashfile.write_text(original_hashes.replace(next(iter(hashes.values())), '0' * 64))
                elif change == 'changed-module': changed_record['releaseInput']['bin/libgtk-4-1.dll']['sha256'] = '0' * 64
                else: changed_record['releaseInput']['bin/' + supplement['supplements'][0]['installed_notice']['path']]['sha256'] = '0' * 64
                write(native_path, bad)
                with self.subTest(change=change), self.assertRaises(ValueError): publication.validate_native_sources(root, evidence, changed_record)
                hashfile.write_text(original_hashes)

    def test_actual_published_supplement_record_and_wrong_missing_unverified_refusals(self):
        path = HERE / 'source/source-supplements.json'
        record = publication.load(HERE / 'source/native-source-supplement-publication.json')
        publication.validate_publication(record, path)
        for change in ('missing', 'unverified', 'wrong-release', 'changed-sha', 'duplicate'):
            bad = copy.deepcopy(record)
            if change == 'missing': bad['assets'].pop()
            elif change == 'unverified': bad['publication_verified'] = False
            elif change == 'wrong-release': bad['release_url'] += '-different'
            elif change == 'changed-sha': bad['assets'][0]['sha256'] = '0' * 64
            else: bad['assets'][1] = bad['assets'][0]
            with self.subTest(change=change), self.assertRaises(ValueError): publication.validate_publication(bad, path)

    def test_original_publication_json_bytes_survive_real_project_attributes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            shutil.copyfile(HERE.parents[1] / '.gitattributes', root / '.gitattributes')
            folder = root / 'installer/windows/source'
            folder.mkdir(parents=True)
            paths = list((HERE / 'source').glob('*.json'))
            self.assertEqual(5, len(paths))
            for path in paths: shutil.copyfile(path, folder / path.name)
            (root / 'ordinary.ps1').write_bytes(b'first\nsecond\n')
            for args in (('init', '-q'), ('config', 'core.autocrlf', 'true'), ('config', 'user.email', 'fixture@example.invalid'), ('config', 'user.name', 'Fixture'), ('add', '.'), ('commit', '-qm', 'fixture')):
                subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
            for path in folder.glob('*.json'): path.unlink()
            (root / 'ordinary.ps1').unlink()
            subprocess.run(['git', '-C', str(root), 'checkout', '--', '.'], check=True)
            self.assertEqual(b'first\r\nsecond\r\n', (root / 'ordinary.ps1').read_bytes())
            for path in paths: self.assertEqual(path.read_bytes(), (folder / path.name).read_bytes())
            publication.validate_publication(publication.load(folder / 'native-source-supplement-publication.json'), folder / 'source-supplements.json')

    def test_git_archive_matches_blobs_across_actual_crlf_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); source = root / 'source'; source.mkdir()
            (source / '.gitattributes').write_bytes(b'* text=auto\nsource.json -text\n')
            (source / 'file.ps1').write_bytes(b'one\ntwo\n'); (source / 'source.json').write_bytes(b'{"exact":true}\n')
            for args in (('init', '-q'), ('config', 'user.email', 'fixture@example.invalid'), ('config', 'user.name', 'Fixture'), ('add', '.'), ('commit', '-qm', 'fixture')):
                subprocess.run(['git', '-C', str(source), *args], check=True, capture_output=True)
            commit = publication.git(source, 'rev-parse', 'HEAD').decode().strip()
            archive = root / 'source.tar.gz'; subprocess.run(['git', '-C', str(source), 'archive', '--format=tar.gz', '--prefix=fixture/', '-o', str(archive), commit], check=True)
            (source / 'file.ps1').unlink(); (source / 'source.json').unlink()
            subprocess.run(['git', '-C', str(source), '-c', 'core.autocrlf=true', 'checkout', '--', '.'], check=True)
            self.assertEqual(b'one\r\ntwo\r\n', (source / 'file.ps1').read_bytes())
            self.assertEqual(b'{"exact":true}\n', (source / 'source.json').read_bytes())
            self.assertEqual(3, publication.verify_application_archive(archive, source, commit)['verified_tracked_files'])
            for mutation in ('changed', 'omitted', 'extra'):
                bad = root / (mutation + '.tar.gz')
                with tarfile.open(archive, 'r:gz') as original, tarfile.open(bad, 'w:gz') as target:
                    for member in original:
                        if mutation == 'omitted' and member.name == 'fixture/file.ps1': continue
                        data = original.extractfile(member).read() if member.isfile() else None
                        if mutation == 'changed' and member.name == 'fixture/file.ps1': data = b'changed'; member.size = len(data)
                        target.addfile(member, io.BytesIO(data) if data is not None else None)
                    if mutation == 'extra':
                        member = tarfile.TarInfo('fixture/extra.txt'); member.size = 5; target.addfile(member, io.BytesIO(b'extra'))
                with self.subTest(mutation=mutation), self.assertRaises(ValueError): publication.verify_application_archive(bad, source, commit)


if __name__ == '__main__': unittest.main()
