"""Windows Tkinter UI with sequential processes and a disk-backed live console."""

import codecs
import os
import shutil
import subprocess
import tkinter as tk
from dataclasses import fields
from datetime import datetime
from tkinter import filedialog, ttk

from app.config import Options, Settings
from app.runner import build_command, prepare_run


class MainView(ttk.Frame):
    def __init__(self, parent, settings):
        super().__init__(parent, padding=16)
        self.settings = settings
        self.process = None
        self.log_reader = None
        self.log_path = None
        self.timer = None
        self.stopping = False
        self.closing = False
        self.inputs = []
        self.variables = {
            field.name: (tk.BooleanVar if field.type is bool else tk.StringVar)(
                self, value=getattr(settings.values, field.name),
            ) for field in fields(Options)
        }
        self.status = tk.StringVar(self, value="Choose a URL or text file to begin.")
        self.follow = tk.BooleanVar(self, value=True)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        ttk.Label(self, text="EZ Gallery DL", font=("Segoe UI", 20, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12),
        )
        self.panes = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        self.panes.grid(row=1, column=0, sticky="nsew")
        tabs = ttk.Notebook(self.panes)
        self.panes.add(tabs, weight=0)
        tabs.enable_traversal()
        download = ttk.Frame(tabs, padding=12)
        options = ttk.Frame(tabs, padding=12)
        advanced = ttk.Frame(tabs, padding=12)
        settings_tab = ttk.Frame(tabs, padding=12)
        for tab, title in ((download, "Download"), (options, "Options"), (advanced, "Advanced"), (settings_tab, "Settings")):
            tabs.add(tab, text=title)
            tab.columnconfigure(1, weight=1)

        source = ttk.Frame(download)
        source.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
        for mode in ("URL", "Text file"):
            button = ttk.Radiobutton(source, text=mode, variable=self.variables["source_mode"], value=mode, command=self.source_changed)
            button.pack(side="left", padx=(0, 16))
            self.inputs.append(button)
        self.url_entry = self.entry(download, 1, "Gallery URL", "url")
        self.file_entry = self.entry(download, 2, "URL text file", "input_file", "file")
        self.file_button = self.inputs[-1]
        self.entry(download, 3, "Working folder", "working_directory", "directory")
        ttk.Label(download, text="Blank working folder: text file's parent folder,\nor Downloads for a direct URL.", justify="left").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(4, 18),
        )
        self.entry(download, 5, "Download location", "destination", "directory")
        self.check(download, 6, "Use exact location (no gallery subfolders)", "exact_directory")
        ttk.Label(download, text="Blank download location keeps gallery-dl's configuration.\nRelative paths are resolved inside the working folder.", justify="left").grid(
            row=7, column=0, columnspan=3, sticky="w", pady=(4, 18),
        )
        self.check(download, 8, "Simulate extraction without downloading", "simulate")
        self.check(download, 9, "Verbose console output", "verbose")

        for row, (title, key, browse) in enumerate((
            ("gallery-dl config", "gallery_config", "file"),
            ("Cookies file", "cookies", "file"),
            ("Browser / profile", "browser", None),
            ("Download archive", "archive", "save"),
            ("Filename format", "filename", None),
            ("Rate limit (e.g. 2M)", "limit_rate", None),
            ("Sleep seconds", "sleep", None),
            ("File range (e.g. 1-20)", "file_range", None),
        )):
            self.entry(options, row, title, key, browse)
        self.check(options, 8, "Write metadata JSON", "metadata")
        self.check(options, 9, "Write tags", "tags")
        ttk.Label(options, text="Browser examples: firefox, chrome:Default, edge\nAuthentication and site settings can go in the config file.").grid(
            row=10, column=0, columnspan=3, sticky="w", pady=12,
        )

        advanced.columnconfigure(0, weight=1)
        advanced.rowconfigure(1, weight=1)
        ttk.Label(advanced, text="Additional CLI arguments: one argument per line.\nPut each option's value on the next line; do not add quotes.\nExample:\n--filter\nimage_width >= 1000").grid(row=0, column=0, sticky="w", pady=(0, 12))
        self.extra = tk.Text(advanced, width=30, height=12, wrap="none", undo=True)
        self.extra.grid(row=1, column=0, sticky="nsew")
        self.extra.insert("1.0", settings.values.extra_arguments)
        extra_scroll = ttk.Scrollbar(advanced, command=self.extra.yview)
        extra_scroll.grid(row=1, column=1, sticky="ns")
        self.extra.configure(yscrollcommand=extra_scroll.set)

        self.entry(settings_tab, 0, "gallery-dl executable", "executable", "file")
        ttk.Label(settings_tab, text="Blank uses gallery-dl installed with this app.\nSelect an existing gallery-dl.exe to use your own CLI.").grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 16))
        ttk.Label(settings_tab, text="Configuration folder").grid(row=2, column=0, columnspan=3, sticky="w")
        location = ttk.Entry(settings_tab)
        location.insert(0, str(settings.directory))
        location.configure(state="readonly")
        location.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 12))
        ttk.Button(settings_tab, text="Open configuration folder", command=lambda: os.startfile(settings.directory)).grid(row=4, column=0, columnspan=3, sticky="w")
        save = ttk.Button(settings_tab, text="Save current options as defaults", command=self.save_defaults)
        save.grid(row=5, column=0, columnspan=3, sticky="w", pady=(16, 8))
        restore = ttk.Button(settings_tab, text="Load saved defaults", command=self.load_defaults)
        restore.grid(row=6, column=0, columnspan=3, sticky="w")
        self.inputs.extend([save, restore])
        ttk.Label(settings_tab, text="The last session is saved automatically on run and close.\nconfig.json stores defaults; state.json stores the last session.").grid(row=7, column=0, columnspan=3, sticky="w", pady=16)

        console_frame = ttk.Frame(self.panes, padding=(12, 0, 0, 0))
        self.panes.add(console_frame, weight=1)
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(1, weight=1)
        console_actions = ttk.Frame(console_frame)
        console_actions.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Label(console_actions, text="Console", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Checkbutton(console_actions, text="Follow output", variable=self.follow).pack(side="right")
        self.console = tk.Text(console_frame, width=45, height=15, wrap="none", state="disabled", font="TkFixedFont", background="#17212b", foreground="#e4edf5", selectbackground="#355d80")
        self.console.grid(row=1, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(console_frame, command=self.console.yview)
        vertical.grid(row=1, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(console_frame, orient="horizontal", command=self.console.xview)
        horizontal.grid(row=2, column=0, sticky="ew")
        self.console.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        log_actions = ttk.Frame(console_frame)
        log_actions.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(log_actions, text="Copy logs", command=self.copy_logs).pack(side="left")
        self.save_log = ttk.Button(log_actions, text="Save logs…", command=self.export_logs, state="disabled")
        self.save_log.pack(side="left", padx=8)
        self.open_log = ttk.Button(log_actions, text="Open log folder", command=lambda: os.startfile(self.log_path.parent), state="disabled")
        self.open_log.pack(side="left")

        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.grid(row=2, column=0, sticky="ew", pady=(16, 8))
        footer = ttk.Frame(self)
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        status_label = ttk.Label(footer, textvariable=self.status, wraplength=760)
        status_label.grid(row=0, column=0, sticky="w")
        footer.bind("<Configure>", lambda event: status_label.configure(wraplength=max(200, event.width - 250)))
        self.start_button = ttk.Button(footer, text="Start download", command=self.start)
        self.start_button.grid(row=0, column=1, padx=8)
        self.stop_button = ttk.Button(footer, text="Stop", command=self.stop, state="disabled")
        self.stop_button.grid(row=0, column=2)
        self.panes.bind("<Map>", self.restore_divider)
        self.source_changed()
        self.url_entry.focus_set()

    def entry(self, parent, row, title, key, browse=None):
        ttk.Label(parent, text=title).grid(row=row, column=0, sticky="w", pady=7)
        entry = ttk.Entry(parent, textvariable=self.variables[key], width=22)
        entry.grid(row=row, column=1, sticky="ew", padx=8, pady=7)
        self.inputs.append(entry)
        if browse:
            button = ttk.Button(parent, text="Browse…", command=lambda: self.browse(key, browse))
            button.grid(row=row, column=2)
            self.inputs.append(button)
        return entry

    def check(self, parent, row, title, key):
        check = ttk.Checkbutton(parent, text=title, variable=self.variables[key])
        check.grid(row=row, column=0, columnspan=3, sticky="w", pady=7)
        self.inputs.append(check)

    def browse(self, key, kind):
        dialog = {"file": filedialog.askopenfilename, "directory": filedialog.askdirectory, "save": filedialog.asksaveasfilename}[kind]
        path = dialog(parent=self, title=key.replace("_", " ").title())
        if path:
            self.variables[key].set(path)

    def source_changed(self):
        file_mode = self.variables["source_mode"].get() == "Text file"
        self.url_entry.state(["disabled" if file_mode else "!disabled"])
        for widget in (self.file_entry, self.file_button):
            widget.state(["!disabled" if file_mode else "disabled"])

    def restore_divider(self, event):
        self.panes.sashpos(0, self.settings.state["divider"])
        self.panes.unbind("<Map>")

    def current_options(self):
        values = {name: variable.get() for name, variable in self.variables.items()}
        values["extra_arguments"] = self.extra.get("1.0", "end-1c")
        return Options(**values)

    def save_state(self):
        self.settings.save_state(self.current_options(), self.winfo_toplevel().geometry(), self.panes.sashpos(0))

    def save_defaults(self):
        self.settings.save_config(self.current_options())
        self.status.set("Saved current options to config.json.")

    def load_defaults(self):
        for name, value in self.settings.defaults.items():
            self.variables[name].set(value)
        self.extra.delete("1.0", "end")
        self.extra.insert("1.0", self.settings.defaults["extra_arguments"])
        self.source_changed()
        self.status.set("Loaded saved defaults.")

    def set_busy(self, busy):
        for widget in self.inputs + [self.start_button]:
            widget.state(["disabled" if busy else "!disabled"])
        self.extra.configure(state="disabled" if busy else "normal")
        self.stop_button.state(["!disabled" if busy else "disabled"])
        if not busy:
            self.source_changed()

    def append_console(self, text):
        self.console.configure(state="normal")
        self.console.insert("end", text)
        # Full output stays in the log file; bound the amount retained by Tk.
        if int(self.console.index("end-1c").split(".")[0]) > 12000:
            self.console.delete("1.0", "2001.0")
        self.console.configure(state="disabled")
        if self.follow.get():
            self.console.see("end")

    def start(self):
        self.options = self.current_options()
        self.urls, self.directory = prepare_run(self.options)
        self.save_state()
        logs = self.settings.directory / "logs"
        logs.mkdir(exist_ok=True)
        self.log_path = logs / (datetime.now().strftime("%Y%m%d-%H%M%S-%f") + ".log")
        self.log_path.write_text(f"Working folder: {self.directory}\n", encoding="utf-8")
        self.log_reader = self.log_path.open("rb")
        self.decoder = codecs.getincrementaldecoder("utf-8")()
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")
        self.save_log.state(["!disabled"])
        self.open_log.state(["!disabled"])
        self.index = 0
        self.stopping = False
        self.progress.configure(maximum=len(self.urls), value=0)
        self.start_next()

    def start_next(self):
        if self.index == len(self.urls):
            self.finish(f"Completed {self.index} of {len(self.urls)} galleries.")
            return
        url = self.urls[self.index]
        command = build_command(self.options, url)
        with self.log_path.open("ab", buffering=0) as output:
            output.write(f"\n[{self.index + 1}/{len(self.urls)}] {subprocess.list2cmdline(command)}\n".encode("utf-8"))
            self.process = subprocess.Popen(
                command, cwd=self.directory, stdin=subprocess.DEVNULL,
                stdout=output, stderr=subprocess.STDOUT,
                env=os.environ | {"PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"},
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        self.status.set(f"{self.index + 1} of {len(self.urls)} — {url}")
        self.set_busy(True)
        self.timer = self.after(100, self.poll)

    def read_log(self):
        text = self.decoder.decode(self.log_reader.read(65536), final=False)
        self.append_console(text.replace("\r\n", "\n").replace("\r", "\n"))

    def poll(self):
        self.timer = None
        self.read_log()
        code = self.process.poll()
        if code is None:
            self.timer = self.after(100, self.poll)
            return
        # Drain remaining output over event-loop ticks, including a final UTF-8 sequence.
        if self.log_reader.tell() < self.log_path.stat().st_size:
            self.timer = self.after(10, self.poll)
            return
        self.append_console(self.decoder.decode(b"", final=True))
        completed = subprocess.CompletedProcess(self.process.args, code)
        self.process = None
        if self.stopping:
            self.finish(f"Stopped. Completed {self.index} of {len(self.urls)} galleries.")
            return
        if code:
            self.finish(f"gallery-dl exited with code {code}. See console. Queue stopped.")
        completed.check_returncode()
        self.index += 1
        self.progress.configure(value=self.index)
        self.decoder = codecs.getincrementaldecoder("utf-8")()
        self.start_next()

    def finish(self, status):
        self.read_log()
        self.log_reader.close()
        self.log_reader = None
        self.set_busy(False)
        self.status.set(status)
        if self.closing:
            self.winfo_toplevel().destroy()

    def stop(self):
        self.stopping = True
        self.stop_button.state(["disabled"])
        self.status.set("Stopping gallery-dl…")
        if self.process.poll() is None:
            self.process.terminate()

    def copy_logs(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_path.read_text(encoding="utf-8") if self.log_path else self.console.get("1.0", "end-1c"))

    def export_logs(self):
        path = filedialog.asksaveasfilename(parent=self, initialfile=self.log_path.name, defaultextension=".log")
        if path:
            shutil.copyfile(self.log_path, path)

    def close(self):
        self.save_state()
        if self.process is not None:
            self.closing = True
            self.stop()
        else:
            self.winfo_toplevel().destroy()


def main():
    settings = Settings()
    root = tk.Tk()
    root.title("EZ Gallery DL")
    root.geometry(settings.state["geometry"])
    root.minsize(1000, 620)
    root.columnconfigure(0, weight=1)
    root.rowconfigure(0, weight=1)
    view = MainView(root, settings)
    view.grid(row=0, column=0, sticky="nsew")
    root.protocol("WM_DELETE_WINDOW", view.close)
    root.mainloop()
