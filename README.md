# OoT emulator forks — Linux PGO AppImages

Builds the Linux x86-64 **PGO AppImage** of the OoT-focused emulator forks, on demand,
from their upstream sources:

| Project | Repository | Branch | GUI binary |
|---|---|---|---|
| **firefly** | [Kradnah/Firefly](https://github.com/Kradnah/Firefly) | `main` | `firefly` |
| **vendichii** | [VendavalSC/Vendichii](https://github.com/VendavalSC/Vendichii) | `main` | `lichii` |
| **fritchii** | [Frizti/Fritchii](https://github.com/Frizti/Fritchii) | `nx2` | `lichii` |

None of them publishes a Linux binary: their releases are Windows-only, even though their
workflow and the PGO profile are in the repository. This repository holds a single workflow
that checks out their source and runs the same build their CI runs, with `eglantine.profdata`.

## Use

Actions → **oot-emulator-linux-pgo** → *Run workflow*:

- `project`: `firefly`, `vendichii` or `fritchii` — the repository and its default branch are
  resolved from this, nothing to type
- `branch`: dropdown with the branches that exist upstream, or `(project default)`, or
  `other (type it below)`
- `ref_custom`: only used when `branch` is `other` — any branch, tag or commit
- `upstream`: optionally build another fork (`owner/name`)

The dropdown is a static list, because `workflow_dispatch` cannot fill a choice input from the
API at click time. When upstream adds a branch, add it to the list in `build.yml`; meanwhile
`other` always works.

| Branch | Firefly | Vendichii | Fritchii |
|---|---|---|---|
| `main` | ✅ | ✅ | |
| `nx2` | | | ✅ (défaut) |
| `hotfix/v4.1` | | | ✅ |
| `oot-gather-fix` | | | ✅ |
| `test/no-sky-fold` | | | ✅ |

When it finishes, download the artifact named
`<project>-linux-x86_64-pgo-<YYYYMMDD-HHMM>` (Paris time of the run):

```sh
chmod +x vendichii-linux-x86_64-pgo-20261108-1755.AppImage
./vendichii-linux-x86_64-pgo-20261108-1755.AppImage
```

The artifact also contains a `.sha256`. If the AppImage packaging fails, the compiled
binaries are still uploaded as `<project>-linux-x86_64-pgo-binaries-<stamp>`.

## Why clang 23

`eglantine.profdata` is profile format **version 14**. LLVM 21 reads 12, LLVM 22 reads 13;
a reader older than the writer refuses the profile. The workflow installs clang 23 from
apt.llvm.org, the version the upstream CI pins (`PGO_LLVM_VERSION: "23"`).

## No game data

The build only produces the emulator. There is no game code, key or firmware in this
repository, and the artifacts contain none. Publishing them is covered by the GPLv3 the
upstream projects are licensed under; the source each one was built from is the upstream
repository at the commit recorded in the artifact name.
