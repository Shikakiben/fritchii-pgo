# Fritchii PGO — Linux AppImage

Builds for *The Legend of Zelda: Ocarina of Time* (Nintendo Switch 2) on Linux, produced on GitHub
Actions and downloadable as workflow **artifacts**:

| Workflow | What it produces | Kind |
|---|---|---|
| **build fritchii** | the Linux x86-64 **PGO AppImage** of [Fritchii](https://github.com/Frizti/Fritchii), a Lichii fork tuned for OoT | artifact |

Everything here builds from the upstream project's own sources. **No game files are included**, and
none is ever needed on this side: each player builds the game from their own dump.

Each build of a **release** publishes it under **Releases**, tagged with Fritchii's own tag
(`fritchii-v5.8.4`) and carrying the AppImage and its `.sha256`. Building the same release again
replaces the asset instead of adding a second one. Branch builds stay as run artifacts only (30 days
for the AppImage, 7 for the fallback binaries).

> The NX2navi GUI build that used to live here was removed on 10 Nov 2026: NX2navi now ships an
> official Linux AppImage (`NX2navi-Linux-<version>-x86_64.AppImage`), so a local GUI wrapper is no
> longer needed.

---

## build fritchii

Fritchii publishes Windows-only releases; its workflow and its PGO profile are in its repository.
This workflow checks the source out and runs the same build its CI runs, with `eglantine.profdata`.

### Use

Actions → **build fritchii** → *Run workflow*:

| Input | Meaning |
|---|---|
| `release` | **`latest`** builds the newest Fritchii release: its tag is checked out and its name labels the output (`Fritchii-v5.7-linux-x86_64-pgo-…`). `no (use the branch)` keeps the branch below |
| `branch` | dropdown with the real branches (`nx2`, `oot-gather-fix`, `fritchii-v5.5`, `fritchii-v5.3`, `hotfix/v4.1`, `test/no-sky-fold`), or `other` |
| `linux_fix` | `none`, `status`, or `v5` — see below |
| `disable_werror` | build with `-DENABLE_WERROR=OFF` |
| `ref_custom` | used when `branch` is `other`: any branch, tag or commit. A pasted GitHub URL is accepted and reduced to the ref |
| `upstream` | optional, build another repository (`owner/name`) |
| `label` | names the artifact and the AppImage after the release, e.g. `Fritchii-v5.7`. Empty keeps `fritchii-…`; `release` fills it on its own |

**Building a new release takes one click**: `release` = `latest`, everything else left alone.
Fritchii publishes every release as a *pre-release*, so `/releases/latest` (which skips
pre-releases) finds nothing — the workflow reads the newest entry of the release list instead.

### `linux_fix`

Fritchii's newer branches do not compile on Linux upstream. These options apply the fixes that are
still open as pull requests there:

| Value | What it does | Needed on |
|---|---|---|
| `none` | upstream source untouched | `nx2`, `test/no-sky-fold`, and every release from **v5.6** on |
| `status` | rename the `Status` clash with Xlib | `hotfix/v4.1` (PR #15) |
| `v5` | the three fixes of PR #19, from `patches/fritchii-v53-linux.diff` | `fritchii-v5.5`, `fritchii-v5.3`, `oot-gather-fix` |
| `pr43-52` | PR #43 (clang `-Wrange-loop-construct` in `fritchii_ui.cpp`) and PR #52 (black blended draws: strict aliasing drops the colour mask), from `patches/fritchii-linux-pr43-pr52.diff` | every release from `fritchii-v5.6` on, while both PRs are open (checked against v5.7 and v5.8.4) |

The three hard errors in v5:

1. `common/host_memory.cpp` — `CommitAllBut` logs `g_committed_bytes`, declared only under
   `#ifdef _WIN32`. The log goes inside the same guard.
2. `video_core/nx2_precompile.cpp` — `Common::FS::GetExeDirectory()` is Windows-only; a local
   `RecipesDir()` reads `/proc/self/exe` elsewhere.
3. `renderer_vulkan/vk_pipeline_cache.cpp` — Xlib's `#define Status int` eats
   `PipelineCacheMergeResult::Status`; `#undef Status` after the includes.

`fritchii-v5.5`, `fritchii-v5.3` and `oot-gather-fix` share the same tree for these files, so the
patch applies to all three. It is byte-for-byte what PR #19 does for them.

### `pr43-52` — what v5.6 and later need on Linux

Two pull requests that are still open upstream, both in `patches/fritchii-linux-pr43-pr52.diff`:

1. **#43** — v5.6's new `src/yuzu/fritchii/fritchii_ui.cpp` copies a `QString` in two range-for
   loops. clang with the project's `-Werror` rejects that (`-Wrange-loop-construct`) and the build
   stops. Two `const QString&` fix it.
2. **#52** — commit `77d7a70cda` builds a `BlendingAttachment` in a local and reads it back through
   a union. Strict aliasing may drop the colour mask, so blended draws write alpha only and the
   title-screen panels, Navi and particles come out as **black silhouettes**. The patch refreshes
   the attachments in place again, as v5.5 did.

`git apply --check` is clean against the `fritchii-v5.7` and `fritchii-v5.8.4` tags. Both are no-ops semantically on a
compiler that does not fall for the aliasing, so they are safe to carry until merged.

`disable_werror` matters on v5: upstream compiles with `-Werror` and v5 raises 11 more warnings.

Verified combinations:

| Branch | `linux_fix` | `disable_werror` | Result |
|---|---|---|---|
| `fritchii-v5.3` | `v5` | ✅ | AppImage, 51 min |
| `fritchii-v5.5` | `v5` | ✅ | AppImage, 15 min (warm ccache) |

`build.yml` is the shared, reusable job; it has no dispatch trigger.

### Output

Artifact `Fritchii-v<version>-linux-x86_64-pgo`, holding the AppImage and its `.sha256`:

```sh
chmod +x Fritchii-v5.8.4-linux-x86_64-pgo.AppImage
./Fritchii-v5.8.4-linux-x86_64-pgo.AppImage
```

The name no longer carries a timestamp: `release: latest` fills it with the release's own name, so
two runs of the same release are told apart by the run, not by a date in the file.

If the AppImage packaging fails, the compiled binaries are still uploaded as
`Fritchii-v<version>-linux-x86_64-pgo-binaries`.

### The Qt SVG plugin is not optional

Fritchii draws **every** icon through `QImageReader("svg")` in `fritchii_ui.cpp` (`RenderSvg`). Qt
reads SVG through a plugin (`imageformats/libqsvg.so`, from Ubuntu's `libqt6svg6`) that is loaded at
run time — never a linked dependency, so `linuxdeploy` only ships it if the package is installed
when it scans the Qt plugin directory.

Without it every icon becomes an empty pixmap: the toolbar (Library, Settings, Help) and the in-game
dock (pause, restart, stop, fullscreen, menu) are **there and clickable but invisible**, showing
nothing but their hover shadow. That is what 5.8.0–5.8.4 shipped. The workflow installs
`libqt6svg6` and checks the built AppImage contains the plugin before uploading.

### Why clang 23

`eglantine.profdata` is profile format **version 14**. LLVM 21 reads 12, LLVM 22 reads 13; a reader
older than the writer refuses the profile. The workflow installs clang 23 from apt.llvm.org, the
version the upstream CI pins (`PGO_LLVM_VERSION: "23"`).

---

## build appimage (NX2navi GUI)

https://github.com/tangerineturtle1/NX2navi builds OoT from a `.nup` with `tools/make_game.py`, and
ships an AppImage packer — but that AppImage is command-line only, and NX2navi's own
`installer/gui.py` wants a base NSP, an update NSP and a console keys file.

This workflow runs the build kit inside a Tk window on the `.nup` route: dependency check, file
pickers, progress bar, Play button. Full description in
[README-nx2navi-gui.md](README-nx2navi-gui.md).

### Use

Actions → **build appimage** → *Run workflow*:

| Input | Meaning |
|---|---|
| `nx2navi_ref` | NX2navi tag, branch or commit; empty = the newest release |
| `force` | build even when this version's AppImage is already published |

**It runs every hour** (`17 * * * *`) and costs nothing when there is no news: a first job reads the
newest NX2navi release and checks whether `nx2navi-gui-<version>` already exists here. Only a new
version starts the 90-minute build. Tags of this repository trigger it too.

Takes the AppImage from Releases:

```sh
chmod +x NX2navi-Linux-GUI-0.6.0-x86_64.AppImage
./NX2navi-Linux-GUI-0.6.0-x86_64.AppImage
```

The window checks for `clang`, `lld` and the development headers of SDL3, Vulkan, Opus, libvpx,
dav1d and zstd, lists what is missing and offers the install command for the distribution. Everything
else — the shader translator, Python 3.14 and its packages — is inside the AppImage.

---

## Why the branch list is static

`workflow_dispatch` cannot fill a `choice` input from the API when the page is opened: GitHub only
accepts options written in the workflow file. The list lives in `build-fritchii.yml`; when upstream
adds a branch, add it there — `other` always covers the gap.

## Safety checks before the long build

The first steps run in seconds and stop the run if something is wrong:

- the branch, tag or commit **exists upstream** (`gh api`), otherwise the available branches are
  printed in the log;
- `eglantine.profdata` is present in the source;
- a patch from `patches/` applies cleanly (`git apply --check`, then `-3`).

## No game data

Every build here produces an emulator or a builder, never game content. There is no game code, key or
firmware in this repository, and the artifacts contain none. Publishing them is covered by the GPLv3
the upstream projects are licensed under; the source each one was built from is the upstream
repository at the commit recorded in the artifact name.
