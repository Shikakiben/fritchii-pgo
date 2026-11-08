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

- `project`: `firefly`, `vendichii` or `fritchii`
- `ref`: leave empty for the project's default branch, or pass a tag/commit
- `upstream`: optionally build any other fork (`owner/name`)

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
