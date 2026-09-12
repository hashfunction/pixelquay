# TintFable assigned Store package and source binding

The release driver preserves the original disposable qualification, then runs the
same complete installed lifecycle with the assigned Store identity. Both use the
same verified self-contained Pinta/.NET/GTK release directory. No application code,
consumer input route, pixel oracle, recipe persistence rule or cleanup predicate
changes in this candidate.

| Field | Assigned Store value |
| --- | --- |
| Package name | `1659hashfunction.PixelQuay` |
| Publisher | `CN=B6A2631A-FD32-45CC-AE12-82466975F528` |
| Publisher display name | `hashfunction` |
| Family | `1659hashfunction.PixelQuay_r3hxytd7jt6c4` |
| Version / architecture | `1.0.1.0` / `x64` |
| Application / executable | `PixelQuay` / `bin\TintFable.exe` |

The GTK application ID, existing `%APPDATA%/PixelQuay` profile, recipes and every
original native/managed license notice retain their compatibility paths and bytes.
Omitting the new mode argument still selects the disposable identity. Its metadata
and historical claims remain intact. `release-ready.json` is a separate receipt;
it does not rewrite a package record's signing, installation, license-clearance or
public-release flags.

## What permits retention

`qualify-msix.ps1` invokes actual SDK pack/unpack and a fresh PowerShell host for
each full installed lifecycle, in order: disposable build/install, assigned Store
build/install, then `store_export.py`. Every original checked failure stops the
remaining sequence. Existing package evidence and export destinations are refused.

The export rederives both package records from the current release tree and artwork,
checks exact manifest identity and every unsigned archive payload entry, validates
the recorded SDK executable hash and independent unpack count, and requires both
packages to contain the same release input. Installed source/run/attempt, exact
package/process identities, loaded package modules and runtime hashes must agree.
All original workflow, byte/pixel, persisted recipe, normal zero-exit close,
uninstall, profile/fixture/display restoration and error-free cleanup evidence must
pass. All thirteen consumer surface screenshots must retain their recorded hashes.

The current checkout must be clean and match the workflow commit. An anonymous
download of that exact GitHub commit archive is checked against every Git tree
blob and file mode. This compares committed bytes correctly when Windows uses
CRLF checkout conversion. The five public source records explicitly disable text
conversion through this project's `.gitattributes`.

All evidence is hashed before and after source verification; the Store archive is
rechecked before and after copying. The exclusively created output contains only
`TintFable_1.0.1.0_x64.msix` and `release-ready.json`. The successful workflow uploads
those two files as `TintFable-Store-unsigned`. Temporary signed test copies,
certificates, private keys and disposable packages are not uploaded. Qualification
metadata remains separately available on failure. The receipt reports the exact
package bytes/SHA-256, source commit, run/attempt, assigned identity, public source
bindings and qualification evidence hashes; submission remains false.

## Exact native sources

The original 63-archive collection and historical audit/delivery records are
retained byte-for-byte under `source/`. Its immutable release is
[native-sources-2026-09-11-c9f4add](https://github.com/hashfunction/pixelquay/releases/tag/native-sources-2026-09-11-c9f4add).
The 524,318,720-byte collection SHA-256 is
`f22b8de38b25bbe822975cf7968ea7f59f91f70c319c69940a1bd0158a01dc01`.

Actual successful Windows run `34684998708` contains 64 native package owners.
Only GTK and winpthreads differ from that older collection. Their exact source
inputs are acquired from the original MSYS2 source service and published at
[native-sources-2026-09-12-tintfable](https://github.com/hashfunction/pixelquay/releases/tag/native-sources-2026-09-12-tintfable):

| Original source archive | Bytes | SHA-256 |
| --- | ---: | --- |
| [mingw-w64-gtk4-4.24.0-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-gtk4-4.24.0-1.src.tar.zst) | 17,262,450 | `9092701eae0abf0410e5709779613b3485a4849874294830d889ef86aa9268fb` |
| [mingw-w64-winpthreads-14.0.0.r375.g9c1abbbf5-1.src.tar.zst](https://mirror.msys2.org/mingw/sources/mingw-w64-winpthreads-14.0.0.r375.g9c1abbbf5-1.src.tar.zst) | 54,173,752 | `7bf513784ae0bc4f1a413e1f787f7a3ba2bd7ec0503980ea4d17ddf0e4796c87` |

`source/source-supplements.json` is the exact published 6,805-byte manifest, SHA-256
`08b8cbc9ceb011d0787f1242d10df7bb4b0cbc3230f0dbda2db39be771161e22`.
It records `.SRCINFO`, PKGBUILD, nested source and patch hashes, the exact bare Git
winpthreads commit and twice-repeated Git archive hash, four current native module
hashes and original notice byte mappings. The two GTK utilities and
`libgtk-4-1.dll` map to GTK 4.24.0-1; `libwinpthread-1.dll` maps to
14.0.0.r375.g9c1abbbf5-1. No PKGBUILD, imported Git configuration or hooks were
executed. This establishes exact source inputs, not rebuilt binary parity.

The source COPYING bytes exactly match both the current packaged notices and the
older audited originals. GTK remains LGPL-2.1-or-later; winpthreads remains
MIT AND BSD-3-Clause-Clear. This supplement changes no license election or product
licensing. Existing `rebuild/` materials and the prior component audit remain
available. No prior audit claim is promoted to a blanket legal-clearance claim.

The coordinator re-downloaded all three public supplemental assets anonymously
and verified every byte count/SHA-256 before writing
`source/native-source-supplement-publication.json`. Export checks that exact receipt,
all 64 current owner/version/license/binary-package hashes, all four supplemental
module hashes and original notice bytes, and freshly downloads both public source
manifests. It requires these exact supplemental versions; an uncovered future
MSYS2 update must supply matching source evidence before export.

## Verification and limits

The original disposable run `34684998708`, public source
`8556eb5e329d6fd857d13d1bfb561429f756a824`, completed the actual installed workflow
and normal close/uninstall. Its unsigned SHA-256 was
`1f609e054283ea23bcb3f6488ca1de6cc5945b7943be1d6b3c9140b3d644395c`.
That historical package is not exported by this candidate. The assigned Store
identity, final package and new release receipt require a fresh native Windows run.

Focused local commands, run from the source root:

```sh
python3 installer/windows/test_msix_qualification.py
python3 installer/windows/test_store_identity.py
python3 installer/windows/test_store_export.py
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File installer/windows/test_store_orchestration.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File installer/windows/test_registration_ownership.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File installer/windows/test_registration_ownership.ps1 -IdentityMode store
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File installer/windows/test_unpack_evidence.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File installer/windows/test_unpack_evidence.ps1 -IdentityMode store
```

Package tests exercise real manifests, ZIP files, file hashes and SDK command
construction with a local SDK fixture. Export tests replay saved actual native
consumer records with explicit fixture image bytes, then corrupt identity,
lifecycle, module, pixel/recipe, screenshot, source, publication and cleanup
evidence. They also exercise a real Git checkout with CRLF conversion and all five
actual publication records, and reject changed/missing/extra archive members.
PowerShell tests execute the original production orchestration and registration
closures with only their platform side effects substituted. These local fixtures
do not substitute for the required Windows installed runs.

Final local results: 85 Python cases across MSIX (26), Store identity (5), Store
export/source (9), consumer files (24), native inventory (15) and managed notices
(6): 84 passed, with the Windows junction case skipped on macOS. All 15 PowerShell
suite invocations passed, including ten disposable and eleven Store registration
ownership scenarios, seventeen preflight cases per mode, the dual-run sequencing
and refusal fixture, and the unchanged native input/display/picker/profile suites.
Both live public manifests were independently fetched anonymously again and matched
the exact committed bytes. `git diff --check` passed. No new native Windows result,
Store-ready package, submission or marketing screenshot is claimed here.
