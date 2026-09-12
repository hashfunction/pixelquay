# TintFable native filename observation

Run [34688977137](https://github.com/hashfunction/pixelquay/actions/runs/34688977137),
public source `d88655b1180f414e02d7a38c44a2bf256c4228bf`, failed the first
**disposable** installed consumer workflow at `readback-filename`. The Store
lifecycle and unsigned export were never reached. Build, signing of the separate
install copy, registration, package/PID ownership, and loaded-module observation
had passed. The receipt records no cleanup/evidence errors, no residual packages,
all owned processes stopped, fixture removed, display restored, and the unsigned
original unchanged. Consumer acceptance and normal close remain false.

The 1,310,042-byte metadata artifact `10296876535` was inspected before changes.
`consumer-workflow.json` proves `Open Image File`, PID 2784, dialog HWND 983494,
and retained focused Edit HWND 852490. All Edit/ComboBox/ComboBoxEx32 ancestors
carry control ID 1148 and the same process; native style, visibility, writability,
thread, ancestry, and final focus checks pass. Its later `consumer-failure.png`
(SHA-256 `7078054cefb218a3f4cc2f38c0839d5684943240c49c962ef6d988c540c734a3`)
visibly contains the complete expected path:

```text
D:\a\_temp\pixelquay-consumer-7d8d35edf8034267b7aa436c0c578be7\source.png
```

The failed comparison did **not** record its returned string (`native: null`).
Therefore a particular truncated value, queue delay, or input loss cannot be
asserted from that run. The earlier successful run 34684998708 has the same
classic Open topology and 960×540 picker geometry. Both native and PowerShell
consumer input files are unchanged between its local source `233993ad` and the
failed source's local `e372ace`.

The source-level defect is a single immediate read after a fixed 100 ms pause:
[SendInput](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput)
reports events inserted into the input stream; it does not report that the
application has processed them. Windows can dispatch sent messages before queued
input, as documented for
[PeekMessage](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-peekmessagew).
[WM_GETTEXT](https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-gettext)
reads the Edit's current contents. A read preceding completion of the queued text
is consistent with the exact path in the later screenshot, but remains an
inference for this specific run.

The repair observes the exact retained filename with the existing native
`FileNameText` API until its text equals the expected path, using a monotonic
30-second acceptance deadline and at most 300 read calls. Each native read still
checks owner, foreground, ancestry, style, and retained focus before and after
WM_GETTEXT; any native exception escapes immediately. There is no repeated key,
text, selection, or activation input. An exact value arriving after the deadline
is rejected. A currently executing WM_GETTEXT retains its existing two-second
native timeout; timeout cannot produce acceptance.

`picker_readbacks` stores the exact expected path, dialog/PID/focus, deadline,
and every successfully returned value, attempt, elapsed milliseconds and UTC.
No truncation of the bounded native string is introduced. The existing refusal
stage and native exception evidence remain intact. The final Enter/Choose input
retains its independent immediate ownership/focus validation. No application,
package, pixel/recipe oracle, lifecycle/export rule, or marketing asset changed.

Local verification (2026-09-12):

```sh
PWSH=../../filequay/source/.tools/powershell-7.6.6/pwsh
"$PWSH" -NoProfile -File installer/windows/test_consumer_native_picker.ps1
"$PWSH" -NoProfile -File installer/windows/test_consumer_input.ps1
python3 installer/windows/test_consumer_workflow.py
TMPDIR=/private/tmp python3 installer/windows/test_store_export.py
"$PWSH" -NoProfile -File installer/windows/marketing/test_capture_ui.ps1
"$PWSH" -NoProfile -File installer/windows/marketing/test_capture_operations.ps1
git diff --check
```

The new regression failed against the original immediate comparison before the
repair. It now exercises the actual PowerShell convergence loop with a replayed
native observer and monotonic test clock: prefix→exact, empty→exact, persistent
wrong text, native focus refusal during observation, and exact text returned at
the expired deadline. It proves one text send, one select-all, complete observed
values in serialized JSON, no capture/Enter on failure, finite reads, and no
swallowed/retried native refusal. Existing eight picker sequence/boundary cases,
five Choose cases, primary diagnostic preservation, native C# ownership/ABI
suite, 24 file-oracle cases, nine Store export/source cases, and the unchanged
marketing UI/real-loader suites pass. These are local replay/managed tests;
a fresh actual Windows run must establish both full lifecycles before export.
The committed marketing candidate `271d6f7` remains intact and unbound.
