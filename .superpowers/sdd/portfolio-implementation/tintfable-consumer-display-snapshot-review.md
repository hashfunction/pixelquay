# TintFable consumer evidence snapshot — run 34690127749

Base nested source `4180f4fb543169c080d5cee2a1c74f89dfea063d`.
Actual failed [Windows run 34690127749](https://github.com/hashfunction/pixelquay/actions/runs/34690127749)
used public source `fe08ba6bb7d46049e7547b507483195a3cf6a2a3`.

## Actual failure and exact difference

Both installed identity receipts record successful image editing, recipe save/
reload, export, reopen, normal exit 0, uninstall and owned fixture cleanup.
Their primary, cleanup and evidence errors are empty. The final unsigned Store
export nevertheless failed at `store_export.py:53` with
`Standalone and installed consumer evidence differ`. No accepted Store upload
artifact resulted from this run.

Recursive comparison of each standalone `consumer-workflow.json` against the
embedded `installation-qualification.json.consumer_workflow` found exactly
three differences, identical in both identity runs:

| Field under native_display | Standalone workflow | Embedded workflow |
| --- | --- | --- |
| restore_result | null | 0 |
| restored | null | Original 1024×768, 32-bpp, 64-Hz mode, orientation/flags 0 |
| restore_verified | false | true |

There were no other workflow differences. Standalone `consumer-verified-files`
and embedded `consumer_images_and_recipe` matched exactly in both runs. No date
or depth conversion difference was observed.

`Invoke-PixelQuayConsumerWorkflow` assigned the mutable outer
`DisplayState.displayEvidence` dictionary directly to `ui.record.native_display`
in its finally block. It wrote the standalone record using the exclusive
CreateNew writer and returned that same record. Outer cleanup subsequently ran
`Restore-PixelQuayConsumerDisplay`, which updated the three dictionary fields.
The final installation writer serialized the now-mutated object. This explains
the observed differences without weakening the exporter or altering receipts.

Original evidence remains unchanged under
`/private/tmp/tintfable-34690127749-review/TintFable-Windows-qualification/pixelquay/pixelquay/build-evidence`.
SHA256 values:

| Identity / file | SHA256 |
| --- | --- |
| qualification / installation-qualification.json | `ae43906396d51f4385e7205beabfef7490f42e5570408f56f31150e11023e6e1` |
| qualification / consumer-workflow.json | `a6fe577403a064548bebe80bb67e5b78d34bb104d76d163b5ef36acfd79a2847` |
| qualification / consumer-verified-files.json | `47e21164b3f6209aa7eaeb2e2438542e3e590d84b447a5fd09e5da55c04232c0` |
| store / installation-qualification.json | `840bd5088cf59fb107f8c736708ec23c0aee37d0074b866fffd9eeeabafea68b` |
| store / consumer-workflow.json | `b2df8d3f8e16fdd54c8cdcd0a6805abb1fa51d26e5d4dabe22ee38b9418b6980` |
| store / consumer-verified-files.json | `8a825fc82ce86fc0e4578a168efcafcfb79e6cb17041d534e3bf33b755c359c2` |

## Source correction and preserved gates

The sole production change deep-copies the display evidence through the existing
JSON representation when attaching it to the workflow record. This freezes the
workflow-time observation, including its null/false restoration fields. The
outer `consumer_native_display` remains the independent final restoration
record and must still have `restore_verified=true` for Store export.

The exporter, its whole-object equality comparison, all qualification inputs,
source/run/package/module bindings, actual consumer actions, original display
restore, normal close/uninstall and CreateNew evidence semantics are unchanged.
No field is dropped or exempted. No old artifact is rewritten. No product,
branding, package version, historical package binding or marketing input changes
are included.

## Regression and verification

The 6-KB fixture `34690127749-display-lifecycle.json` retains the actual complete
before/after display records with original receipt hashes and run/source IDs.
The PowerShell test extracts and executes the real consumer finally block and
CreateNew writer, then invokes production restoration with only the native
display calls adapted. It failed before the fix with the actual equality error.
After the fix, it verifies equality through successful and failed restoration,
unchanged standalone file bytes, retained original consumer failure, broker
disposal, final restoration truth, and isolation of nested mode-list mutations.

The exporter regression requires both equal workflow snapshots and independent
successful restoration. It separately reproduces all three corruptions for both
identities (six refusals), rejects missing final restore success in both modes,
and passes the full local export fixture only after both records are correct.
This adds coverage without changing exporter acceptance code.

Final local verification:

- `python3 -m unittest discover -s installer/windows -p 'test_*.py' -v`: 86 tests,
  85 passed, one existing Windows-native junction test skipped on macOS.
- All 13 top-level `installer/windows/test_*.ps1` fixtures passed in isolated
  PowerShell processes, plus store-mode registration/unpack fixtures: 15 runs.
- `git diff --check` passed.

PowerShell runtime:
`/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh`.
Logs: `/private/tmp/tintfable-display-snapshot-red.log`,
`/private/tmp/tintfable-display-snapshot-green.log`,
`/private/tmp/tintfable-display-python-tests.log`, and
`/private/tmp/tintfable-display-powershell-tests.log`.
The existing CI fixture list already runs the extended tests.

Independent review and a fresh Windows run are pending. The previous actual
installed successes do not establish that this changed source has passed final
Store export. No push, dispatch, Store/site/parent changes or Ink/File source
edits were performed.
