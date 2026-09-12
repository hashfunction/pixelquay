# TintFable real Windows marketing capture

This separate workflow captures the existing, unchanged, qualified Store package.
It does not build the app, replay substitute qualification evidence, submit a
package, edit screenshots or modify the original consumer qualification helpers.
The exact successful Store package is bound in `binding.json`; see
`BOUND-PACKAGE.md` for its independently replayed qualification evidence.

The three intended files are native maximized-editor captures of the actual monitor work area
(at least 1920×1000 on a 1920×1080 or larger display at 96 DPI):

1. `01-edited-canvas.png`: the real editor showing the saved upright Cedar Coast
   campaign artwork after ordinary Open, Rotate Clockwise and Save As actions.
2. `02-export-recipe.png`: the actual reopened saved **Newsletter banner** recipe,
   1200×800 PNG, with its chosen `C:\TintFable Demo` destination. The complete
   editor remains visible behind its owned modal dialog.
3. `03-exported-image.png`: the actual exported `Cedar Coast-newsletter.png` opened
   again in the editor. A further ordinary rotate/save produces an independent
   pixel witness before the capture can succeed.

`Ctrl+B` is the original product's **Best Fit** command in
`Pinta.Core/Actions/ViewActions.cs`. It makes the large canvas visible without
changing document pixels. Every input preserves the original qualified native
PID/retained-handle/window/foreground/picker-focus guards. Filename text uses
the capture-only control operation described below. Screenshots use native
CopyFromScreen into PNG without resizing, cropping after capture, overlays,
retouching or generated application UI. Each image has a receipt with actual
before/after main and modal rectangles, maximized state, full work-area capture
rectangle, foreground, title, PID, source commit,
package identity, byte count and SHA-256; all three files are rechecked.

## Original sample content

`artwork/cedar-coast.png` is an original fictional travel campaign poster authored
for this demonstration, 1800×1200 pixels. The code in `author_artwork.py` draws the
illustration and text. It contains no application UI. Local installed Georgia and
Arial fonts were rendered into the original PNG; no font files are redistributed.
Pillow is used only by that optional authoring script, not by the capture runner.
The committed source artwork was visually inspected locally.

The capture fixture starts this user image sideways. The actual application's
normal rotate action creates the upright composition. A separate standard-library
PNG reader checks all 2,160,000 saved image pixels against the original artwork.
The actual 1200×800 export must match at least 700,000 independently checked pixels
inside constant-color source regions; interpolation edges are excluded. The second
rotate/save after reopening must match every one of the 960,000 exported pixels
under the independent clockwise transform. Native output bytes and the actual
saved recipe are recorded before cleanup. These checks apply only to the large
capture content. The original tiny qualification image and oracle are untouched.

## Activation binding

After independently verifying a successful dual-identity native run and its
retained Store artifact, the coordinator fills only `qualified` in `binding.json`:

```json
{
  "source_commit": "exact 40-character public qualified commit",
  "workflow_run_id": "exact successful native run ID",
  "workflow_run_attempt": "exact successful attempt",
  "package": {"bytes": 1, "sha256": "exact unsigned MSIX SHA-256"},
  "readiness_receipt": {"bytes": 1, "sha256": "exact release-ready.json SHA-256"},
  "store_artifact_id": 1,
  "metadata_artifact_id": 1
}
```

These illustrative values are documentation, not an executable binding. The
workflow reads the reviewed binding before checking out the exact qualified
source. It fetches only those existing GitHub artifacts, checks their run/source,
name, expiration, size, ZIP paths and members, then verifies the exact package and
readiness bytes. Both original full installed workflows, pixel/recipe evidence,
all retained metadata hashes and the original public source records must pass the
release verifier. The only unretained evidence is the exact MSYS2 package-cache
archive/signature set listed in the separately hash-bound original
`msys2-cache-sha256.txt`. Arbitrary missing metadata is refused.

The native capture installs a temporary signed copy with the assigned
`1659hashfunction.PixelQuay` identity. It preserves `PixelQuay` ApplicationId and
profile compatibility. Existing registrations, profiles or demo directories are
refused. Registration ownership requires successful Add plus the exact observed
name/publisher/version/architecture/family/full name. Only that owned registration
can be removed. All installed payload files and loaded package modules are
rechecked against the original package record. Temporary signing keys are
nonexportable; no key, certificate or binary is uploaded by the capture workflow.

Success requires normal zero-exit close, uninstall, no residual registrations,
owned marker/byte-checked demo and profile removal, original display restoration,
all three screenshot hashes and unchanged original unsigned MSIX bytes. Failures
preserve unknown or changed state, attempt a bounded owned native screenshot/UIA
snapshot before cleanup, and retain the original error separately from cleanup
errors. `capture-result.json` always distinguishes capture from original acceptance:
`consumer_acceptance`, `installation_qualification_claimed`, `product_binary_changed`
and `submission_changed` remain false.

## Local verification

```sh
python3 -m unittest discover -s installer/windows/marketing -p 'test_*.py' -v
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_helpers.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_operations.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_ui.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_filename.ps1
```

Ten Python cases passed: real ZIP/package and original native-record replay,
source/run/readiness/artifact refusals, safe extraction, actual large artwork and
independent output pixels/recipe/cleanup. All three PowerShell suites passed:
actual qualified helper loading and native compilation; four production capture
registration scenarios; unproved-process cleanup refusal; eleven frame ownership/
geometry refusals; before/after frame stability; actual three-image hash recheck;
all eight lifecycle failure boundaries; and real UI sequence with four stops on
input/file failure. Run 34691905174 completed all original native capture and cleanup checks. Visual
review found the console visible through GTK’s transparent window shadow, so those
images are not used for publication. This capture-only revision maximizes the
owned editor once with ShowWindowAsync, independently observes IsZoomed, and
requires its native bounds to cover the entire monitor work area. Only that full
visible work area is captured directly; there is no image postprocessing. The
original qualified package and all document/pixel/recipe checks remain unchanged.
A fresh native capture and visual review are required before publishing images.

Win32 references: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-showwindowasync
and https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-iszoomed.

## Native filename control operation

The first maximized capture, run 34692686058, retained only `C:\TintF` after
one full-path Unicode input batch. Run 34692993051 used separate character sends
and retained the entire Save path except its first `C`. Run 34693355675 failed
before text entry because the immediate post-Alt+N focus was the owned filename
ComboBoxEx32 container, not its Edit. The original exact filename checks refused
all three. Those failures do not prove a particular Windows autocomplete bug.

The current screenshot driver replaces queued character injection for filename
text with one normal Win32 `WM_SETTEXT` on the actual focused filename **Edit**.
Immediately before and after this call it runs the qualified native filename
observer, which proves the retained dialog/process, writable Edit class,
filename-ID ancestry and exact focus HWND. It sends no broadcast, uses
`SendMessageTimeoutW` with `SMTO_BLOCK|SMTO_ABORTIFHUNG|SMTO_ERRORONEXIT` and a
1,000 ms timeout, and requires both successful dispatch and the Edit's TRUE
result. There is no input retry. The driver then independently reads all text
with the original bounded `WM_GETTEXT` and requires exact path equality before
returning. The unchanged original picker helper repeats its complete readback
before actual Enter/Choose. A receipt records the precise dialog, focus HWND,
expected/actual path, delivery method and timeout. No file is written by this
capture driver: ordinary app Open, Save, Export, and reopen operations still
produce the independently checked output bytes.

Capture key chords now retain a one-second settling interval after the original
native guarded send, allowing normal mnemonic focus transitions before the
strict observer. This interval does not authorize focus or suppress a refusal.
The original helper source, qualified package, prior consumer evidence, output
pixel/recipe oracles and lifecycle checks remain unchanged.

Portable tests reproduce the prior absence of a single native write/readback,
then check one exact write, ownership refusals before/after, failed send, partial
readback, no replay, one-shot chord settling, Unicode/length/NUL bounds and native
HWND/broadcast rejection. The actual C# implementation compiles in those tests;
its Win32 call and the complete new screenshot run remain pending Windows.

Win32 references:
https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settext
https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendmessagetimeoutw
