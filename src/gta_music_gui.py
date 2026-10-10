#!/usr/bin/env python3
"""GUI for converting music to .gta files for GTA LCS / VCS on PSP."""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import mp3_to_gta as core
import track_names as tn

GAMES = {
    "Liberty City Stories (US) - ULUS10041": "ULUS10041",
    "Vice City Stories (US) - ULUS10160": "ULUS10160",
    "Liberty City Stories (EU) - ULES00182": "ULES00182",
    "Vice City Stories (EU) - ULES00503": "ULES00503",
    "Other (type game ID below)": "",
}
STYLE_LABELS = {
    "Artist - Title (from tags)": "artist-title",
    "Title only (from tags)": "title",
    "Keep file name (tidied)": "filename",
}
FILETYPES = [("Audio files", "*.mp3 *.wav *.flac *.ogg"), ("All files", "*.*")]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GTA Stories Music Converter (PSP)")
        self.geometry("760x720")
        self.minsize(660, 640)
        self.entries = []  # dicts: path, manual (str or None), final (str)
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
        ttk.Button(btns, text="Remove", command=self.remove_sel).pack(side="left")
        ttk.Button(btns, text="Clear", command=self.clear).pack(side="left", padx=4)
        ttk.Button(btns, text="Up", width=5, command=lambda: self.move(-1)).pack(side="left", padx=(12, 0))
        ttk.Button(btns, text="Down", width=5, command=lambda: self.move(1)).pack(side="left", padx=2)
        self.count_lbl = ttk.Label(btns, text="0 songs")
        self.count_lbl.pack(side="right")

        tf = ttk.Frame(top)
        tf.pack(fill="both", expand=True, padx=6, pady=(0, 4))
        self.tree = ttk.Treeview(tf, columns=("n", "src", "name"), show="headings",
                                 selectmode="extended", height=8)
        self.tree.heading("n", text="#")
        self.tree.heading("src", text="Song file")
        self.tree.heading("name", text="Name shown in game  (double-click to edit)")
        self.tree.column("n", width=34, anchor="e", stretch=False)
        self.tree.column("src", width=240)
        self.tree.column("name", width=330)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.rename_selected)

        opt = ttk.Frame(top)
        opt.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Label(opt, text="Name style:").grid(row=0, column=0, sticky="w")
        self.style_var = tk.StringVar(value=list(STYLE_LABELS)[0])
        cb = ttk.Combobox(opt, textvariable=self.style_var, values=list(STYLE_LABELS),
                          state="readonly", width=26)
        cb.grid(row=0, column=1, sticky="w", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._recompute())
        ttk.Label(opt, text="Max length:").grid(row=0, column=2, sticky="e", padx=(14, 0))
        self.len_var = tk.IntVar(value=40)
        sp = ttk.Spinbox(opt, from_=16, to=80, width=4, textvariable=self.len_var, command=self._recompute)
        sp.grid(row=0, column=3, sticky="w", padx=6)
        sp.bind("<FocusOut>", lambda e: self._recompute())
        sp.bind("<Return>", lambda e: self._recompute())
        self.punct_var = tk.BooleanVar(value=False)
        self.caps_var = tk.BooleanVar(value=False)
        self.num_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="Keep punctuation  ' & , . ! ( )", variable=self.punct_var,
                        command=self._recompute).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))
        ttk.Checkbutton(opt, text="Fix ALL CAPS / lowercase", variable=self.caps_var,
                        command=self._recompute).grid(row=1, column=2, columnspan=2, sticky="w", pady=(4, 0), padx=(14, 0))
        ttk.Checkbutton(opt, text='Number tracks ("01 - ", "02 - " in list order)', variable=self.num_var,
                        command=self._recompute).grid(row=2, column=0, columnspan=4, sticky="w")

        dest = ttk.LabelFrame(self, text="2. Where to put the .gta files")
        dest.pack(fill="x", **pad)
        self.mode = tk.StringVar(value="folder")

        r1 = ttk.Frame(dest)
        r1.pack(fill="x", padx=6, pady=2)
        ttk.Radiobutton(r1, text="A folder on this PC:", variable=self.mode,
                        value="folder").pack(side="left")
        self.out_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "gta_output"))
        self.out_entry = ttk.Entry(r1, textvariable=self.out_var)
        self.out_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.out_btn = ttk.Button(r1, text="Browse...", command=self.browse_out)
        self.out_btn.pack(side="left")

        r2 = ttk.Frame(dest)
        r2.pack(fill="x", padx=6, pady=2)
        ttk.Radiobutton(r2, text="Straight to my PSP Memory Stick:", variable=self.mode,
                        value="psp").pack(side="left")

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
        self.log = tk.Text(run, height=6, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=6, pady=(0, 6))

        self._mode_changed()

    # ---------- destination helpers ----------
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
        self._mode_changed_labels_only()

    def _mode_changed_labels_only(self):
        if self.mode.get() == "psp":
            d = self._dest_dir()
            self.path_lbl.configure(text=("Will write to: " + d) if d else "Pick the drive and game.")
        else:
            self.path_lbl.configure(text="")

    # ---------- naming ----------
    def _opts(self):
        try:
            ml = max(16, min(80, int(self.len_var.get())))
        except (tk.TclError, ValueError):
            ml = 40
        return (STYLE_LABELS.get(self.style_var.get(), "artist-title"),
                self.punct_var.get(), ml, self.caps_var.get(), self.num_var.get())

    def _recompute(self):
        style, punct, maxlen, caps, number = self._opts()
        raw = []
        for e in self.entries:
            raw.append(e["manual"] if e["manual"] is not None
                       else tn.suggest_name(e["path"], style, punct, maxlen, caps))
        finals = tn.number_and_dedupe(raw, punct, maxlen, number)
        for e, f in zip(self.entries, finals):
            e["final"] = f
        self._refresh_tree()

    def _refresh_tree(self, keep=None):
        sel = set(self.tree.selection()) if keep is None else keep
        self.tree.delete(*self.tree.get_children())
        for i, e in enumerate(self.entries):
            mark = "  (edited)" if e["manual"] is not None else ""
            self.tree.insert("", "end", iid=str(i),
                             values=(i + 1, os.path.basename(e["path"]), e["final"] + mark))
        for iid in sel:
            if self.tree.exists(iid):
                self.tree.selection_add(iid)
        self.count_lbl.configure(text=f"{len(self.entries)} songs")

    def rename_selected(self, event=None):
        iid = self.tree.identify_row(event.y) if event else (self.tree.selection() or [None])[0]
        if not iid:
            return
        e = self.entries[int(iid)]
        new = simpledialog.askstring("Name shown in game",
                                     "Name for this song in game (leave empty to go back to automatic):",
                                     initialvalue=e["final"], parent=self)
        if new is None:
            return
        e["manual"] = new.strip() or None
        self._recompute()

    # ---------- list actions ----------
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
        have = {e["path"] for e in self.entries}
        for p in paths:
            if p not in have:
                self.entries.append({"path": p, "manual": None, "final": ""})
        self._recompute()

    def add_files(self):
        self._add(filedialog.askopenfilenames(title="Choose songs", filetypes=FILETYPES))

    def add_folder(self):
        d = filedialog.askdirectory(title="Choose a folder of songs")
        if d:
            self._add(core.collect([d]))

    def remove_sel(self):
        for iid in sorted((int(i) for i in self.tree.selection()), reverse=True):
            del self.entries[iid]
        self._recompute()

    def clear(self):
        self.entries.clear()
        self._recompute()

    def move(self, d):
        sel = sorted(int(i) for i in self.tree.selection())
        if not sel:
            return
        if d < 0 and sel[0] == 0 or d > 0 and sel[-1] == len(self.entries) - 1:
            return
        for i in (sel if d < 0 else reversed(sel)):
            self.entries[i + d], self.entries[i] = self.entries[i], self.entries[i + d]
        self._recompute()
        self.tree.selection_set([str(i + d) for i in sel])

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

    # ---------- convert ----------
    def start(self):
        if not self.entries:
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
        self._recompute()
        jobs = [(e["path"], e["final"]) for e in self.entries]
        self.cancel = False
        self.go_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.bar.configure(maximum=len(jobs), value=0)
        self.logmsg(f"Output: {dest}")
        self.worker = threading.Thread(target=self._run, args=(jobs, dest, enc), daemon=True)
        self.worker.start()

    def stop(self):
        self.cancel = True
        self.stop_btn.configure(state="disabled")

    def _run(self, jobs, dest, enc):
        ok, total = 0, 0.0
        for i, (path, name) in enumerate(jobs, 1):
            if self.cancel:
                self.q.put(("log", "Stopped."))
                break
            self.q.put(("log", f"[{i}/{len(jobs)}] {os.path.basename(path)}  ->  {name} ..."))
            try:
                out, secs = core.convert_one(path, dest, enc, name)
                ok += 1
                total += secs
                self.q.put(("log", f"    done ({secs / 60:.1f} min)"))
                if secs > core.MAX_SECONDS:
                    self.q.put(("log", "    WARNING: over 120 minutes; the PSP may not play it."))
            except BaseException as e:  # noqa: BLE001 - keep going on a bad file
                self.q.put(("log", f"    FAILED: {e}"))
            self.q.put(("progress", i))
        self.q.put(("finish", (ok, len(jobs), total, dest)))

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
