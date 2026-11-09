# NX2navi Linux GUI

Builds **Ocarina of Time (Switch 2)** natively on Linux from your own `.nup` dump, in a window —
dependency check, file pickers, progress bar, then a **Play** button.

NX2navi already ships a Linux build kit (`tools/make_game.py`) and an AppImage packer
(`tools/make_appimage.py`), but:

- the AppImage it produces is **command-line only**, and
- its own `installer/gui.py` wants a **base NSP + update NSP + console keys**, while the `.nup`
  route needs none of that.

This repository adds the window that route was missing, in the same way Hookshot's Linux builder
does it: the kit and a relocatable Python go inside the AppImage, and the window drives
`make_game.py --events`.

## Download and run

Take `NX2navi-Linux-GUI-<version>-x86_64.AppImage` from
[Releases](../../releases), make it executable, run it:

```sh
chmod +x NX2navi-Linux-GUI-0.6.0-x86_64.AppImage
./NX2navi-Linux-GUI-0.6.0-x86_64.AppImage
```

The window opens: pick your `.nup`, pick where to build, press **Build**, then **Play**.

Nothing else to install on the emulator side — the shader translator, a relocatable Python 3.14
and its packages are inside the AppImage.

## The one thing that stays outside

NX2navi links against the system's compiler and libraries, by design
(`README-BuildKit.md`, "Linux"). The window checks them, lists what is missing and offers to run
the install command for you. On Fedora:

```sh
sudo dnf install -y clang lld SDL3-devel opus-devel libvpx-devel libdav1d-devel libzstd-devel \
    vulkan-headers vulkan-loader-devel libstdc++-static libatomic
```

`zbic` is installed by the build itself on first use.

## Builds are automatic

`.github/workflows/build-appimage.yml` builds the AppImage on GitHub, daily and on every NX2navi
release, so the file is always current. To build it by hand:

```bash
git clone --depth 1 --branch v0.6.0 https://github.com/tangerineturtle1/NX2navi.git
cd NX2navi && python3 tools/build_xlate.py       # needs the .NET 10 SDK, once
cd .. && git clone <this repo> nx2navi-gui && cd nx2navi-gui
./build-appimage.sh ../NX2navi                   # → dist/NX2navi-Linux-GUI-0.6.0-x86_64.AppImage
```

## What the window does

| Feature | How |
|---|---|
| **Missing dependencies** | checks `clang`, `clang++`, `ld.lld` and the six headers the build links against; lists what is missing and offers **Install them for me** (runs `dnf`/`pacman`/`apt` in a terminal, after asking) |
| **Choose the `.nup`** | file dialog, filtered on `*.nup` |
| **Choose the destination** | folder dialog; remembers the last choices in `~/.config/nx2navi-gui/gui.json` |
| **Compile jobs** | prefilled from the RAM (one clang per ~4 GB), because one per thread fills the RAM and swap until the kernel kills desktop processes |
| **Progress** | stage name, bar, counts (bytes for the RomFS, files for the compile), and the shaders step's own sentence — including *"No change for N min, but it is still running"* |
| **Log** | every other line the build prints |
| **Cancel** | `SIGINT`; what finished is kept and reused by the next run |
| **Play** | starts the built game, with `NX2NAVI_SHADOW=0` set on NVIDIA (the black-world workaround, issue #72) |

The window reads the `"@@{json}"` events that `make_game.py --events` prints — the same protocol
Hookshot's `builder/linux/hookshot_builder.py` follows, so the two behave alike.

## What stays outside the AppImage

The compiler and the system libraries are **not** bundled, as NX2navi decided
(`README-BuildKit.md`, "Linux"): the AppImage needs `clang`, `lld` and the development headers of
SDL3, Vulkan, Opus, libvpx, dav1d and zstd. The window detects them and offers the install command
for your distribution.

`zbic` is installed by `make_game.py` itself on first use, as upstream does.

## No game data

Nothing here contains game code, keys or firmware. Everything the build writes comes from the
player's own dump.
