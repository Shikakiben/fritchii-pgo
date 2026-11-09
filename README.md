# Fritchii — Linux PGO AppImage

Builds the Linux x86-64 **PGO AppImage** of [Frizti/Fritchii](https://github.com/Frizti/Fritchii),
a Lichii fork tuned for *Ocarina of Time* (Switch 2), on demand, from its source.

Fritchii publishes Windows-only releases; its workflow and its PGO profile are in the repository.

## Why only Fritchii

Firefly and Vendichii were built here too and have been dropped (9 Nov 2026): both had stopped
committing for 30–40 h, are single-person forks far behind upstream, and their Linux value is
covered by Fritchii, which is more active and further along. Any other repository can still be
built through the `upstream` input below.

## Use

Actions → **build fritchii** → *Run workflow*:

| Input | Meaning |
|---|---|
| `branch` | dropdown with the real branches (`nx2`, `hotfix/v4.1`, `oot-gather-fix`, `fritchii-v5.3`, `test/no-sky-fold`), or `other` |
| `linux_fix` | `none`, `status`, or `v5` — see below |
| `disable_werror` | build with `-DENABLE_WERROR=OFF` |
| `ref_custom` | used when `branch` is `other`: any branch, tag or commit. A pasted GitHub URL is accepted and reduced to the ref |
| `upstream` | optional, build another repository (`owner/name`) |

### `linux_fix`

Fritchii's newer branches do not compile on Linux upstream. These options apply the fixes that
are still open as pull requests there:

| Value | What it does | Needed on |
|---|---|---|
| `none` | upstream source untouched | `nx2`, `test/no-sky-fold` |
| `status` | rename the `Status` clash with Xlib | `hotfix/v4.1` (PR #15) |
| `v5` | the three fixes of PR #19, from `patches/fritchii-v53-linux.diff` | `fritchii-v5.3`, `oot-gather-fix` |

The three hard errors in v5:

1. `common/host_memory.cpp` — `CommitAllBut` logs `g_committed_bytes`, declared only under
   `#ifdef _WIN32`. The log goes inside the same guard.
2. `video_core/nx2_precompile.cpp` — `Common::FS::GetExeDirectory()` is Windows-only; a local
   `RecipesDir()` reads `/proc/self/exe` elsewhere.
3. `renderer_vulkan/vk_pipeline_cache.cpp` — Xlib's `#define Status int` eats
   `PipelineCacheMergeResult::Status`; `#undef Status` after the includes.

`fritchii-v5.3` and `oot-gather-fix` are the same commit (`1a7a3c03`), so the patch applies to
both. It is byte-for-byte what PR #19 does for these files.

`disable_werror` matters on v5: upstream compiles with `-Werror` and v5 raises 11 more warnings.
Verified working combination: `branch=fritchii-v5.3`, `linux_fix=v5`, `disable_werror=true` →
AppImage built in ~51 min.

`build.yml` is the shared, reusable job; it has no dispatch trigger.

## Why the branch list is static

`workflow_dispatch` cannot fill a `choice` input from the API when the page is opened: GitHub
only accepts options written in the workflow file. The list lives in `build-fritchii.yml`; when
upstream adds a branch, add it there — `other` always covers the gap.

## Safety checks before the 30-minute build

The first steps run in seconds and stop the run if something is wrong:

- the branch, tag or commit **exists upstream** (`gh api`), otherwise the available branches are
  printed in the log;
- `eglantine.profdata` is present in the source;
- a patch from `patches/` applies cleanly (`git apply --check`, then `-3`).

## Output

Artifact `<project>-linux-x86_64-pgo-<YYYYMMDD-HHMM>` (Paris time), containing the AppImage and
its `.sha256`:

```sh
chmod +x fritchii-linux-x86_64-pgo-20261109-1125.AppImage
./fritchii-linux-x86_64-pgo-20261109-1125.AppImage
```

If the AppImage packaging fails, the compiled binaries are still uploaded as
`<project>-linux-x86_64-pgo-binaries-<stamp>`.

## Why clang 23

`eglantine.profdata` is profile format **version 14**. LLVM 21 reads 12, LLVM 22 reads 13;
a reader older than the writer refuses the profile. The workflow installs clang 23 from
apt.llvm.org, the version the upstream CI pins (`PGO_LLVM_VERSION: "23"`).

## No game data

The build only produces the emulator. There is no game code, key or firmware in this
repository, and the artifacts contain none. Publishing them is covered by the GPLv3 the
upstream project is licensed under; the source it was built from is the upstream repository at
the commit recorded in the artifact name.
