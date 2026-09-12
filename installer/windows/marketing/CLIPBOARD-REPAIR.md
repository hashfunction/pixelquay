# Capture-only filename delivery review — 2026-09-12

Base: `23262340b14f6cdd15790702e6587aa6a59398da`. This change affects only the
separate screenshot driver and its tests/documentation/workflow test list.

## Observed failure

Actual capture run **34694221903**, public capture source
`8fc777409a016e4ae82a6d0b1759b230173b8c7c`, failed waiting for the native picker to
disappear. Its retained `capture-workflow.json` records Save dialog HWND **721394**,
installed process **7648**, actual filename Edit **131738**, and exact
`C:\TintFable Demo\Cedar Coast.png` after both the direct `WM_SETTEXT` write and
original native `WM_GETTEXT` readback at `2026-09-12T12:41:06.4220731Z`.
The actual `consumer-failure.png`, viewed before implementing this repair, shows
**Confirm Save As** asking to replace **Cedar Coast - draft.png**. Thus exact
control text did not establish the modern Save dialog's selected filename.
The artifact does not prove the dialog's undocumented internal implementation.

The original package remained unchanged and failure cleanup reported no errors
or residual registrations. This failed capture did not reach normal close or
complete screenshot acceptance. The repaired route requires a fresh Windows run.

## Repair and boundaries

The obsolete `capture_filename.cs` direct-control writer is removed. The driver
publishes bounded, NUL-terminated `CF_UNICODETEXT` with an owned hidden message-only
window, then uses the **original qualified `FileNameChord` Ctrl+V**. That method
still enforces the retained installed process, exact owned picker, observed
filename ancestry, writable native Edit and expected focus at final SendInput.
The existing one-second capture chord settling is retained and also applies to
paste. The original 30-second, at-most-300-read complete-path observer runs before
clipboard restoration; the unchanged picker repeats its proof before submission.
No key, failed ownership check, clipboard open or text delivery is replayed.

A native format count of zero under `OpenClipboard` is required before any
clipboard mutation. A NULL clipboard owner alone is never accepted as empty.
The eager movable-memory block transfers to Windows only after SetClipboardData
succeeds; untransferred memory is freed. Lock, unlock, close, transfer and owned
window cleanup errors remain terminating and preserve the original exception.

Before paste, and again under the clipboard lock before restoration, the lease
checks its exact owner HWND, retained nonzero clipboard sequence, and exact
Unicode content. Changed/busy clipboard state is preserved and the capture fails.
Restoration only empties the still-owned data to its verified empty baseline.
The hidden window is never shown or activated. A changed owner thread fails
closed. Capture receipts retain owner/sequence, exact expected/actual path,
completion/restoration status and separate primary and cleanup errors. An input
error remains primary when clipboard cleanup also fails.

The app, qualified native/PowerShell helpers, immutable package binding, source
qualification, image artwork, original rotate/export/reopen oracles, normal-close,
uninstall and residue requirements are unchanged. This code writes no image or
output document; the real application still produces every independently checked
output. No captured pixels are edited.

Microsoft's applicable primary API records are linked in the README: normal Edit
clipboard operations, Unicode text format, OpenClipboard/owner semantics,
CountClipboardFormats, SetClipboardData memory transfer and clipboard sequence
changes. Sequence numbers are compared for ownership, not polled for notification.

## Verification

The production paste-sequence fixture was run against the original writer first
and failed `Input replayed or bypassed guard: pass`, because the old route never
called the required original guarded Ctrl+V boundary. After replacement:

- `test_capture_filename.ps1`: **15** production sequence/refusal cases, including
  final focus refusal, no replay, readback before restoration, simultaneous
  primary/cleanup failures, text/write bounds and one-second chord settling.
- `test_capture_clipboard.ps1`: **17** replays of the actual compiled lease policy
  against the native boundary: empty/ownerless/foreign data, open/transfer/close
  failures, owner/sequence/text/thread changes, and preservation of foreign data.
- All existing capture PowerShell suites passed: actual qualified helper loading
  and native compilation, four registration ownership scenarios, unproved-process
  cleanup refusal, thirteen frame ownership/geometry refusals, frame stability,
  actual three-frame hash recheck, eight lifecycle failures and four UI/file stops.
- All **10** capture Python tests passed, including actual package/evidence
  verification and large-artwork pixel, recipe, reopen and cleanup checks.
- `git diff --check` passed. The new native clipboard execution fixture is also
  checked by the screenshot workflow before package activation.

Commands (from this source repository):

```sh
TMPDIR=/private/tmp python3 -m unittest discover -s installer/windows/marketing -p 'test_*.py' -v
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_helpers.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_operations.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_ui.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_filename.ps1
TMPDIR=/private/tmp ../../filequay/source/.tools/powershell-7.6.6/pwsh -NoProfile -File installer/windows/marketing/test_capture_clipboard.ps1
```

Local host is macOS. The last test compiles the actual Win32 implementation and
replays its policy here; its real native clipboard publish/read/restore case is
explicitly skipped outside Windows. Real Windows paste, the entire screenshot
workflow and visual review remain pending. No new screenshots are accepted by
these local tests.

## Publication close sequence correction

Actual run 34695478978 passed all prior fixture suites but stopped in the real native clipboard fixture before installing the app. Begin succeeded, then Verify/Restore reported changed owner/sequence/text. That older generic error did not retain which value changed; the new native fixture records before/after publication sequence and preserves both primary and cleanup errors.

The prior lease anchored its sequence before CloseClipboard. Windows synthesizes companion text formats when publishing text; upstream Wine's real-Windows conformance tests explicitly check that closing a clipboard containing text advances its sequence and that a close with no synthesis does not (dlls/user32/tests/clipboard.c, test_messages). Microsoft's clipboard format documentation describes these synthesized formats: https://learn.microsoft.com/en-us/windows/win32/dataxchg/clipboard-formats . This explains a concrete invalid assumption in the prior lease; the exact failed runner value still requires the fresh native trace.

After completing publication, the driver now takes one fresh locked read, requires its exact owned HWND and Unicode text, then anchors the nonzero sequence. It never repeats publication or adopts a changed owner/content. Every subsequent Verify and Restore still requires exact sequence equality. A new production policy replay first failed the old code when Close synthesized formats, then passed the corrected lease. Another case refuses a foreign owner/content introduced at publication close without clearing it. All 19 compiled clipboard policy cases and 15 original production paste cases pass locally. Fresh real Windows clipboard and full capture remain required.
