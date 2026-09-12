# PixelQuay installed consumer workflow candidate

Baseline: `dc25736b711e142a78e82f845812513dc950e558`.
The prior Windows run `34651740848` passed 899 application tests with one existing
skip and startup/install/close/uninstall checks. It did not exercise image export.
This candidate requires that missing normal consumer flow; no application source,
GTK resources, native library selection, product rendering, or feature flags change.

## What the new gate proves

The actual broker process opens the generated asymmetric 96×64 opaque PNG through
the native file picker, rotates clockwise with the existing Ctrl+H action, and
saves an edited copy. An external PNG decoder checks all 64×96 pixels. The actual
Export with Recipe dialog creates and saves `Consumer proof 32x48`, using PNG,
32×48, suffix `-proof`, no JPEG quality, and no overwrite. The driver cancels and
reopens that dialog before exporting, so fresh default recipe values cannot
satisfy the expected output. The exported PNG must have the requested dimensions,
opaque pixels and the independently expected quadrant colors outside its narrow
bilinear transition bands. Input and edited-file bytes remain fixed; no staging
output is accepted.

The exported file is opened in the normal app, rotated, and saved as a separate
witness. Every witness pixel must equal the external rotation of the decoded
export. This verifies that the app loaded and edited that file. After proven
normal zero-exit shutdown, the actual XML settings and embedded recipe JSON must
contain exactly the named recipe with every expected field. The harness never
writes recipe settings or invokes product model/export APIs.

## Ownership and lifecycle

Both the preexisting unpackaged startup check and the later installed check need
fresh profiles. Each creates an absent `%APPDATA%/PixelQuay` profile with an
exclusive marker before launching any app; the unpackaged phase creates it before
the managed tests too. It cleans the profile before MSIX creates its own fresh
one. An existing profile is refused. Input PNGs live in separate newly owned
fixture directories.

The Windows input adapter is compiled from `consumer_native.cs` using BCL APIs
only, before install/trust mutation. It does not load any published application
assembly into PowerShell. Every input validates retained application/target
process handles, exact HWND/PID, owner chain, title, visibility/enabled state and
foreground. Native pickers additionally require an owned `#32770` dialog and
unique visible UIA filename and accept controls. Their ancestry is checked again
before setting a value or invoking the button. Brokered picker processes are
observed through retained handles and never killed.

The GTK4 startup receipt exposes one UIA root. GTK controls use their actual
shortcuts, field mnemonics and source-defined focus order; meaningful screenshots
show the loaded image, rotation, saved/reloaded recipe, export plan, completion and
reopened witness. Screen capture repeats ownership, foreground and complete
visible-window bounds before and after capture. Export completion text is not used
as an acceptance signal: the independent file checks and subsequent reopen are.
The first real Windows run must confirm the GTK focus route and native picker
control exposure; any mismatch fails with bounded owned-window metadata.

Both application launches retain their own process objects/handles. Normal close
uses the original deadlines (five seconds for unpackaged startup, fifteen seconds
for installed launches), followed by a native wait and exit-code observation.
Cleanup can stop only a process whose retained identity was established, and cannot
reacquire a PID later. Fixture/profile removal waits for every owned application
process to be proven stopped. Both complete trees must match their marker and
sealed hashes before either is removed; changed/unexpected files or directories
and links/reparse points are preserved and fail cleanup. Registration removal and
temporary trust cleanup remain required even when the workflow fails.

## Local validation and pending Windows evidence

The new Python suite first failed before the helper existed, and now covers exact
rotation and dimensions, resized orientation, RGB/RGBA decoding and all five PNG
filters, original-byte preservation, staging leftovers, reopen pixels, actual
recipe XML/JSON, stop-before-read, profile/file ownership, changed markers/bytes,
foreign files/directories, links, and complete cleanup. The actual native ownership
predicate and input wrappers cover foreign/stale/hidden/disabled targets, title and
foreground changes, broken owner chains, and Windows x64 INPUT structure size.
Existing orchestration tests include consumer failure and cleanup ordering; existing
registration, final-hash reporting, unpack verification and temporary-collision
checks remain active.

Final local validation:

- `python3 -m unittest discover -s installer/windows -p 'test_*.py'`: 70 tests,
  69 passed and one preexisting Windows-only junction test skipped on macOS.
  All 24 new consumer tests passed; no new skip was added.
- Actual PowerShell 7.6.6: 17 ownership/input/ABI cases, seven actual unpackaged
  lifecycle cases, seven orchestration cases, ten registration cases, five
  reporting cases, ten unpack-preflight cases, and one temporary-collision case
  passed (57 total).
- The native C# adapter compiled under the actual PowerShell host; all Windows
  helper scripts parsed, and `git diff --check` passed. No actual Win32 input, GTK
Windows interaction, or complete native build is claimed from macOS. Root review
and a fresh Windows run are still required. Only `consumer-*.json` and
`consumer-*.png` were added to the MSIX artifact list; fixture images, profile
payloads, binaries, packages, sites and parent release status are not published.

## Native picker semantic label repair

Run34674473214 reached the exact owned Open Image File dialog on Windows. Its
actual screenshot shows the enabled File name field, but the hard-coded UIA
1001/Edit lookup failed. That identifier was an unsupported assumption. The
picker now requires exactly one visible, enabled, same-process Edit with the
standard File name: or Folder: label inside the already-verified dialog. The
primary button, ancestor rechecks, exact written path and all consumer checks
remain unchanged. Observed label and actual AutomationId are retained. A real
UIA-node replay of the production selection rejects duplicate fields, wrong
control type, foreign PID, disabled/hidden fields and a Search field with the
previous numeric ID. Eleven cases and seventeen native ownership cases pass
locally; actual Windows picker/workflow completion remains required.
