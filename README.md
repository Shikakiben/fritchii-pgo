# firefly-pgo

Builds the Linux x86-64 **PGO AppImage** of [Firefly](https://github.com/Kradnah/Firefly),
a fork of Lichii/Eglantine tuned for *Ocarina of Time* (Switch 2).

Upstream ships Windows-only releases and does not publish its Linux build, even though the
workflow and the PGO profile are in the repository. This workflow checks out the upstream
source and runs the same build upstream's CI does, with `eglantine.profdata`.

## Use

Actions → **firefly-linux-pgo** → *Run workflow* → leave `Kradnah/Firefly` / `main`, or pick a
tag/commit.

When it finishes, download the `firefly-linux-x86_64-pgo` artifact:

```sh
chmod +x firefly-linux-x86_64-pgo.AppImage
./firefly-linux-x86_64-pgo.AppImage
```

## Why clang 23

`eglantine.profdata` is profile format **version 14**. LLVM 21 reads 12, LLVM 22 reads 13;
a reader older than the writer refuses the profile. The workflow installs clang 23 from
apt.llvm.org, the version upstream's CI pins (`PGO_LLVM_VERSION: "23"`).

## No game data

The build only produces the emulator. There is no game code, key or firmware in this
repository, and the artifact contains none. Publishing it is covered by the GPLv3 the
upstream project is licensed under; the source it was built from is the upstream repository
at the commit recorded in the artifact name.