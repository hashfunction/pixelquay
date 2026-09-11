# PixelQuay libiconv two-DLL source proof

This dispatch-only, metadata-only proof covers the remaining LGPL runtime files
`libcharset-1.dll` and `libiconv-2.dll`. It materializes the exact retained
5,131,029-byte MSYS2 source wrapper, verifies all eight regular members and the
1,109-file upstream source tree, preserves the exact GPL/LGPL texts, and never
executes the retained `PKGBUILD`.

On Windows, `prove-windows.sh` creates separate original and modified package
trees. Both use the retained upstream inputs and MSYS2 patches. The local recipes
make `make check` fatal (the retained recipe merely printed a warning), hash both
unstripped DLLs before and after the suite, and bind each stripped DLL back to the
actual package archive and recipe hash. The modified source adds one dated marker
function to each library. A standalone dynamic probe loads both exact DLL paths,
checks `locale_charset`, converts ISO-8859-1 `é` to UTF-8 through libiconv, and
requires both markers only for the modified variant. Exact exports, imports,
licenses, environment and wrong-mode rejection are recorded.

The upstream signature bytes are hash-bound here and were independently verified
in `NativeSignatureVerification.json`; the workflow therefore uses makepkg's
`--skippgpcheck` while retaining all content checksum verification. It uploads
JSON/text evidence only. DLLs, packages, EXEs, signing material and source archives
are excluded from the artifact.

Windows run `34645193416` proved the original recipe through its native tests but
the modified recipe stopped in `prepare()`: the local patch named paths relative
to the source archive's parent while the recipe runs `patch -p1` from inside
`libiconv-1.19`. The patch now names paths relative to that production working
directory, and the source regression applies it from the same directory. A fresh
Windows run is required before the two-DLL proof can be accepted.

This proof can establish that both libraries can be rebuilt and replaced at their
normal ABI names. It does not rebuild PixelQuay, create an MSIX, prove the installed
application loads the modified DLLs, perform the LGPL-to-GPL license conversion,
or declare product-wide license clearance. Those fields remain false in the
receipt and require the independent app rebuild/repackage/install workflow.
