# Original gettext notice collision fixture

These two files retain their original bytes and paths from the MSYS2 CLANG64
`mingw-w64-clang-x86_64-gettext-runtime-1.0-1-any.pkg.tar.zst` archive. They are
upstream notice text, not authored or relicensed as PixelQuay test code.

Archive SHA-256: `6f22a64727816c9d9c8289bac9493a3c50691da678de22489d0545114568bb90`.
The coordinator retained it in PixelQuay's `Release/artifacts/run-34574471808/build-evidence/package-cache/`.
Extraction used `zstd -dc` and Python tarfile streaming through archive EOF;
zstd exited zero. No archive binaries are part of this fixture.

| Original archive path | Bytes | SHA-256 |
| --- | ---: | --- |
| `clang64/share/licenses/gettext-runtime/COPYING` | 495 | `7ef2cdfe58e0c0460657b6598b49af29d4e03c1e41cbaf0e1da1eb8ad74b95d0` |
| `clang64/share/licenses/gettext-runtime/libasprintf/COPYING` | 65 | `03133addae5b99a6148c538300e6d97074453089be1423b741bd081f18e2b298` |

The regression proves both same-basename notices survive copying and package
validation separately. This small fixture is not the complete gettext license
or corresponding-source payload; the retained texts refer to other upstream
license files that remain required by the actual distribution.
