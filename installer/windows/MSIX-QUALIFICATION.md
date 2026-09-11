# PixelQuay disposable MSIX qualification

This path builds and installs a **CI-only** package from the complete verified Windows `release` directory. It does not assign or approximate a Microsoft Store identity. It does not clear licenses, sign a release package, test the export workflow, or authorize binary publication.

Prior Windows run `34578052932` passed 899 tests, launched the unpackaged `release/bin/PixelQuay.exe` main window, and recorded 233 loaded modules plus 64 distinct native package owners. Its evidence explicitly says `msix_built=false`; it is input history rather than MSIX evidence.

The fixed qualification identity is:

- package: `Trieflow.PixelQuay.Qualification`
- publisher: `CN=PixelQuay-CI-Qualification`
- version: `1.0.0.0`
- architecture: `x64`
- application ID: `PixelQuay`
- executable: `bin\PixelQuay.exe`
- capability: `runFullTrust`

The manifest is created through Python's XML API and permits one `Windows.Desktop` dependency, one full-trust application, and one `runFullTrust` restricted capability. It has no associations, protocols, updater, registry declarations, COM extensions, or Store identity.

## Package boundary

`msix_qualification.py` rejects a preexisting output, links/reparse points, special files, unsafe Windows names, case/Unicode aliases, input changes, and missing self-contained runtime files. It requires:

```text
release/bin/PixelQuay.exe
release/bin/PixelQuay.dll
release/bin/PixelQuay.runtimeconfig.json
release/bin/coreclr.dll
release/bin/hostfxr.dll
release/bin/native-files.json
release/bin/licenses/managed-packages.json
```

Native inventory rows are rebound to their actual `release/bin`, `release/etc`, `release/lib`, or `release/share` bytes and hashes. Each recorded native package must include a complete source-to-copy notice mapping under `release/bin/licenses/native`, with exact paths, sizes and SHA-256 values; a nonempty notice directory alone is insufficient. Each managed inventory package must point to a notice retained under `release/bin/licenses`. The helper copies the complete tree without flattening it, so locale, icon, font, loader, schema, imported configuration, runtime, and license bytes retain their release paths.

These checks prove byte retention and provenance-record consistency. The inventory status remains `requires-release-license-review`; corresponding source, LGPL replacement mechanics, fonts/resources, codecs, supplemental notices, and every shipped dependency still require an independent release audit.

The three Store-sized PNGs are deterministically resized from the original `branding/pixelquay.png`. Their dimensions and SHA-256 hashes, the original artwork hash, every release-input hash, and every final payload hash are recorded in `package-record.json`.

The builder requires the absolute `x64\makeappx.exe` path under an explicit Windows SDK version. It hashes the tool before every command and afterward, packs with `/v /h SHA256` and no semantic-validation bypass, unpacks into a fresh directory, and verifies:

- parsed manifest identity, executable, assets, target family, application, and capability;
- every independently parsed MSIX entry and hash;
- every SDK-unpacked payload path and hash;
- absence of unreviewed payload entries and Windows path aliases.

The unsigned package and `package-record.json` are published only into a newly created output directory. All record claims remain false for signing, installation, license clearance, public release, and Store submission.

Windows run `34596219976` completed actual SDK pack/unpack, then exposed an independent-verifier filename mismatch: SDK 10.0.26100.0 stored `bin/libc++.dll` as `bin/libc%2B%2B.dll` inside the ZIP. MSIX uses the [OPC format](https://learn.microsoft.com/en-us/windows/win32/appxpkg/appx-portal). The verifier now decodes URI escapes exactly once before comparing payload names and hashes, rejects encoded separators, malformed escapes, invalid UTF-8 and unsafe decoded paths, and checks aliases after decoding. A literal percent filename remains literal after one decode; plus signs never become spaces. New ZIP fixtures cover the actual library name, Unicode/spaces, literal percent, aliases and invalid paths. The prior code failed the encoded-library fixture; the repaired Python suite passes 35 cases with one Windows-only junction case skipped locally. Actual installed-package qualification still requires the next Windows run.

## Root-owned workflow hooks

After the existing restore/test/publish/inventory steps produce `release`, use the exact installed SDK selection already recorded by the workflow:

```powershell
python installer/windows/test_msix_qualification.py
pwsh -NoLogo -NoProfile -File installer/windows/test_qualify_msix_install.ps1

$sourceCommit = (git rev-parse HEAD).Trim()
$sdkVersion = '10.0.26100.0' # replace only with the workflow's exact selected installed SDK
$sdkDirectory = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin\$sdkVersion\x64"
$packageOutput = Join-Path $env:RUNNER_TEMP 'pixelquay-msix-package'

python installer/windows/msix_qualification.py `
  --release release `
  --artwork branding/pixelquay.png `
  --source-root . `
  --source-commit $sourceCommit `
  --makeappx (Join-Path $sdkDirectory 'makeappx.exe') `
  --sdk-version $sdkVersion `
  --output $packageOutput

pwsh -NoLogo -NoProfile -File installer/windows/qualify-msix-install.ps1 `
  -Package (Join-Path $packageOutput 'PixelQuay.Qualification_1.0.0.0_x64.msix') `
  -PackageRecord (Join-Path $packageOutput 'package-record.json') `
  -SignTool (Join-Path $sdkDirectory 'signtool.exe') `
  -Output build-evidence/msix-install
```

The first test command is cross-platform. The second executes the real PowerShell orchestration failure paths through injected operations. It was parsed and executed locally with the repository-provided FileQuay `.tools/powershell-7.6.6/pwsh`. `msix_qualification.py` itself refuses a package build unless `sys.platform == 'win32'` and `CI == true`. The installation script independently requires Windows CI.

Local implementation verification on macOS arm64 completed 16 cross-platform MSIX cases plus one Windows-only junction/reparse case registered and skipped, four PowerShell orchestration scenarios, and the full 32-test `installer/windows` Python suite (one Windows-only skip). PowerShell 7.6.6 parsed both scripts without errors. The tests use actual temporary files, PNG decoding/resizing, XML parsing, ZIP payloads/hashes, SDK command construction, and native helper orchestration; the SDK runner and Windows operations are substituted locally. These results are not a Windows build or installation claim.

## Installed qualification boundary

`qualify-msix-install.ps1` refuses a matching preexisting package before creating a certificate. It copies the unsigned MSIX, creates a 12-hour nonexportable CurrentUser signing key, exports and trusts only its public certificate, signs the copy, verifies the signature, and proves the unsigned original hash did not change.

It installs and queries the exact name, publisher, version, and x64 architecture. A first installed diagnostic launch redirects native stdout/stderr, verifies its package full name, requires a normal close, and fails on Fontconfig missing-configuration or fatal/exception output. It then launches through `IApplicationActivationManager` using the registered package-family AUMID. The returned process handle must produce `ERROR_INSUFFICIENT_BUFFER` and then success from `GetPackageFullName`, with the exact installed full name. The installed executable, `coreclr.dll`, `hostfxr.dll`, and runtime configuration must match their package-record hashes. Every loaded module must resolve either to the exact package installation root and payload hash or beneath the canonical Windows directory; packaged `coreclr.dll` must be observed at its exact path.

The probe requires the `PixelQuay` main window, records up to 1,000 accessibility nodes, rejects named fatal/exception surfaces, notes whether actionable controls were positively exposed, attempts a screenshot, requires three seconds of stable window lifetime, and requests a normal zero-exit close. A title match alone never sets workflow acceptance. Missing actionable accessibility controls leaves `startup_limited=true` even when native startup passes.

Uninstall and exact registration removal are mandatory. Process, owned package, trusted certificate, personal certificate, and temporary signed-copy cleanup are attempted independently in all cases. Every cleanup error is retained beside the primary error and makes `installation_qualification_passed=false`. No PFX or private certificate is exported.

## Metadata-only artifacts

The root workflow may upload only these qualification outputs:

```text
<package-output>/package-record.json
build-evidence/msix-install/installation-qualification.json
build-evidence/msix-install/loaded-modules.json
build-evidence/msix-install/accessible-window-tree.json
build-evidence/msix-install/qualification-window.png   # only when capture succeeds
build-evidence/msix-install/installed-native-stdout.txt
build-evidence/msix-install/installed-native-stderr.txt
```

Artifact globs must exclude `*.msix`, `*.msixbundle`, `*.appx`, `*.appxbundle`, `*.cer`, `*.pfx`, `release/**`, the private temporary stage/unpack directories, and executable/native payload files. Root may retain runner logs that contain no package bytes.

## Still-open Windows and release checks

Only an actual Windows run can establish package build, semantic SDK validation, disposable signature trust, installation, broker activation, `GetPackageFullName`, module origins, accessibility capture, normal close, uninstall, and cleanup. Until that run succeeds, both `installationQualificationPassed` and `installation_qualification_passed` remain false.

Installed export/overwrite/cancellation/permission behavior, read-only and Unicode destinations, upgrade, 100/150/200% DPI, high contrast, keyboard/screen-reader acceptance, WACK, source/license closure, Store identity, release signing, submission, and publication remain independent gates.

The installation-flow structure was adapted from ReticleQuay's MIT helper. The retained upstream license is [RETICLEQUAY-MIT.txt](RETICLEQUAY-MIT.txt).


## Native notice path repair

The native collector previously flattened installed license paths to basenames.
That preserved some notices but overwrote distinct notices named `COPYING` within
the same package. The observed gettext-runtime top-level notice (495 bytes) was
replaced by its nested libasprintf notice (65 bytes). This is a collision defect,
not a claim that the prior native package contained no license notices.

Installed notices now retain their full pacman-relative path at
`licenses/native/<package>/<original-pacman-path>`, relative to `release/bin`.
Every package record includes `includedLicenseFiles` entries with `sourcePath`,
`path`, `size` and `sha256`. Original `licenseFiles` remain intact. The collector
hashes each original open file, copies those bytes and rehashes its destination.
Existing reviewed source-supplement choices, original metadata, hashes and copied
destinations are unchanged; their single notice is now mapped explicitly too.

MSIX validation requires consistent package records, exact coverage of all
original installed license paths (or the existing exact supplement), safe unique
Windows paths and complete equality between the actual native notice tree and
its mappings. Missing, changed, flattened, duplicated, unlisted or ambiguous
copies fail before stage creation. Coherently changing a supplemental copy and
its mapping still fails against the original supplemental source digest.
Historical inventories lacking the new required mapping must be regenerated
from their actual native inputs; they cannot qualify as repaired evidence.

The regression fixture retains the actual two gettext archive notice texts and
provenance under `test-fixtures/native-notices/`. The initial real-file test
reproduced the single-file overwrite. Mapping and notice-corruption tests also
failed against the original implementation. The final suite contains 42 Python
tests (41 passed, one Windows-only junction skip on macOS), including all 11
native inventory, six managed notice and 25 MSIX tests. A real collector-to-stage
fixture proves both original notice paths and bytes reach the package map.

This changes packaging evidence and notice layout only. Product/runtime versions,
license selections, source supplements and Store flags are unchanged. It does
not establish full license/source closure or retroactively repair prior native
artifacts. Exact Windows regeneration, SDK/package verification and coordinator
source-license reconciliation remain required.
