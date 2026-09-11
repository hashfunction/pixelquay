# Review regression evidence

The independent review of `4d231fc87d49a3c4f1f6c0a33448e4bb9b2faa82`
identified destructive recipe saves following unreadable settings (P1) and active
text editing decoration entering exported content (P2). Both were reproduced
before implementation changes.

- `review-p1-red.log`: three behavioral failures from the initial real-store
  regressions (new save, delete and Save without Load).
- `review-p2-red.log`: three pixel assertion failures from the initial real-layer
  probes (caret, selected-text highlight and editing frame).
- `review-p1-api-red.log` / `review-p2-api-red.log`: expanded tests failed to compile
  before the recovery and detached text-rendering APIs existed.
- `review-focused-green.log`: all 14 final new cases passed (six recovery and eight
  pending-text cases, including clean transformed-cache preservation).
- `review-full-tests.log`: 782 core passed; 117 effects passed and the existing
  Voronoi8 case skipped; no failures.
- `review-build.log`: full Release solution build passed, zero warnings/errors.

Commands from the source root:

```sh
DYLD_LIBRARY_PATH=/opt/homebrew/lib dotnet test tests/Pinta.Core.Tests/Pinta.Core.Tests.csproj -c Release --filter ExportRecipeRecoveryTests
DYLD_LIBRARY_PATH=/opt/homebrew/lib dotnet test tests/Pinta.Core.Tests/Pinta.Core.Tests.csproj -c Release --filter PendingTextExportTests
DYLD_LIBRARY_PATH=/opt/homebrew/lib dotnet test tests/Pinta.Core.Tests/Pinta.Core.Tests.csproj -c Release --filter 'ExportRecipeRecoveryTests|PendingTextExportTests'
dotnet build Pinta.sln -c Release --no-restore
DYLD_LIBRARY_PATH=/opt/homebrew/lib dotnet test Pinta.sln -c Release --no-restore
```

Environment: macOS arm64, .NET SDK 8.0.204, installed Homebrew native libraries.
These runs initialize native modules and render through real Pango/Cairo objects,
without initializing a display, constructing GTK widgets or operating the GUI.
Expected corrupt-input stderr messages are exercised by preservation tests.
Source paths in logs are normalized to `<source>`.

The text tests snapshot source dimensions, layer pixels, dirty/saved state, file
association, history, selection and text model/cursor/selection/style/bounds, and
assert no source text modification event. The production text tool captures its
content options during its ordinary redraw; export clones those options and the
model into independent text layouts and surfaces. Clean cached text surfaces are
retained because they may already have been resized or transformed. The live tool
is never committed by export. A real Windows active-text/dialog interaction check
remains required as described in `installer/windows/RELEASE.md`.
