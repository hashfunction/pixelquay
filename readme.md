# TintFable

TintFable by Trieflow LLC is an independent layered image editor with named export recipes.

- Product: https://tintfable.trieflow.com
- Privacy: https://tintfable.trieflow.com/privacy
- Support: https://tintfable.trieflow.com/support

Use **File → Export with Recipe…** (Ctrl+Alt+E) to create, name, save, select, rename or delete recipes. Choose a size, runtime-supported image format, filename suffix and destination folder. JPEG requires explicit quality (1–100). Quality is unavailable for other exporters. The preview shows the exact absolute output path. Replacement is off by default and must be explicitly enabled.

Exports flatten and resize a detached copy using bilinear resampling, keeping the open document's layers, pixels, selection, undo history, dimensions, filename and dirty state unchanged. A modal progress dialog prevents editing while the worker runs. Cancel waits for the current native image operation, then removes that operation's staging file. Publication uses a same-directory atomic move; an output created during rendering is protected when replacement is off. An original-file destination is rejected even when replacement is enabled.

Per-axis dimensions are capped at 32,767 and total pixels at 100 million. The incremental working-image estimate (two source surfaces and four output surfaces) must also fit 400 MB. Consequently a 100 MP requested image passes the size limit but fails the working-set limit. This budget does not guarantee native encoders' total process memory usage.

Settings and add-ins retain the established `PixelQuay` application-data directory and `pixelquay.export-recipes.v1` key so existing preferences and export recipes remain available after the TintFable rename. Upstream settings are not automatically imported, and upstream add-in feeds are not registered. Paint.NET plug-in compatibility is not provided. No analytics or remote image processing is added by this fork.

Based on Pinta 3.1.2, commit `b3df1e579f6b3dd23193d2f6877deced20d8063b`, with complete upstream source history retained. Product identity and original artwork are by Trieflow LLC. Pinta contributors' MIT rights and Paint.NET 3.36 MIT source notices remain in `license-mit.txt` and `license-pdn.txt`. See `THIRD-PARTY-NOTICES.txt` and About for credits. Native/managed dependency inventories and full license texts must accompany a Windows release; see `installer/windows/RELEASE.md`.

## Icons are from:

- [Paint.Net 3.0](http://www.getpaint.net/)
Used under [MIT License](http://www.opensource.org/licenses/mit-license.php)

- [Silk icon set](https://github.com/markjames/famfamfam-silk-icons)
Used under [Creative Commons Attribution 3.0 License](http://creativecommons.org/licenses/by/3.0/)

- [Fugue icon set](https://p.yusukekamiyamane.com)
Used under [Creative Commons Attribution 3.0 License](http://creativecommons.org/licenses/by/3.0/)

- Pinta contributors, under the same license as the project itself
(see `Pinta.Resources/icons/pinta-icons.md` for the list of such icons)

Additional retained icons include Google Material Icons (Apache-2.0) and Microsoft Fluent UI System Icons (MIT), as documented in the icon source directories and About dialog.

## Building on Windows

First, install the required GTK-related dependencies:
- Install [MSYS2](https://www.msys2.org)
- From the CLANG64 terminal, run `pacman -S mingw-w64-clang-x86_64-libadwaita mingw-w64-clang-x86_64-webp-pixbuf-loader`.
  - For ARM64 Windows, use the `CLANGARM64` terminal and replace `clang-x86_64` with `clang-aarch64`.

TintFable can then be built by opening `Pinta.sln` in [Visual Studio](https://visualstudio.microsoft.com/).
Ensure that .NET 8 is installed via the Visual Studio installer.

For building on the command line:
- [Install the .NET 8 SDK](https://dotnet.microsoft.com/).
- Build:
  - `dotnet build`
- Run:
  - `dotnet run --project Pinta`

## Building on macOS

- Install .NET 8 and GTK4
  - `brew install dotnet-sdk libadwaita adwaita-icon-theme gettext webp-pixbuf-loader`
  - For Apple Silicon, set `DYLD_LIBRARY_PATH=/opt/homebrew/lib` in the environment so that TintFable can load the GTK libraries
  - For Intel, you may need to set `DYLD_LIBRARY_PATH=/usr/local/lib` when using .NET 9 or higher
- Build:
  - `dotnet build`
- Run:
  - `dotnet run --project Pinta`

## Building on Linux

- Install [.NET 8](https://dotnet.microsoft.com/) following the instructions for your Linux distribution.
- Install other dependencies (instructions are for Ubuntu 22.10, but should be similar for other distros):
  - `sudo apt install autotools-dev autoconf-archive gettext intltool libadwaita-1-dev`
  - Minimum library versions: `gtk` >= 4.18 and `libadwaita` >= 1.7
  - Optional dependencies: `webp-pixbuf-loader`
- Build (option 1, for development and testing):
  - `dotnet build`
  - `dotnet run --project Pinta`
- Build (option 2, for installation):
  - `./autogen.sh`
    - If building from a tarball, run `./configure` instead.
    - Add the `--prefix=<install directory>` argument to install to a directory other than `/usr/local`.
  - `make install`

## Building and Debugging in Docker

Follow the instructions of the corresponding [pinta-virtual-dev-environment](https://github.com/janrothkegel/pinta-virtual-dev-environment) project

## TintFable support

For product help and issue reports, visit https://tintfable.trieflow.com/support.

## Upstream Pinta resources and contributing:

- You can get [technical help](https://github.com/PintaProject/Pinta/discussions).
- You can report [bugs/issues](https://github.com/PintaProject/Pinta/issues).
- You can make [suggestions](https://github.com/PintaProject/Pinta/discussions/categories/ideas).
- You can help [translate Pinta to your native language](https://hosted.weblate.org/engage/pinta/).
- You can fork the project on [Github](https://github.com/PintaProject/Pinta).
- You can get help in #pinta on irc.gnome.org.
- For details on notable changes of each release, take a look at the [CHANGELOG](https://github.com/PintaProject/Pinta/blob/master/CHANGELOG.md).
- For details on patching, take a look at `patch-guidelines.md` in the repo.

## Upstream Pinta code signing policy

The following retained upstream policy does not describe TintFable signing.

- Free code signing on Windows provided by [SignPath.io](https://about.signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).
- Committers and approvers: [Pinta Maintainers](https://github.com/orgs/PintaProject/people)
- Privacy policy: this program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.
