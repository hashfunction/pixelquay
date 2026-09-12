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

Run 34694221903 then recorded exact `C:\TintFable Demo\Cedar Coast.png`
after `WM_SETTEXT` and the original `WM_GETTEXT` proof, but its actual **Confirm
Save As** dialog still named **Cedar Coast - draft.png**. The modern Save dialog's
selected filename therefore was not established by changing that Edit text alone.
The capture removes that direct-control writer and uses ordinary **Ctrl+V** through
the original `FileNameChord` final native ownership/focus boundary. It retains the
original selection, full-path readback, Enter/Choose, output pixels and lifecycle.

The capture-only clipboard lease requires **zero native clipboard formats** while
holding `OpenClipboard` before any mutation. A NULL owner alone is insufficient.
A hidden message-only window in the capture process owns eagerly allocated,
NUL-terminated `CF_UNICODETEXT`; memory transfers to Windows only after successful
`SetClipboardData`. The clipboard is closed before paste so the Edit can read it.
The lease checks exact owner, retained nonzero sequence and Unicode content before
paste. After the same one-second capture chord settling, the original bounded complete-path
readback runs while that data remains
available, before restoring the original empty baseline. The unchanged picker
helper repeats its full-path proof before submission.

Restoration rechecks owner, sequence and text under the clipboard lock. Changed
or busy clipboard state is preserved and fails the capture; it is never cleared
to force a pass. There is no clipboard open retry or input replay. Receipts retain
owner/sequence, expected/actual path, completion/restoration and separate primary
and cleanup errors. The owned hidden window is destroyed after restoration or a
refusal, and has no visible/foreground interaction. A thread mismatch fails closed.

Capture key chords retain the existing one-second settling interval after the
original guarded send. This permits normal mnemonic focus transitions before the
strict observer without authorizing focus or suppressing a refusal. No app source,
qualified helper, package, data path, artwork or screenshot pixels are changed.

`test_capture_filename.ps1` replays the production capture function: exactly one
original guarded paste, initial/final focus refusal, nonempty/changed clipboard,
failed paste, bounded readback refusal, restoration failure and preservation of
simultaneous primary/cleanup errors, plus text/count bounds and chord settling.
`test_capture_clipboard.ps1` compiles the actual C# implementation, replays its lease
policy against a stateful native boundary, and on Windows also executes the real
eager Unicode allocation/transfer/read/empty-baseline restoration. The portable
lease fixture does not claim execution of Windows APIs. Fresh native capture,
full original pixel/lifecycle checks and visual review remain required.

Additional focused verification:

```sh
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_clipboard.ps1
```

Microsoft documents [normal Edit clipboard operations](https://learn.microsoft.com/en-us/windows/win32/controls/edit-controls-text-operations),
[Unicode clipboard format](https://learn.microsoft.com/en-us/windows/win32/dataxchg/standard-clipboard-formats),
[clipboard opening and non-NULL ownership](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-openclipboard),
[ownerless data](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getclipboardowner),
[format counts](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-countclipboardformats),
[eager memory ownership transfer](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setclipboarddata)
and [sequence changes](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getclipboardsequencenumber).
The sequence is used for ownership comparisons, not polled as a notification API.
