#!/usr/bin/env python3
"""GUI for converting music to .gta files for GTA LCS / VCS on PSP."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import mp3_to_gta as core

GAMES = {
    "Liberty City Stories (US) - ULUS10041": "ULUS10041",
    "Vice City Stories (US) - ULUS10160": "ULUS10160",
    "Liberty City Stories (EU) - ULES00182": "ULES00182",
    "Vice City Stories (EU) - ULES00503": "ULES00503",
    "Other (type game ID below)": "",
}
FILETYPES = [("Audio files", "*.mp3 *.wav *.flac *.ogg"), ("All files", "*.*")]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GTA Stories Music Converter (PSP)")
        self.geometry("680x560")
        self.minsize(600, 500)
        self.files = []
        self.q = queue.Queue()
        self.worker = None
        self.cancel = False
        self._build()
        self.after(100, self._poll)
        self.after(200, self._startup_checks)

    # ---------- UI ----------
    def _build(self):
        pad = {"padx": 10, "pady": 4}

        top = ttk.LabelFrame(self, text="1. Songs")
        top.pack(fill="both", expand=True, **pad)
        btns = ttk.Frame(top)
        btns.pack(fill="x", padx=6, pady=4)
        ttk.Button(btns, text="Add files...", command=self.add_files).pack(side="left")
        ttk.Button(btns, text="Add folder...", command=self.add_folder).pack(side="left", padx=4)
        ttk.Button(btns, text="Remove selected", command=self.remove_sel).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear).pack(side="left", padx=4)
        self.count_lbl = ttk.Label(btns, text="0 songs")
        self.count_lbl.pack(side="right")

        lf = ttk.Frame(top)
        lf.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.listbox = tk.Listbox(lf, selectmode="extended", height=8)
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        dest = ttk.LabelFrame(self, text="2. Where to put the .gta files")
        dest.pack(fill="x", **pad)
        self.mode = tk.StringVar(value="folder")

        r1 = ttk.Frame(dest)
        r1.pack(fill="x", padx=6, pady=2)
        ttk.Radiobutton(r1, text="A folder on this PC:", variable=self.mode,
                        value="folder", command=self._mode_changed).pack(side="left")
        self.out_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "gta_output"))
        self.out_entry = ttk.Entry(r1, textvariable=self.out_var)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.out_btn = ttk.Button(r1, text="Browse...", command=self.browse_out)
        self.out_btn.pack(side="left")

        r2 = ttk.Frame(dest)
        r2.pack(fill="x", padx=6, pady=2)
        ttk.Radiobutton(r2, text="Straight to my PSP Memory Stick:", variable=self.mode,
                        value="psp", command=self._mode_changed).pack(side="left")

        r3 = ttk.Frame(dest)
        r3.pack(fill="x", padx=26, pady=2)
        ttk.Label(r3, text="Memory Stick drive:").grid(row=0, column=0, sticky="w")
        self.psp_var = tk.StringVar()
        self.psp_entry = ttk.Entry(r3, textvariable=self.psp_var, width=24)
        self.psp_entry.grid(row=0, column=1, sticky="we", padx=6, pady=2)
        self.psp_btn = ttk.Button(r3, text="Browse...", command=self.browse_psp)
        self.psp_btn.grid(row=0, column=2)
        ttk.Label(r3, text="Game:").grid(row=1, column=0, sticky="w")
        self.game_var = tk.StringVar(value=list(GAMES)[0])
        self.game_box = ttk.Combobox(r3, textvariable=self.game_var, values=list(GAMES),
                                     state="readonly", width=40)
        self.game_box.grid(row=1, column=1, columnspan=2, sticky="we", padx=6, pady=2)
        self.game_box.bind("<<ComboboxSelected>>", lambda e: self._mode_changed())
        ttk.Label(r3, text="Game ID:").grid(row=2, column=0, sticky="w")
        self.id_var = tk.StringVar()
        self.id_entry = ttk.Entry(r3, textvariable=self.id_var, width=24)
        self.id_entry.grid(row=2, column=1, sticky="w", padx=6, pady=2)
        r3.columnconfigure(1, weight=1)
        self.path_lbl = ttk.Label(dest, text="", foreground="#555")
        self.path_lbl.pack(fill="x", padx=26, pady=(0, 4))
        for v in (self.psp_var, self.id_var, self.game_var):
            v.trace_add("write", lambda *a: self._update_path_label())
        self.mode.trace_add("write", lambda *a: self._mode_changed())

        run = ttk.LabelFrame(self, text="3. Convert")
        run.pack(fill="both", expand=True, **pad)
        rb = ttk.Frame(run)
        rb.pack(fill="x", padx=6, pady=4)
        self.go_btn = ttk.Button(rb, text="Convert", command=self.start)
        self.go_btn.pack(side="left")
        self.stop_btn = ttk.Button(rb, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=4)
        self.bar = ttk.Progressbar(rb, mode="determinate")
        self.bar.pack(side="left", fill="x", expand=True, padx=8)
        self.log = tk.Text(run, height=7, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self._mode_changed()

    def _mode_changed(self):
        folder = self.mode.get() == "folder"
        for w in (self.out_entry, self.out_btn):
            w.configure(state="normal" if folder else "disabled")
        for w in (self.psp_entry, self.psp_btn):
            w.configure(state="disabled" if folder else "normal")
        self.game_box.configure(state="disabled" if folder else "readonly")
        other = GAMES.get(self.game_var.get(), "") == ""
        self.id_entry.configure(state="normal" if (not folder and other) else "disabled")
        self._update_path_label()

    def _game_id(self):
        gid = GAMES.get(self.game_var.get(), "")
        return (gid or self.id_var.get()).strip().upper()

    def _dest_dir(self):
        if self.mode.get() == "folder":
            return self.out_var.get().strip()
        drive = self.psp_var.get().strip()
        gid = self._game_id()
        if not drive or not gid:
            return ""
        return os.path.join(drive, "PSP", "SAVEDATA", gid + "CUSTOMTRACKS")

    def _update_path_label(self):
        if self.mode.get() == "psp":
            d = self._dest_dir()
            self.path_lbl.configure(text=("Will write to: " + d) if d else "Pick the drive and game.")
        else:
            self.path_lbl.configure(text="")

    # ---------- actions ----------
    def _startup_checks(self):
        if not core.find_encoder():
            messagebox.showerror("Missing file",
                                 "atracdenc.exe not found. Keep it in the same folder as this program.")
        try:
            import miniaudio  # noqa: F401
        except ImportError:
            messagebox.showwarning(
                "One-time setup needed",
                "The audio decoder is not installed yet.\n\n"
                "Open Command Prompt and run:\n    pip install miniaudio\n\n"
                "then start this program again.")

    def _add(self, paths):
        have = set(self.files)
        for p in paths:
            if p not in have:
                self.files.append(p)
                self.listbox.insert("end", os.path.basename(p))
        self.count_lbl.configure(text=f"{len(self.files)} songs")

    def add_files(self):
        self._add(filedialog.askopenfilenames(title="Choose songs", filetypes=FILETYPES))

    def add_folder(self):
        d = filedialog.askdirectory(title="Choose a folder of songs")
        if d:
            self._add(core.collect([d]))

    def remove_sel(self):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)
            del self.files[i]
        self.count_lbl.configure(text=f"{len(self.files)} songs")

    def clear(self):
        self.listbox.delete(0, "end")
        self.files.clear()
        self.count_lbl.configure(text="0 songs")

    def browse_out(self):
        d = filedialog.askdirectory(title="Output folder")
        if d:
            self.out_var.set(d)

    def browse_psp(self):
        d = filedialog.askdirectory(title="Select the PSP Memory Stick (the drive root, e.g. E:\\)")
        if d:
            self.psp_var.set(d)

    def logmsg(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start(self):
        if not self.files:
            messagebox.showinfo("No songs", "Add some songs first.")
            return
        dest = self._dest_dir()
        if not dest:
            messagebox.showinfo("Destination", "Choose the output folder, or the PSP drive and game.")
            return
        enc = core.find_encoder()
        if not enc:
            messagebox.showerror("Missing file", "atracdenc.exe not found next to this program.")
            return
        try:
            import miniaudio  # noqa: F401
        except ImportError:
            messagebox.showerror("Missing decoder", "Run:  pip install miniaudio   then restart.")
            return
        try:
            os.makedirs(dest, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Can't create folder", str(e))
            return
        self.cancel = False
        self.go_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.bar.configure(maximum=len(self.files), value=0)
        self.logmsg(f"Output: {dest}")
        self.worker = threading.Thread(target=self._run, args=(list(self.files), dest, enc), daemon=True)
        self.worker.start()

    def stop(self):
        self.cancel = True
        self.stop_btn.configure(state="disabled")

    def _run(self, files, dest, enc):
        used, ok, total = set(), 0, 0.0
        for i, f in enumerate(files, 1):
            if self.cancel:
                self.q.put(("log", "Stopped."))
                break
            self.q.put(("log", f"[{i}/{len(files)}] {os.path.basename(f)} ..."))
            try:
                out, secs = core.convert_one(f, dest, enc, used)
                ok += 1
                total += secs
                self.q.put(("log", f"    done -> {os.path.basename(out)} ({secs / 60:.1f} min)"))
                if secs > core.MAX_SECONDS:
                    self.q.put(("log", "    WARNING: over 120 minutes; the PSP may not play it."))
            except BaseException as e:  # noqa: BLE001 - keep going on a bad file
                self.q.put(("log", f"    FAILED: {e}"))
            self.q.put(("progress", i))
        self.q.put(("finish", (ok, len(files), total, dest)))

    def _poll(self):
        try:
            while True:
                kind, val = self.q.get_nowait()
                if kind == "log":
                    self.logmsg(val)
                elif kind == "progress":
                    self.bar.configure(value=val)
                elif kind == "finish":
                    ok, n, total, dest = val
                    self.logmsg(f"\nFinished: {ok}/{n} converted ({total / 60:.1f} min).")
                    self.logmsg("In game: Pause > Audio > My Songs ON, then get in a vehicle.")
                    self.go_btn.configure(state="normal")
                    self.stop_btn.configure(state="disabled")
        except queue.Empty:
            pass
        self.after(100, self._poll)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":  # used for testing the bundled exe
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        core.main()
    else:
        App().mainloop()
