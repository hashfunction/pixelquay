# TintFable Windows source handoff

This source is based on Pinta 3.1.2, commit b3df1e579f6b3dd23193d2f6877deced20d8063b.
TintFable executable: `TintFable.exe`; assembly: `TintFable.dll`; version: 1.0.1;
application ID: `com.trieflow.PixelQuay`; publisher: Trieflow LLC.
Canonical product, privacy and support: https://tintfable.trieflow.com,
https://tintfable.trieflow.com/privacy, https://tintfable.trieflow.com/support.

The customer-facing release is TintFable 1.0.1 (package version 1.0.1.0).
The assigned Store package identity remains `1659hashfunction.PixelQuay`; its
existing publisher and application ID must be retained by the Store release
controller. This source builds the separate disposable qualification identity
`Trieflow.PixelQuay.Qualification`, publisher `CN=PixelQuay-CI-Qualification`,
application ID `PixelQuay`. Neither identity is renamed to TintFable. The GTK
application ID, `%APPDATA%/PixelQuay` profile, saved recipe key, and Inno Setup
AppId/install directory are also retained for update and data compatibility.

The renamed Windows release remains unverified. The local macOS solution build and native
headless tests do not prove GTK launch, Windows file picking, MSIX installation,
Store certification, HiDPI, signed packaging or licensing clearance.

From a Windows development shell with .NET 8, Python 3 and MSYS2 CLANG64 installed:

```powershell
dotnet restore Pinta.sln
dotnet test Pinta.sln -c Release --no-restore
dotnet publish Pinta/Pinta.csproj -p:BuildTranslations=true -p:MinGWFolder=C:\msys64\clang64 -c Release -r win-x64 --self-contained true -p:PublishDir=../release/bin/
python installer/windows/inventory_managed.py --assets Pinta/obj/project.assets.json --output release/bin/licenses/managed-packages.json
.\release\bin\TintFable.exe
```

Install MSYS2's `mingw-w64-clang-x86_64-libadwaita` and
`mingw-w64-clang-x86_64-webp-pixbuf-loader`; include gettext for `msgfmt`.
`PythonExecutable` can override the Python command used by MSBuild.
`bundle_gtk.targets` runs `inventory_native.py` after Windows publish, against
its exact `GtkFile` input list and the installed pacman metadata. It writes
`release/bin/native-files.json` and `release/bin/licenses/native/`. Installed
notices retain their full original pacman-relative paths beneath each package
directory; `includedLicenseFiles` maps every source path to copied path, size and
SHA-256. Final packaging checks the complete mapping and exact copied tree.
Existing source-supplement destinations and digest checks remain unchanged.
Unknown owner/version/license/upstream source or missing installed license text
is a hard error. Resolve package provenance; do not bypass the inventory gate.
Generated schemas/loader caches are attributed to their concrete package-owned
inputs. Review this generated attribution before packaging. Dynamic DLL dependency
closure must also be checked on Windows; the upstream static copy list is retained.

The managed snapshot in `licenses/managed-packages.json` records the local restore,
including build-only and other-platform package alternatives. Rerun on the actual
Windows restore and reconcile it with the files shipped. Many NuGet packages
provide a license expression/URL without shipping the upstream copyright text;
`noticeReviewRequired` explicitly identifies those outstanding source-notice checks.
Do not treat the snapshot or NuGet vulnerability scan as final license clearance.
Copy .NET runtime LICENSE/ThirdPartyNotices and retain all LGPL/MIT/CC-BY/Apache/
Boost notices. Provide the matching native sources or other required LGPL source
delivery, and preserve replaceability/relinking rights when packaging the DLLs.
The root controller owns the public source bundle, manifest, signing and Store work.

Acceptance before signing: runtime-advertised PNG/JPEG/WebP; explicit JPEG quality;
quality rejected for PNG/WebP; real active layered-document preservation including
pending text/selection; keyboard Tab/Escape/Alt+F; Unicode and inaccessible paths;
existing destination/no-overwrite race; explicit overwrite; cancellation during
render and encode; 100/150/200% scaling; install, upgrade, launch and uninstall.
The per-image limit is 100 MP, but the 400 MB combined working-image budget rejects
a 100 MP export. Cancellation is cooperative between native render/encode operations
and is honored up to the atomic publication point.

Recipe recovery acceptance: seed unreadable saved recipes, reopen the recipe dialog,
and verify that Save/Delete are disabled and the recovery explanation is visible.
The explicit **Back up unreadable recipes and start fresh** action must preserve
the exact recipe JSON in a unique `export-recipes-recovery-*.json` file inside the
established `PixelQuay` settings directory before clearing the setting. A failed backup must
leave the original setting locked and unchanged. Retry rereads the application's
current settings service; external file repairs require restarting the application.

Active text acceptance: export while the caret is visible, text is selected, and
the editing frame is visible. Output must retain glyphs, fill/stroke/background,
alignment and the selection captured when editing began, with none of those editing
decorations. The open document, pending text and selection must remain editable
with unchanged history. Headless regressions cover real text models and surfaces;
the actual Windows text tool/dialog interaction remains an acceptance gate.

No automatic upstream-settings migration occurs, and upstream add-in feeds are not
registered. Product metadata and artwork are independent of Pinta. Framework source
namespaces and compatibility identifiers are retained where necessary; no Paint.NET
plug-in compatibility is claimed.
