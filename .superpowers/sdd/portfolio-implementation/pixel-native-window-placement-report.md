# Pixel native window placement after Windows run 34677387985

Base source: `1875c1b8a0c5406f9083c41c86a35539340dd1ef`.
Public run source: `01b861e1275e9a53ca9f1abac361de3b029a2521`.
This repair changes external Windows qualification helpers only. Product code,
branding, package identity, qualification acceptance, native input, image/recipe
checks, binary/module provenance and normal-close/uninstall obligations remain
intact. No public push or workflow dispatch is part of this candidate.

## Proven failure boundary

The actual run at 06:15:54 UTC passed native filename input/readback and the
owned Open Image File dialog disappeared. The next retained main observation was
PID 4916, HWND 655474, class `gdkSurfaceToplevel`, title `source.png - PixelQuay`.
`Save-PixelQuayObservation` then failed with `Owned window is not fully visible
within bounded desktop`. Rotation, recipe export and reopen had not run.

The real picker receipt measured a 1024×768 desktop. The startup raster is
1074×770 and visibly extends outside that desktop; product source requests a
1100×750 default window. The failing after-open raw rectangle was not retained,
so this candidate does not assume a four-pixel border exception or crop any
pixels. The prior filename-focus repair passed its actual Windows boundary.
Cleanup stopped owned processes, removed the owned consumer fixtures/package,
and reported no residual packages or cleanup/evidence errors. Normal consumer
close and successful workflow acceptance were not established.

Metadata (996,677-byte artifact, no package downloaded) remains under
`/private/tmp/pixelquay-34677387985-review/pixelquay/pixelquay/build-evidence/msix-install`.
The bounded failed log is `/private/tmp/pixelquay-34677387985-failed.log`.

## Repair and retained gates

`consumer_display.ps1` reuses Cut's independently native-verified display helper
from its successful capture run 34675620319. The production file is identical
apart from namespace/function names. It inventories actual supported modes,
selects bounded 32-bpp landscape modes, performs CDS_TEST, and applies flags 0
without registry, unsafe-mode, DPI or renderer changes. It retains the exact
original DEVMODE and device before application, including partial failures.
The source helper SHA256 is
`3a834299264963afb9a77e81fc46c63665497ceb967e48e7640895e966a89a9c`;
the renamed Pixel helper is
`7c10f1cdeb90c2eba4eb02d5ae8d9eb295e24a10b246e3139d17c3156bf7dc04`.
The original MIT copyright notice remains.

After the exact owned main window is found, the consumer driver prepares the
actual display and calls MoveWindow once for a centered 1472×940 rectangle in
its actual monitor work area. The native boundary rechecks the retained process
object, exact main HWND/PID/title/foreground, and GTK root class immediately
before placement; picker/child/foreign targets cannot be moved. A bounded poll
requires the actual resulting window to be at least 1400×850 and fully inside
both the work area and desktop. The existing screenshot bounds predicate still
rejects every clipped window and windows above 16 million pixels. Captures use
the observed 96-DPI coordinate context only; unqualified scaling fails closed.

Up to 64 owned geometry records retain exact window rectangle, desktop, monitor
work area and DPI before display preparation, before/after placement, and before
each screenshot can fail. Screenshots remain unedited CopyFromScreen captures,
with full visibility/ownership rechecks and exclusive PNG/hash evidence.

The outer qualification owner restores the original display in its mandatory
finally cleanup sequence after owned-process cleanup. Restoration failures remain
secondary cleanup errors and cannot replace the original workflow error or skip
other cleanup. Final installation evidence includes actual mode restoration and
refuses success if that evidence is absent or false. The earlier workflow JSON
is written before outer cleanup; its restoration fields may still be pending.
`installation-qualification.json.consumer_native_display` is the final record.

## Executed verification and limits

New tests first reproduced missing geometry evidence and the missing restoration
cleanup operation. The production fixtures cover raw clipped bounds and numeric
failure retention, native monitor ABI, negative monitor origins, unsupported
size/DPI/work-area rejection, exact root-only placement, ownership refusal before
native movement, native movement failure, and the bounded PowerShell screenshot
failure record. The reused display fixture also checks an already adequate mode
and rejects an API success without actual restoration. Core and final-evidence
fixtures retain primary errors and reject missing/failed restoration.

Final local commands used PowerShell 7.6.6 at
`/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh`,
with `TMPDIR=/private/tmp`, and Python 3.10:

- `python3 -m unittest discover -s installer/windows -p 'test_*.py'`: 70 tests,
  69 passed, one existing Windows-only junction test skipped.
- All 12 `installer/windows/test_*.ps1` fixtures passed, including the unchanged
  native input/picker, ownership, unpack/profile lifecycle and cleanup suites.
- All Windows PowerShell helpers parsed; the real production native C# and
  display types compiled under PowerShell. `git diff --check` passed.
- Full command/output log: `/private/tmp/pixelquay-native-placement-tests.log`.

This host is macOS. New Pixel native display preparation, GTK placement and the
remaining consumer workflow have not yet run on Windows. Root independent review
and a fresh actual packaged run remain necessary; neither complete consumer
qualification nor final marketing screenshots are claimed. Branding is held for
the separate naming decision.
