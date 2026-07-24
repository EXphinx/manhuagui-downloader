# ManhuaGui Downloader

[简体中文](README_CN.md)

ManhuaGui Downloader is a local desktop download queue for ManhuaGui. The
interface is built with React and Tauri, while the bundled download service uses
Python's standard library.

## Features

- Accepts comic URLs from `m.manhuagui.com` and `www.manhuagui.com`.
- Loads the complete numbered chapter list.
- Selects chapters by range, search result, status, latest chapters, or all
  chapters not downloaded yet.
- Downloads chapters one at a time and shows image and ZIP progress.
- Reuses completed images and `.part` files after an interruption.
- Saves queue state inside the selected download directory.
- Creates and verifies one ZIP archive per chapter.
- Opens a separate verification window when ManhuaGui requests a human check.
- Includes both a desktop interface and a command-line interface.

## Download and use

Download the latest packages from
[GitHub Releases](https://github.com/EXphinx/manhuagui-downloader/releases/latest).

- **Windows x64:** use the `.exe` installer.
- **Mac with Apple Silicon:** use the `aarch64` DMG.
- **Mac with an Intel processor:** use the `x64` DMG.

The `0.0.1` packages are not signed with a trusted publisher certificate or
notarized. Windows SmartScreen may ask for confirmation. On macOS, right-click
the app and choose **Open** the first time if Gatekeeper blocks a normal
double-click. The macOS bundles use an ad-hoc signature so Apple Silicon can
verify their internal files.

After starting the app:

1. Choose a download directory.
2. Paste a ManhuaGui comic URL.
3. Load the chapter list and select chapters.
4. Add them to the queue. Completed chapters are saved as ZIP files.

## Download directory

The app stores downloads and resumable state in the chosen directory:

```text
chosen directory/
├── .manhuagui/
│   └── tasks.json
└── comic title/
    ├── 001_chapter title.zip
    └── .manhuagui-work/
```

Choosing the same directory again restores unfinished tasks. Existing non-empty
ZIP files are not downloaded again.

## Build from source

### Common requirements

- Python 3.10 or newer
- Node.js 20 or newer
- pnpm 11
- The stable Rust toolchain

Install the JavaScript dependencies:

```bash
corepack enable
pnpm install --frozen-lockfile
```

### Windows build requirements

Install the following first:

- Visual Studio 2022 Build Tools with **Desktop development with C++**
- A Windows 10 or Windows 11 SDK
- Microsoft Edge WebView2 Runtime

Create the Python build environment in PowerShell:

```powershell
py -3 -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
python -m pip install --upgrade pip pyinstaller
pnpm desktop:build
```

The installers are written to:

```text
src-tauri\target\release\bundle\nsis\
```

### macOS build requirements

Install Xcode Command Line Tools:

```bash
xcode-select --install
```

Create the Python build environment and package the app:

```bash
python3 -m venv .venv-build
source .venv-build/bin/activate
python -m pip install --upgrade pip pyinstaller
pnpm desktop:build
```

The DMG is written to:

```text
src-tauri/target/release/bundle/dmg/
```

PyInstaller creates a native sidecar, so build each macOS package on a machine
with the matching architecture. This repository's release workflow uses native
GitHub-hosted runners for Windows x64, macOS Intel, and macOS Apple Silicon.

## Development

Start the browser development mode:

```bash
pnpm dev
```

Then open `http://127.0.0.1:1420/`. Start the Tauri desktop development window
with:

```bash
pnpm desktop
```

The local API listens only on `127.0.0.1:48135`.

## Command-line interface

```bash
python3 -m manhuagui_downloader \
  "https://m.manhuagui.com/comic/1325/" \
  --select 1-3
```

Useful options:

```text
-s, --select RANGE   Chapter range: 1-5, 1,3,8-10, or all
-o, --output DIR     Output directory; default: ./downloads
-j, --workers N      Concurrent image downloads per chapter; default: 4
--list               List chapters without downloading
```

## Tests

```bash
python -m unittest discover -v
pnpm test
pnpm build:web
```

Only download content that you are allowed to save, and follow the website's
terms and applicable laws.

## License

[MIT](LICENSE)
