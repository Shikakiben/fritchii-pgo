# Fritchii — Linux AppImage (PGO)

The Linux x86-64 build of [Fritchii](https://github.com/Frizti/Fritchii): *The Legend of Zelda:
Ocarina of Time* (Nintendo Switch 2) running natively.

Fritchii ships **Windows only**. This repository builds the Linux AppImage from its own source on
GitHub Actions and publishes it under **Releases** — that is the only place to download it.

| | |
|---|---|
| Upstream | [Frizti/Fritchii](https://github.com/Frizti/Fritchii) |
| Workflow | **build fritchii** (Actions, manual) |
| Output | `Fritchii-v<version>-linux-x86_64-pgo.AppImage` + `.sha256` |
| Where | Releases, tagged with Fritchii's own tag |

**No game files.** This repository holds no game code, key or firmware, and the AppImage contains
none. Like the Windows build, it compiles the game on your PC from your own dump.

## Build a new release

Actions → **build fritchii** → *Run workflow*. Leave `release` on `latest`, change nothing else.

It reads the newest Fritchii release, builds its tag, names the AppImage after it, and publishes the
result as a release under the same tag. Building the same release again **replaces** the asset.

Fritchii publishes every release as a *pre-release*, so `/releases/latest` (which skips
pre-releases) returns 404; the workflow reads the newest entry of the release list instead.

### Inputs

| Input | Meaning |
|---|---|
| `release` | `latest` (default) builds the newest release. `no (use the ref below)` builds `ref` and publishes nothing |
| `ref` | branch, tag or commit, when `release` is `no`. A pasted GitHub URL is accepted. Default `nx2` |
| `linux_fix` | `pr43-52` (default) or `none` — see below |
| `disable_werror` | configure with `-DENABLE_WERROR=OFF` |
| `label` | override the output name (`Fritchii-v5.8.4`). Empty = the release's name, else `fritchii` |

### `linux_fix`

`pr43-52` applies `patches/fritchii-linux-pr43-pr52.diff`, two pull requests still open upstream:

| PR | Bug | Fix |
|---|---|---|
| #43 | v5.6's `fritchii_ui.cpp` copies a `QString` in two range-for loops; clang under `-Werror` rejects it and the build stops | `const QString&` |
| #52 | `77d7a70cda` builds a `BlendingAttachment` in a local and reads it back through a union; strict aliasing drops the colour mask, so blended draws write alpha only — black silhouettes for the title panels, Navi and particles | refresh the attachments in place, as v5.5 did |

Both apply cleanly to the `fritchii-v5.7` and `fritchii-v5.8.4` tags. **Set `linux_fix` to `none` once
upstream merges them**: the patch then stops applying and the build says so in seconds.

## Run it

```sh
chmod +x Fritchii-v5.8.4-linux-x86_64-pgo.AppImage
./Fritchii-v5.8.4-linux-x86_64-pgo.AppImage
```

## What the build does

1. resolves the tag, checks it exists upstream, and checks out that source;
2. applies `patches/` when asked;
3. installs the dependencies, including **`libqt6svg6`**;
4. compiles with clang 23 against `eglantine.profdata` (PGO), the profile upstream's CI uses;
5. packages the AppImage with `linuxdeploy` and its Qt plugin;
6. checks the AppImage really contains the Qt SVG plugin;
7. publishes it as a release, and as a run artifact kept 30 days.

### The Qt SVG plugin is not optional

Fritchii draws every icon through `QImageReader("svg")` (`fritchii_ui.cpp`, `RenderSvg`). Qt reads
SVG through a plugin, `imageformats/libqsvg.so` (Ubuntu's `libqt6svg6`), loaded at run time — never a
linked dependency, so `linuxdeploy` only ships it if the package is installed when it scans the Qt
plugin directory.

Without it every icon is an empty pixmap: the toolbar (Library, Settings, Help) and the in-game dock
(pause, restart, stop, fullscreen, menu) are there and clickable but **invisible**, showing only
their hover shadow. That is what 5.8.0–5.8.4 shipped. The workflow installs `libqt6svg6` and fails
if the built AppImage lacks the plugin.

### Why clang 23

`eglantine.profdata` is profile format **version 14**. LLVM 21 reads 12, LLVM 22 reads 13; a reader
older than the writer refuses the profile. The workflow installs clang 23 from apt.llvm.org, the
version upstream's CI pins.

### Robustness, and why each guard exists

| Guard | What it prevents |
|---|---|
| apt retries five times | a runner losing DNS threw away 1 h 40 before compiling anything |
| fallback upload is `continue-on-error` | a flaky artifact service failed a run whose build had succeeded |
| AppImage upload is `always()` | a failed publish used to skip the upload, losing a finished AppImage with the runner |
| `gh release` carries `--repo` | the job runs inside a checkout of upstream, so `gh` targeted *its* release (403) |

## Licence

Fritchii is GPL-3.0-or-later. Every build here is of its source at the tag recorded in the release.
