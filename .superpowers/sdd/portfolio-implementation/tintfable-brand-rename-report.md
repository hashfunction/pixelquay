# TintFable source rename for independent review

Base: `fc082d18545a5a79d8a2efbe21345dae0b9f2756` (reviewed native placement candidate).
Approved brand: TintFable. Canonical URL: `https://tintfable.trieflow.com`.
This implements the source portion of the parent product-renaming plan. No public
push, workflow dispatch, Store operation, parent status, or website edit is included.

## Changed customer contracts

The application, CLI description, document/main titles, About, product/support/
privacy actions, own notices, desktop display metadata, and documentation use
TintFable. The assembly and apphost are `TintFable.dll` / `TintFable.exe`.
Application version is 1.0.1 and assembly/package version is 1.0.1.0. The Inno
installer name/output and portable ZIP name use TintFable; launch/package helpers
reference the actual renamed assembly and executable. The obsolete upstream main
assembly reference in the retained Linux launcher/pkg-config entry follows the
same renamed DLL without changing its install directory.

The disposable package file is `TintFable.Qualification_1.0.1.0_x64.msix`.
The generated manifest and its independent validator require TintFable display
names, version 1.0.1.0 and `bin\TintFable.exe`. The installer independently checks
that same executable/version and hashes the installed executable/runtime inputs.
Workflow/artifact display names use TintFable, including retained library-proof
workflow labels; immutable historical proof receipts/source files remain intact.
Only customer-title literals changed in the consumer UI driver. Its exact input,
UI ownership, geometry, pixels, recipe/output/reopen and lifetime checks remain.

The original raster icon contains no text. PNG and ICO files have renamed paths
with byte-identical contents; SVG title/description text changes while the paths,
colors and shapes remain unchanged. No screenshots were fabricated or edited.
PNG SHA256: `95e6b02e3afe421d29cc61abdd5791b5b45fd131c583ca27520b277853bd42d8`.
Each ICO SHA256: `11df5f35d11a4ee2997d8a4760a7440ec48f5149ec15bb5133ca6d792738bc2c`.

## Preserved compatibility and evidence

- Assigned Store identity remains `1659hashfunction.PixelQuay`. The assigned
  publisher/application ID belong to the parent release controller; this source
  has no assigned Store manifest to alter. No Store signing tuple is invented.
- Disposable identity remains `Trieflow.PixelQuay.Qualification`, publisher
  `CN=PixelQuay-CI-Qualification`, application ID `PixelQuay`.
- GTK/application/icon ID remains `com.trieflow.PixelQuay`; corresponding desktop
  resource filenames and internal root window ID remain stable.
- Preferences/add-ins remain in the established `PixelQuay` application-data
  directory; recipes retain `pixelquay.export-recipes.v1`. Inno AppId remains
  `5296E263-5F86-4869-9D59-70D1A8E8A832`, with its original install directory.
- Internal qualification schemas, namespaces, ownership/staging markers, environment
  variables and repository/branch names retain their existing identifiers.
- Upstream Pinta/Paint.NET attribution, license texts, native corresponding-source
  inputs, proof patches/receipts and old validation/design reports remain original.

The remaining `PixelQuay`/`pixelquay` source references were inspected and fall in
these compatibility, internal-helper, negative-fixture or historical categories.
The historic Windows report retains the actual old window title and executable
rather than relabeling old evidence. License/provenance directories and the
native input/display/file-workflow production helpers compare byte-identical to
base. New final Windows evidence is still required after the rename.

## Executed verification

The new manifest regression first failed against the old display name. It now
executes the production generator/independent validator and rejects each old
property/visual display name, executable and version, plus accidental package or
application-ID rename. The production PowerShell preflight fixture separately
rejects old executable/version and renamed package/publisher/application IDs,
and requires registration queries to use the retained qualification identity.
The existing recipe-store fixture now seeds a literal pre-rename recipe key,
loads/saves/reloads the recipe through production code, and verifies no new-brand
key appears. It uses an isolated settings adapter and does not modify user data.

- Full local solution build succeeded and produced `build/bin/TintFable.dll`.
- Full managed suite: 900 passed, one existing Voronoi8 skip (783 core + 117 effects).
- All Windows Python fixtures: 71 total, 70 passed, one existing Windows-only
  junction skip. Final log: `/private/tmp/tintfable-python-tests.log`.
- All 12 Windows PowerShell fixture scripts passed. The expanded final preflight
  script passed all 15 variants. Logs: `/private/tmp/tintfable-pwsh-tests.log` and
  `/private/tmp/tintfable-preflight-rename-tests.log`.
- Actual built CLI `--help` reports TintFable and `--version` reports
  `1.0.1+fc082d18545a5a79d8a2efbe21345dae0b9f2756` (the pre-commit source SHA).
  Reflection confirms actual assembly name TintFable, version 1.0.1.0 and product
  attribute TintFable. All Windows PowerShell scripts parse; XML parses and
  `git diff --check` pass. Raster byte comparisons pass.

This macOS host has .NET SDK 8.0.204, while production `global.json`/Windows CI pins
8.0.425 unchanged. Local commands invoke the installed SDK's MSBuild explicitly:

```
DOTNET_MSBUILD_SDK_RESOLVER_SDKS_DIR=/usr/local/share/dotnet/sdk/8.0.204/Sdks \
DYLD_LIBRARY_PATH=/opt/homebrew/lib \
dotnet exec /usr/local/share/dotnet/sdk/8.0.204/MSBuild.dll Pinta.sln \
-restore -target:VSTest -property:Configuration=Release -verbosity:minimal
```

The build used the same command with `-target:Build`. Full logs are
`/private/tmp/tintfable-dotnet-tests.log` and `/private/tmp/tintfable-build.log`.
PowerShell 7.6.6 is at
`/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh`,
with `TMPDIR=/private/tmp`; Python is 3.10. Actual native Windows 8.0.425 build,
MSIX activation/consumer flow/normal close/uninstall, native placement, profile
persistence across an installed update, and renamed marketing screenshots remain
pending. Local checks do not establish Store readiness or final website state.
