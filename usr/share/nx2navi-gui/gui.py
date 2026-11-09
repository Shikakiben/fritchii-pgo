"""NX2navi Linux GUI: a Tk window that builds Ocarina of Time (Switch 2) from a .nup dump.

What NX2navi's own installer/gui.py wants, this game does not need: it asks for a base NSP, an
update NSP and a console keys file. The .nup route (tools/make_game.py --nup) needs none of that;
this window is that route with a face on it.

It runs tools/make_game.py --events and follows the "@@{json}" lines it prints, the same protocol
Hookshot's Linux builder follows.

Layout inside the AppImage (see build-appimage.sh):
    usr/kit/tools/make_game.py          the build
    usr/python/bin/python3              relocatable CPython, with the kit's packages
    usr/bin/nx2navi_xlate               the shader translator, built already
"""

import json
import os
import queue
import shutil
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

HERE = Path(__file__).resolve().parent
APP = HERE.parent                      # .../usr
KIT = Path(os.environ.get("NX2NAVI_KIT") or (APP / "kit"))
PY = Path(os.environ.get("NX2NAVI_PY") or (APP / "python" / "bin" / "python3"))
MAKE_GAME = KIT / "tools" / "make_game.py"
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "nx2navi-gui" / "gui.json"

STEPS = {
    "check": "Checking the dump",
    "exefs": "Unpacking the game code",
    "romfs": "Extracting the RomFS (about 26 GB)",
    "lift": "Translating AArch64 to C",
    "compile": "Compiling",
    "shaders": "Preparing the shaders",
    "prompts": "Drawing the button prompts",
}

# What the build needs from the distribution. tools/make_game.py links against the system's
# libraries; the compiler and the headers are not in this AppImage on purpose (NX2navi's choice).
TOOLS = ("clang", "clang++", "ld.lld")
HEADERS = ("SDL3/SDL.h", "vulkan/vulkan.h", "opus/opus.h", "vpx/vpx_decoder.h",
           "dav1d/dav1d.h", "zstd.h")
HEADER_INCLUDE = ("/usr/include", "/usr/local/include")

INSTALL = {
    "fedora": ("sudo dnf install -y clang lld SDL3-devel opus-devel libvpx-devel "
               "libdav1d-devel libzstd-devel vulkan-headers vulkan-loader-devel "
               "libstdc++-static libatomic"),
    "arch": ("sudo pacman -S --needed clang lld sdl3 opus libvpx dav1d zstd "
             "vulkan-headers vulkan-icd-loader"),
    "debian": ("sudo apt install -y clang lld libsdl3-dev libopus-dev libvpx-dev "
               "libdav1d-dev libzstd-dev libvulkan-dev"),
}


def distro():
    """fedora / arch / debian, from /etc/os-release and the package manager present."""
    if shutil.which("dnf"):
        return "fedora"
    if shutil.which("pacman"):
        return "arch"
    if shutil.which("apt-get"):
        return "debian"
    return "fedora"


def missing_packages():
    """The tools and headers the build would stop on, as human-readable names."""
    missing = [f"{t} (compiler)" for t in TOOLS if shutil.which(t) is None]
    for header in HEADERS:
        if not any(Path(inc, header).exists() for inc in HEADER_INCLUDE):
            missing.append(header)
    return missing


def default_jobs():
    """One clang per ~4 GB of RAM, as NX2navi's own AppRun does: more fills the RAM and the swap and
    the kernel starts killing desktop processes."""
    try:
        page = os.sysconf("SC_PAGE_SIZE")
        total_gb = os.sysconf("SC_PHYS_PAGES") * page / (1024 ** 3)
    except (ValueError, OSError, AttributeError):
        return 4
    return max(2, min(8, int(total_gb // 4)))


def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_config(data):
    try:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit in ("B", "KB") else f"{n:.1f} {unit}"
        n /= 1024


class Window(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NX2navi — build Ocarina of Time")
        self.minsize(760, 520)
        cfg = load_config()

        self.nup = tk.StringVar(value=cfg.get("nup", ""))
        self.out = tk.StringVar(value=cfg.get("out", str(Path.home() / "Games" / "Ocarina")))
        self.jobs = tk.IntVar(value=int(cfg.get("jobs") or default_jobs()))
        self.status = tk.StringVar(value="")
        self.stage = tk.StringVar(value="")
        self.detail = tk.StringVar(value="")
        self.proc = None
        self.lines = queue.Queue()
        self.started = None

        self.page = None
        self.show_form()
        self.check_environment()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------------------------------------------------------- pages

    def clear(self):
        if self.page:
            self.page.destroy()

    def show_form(self):
        self.clear()
        pad = dict(padx=10, pady=6)
        f = self.page = ttk.Frame(self)
        f.pack(fill="both", expand=True, padx=16, pady=12)
        f.columnconfigure(1, weight=1)

        ttk.Label(f, text="NX2navi", font=("TkDefaultFont", 16, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(f, text="Builds Ocarina of Time (Switch 2) from your own .nup dump. "
                          "No game files are included.").grid(
            row=1, column=0, columnspan=3, sticky="w", **pad)

        ttk.Label(f, text="Game dump (.nup)", font=("TkDefaultFont", 10, "bold")).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(16, 4), padx=10)
        ttk.Entry(f, textvariable=self.nup).grid(row=3, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Button(f, text="Choose…", command=self.pick_nup).grid(row=3, column=2, **pad)

        ttk.Label(f, text="Build into", font=("TkDefaultFont", 10, "bold")).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(10, 4), padx=10)
        ttk.Entry(f, textvariable=self.out).grid(row=5, column=0, columnspan=2, sticky="ew", **pad)
        ttk.Button(f, text="Choose…", command=self.pick_out).grid(row=5, column=2, **pad)

        row = ttk.Frame(f)
        row.grid(row=6, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(row, text="Compile jobs:").pack(side="left")
        ttk.Spinbox(row, from_=2, to=16, width=4, textvariable=self.jobs).pack(side="left", padx=6)
        ttk.Label(row, text=f"(this PC: {os.cpu_count()} threads, "
                            f"{human(os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE'))} RAM)"
                 ).pack(side="left", padx=6)

        self.env_box = ttk.Frame(f)
        self.env_box.grid(row=7, column=0, columnspan=3, sticky="ew", **pad)

        self.start_button = ttk.Button(f, text="Build the game", command=self.start)
        self.start_button.grid(row=8, column=0, columnspan=3, pady=18)

        ttk.Label(f, textvariable=self.status, foreground="#a04000").grid(
            row=9, column=0, columnspan=3, sticky="w", padx=10)

    def show_progress(self):
        self.clear()
        f = self.page = ttk.Frame(self)
        f.pack(fill="both", expand=True, padx=16, pady=12)
        f.columnconfigure(0, weight=1)
        f.rowconfigure(3, weight=1)

        ttk.Label(f, text="Building Ocarina of Time", font=("TkDefaultFont", 14, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Label(f, textvariable=self.stage, font=("TkDefaultFont", 11)).grid(
            row=1, column=0, sticky="w")
        self.bar = ttk.Progressbar(f, mode="determinate", maximum=1000)
        self.bar.grid(row=2, column=0, sticky="ew", pady=8)
        ttk.Label(f, textvariable=self.detail, foreground="#555").grid(row=3, column=0, sticky="nw")

        self.log = tk.Text(f, height=8, wrap="none")
        self.log.grid(row=4, column=0, sticky="nsew", pady=(10, 0))
        f.rowconfigure(4, weight=1)

        self.action = ttk.Button(f, text="Cancel", command=self.cancel)
        self.action.grid(row=5, column=0, pady=12)

    # ---------------------------------------------------------------- actions

    def pick_nup(self):
        path = filedialog.askopenfilename(title="Your .nup dump",
                                          filetypes=[("NX2 navi dump", "*.nup"), ("All files", "*")])
        if path:
            self.nup.set(path)

    def pick_out(self):
        path = filedialog.askdirectory(title="Where to build the game")
        if path:
            self.out.set(path)

    def check_environment(self):
        for w in self.env_box.winfo_children():
            w.destroy()
        missing = missing_packages()
        if not missing:
            return
        ttk.Label(self.env_box, text="Missing for the build: " + ", ".join(missing),
                  foreground="#a00000", wraplength=700, justify="left").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(8, 2), padx=10)
        ttk.Button(self.env_box, text="Install them for me",
                   command=self.install_deps).grid(row=1, column=0, sticky="w", padx=10, pady=4)
        ttk.Button(self.env_box, text="Show the command",
                   command=self.show_command).grid(row=1, column=1, sticky="w", padx=4, pady=4)

    def install_deps(self):
        cmd = INSTALL[distro()]
        if not messagebox.askyesno("Install the build dependencies",
                                   f"This runs:\n\n{cmd}\n\nIt asks for your password."):
            return
        term = shutil.which("gnome-terminal") or shutil.which("konsole") or shutil.which("xterm")
        if term is None:
            self.show_command()
            return
        if term.endswith("gnome-terminal"):
            subprocess.Popen([term, "--", "bash", "-c", cmd + "; echo; echo 'Done. Close this window.'; read"])
        else:
            subprocess.Popen([term, "-e", f"bash -c \"{cmd}; echo; echo 'Done. Close this window.'; read\""])
        self.after(2000, self.check_environment)

    def show_command(self):
        cmd = INSTALL[distro()]
        self.clipboard_clear()
        self.clipboard_append(cmd)
        messagebox.showinfo("Install the build dependencies",
                            f"{cmd}\n\n(copied to the clipboard)")

    def start(self):
        nup = self.nup.get().strip()
        out = self.out.get().strip()
        if not nup or not Path(nup).is_file():
            messagebox.showerror("No game dump", "Choose your .nup file first.")
            return
        if not out:
            messagebox.showerror("No folder", "Choose where to build the game.")
            return
        save_config({"nup": nup, "out": out, "jobs": self.jobs.get()})
        self.check_environment()
        self.show_progress()
        self.stage.set("Starting…")
        self.detail.set("")
        self.bar.configure(value=0)
        self.started = time.time()

        cmd = [str(PY), str(MAKE_GAME), "--nup", nup, "--out", out,
               "--jobs", str(self.jobs.get()), "--events"]
        env = dict(os.environ)
        env.setdefault("NX2NAVI_KIT", str(KIT))
        if shutil.which("nvidia-smi"):
            env.setdefault("NX2NAVI_SHADOW", "0")     # the black-world workaround, issue #72
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                     text=True, bufsize=1, env=env)
        threading.Thread(target=self.read, args=(self.proc,), daemon=True).start()
        self.action.configure(text="Cancel", command=self.cancel)
        self.after(200, self.pump)
        self.tick()

    def cancel(self):
        if self.proc and self.proc.poll() is None:
            if messagebox.askyesno("Stop the build",
                                   "Stop the build? What finished is kept and reused next time."):
                self.proc.send_signal(signal.SIGINT)
                self.status.set("Stopped. Run the build again to carry on.")

    def on_close(self):
        if self.proc and self.proc.poll() is None:
            if not messagebox.askyesno("Quit", "A build is running. Quit anyway?"):
                return
            self.proc.kill()
        self.destroy()

    # ---------------------------------------------------------------- the build

    def read(self, proc):
        for line in proc.stdout:
            self.lines.put(line.rstrip("\n"))
        self.lines.put(None)

    def pump(self):
        try:
            while True:
                line = self.lines.get_nowait()
                if line is None:
                    return
                if line.startswith("@@"):
                    try:
                        self.on_event(json.loads(line[2:]))
                    except ValueError:
                        pass
                else:
                    self.write(line)
        except queue.Empty:
            pass
        if self.proc and self.proc.poll() is None:
            self.after(200, self.pump)

    def on_event(self, ev):
        kind = ev.get("ev")
        if kind == "check":
            self.stage.set(f"Game: {ev.get('version')} ({ev.get('build')})")
        elif kind == "step":
            name = ev.get("step")
            if ev.get("state") == "start":
                self.stage.set(STEPS.get(name, name))
                self.bar.configure(value=0)
            elif ev.get("state") == "done" and ev.get("seconds") is not None:
                self.write(f"{name}: done in {ev['seconds']} s")
        elif kind == "progress":
            done, total = ev.get("done"), ev.get("total")
            if ev.get("fraction") is not None:
                self.bar.configure(value=int(ev["fraction"] * 1000))
            elif total:
                self.bar.configure(value=int(done / total * 1000))
            # the shaders step sends a sentence instead of counts, and repeats it while nothing moves
            if ev.get("detail"):
                self.detail.set(ev["detail"])
            else:
                unit = ev.get("unit") or ""
                self.detail.set(f"{done:,} of {total:,} {unit}".strip() if total else "")
        elif kind == "phase":
            self.detail.set(f"{ev.get('step', '')}: {ev.get('phase', '')}")
        elif kind == "end":
            self.done(ev.get("exe"), ev.get("seconds"))
        elif kind == "error":
            self.failed(ev.get("message", "the build failed"))

    def write(self, text):
        self.log.insert("end", text + "\n")
        self.log.see("end")

    def tick(self):
        if self.proc and self.proc.poll() is None:
            if self.started:
                spent = int(time.time() - self.started)
                self.title(f"NX2navi — {spent // 60} min {spent % 60:02d} s")
            self.after(1000, self.tick)

    def done(self, exe, seconds):
        self.bar.configure(value=1000)
        self.stage.set(f"Finished in {seconds / 60:.0f} min" if seconds else "Finished")
        self.action.configure(text="Play", command=lambda: self.play(exe))
        self.after(400, lambda: self.play(exe))

    def failed(self, message):
        self.stage.set("The build failed")
        self.detail.set(message)
        self.action.configure(text="Back", command=self.show_form)
        self.status.set("See the log above. Fixing what it names and building again resumes "
                        "where it stopped.")

    def play(self, exe):
        if not exe or not Path(exe).is_file():
            self.show_form()
            return
        env = dict(os.environ)
        if shutil.which("nvidia-smi"):
            env.setdefault("NX2NAVI_SHADOW", "0")
        subprocess.Popen([exe], env=env, cwd=str(Path(exe).parent))
        self.destroy()


def main():
    if not MAKE_GAME.is_file():
        sys.exit(f"the build kit is missing: {MAKE_GAME}")
    if not PY.is_file():
        sys.exit(f"the bundled Python is missing: {PY}")
    Window().mainloop()


if __name__ == "__main__":
    main()
