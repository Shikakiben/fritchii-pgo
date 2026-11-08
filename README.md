# OoT emulator forks — Linux PGO AppImages

Builds the Linux x86-64 **PGO AppImage** of the OoT-focused emulator forks, on demand,
from their upstream sources.

## Three workflows, one per project

Actions → pick the one you want. Each has **its own branch list**, so a branch can never be
paired with the wrong repository.

| Workflow | Repository | Default branch | Branches in the menu |
|---|---|---|---|
| **build firefly** | [Kradnah/Firefly](https://github.com/Kradnah/Firefly) | `main` | `main` |
| **build vendichii** | [VendavalSC/Vendichii](https://github.com/VendavalSC/Vendichii) | `main` | `main` |
| **build fritchii** | [Frizti/Fritchii](https://github.com/Frizti/Fritchii) | `nx2` | `nx2`, `hotfix/v4.1`, `oot-gather-fix`, `test/no-sky-fold` |

Every workflow also has:

- `ref_custom` — used when the branch is **other**: any branch, tag or commit. A pasted GitHub
  URL (`https://github.com/Frizti/Fritchii/tree/hotfix/v4.1`) is accepted and reduced to the ref.
- `upstream` — optional, to build another repository (`owner/name`).

`build.yml` is the shared, reusable job; it has no dispatch trigger and is not meant to be run
directly.

## Why the lists are static

`workflow_dispatch` cannot fill a `choice` input from the API when the page is opened: GitHub
only accepts options written in the workflow file. Splitting into one workflow per project is
the only way to show a list that matches what is being built. When upstream adds a branch, add
it to the matching `build-*.yml`; `other` always covers the gap.

## Safety checks before the 30-minute build

The first steps run in seconds and stop the run if something is wrong:

- the branch, tag or commit **exists upstream** (`gh api`), otherwise the available branches are
  printed in the log;
- `eglantine.profdata` is present in the source.

## Output

Artifact `<project>-linux-x86_64-pgo-<YYYYMMDD-HHMM>` (Paris time), containing the AppImage and
its `.sha256`:

```sh
chmod +x vendichii-linux-x86_64-pgo-20261108-1755.AppImage
./vendichii-linux-x86_64-pgo-20261108-1755.AppImage
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
upstream projects are licensed under; the source each one was built from is the upstream
repository at the commit recorded in the artifact name.
