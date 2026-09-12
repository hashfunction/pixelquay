# TintFable Export destination folder-field route

Windows run **34682286222**, source
`799539cd07c55f0b10050e264e348e9cf8ae1d82`, public source
`37b3b812a27bf38207a17faefdfed1a32e4fa32c`, passed the modern Save Image File
route and independently verified the edited 64×96 PNG. It then saved/reloaded the
recipe and stopped after Alt+N in **Export destination**, before any path text or
Enter was sent. The sole failed predicate was the legacy `filename_id_1148`.

The actual native receipt proves dialog HWND 197274, PID 6024, and focused Edit
HWND 262730. The field is visible, enabled, writable, and directly parented to
that exact `#32770` dialog. Its sole ancestor entry has control ID **1152**, class
**Edit**, the same PID, and `Descendant=true`; dialog/focus thread IDs are both
3056. The ancestry reaches the exact dialog without truncation. The retained
owner chain is 197274 → 262762 (Export with Recipe) → 393572 (TintFable main).
The unedited screenshot shows the focused **Folder:** field and **Choose** button.

Source `Pinta/Dialogs/ExportRecipeDialog.cs::ChooseDestination` creates exactly
this title with `Gtk.FileChooserAction.SelectFolder` and acceptance label
`Choose`. This establishes a qualification selector gap. No failure of the
product's folder acceptance or export operation has yet been observed, because
the guard refused before submitting a folder.

The new `IsObservedExportFolderName` predicate recognizes only that exact title,
one direct-child Edit1152, matching focused HWND, parent/PID, untruncated ancestry,
and a nonzero matching dialog/focus thread. It supplements field identification
inside the existing native `FileName` observer. Classic1148 and modern Save1001
routes remain intact. Full process/window/owner/foreground validation, writable
style, retained focus, final focus/active-window recheck, exact path readback,
input delivery checks, file/recipe/export/reopen assertions and cleanup are
unchanged. Product code, runtime and workflow YAML were not changed.

Verification:

- The new regression failed before the predicate existed and passed afterward.
- `test_consumer_input.ps1` passed all existing cases plus 25 export-folder
  topology cases, nine unchanged filename predicate refusals, and final folder
  focus replacement before native delivery.
- `test_consumer_native_picker.ps1` passed eight real wrapper sequencing/input
  boundary cases and preservation of the original refusal after diagnostic error.
- `test_consumer_picker.ps1` passed 11 existing picker-selection cases.
- `git diff --check` passed. No repeated product build was needed for this
  qualification-only change.

Evidence read and visually reviewed:

- `consumer-workflow.json` SHA-256:
  `bbd6f29565ae9b7019e353c745d1754c31eb529b4c44879f35c98308a7c932ff`.
- `consumer-failure.png` SHA-256, independently checked against the receipt:
  `2c31237d38277358da883fde4060fff02bc65557e3567b0a02d38f75ddf296c6`.

**Windows rerun remains pending.** This candidate must still prove the normal
folder submission and all remaining export, reopen, normal close, uninstall and
owned-state cleanup gates. No Windows success, source publication, parent status
or website change is claimed by these local predicate tests.
