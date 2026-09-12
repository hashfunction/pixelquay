# Native folder Choose route — 2026-09-12

Starting source `1a0acc95122a4784d359ec5aff1630b33663d2c2`. This is a qualification-only input correction; product UI/export code and acceptance rules are unchanged.

Windows run `34683168237` passed the previous Edit1152 field route. Its `consumer-workflow.json` shows PID 7780, owned `Export destination` dialog HWND 1180118, direct folder Edit HWND 1114606/ID 1152/thread 8960, all original filename guards, exact text readback, and the subsequent normal Enter. It then failed only at the unchanged 30-second `native picker disappearance` wait. The actual unedited failure screenshot shows the requested generated destination in both the shell address bar and Folder field, with a visible **Choose** button. Enter navigated into the folder and did not accept it. The record does not contain a native Choose control ID; none is invented here.

Evidence under `/private/tmp/tintfable-34683168237-review/TintFable-Windows-qualification/pixelquay/pixelquay/build-evidence/msix-install`:

- `consumer-workflow.json`: SHA-256 `cb7567a03cf42e9974ffe13feb573ed72e63060f00ef37fc3e2a8aec3f1c6be2`.
- `consumer-failure.png`: SHA-256 `b9e3d6d61fbe0477007de3212d75311f4ccb7f342e64ed0c328cbc2d37069663`, matched to the original observation receipt and viewed directly.

`Pinta/Dialogs/ExportRecipeDialog.cs:250` constructs a normal `Gtk.FileChooserNative` with title **Export destination**, action **SelectFolder**, accept label **Choose**, cancel label **Cancel**. The scoped observer route now reads native direct-child button metadata while the exact retained folder field still has focus. It requires one enabled visible **Button** labelled exactly **Choose**, a positive observed control ID, same dialog PID/thread, direct parent HWND, native child relationship, push/default-pushbutton style and tab-stop style. Both `GetDlgItem(dialog, observed ID)` and `GetNextDlgTabItem(dialog, retained filename)` must resolve to that exact HWND. Enumeration is bounded to 512 child windows and 16 direct Button records; captions use bounded read-only `WM_GETTEXT`. The actual Windows HWND/ID/class/label/thread/style and refusal stage are recorded as metadata.

Only after this proof does the harness send one normal Tab through the unchanged final filename-focus guard. It then re-queries the same native evidence, requires focus on the retained Choose HWND, and checks the same ID/thread binding and unchanged exact folder text. Space uses the existing `DeliverInput` boundary: retained app/dialog/foreground ownership first, then a fresh complete Choose/path/focus check immediately before `SendInput`. Final `GetGUIThreadInfo` must still show that focused button and the exact active dialog. No `BM_CLICK`, posted command, direct focus mutation, guessed control ID, coordinate click, extra Tab loop or larger timeout is used. Open/Save dialogs retain their prior exact filename Enter route.

The existing picker-disappearance requirement, export plan/completion, independent image pixels/dimensions/bytes, recipe persistence after proven normal stop, reopened witness, exact package/process ownership, normal close/uninstall and marker-owned cleanup remain mandatory. A missing/ambiguous button, unproved next tab stop, changed field, changed control ID/HWND/thread, wrong focus, or foreign foreground refuses activation and retains bounded failure metadata. The new candidate has **not** yet proved the real Windows button identity or completed export.

Local checks passed using `/Users/hashfunction/workspace/project_app_factory/microsoft-store/apps/filequay/source/.tools/powershell-7.6.6/pwsh -NoLogo -NoProfile -File`:

- `installer/windows/test_consumer_input.ps1`: new predicate was RED before the helper existed, then GREEN. All prior native/window/filename guards remain, with 29 new unsafe Choose variants, explicit wrapper refusal, actual final delivery focus replacement, and real exception-to-JSON metadata retention. The positive fixture's arbitrary ID 47 is explicitly hypothetical, not a Windows ID assertion.
- `installer/windows/test_consumer_native_picker.ps1`: all eight original filename route cases remain; five new production sequencing cases prove query-before-Tab, exact focused observation before Space, retained native-boundary refusal and no activation after failure. Existing diagnostic-error preservation still passes.
- `installer/windows/test_consumer_picker.ps1`: all 11 previous UIA picker selection cases pass.
- Real C# helper compiles through PowerShell; `git diff --check` passes. No full product test rerun was needed because product/runtime code is unchanged.

Fresh Windows must establish the actual native Choose ID/tab order and record the successful normal Tab/Space action, then complete the full disappearance/export/reopen/normal-close gates. No public push, parent/site/status changes or new native success claim is included.
