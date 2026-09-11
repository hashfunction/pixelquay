# Retained-LGPL libdatrie source proof

This increment verifies and materializes the exact libdatrie 0.2.14 source,
builds original and modified libraries in the same recorded environment, and
checks actual trie behavior and library exports. It does not rebuild PixelQuay,
create an MSIX, install an application, change an app loader, or establish
complete corresponding-source/license clearance.

The helpers and probe are MIT licensed. The included source archive and the
dated local modification retain **LGPL-2.1-or-later**, including the original
COPYING and header notices. `COPYING.LIBDATRIE` is the unchanged upstream text.
The original MSYS2 recipe/maintainer attribution is retained in both derived
recipes. No LGPL-to-GPL conversion is made.

## Source inputs

`inputs/mingw-w64-libdatrie-0.2.14-1.src.tar.zst` is an unchanged **source-only**
archive, 327,473 bytes, SHA-256
`da58ca439051a8cfb1d7f15cdd82af104e1ea1eeefdb090e608d2305a747df7d`.
It is part of the [published 63-archive source collection](https://github.com/hashfunction/pixelquay/releases/tag/native-sources-2026-09-11-c9f4add)
and was obtained from [MSYS2](https://mirror.msys2.org/mingw/sources/mingw-w64-libdatrie-0.2.14-1.src.tar.zst).

The exact three members are checked before writing: PKGBUILD, .SRCINFO and
`libdatrie-0.2.14.tar.xz`. The latter is 325,696 bytes, SHA-256
`f04095010518635b51c2313efa4f290b7db828d6273e39b2b8858f859dfe81d5`.
The materializer validates both archive levels, rejects links, devices,
traversal, aliases and duplicate names, and writes only to a new directory.
It does not execute a PKGBUILD. Interrupted partial output is preserved.

```sh
python installer/windows/rebuild/libdatrie_source.py \
  --archive installer/windows/rebuild/inputs/mingw-w64-libdatrie-0.2.14-1.src.tar.zst \
  --output /absolute/existing-parent/new-libdatrie-source
python -m unittest discover -s installer/windows/rebuild/tests -p 'test_*.py' -v
```

Use a real parent directory rather than a symlink/junction. The source command
requires Python with `lzma`, plus `zstd` on PATH. It emits a receipt hashing every
materialized file, including unchanged COPYING. The source package's .SRCINFO
was generated under UCRT64; actual builds explicitly select **CLANG64** from the
multi-environment PKGBUILD.

## What the modification and tests do

`001-local-marker.patch` adds a dated optional `pixelquay_rebuild_marker` export
to the C implementation, header, `.def` and version map. It returns a fixed
diagnostic string without changing existing trie behavior. The original recipe
keeps package version 0.2.14-1; the modified local recipe uses 0.2.14-1.1. Both
retain the original configure flags, run the ten upstream tests through a new
`check()` function, and retain a library linker map. Both also apply
`002-windows-alpha-test-data.patch` solely to four upstream test sources. The
upstream suite cast C wide-string literals to its fixed 32-bit `AlphaChar` type;
Windows uses 16-bit `wchar_t`, so seven data-driven tests failed while the three
tests without those literals passed. The dated patch uses C11 32-bit string
literals for the same 49 ASCII keys. It does not modify library source. Each
recipe hashes the library before and after the tests, fails on a change, and
retains the matching post-test hash and verifies it against that same build DLL.
The separately recorded package DLL may differ because makepkg's retained
configuration enables stripping; package staging, archive membership, PE/API
behavior and exports are verified independently. All source
checks remain enabled; no dependency installation happens inside either build.

The external C probe dynamically loads the exact absolute library path and
checks 21 conditions covering alphabet maps, insertion, retrieval, overwrite,
insert-if-absent, invalid characters, state walking, save/load, deletion and
independence of the reloaded trie. It checks the actual loaded module path and
marker state. Requiring the modified marker from the original library (and the
reverse) must return exit 4. Existing `probe.trie` output is preserved (exit 5).
The probe is never linked into or staged with PixelQuay.

## Current Windows environment and proof

The selected current CLANG64 inputs are asserted before building. These package
versions/hashes are from the linked primary MSYS2 package records, accessed
2026-09-11; `library_receipt.py` contains their exact archive SHA-256 values:

| Package | Version |
|---|---|
| [clang](https://packages.msys2.org/packages/mingw-w64-clang-x86_64-clang) | 22.1.8-2 |
| [autotools](https://packages.msys2.org/packages/mingw-w64-clang-x86_64-autotools) | 2026.08.04-1 |
| [doxygen](https://packages.msys2.org/packages/mingw-w64-clang-x86_64-doxygen) | 1.18.0-3 |
| [libiconv](https://packages.msys2.org/packages/mingw-w64-clang-x86_64-libiconv) | 1.19-1 |

libiconv matches the qualified application's native ecosystem. This is a
functional replacement proof using the current compiler, not a reconstruction
of the historical clang 21.1.5 build or a bit-identical-binary claim.

`.github/workflows/libdatrie-proof.yml` is a separate manually dispatched
Windows job. The setup action is commit-pinned. It installs current packages,
then fails if the four selected versions/archive hashes no longer match;
updating those pins requires a reviewed source change. It records every other
actual installed package version and downloads its exact archive before either
build. Tool and makepkg configuration bytes must match those archives. The
complete package archive hashes, tools, configurations, compiler search paths
and relevant environment variables are recorded and must remain unchanged.
This receipt identifies the environment used; it does not claim an immutable
Windows runner image or a fully locked bootstrap of every package in advance.

After setup, the native command is:

```sh
mkdir -p build-evidence
bash installer/windows/rebuild/prove-windows.sh \
  "$RUNNER_TEMP/pixelquay-libdatrie-proof" \
  "$GITHUB_WORKSPACE/build-evidence/libdatrie"
```

Run from a clean committed source checkout in a CLANG64 shell with base-devel,
git, the four selected packages and CLANG64 Python installed. For a local
isolated Windows environment, substitute two new absolute directories for the
arguments; a GitHub account is not needed. Both output parents must exist.

The native job builds both actual pacman packages, compiles the probe with
`-Wall -Wextra -Werror`, and probes the stripped DLL from each package staging
directory. Verification independently compares that DLL to the corresponding
archive member; checks .PKGINFO identity, .BUILDINFO recipe hash and original
COPYING; reads x64 PE export/import tables; and requires all original source
exports plus exactly the new marker on the modified DLL. Every upstream .trs
must say PASS; missing, skipped or failed cases fail the proof.

Artifacts include source/environment/package receipts, library proof JSON,
build/config/linker/test logs and probe results. DLLs, executables and binary
package archives stay private in the runner's work directory and are not
uploaded. Existing normal app/MSIX qualification remains unchanged. On a native
test failure, the aggregate log plus each of the ten `.log` and `.trs` files are
copied byte-for-byte before the build exits; output collisions fail rather than
replace earlier evidence. The build log and failure-line record remain available
for failures before tests. A success receipt is created only after all
verification succeeds.

## Repeatable host check and remaining gates

macOS can independently compile and run the real source/patch/API tests:

```sh
python installer/windows/rebuild/local-smoke.py \
  --work /private/tmp/new-libdatrie-work \
  --evidence /private/tmp/new-libdatrie-evidence
```

This runs configure/make and all ten upstream tests for each variant, verifies
their real Mach-O exports, executes the 21 API checks and both negative controls,
and records `windowsProof: false`. It applies the same portable test-data patch
and verifies test execution leaves each built library unchanged. Separately,
the pre-repair suite was reproduced on macOS with `CFLAGS=-fshort-wchar`: it had
the exact Windows result of seven failures and three passes; the dated test-data
patch changes that counterfactual to ten passes without changing the library
archive hash. It requires Xcode command-line tools, make, patch and zstd. Host
results do not stand in for the Windows job.

Every patched source file carries the dated modification notice. Windows DEF
semicolon comments remain in the modified source. Darwin libtool cannot consume
these comments: the host smoke derives a separate, hashed symbol-only linker
input and passes it through `EXPORTS_FLAGS`, preserving the noticed source.
The Windows recipes use the actual DEF/version-map files without this adapter.

Actual Windows DLL compatibility, later full PixelQuay rebuild, independent
MSIX signing/install and broker-observed changed-DLL loading remain separate
gates. The other runtime sources, generated/embedded code provenance, retained
LGPL source delivery and broader license choices still require their own
evidence. This increment changes none of those statuses.

The companion [`libiconv/README.md`](libiconv/README.md) applies the same
library-only boundary to the remaining `libcharset-1.dll` and `libiconv-2.dll`
from the single libiconv split package. Its independent receipt keeps full app
rebuild, MSIX creation and installed changed-module observation false.
