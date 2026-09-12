# Copyright 2026 Trieflow LLC. MIT.
"""Retain only the current unsigned Store MSIX after both installed consumer runs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import sys

import consumer_workflow as oracle
import msix_qualification as msix
import source_publication as publication

SOURCE_INPUTS = ('qualify-msix-install.ps1', 'consumer_ui.ps1', 'consumer_native.cs',
                 'consumer_display.ps1', 'consumer_workflow.py', 'msix_qualification.py')
SURFACES = ('picker-0', 'opened', 'rotated', 'picker-3', 'recipe-saved', 'recipe-reloaded',
            'picker-6', 'export-plan', 'export-completed', 'picker-9', 'reopened', 'picker-11', 'reopened-witness')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate release evidence JSON key')
            result[key] = value
        return result
    with msix._regular_stream(path) as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    require(len(raw) <= 16 * 1024 * 1024, 'Oversized release evidence')
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique)


def digest(data):
    return dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def check_context(record, context):
    require(all(record.get(key) == value for key, value in context.items()), 'Stale source/run/attempt evidence')


def validate_consumer(folder, install):
    workflow = load(folder / 'consumer-workflow.json')
    facts = load(folder / 'consumer-verified-files.json')
    fixture = load(folder / 'consumer-fixture-state.json')
    require(workflow == install.get('consumer_workflow') and facts == install.get('consumer_images_and_recipe'),
            'Standalone and installed consumer evidence differ')
    require(workflow.get('schema') == 'pixelquay-consumer-workflow-v1'
            and workflow.get('phase') == 'normal-consumer-ui-actions' and workflow.get('ui_actions_completed') is True
            and type(workflow.get('process_id')) is int and workflow['process_id'] > 0, 'Incomplete real consumer actions')
    require(facts.get('source_unchanged') is True and fixture.get('cleanup_removed') is True
            and facts['profile_files'] == fixture['profile_files'], 'Consumer input/profile/cleanup evidence differs')
    source = oracle.encode_png(oracle.fixture_image())
    require(fixture['files']['source.png'] == digest(source), 'Original image fixture bytes differ')
    expected = dict(Name=oracle.RECIPE_NAME, Width=32, Height=48, Extension='png', Quality=None, Suffix='-proof', Overwrite=False)
    recipe = facts['recipe']
    require(set(recipe) == set(expected) | {'Id'} and re.fullmatch('[0-9a-f]{32}', recipe['Id'])
            and all(type(recipe[key]) is type(value) and recipe[key] == value for key, value in expected.items()),
            'Persisted actual recipe differs')
    for stage, filename, dimensions in (
            ('edited', 'edited.png', (64, 96, 6144)), ('exported', 'edited-proof.png', (32, 48, 1305)),
            ('reopened', 'reopened.png', (48, 32, 1536))):
        row = facts['images'][stage]
        require(row == workflow[stage] == fixture['stages'][stage], 'Consumer pixel oracle records differ: ' + stage)
        require(tuple(row.get(key) for key in ('width', 'height', 'checked_pixels')) == dimensions
                and all(type(row[key]) is int for key in ('width', 'height', 'checked_pixels', 'bytes'))
                and row['bytes'] > 0 and re.fullmatch('[0-9a-f]{64}', row['sha256'])
                and fixture['files'][filename] == {key: row[key] for key in ('bytes', 'sha256')},
                'Real consumer pixel/byte proof is incomplete: ' + stage)
    require([row['stage'] for row in workflow['observations']] == list(SURFACES), 'Missing original consumer surfaces')
    for surface in workflow['observations']:
        filename = 'consumer-' + surface['stage'] + '.png'
        require(surface['pid'] == workflow['process_id'] and type(surface['hwnd']) is int and surface['hwnd'] > 0
                and surface['screenshot'] == filename and msix.file_record(folder / filename)['sha256'] == surface['sha256'],
                'Changed or foreign consumer image evidence')
    return workflow


def validate_installation(folder, record, source, context, mode):
    install = load(folder / 'installation-qualification.json')
    check_context(install, context)
    require(install.get('identity') == msix.identity_for_mode(mode) == record['identity']
            and install.get('identity_mode') == mode and install.get('qualification_identity_only') is (mode == 'qualification')
            and install.get('store_identity_used') is (mode == 'store'), 'Wrong installed identity mode')
    for key in ('add_appx_completed', 'registration_ownership_established', 'unsigned_package_unchanged',
                'diagnostic_clean_close_verified', 'clean_close_verified', 'uninstall_verified',
                'installation_qualification_passed', 'workflow_acceptance', 'export_workflow_tested',
                'consumer_fixture_removed', 'all_owned_processes_stopped'):
        require(install.get(key) is True, 'Installed release gate failed: ' + key)
    require(install.get('primary_error') is None and install.get('certificate_private_key_exported') is False
            and type(install.get('normal_process_exit_code')) is int and install['normal_process_exit_code'] == 0,
            'Consumer failed normal exit or private key was exported')
    for key in ('preflight_package_full_names', 'residual_package_full_names', 'cleanup_errors', 'evidence_errors'):
        require(install.get(key) == [], 'Missing/unclean ownership evidence: ' + key)
    require(install.get('consumer_native_display', {}).get('restore_verified') is True, 'Native display was not restored')
    identity = record['identity']; package = install['package_full_name']
    suffix = 'r3hxytd7jt6c4' if mode == 'store' else '[a-z0-9]{13}'
    require(re.fullmatch(re.escape(identity['packageName'] + '_' + identity['version'] + '_x64__') + suffix, package or ''),
            'Installed full name differs from assigned identity')
    require(all(install.get(key) == package for key in ('owned_package_full_name', 'activated_process_package_full_name', 'diagnostic_process_package_full_name'))
            and install['aumid'] == identity['packageName'] + '_' + package.rsplit('__', 1)[1] + '!PixelQuay', 'Installed process/package ownership differs')
    require(install['unsigned_package_sha256'] == record['containerVerification']['package']['sha256'], 'Qualified unsigned package changed')
    for field, filename in (('executable_sha256', 'TintFable.exe'), ('coreclr_sha256', 'coreclr.dll'), ('hostfxr_sha256', 'hostfxr.dll')):
        require(install[field] == record['payload']['bin/' + filename]['sha256'], 'Installed runtime differs from payload')
    require(install.get('qualification_source_inputs') == {name: msix.file_record(source / 'installer/windows' / name)['sha256'] for name in SOURCE_INPUTS},
            'Consumer/qualification helper source changed')
    validate_consumer(folder, install)
    modules = load(folder / 'loaded-modules.json')
    require(isinstance(modules, list) and len(modules) == install['loaded_module_count'] and len(modules) > 0, 'Missing native module evidence')
    executable = [row for row in modules if row.get('origin') == 'package' and row.get('relative_path') == 'bin/TintFable.exe']
    require(len(executable) == 1, 'Missing unique installed executable module')
    root = PureWindowsPath(executable[0]['path']).parent.parent
    require(root.is_absolute() and root.name == package and root.parent.name.casefold() == 'windowsapps', 'Unexpected installed package root')
    payload = {key.casefold(): value for key, value in record['payload'].items()}; seen = set(); required = {'bin/tintfable.exe', 'bin/coreclr.dll', 'bin/hostfxr.dll'}
    for module in modules:
        path = PureWindowsPath(module['path'])
        require(path not in seen and '..' not in path.parts, 'Duplicate or noncanonical loaded module path'); seen.add(path)
        if module['origin'] == 'package':
            relative = module['relative_path']; entry = payload.get(relative.casefold())
            require(entry and module['sha256'] == entry['sha256'] and path == root / relative, 'Loaded module differs from exact package bytes/path')
            required.discard(relative.casefold())
        else:
            require(module['origin'] == 'windows' and path.is_absolute() and path.is_relative_to(PureWindowsPath('C:/Windows'))
                    and module['relative_path'] is None and module['sha256'] is None, 'Unqualified external module origin')
    require(not required, 'Missing actual loaded runtime modules')
    return install


def clean_source(source, commit):
    require(publication.git(source, 'rev-parse', 'HEAD').decode().strip() == commit, 'Export source commit changed')
    require(not publication.git(source, 'status', '--porcelain=v1', '--untracked-files=all').strip(), 'Export source is not clean')


def export_store(source, evidence, qualification_package, store_package, output, context):
    source, evidence, output = Path(source).resolve(), Path(evidence).resolve(), Path(output).absolute()
    require(re.fullmatch('[0-9a-f]{40}', context.get('source_commit', ''))
            and all(re.fullmatch('[1-9][0-9]*', context.get(key, '')) for key in ('workflow_run_id', 'workflow_run_attempt')), 'Missing current CI source/run context')
    require(output == evidence / 'store-upload' and not os.path.lexists(output), 'Store output must be a new evidence/store-upload directory')
    commit = context['source_commit']; clean_source(source, commit)
    before = msix.inventory_tree(evidence)
    startup = load(evidence / 'windows-startup.json')
    require(startup.get('source_commit') == commit and startup.get('windows_native_startup') is True, 'Current native startup failed')
    cleanup = load(evidence / 'unpackaged-profile-cleanup.json')
    require(all(cleanup.get(key) is True for key in ('retained_process_owned', 'process_stopped', 'normal_close_verified', 'owned_profile_and_fixture_removed'))
            and cleanup.get('primary_error') is None and cleanup.get('cleanup_errors') == [], 'Unpackaged profile lifecycle failed')
    records = {}
    paths = dict(qualification=Path(qualification_package), store=Path(store_package))
    for mode in ('qualification', 'store'):
        record_path = evidence / ('msix-store-package-record.json' if mode == 'store' else 'msix-package-record.json')
        records[mode] = msix.verify_record_inputs(paths[mode], record_path, source / 'release', source / 'branding/tintfable.png', commit, mode)
        validate_installation(evidence / ('msix-store-install' if mode == 'store' else 'msix-install'), records[mode], source, context, mode)
    require(records['store']['releaseInput'] == records['qualification']['releaseInput'], 'Both identities must contain the exact same build')
    require(startup['executable_sha256'].lower() == records['store']['payload']['bin/TintFable.exe']['sha256'], 'Startup executable differs from final package')
    public = publication.verify_public_sources(source, evidence, records['store'], commit)
    require(msix.inventory_tree(evidence) == before, 'Qualification evidence changed during public verification')
    clean_source(source, commit)
    record_path = evidence / 'msix-store-package-record.json'
    record = msix.verify_record_inputs(paths['store'], record_path, source / 'release', source / 'branding/tintfable.png', commit, 'store')
    for ancestor in (output.parent, *output.parent.parents): msix._reject_link(ancestor)
    output.mkdir()
    try:
        filename = msix.package_name('store'); destination = output / filename
        with msix._regular_stream(paths['store']) as original, destination.open('xb') as target:
            shutil.copyfileobj(original, target, 1024 * 1024)
        require(msix.verify_msix(destination, record['payload'], 'store') == record['containerVerification'], 'Retained unsigned package changed')
        clean_source(source, commit)
        require({key: value for key, value in msix.inventory_tree(evidence).items() if not key.startswith('store-upload/')} == before, 'Evidence changed during retention')
        receipt = dict(schema_version=1, product='TintFable', generated_at_utc=datetime.now(timezone.utc).isoformat(), **context,
                       identity=msix.STORE_IDENTITY, package=dict(filename=filename, **msix.file_record(destination)), signed=False,
                       store_upload_ready=True, submitted=False, public_release=False, qualified_identity_modes=['qualification', 'store'],
                       public_sources=public, qualification_evidence=before)
        msix._write_new(output / 'release-ready.json', msix._canonical_json(receipt))
    except BaseException:
        for name in (msix.package_name('store'), 'release-ready.json'): (output / name).unlink(missing_ok=True)
        output.rmdir()
        raise
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'evidence', 'qualification-package', 'store-package', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    if sys.platform != 'win32' or os.environ.get('CI') != 'true' or os.environ.get('GITHUB_REPOSITORY') != 'hashfunction/pixelquay':
        parser.error('Store retention requires the current TintFable Windows CI run')
    context = dict(source_commit=os.environ.get('GITHUB_SHA', ''), workflow_run_id=os.environ.get('GITHUB_RUN_ID', ''), workflow_run_attempt=os.environ.get('GITHUB_RUN_ATTEMPT', ''))
    export_store(args.source_root, args.evidence, args.qualification_package, args.store_package, args.output, context)
    print('PASS: unsigned TintFable Store package retained after both full installed workflows and public source verification.')


if __name__ == '__main__': main()
