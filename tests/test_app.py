import base64
import functools
import subprocess
import tempfile
import threading
import time
import tkinter as tk
import unittest
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.config import Options, Settings
from app.main import MainView
from app.runner import build_command, prepare_run


class RunnerTests(unittest.TestCase):
    def test_text_input_preserves_order_duplicates_and_uses_parent(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "galleries ü.txt"
            source.write_text("\ufeff  https://one.test/a  \n\n \t\nhttps://two.test/b\nhttps://one.test/a\n", encoding="utf-8")
            urls, directory = prepare_run(Options(source_mode="Text file", input_file=str(source)))
            self.assertEqual(urls, ["https://one.test/a", "https://two.test/b", "https://one.test/a"])
            self.assertEqual(directory, source.parent)

    def test_literal_arguments_and_directory_override(self):
        with tempfile.TemporaryDirectory() as folder:
            options = Options(url=" https://example.test/a?x=1&y=2 ", working_directory=folder,
                              executable=r"C:\Tools With Spaces\gallery-dl.exe", destination=folder,
                              exact_directory=True, extra_arguments='--filter\nimage_width >= 1000\n--option\nextractor.directory=["a b"]')
            urls, directory = prepare_run(options)
            command = build_command(options, urls[0])
            self.assertEqual(directory, Path(folder))
            self.assertEqual(command[0], options.executable)
            self.assertEqual(command[-2:], ["--", urls[0]])
            self.assertIn("--directory", command)
            self.assertIn("image_width >= 1000", command)
            self.assertIn('extractor.directory=["a b"]', command)

    def test_config_and_session_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            settings = Settings(Path(folder))
            settings.save_config(Options(limit_rate="2M"))
            settings.save_state(Options(limit_rate="5M", url="https://example.test"), "1000x700", 480)
            restored = Settings(Path(folder))
            self.assertEqual(restored.defaults["limit_rate"], "2M")
            self.assertEqual(restored.values.limit_rate, "5M")
            self.assertEqual(restored.state["divider"], 480)


class AppIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.image = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDWQAAAAASUVORK5CYII=")
        (cls.folder / "sample.png").write_bytes(cls.image)
        handler = functools.partial(SimpleHTTPRequestHandler, directory=str(cls.folder))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/sample.png"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def setUp(self):
        self.root = tk.Tk()
        self.root.geometry("1180x780")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.settings = Settings(self.folder / self._testMethodName)
        self.view = MainView(self.root, self.settings)
        self.view.grid(row=0, column=0, sticky="nsew")
        self.root.update()
        self.view.variables["url"].set(self.url)
        self.view.variables["working_directory"].set(str(self.folder))
        self.view.variables["destination"].set(str(self.settings.directory / "downloads"))
        self.view.variables["filename"].set("{filename}.{extension}")
        self.view.variables["exact_directory"].set(True)
        self.view.extra.insert("1.0", "--config-ignore\n")

    def tearDown(self):
        self.root.destroy()

    def wait_for_run(self):
        deadline = time.monotonic() + 15
        while self.view.process is not None and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertIsNone(self.view.process)

    def test_real_download_and_repeat_batch(self):
        self.view.start_button.invoke()
        self.assertTrue(self.view.start_button.instate(["disabled"]))
        self.wait_for_run()
        self.assertEqual((self.settings.directory / "downloads" / "sample.png").read_bytes(), self.image)
        self.assertEqual(self.view.progress["value"], 1)
        source = self.folder / "batch.txt"
        source.write_text(f"\ufeff {self.url} \n\n{self.url}\n", encoding="utf-8")
        self.view.variables["source_mode"].set("Text file")
        self.view.variables["input_file"].set(str(source))
        self.view.variables["working_directory"].set("")
        self.view.source_changed()
        self.assertTrue(self.view.url_entry.instate(["disabled"]))
        self.view.start_button.invoke()
        self.wait_for_run()
        self.assertEqual(self.view.progress["value"], 2)
        self.assertEqual(self.view.directory, self.folder)
        self.assertIn("[2/2]", self.view.log_path.read_text(encoding="utf-8"))
        self.view.copy_logs()
        self.assertIn("[2/2]", self.root.clipboard_get())
        self.view.save_defaults()
        self.view.save_state()
        self.assertEqual(Settings(self.settings.directory).values.input_file, str(source))

    def test_resize_tabs_focus_and_cancel(self):
        for geometry in ("1000x620", "1400x900"):
            self.root.geometry(geometry)
            self.root.update()
            self.assertGreater(self.view.console.winfo_width(), 300)
            self.assertGreater(self.view.console.winfo_height(), 250)
        notebook = self.view.nametowidget(self.view.panes.panes()[0])
        for tab in notebook.tabs():
            notebook.select(tab)
            self.root.update()
        notebook.select(0)
        self.root.update()
        self.view.url_entry.focus_force()
        self.view.url_entry.event_generate("<Tab>")
        self.root.update()
        self.assertIsNotNone(self.root.focus_get())
        self.view.variables["sleep"].set("20")
        self.view.start_button.invoke()
        self.view.stop_button.invoke()
        self.wait_for_run()
        self.assertTrue(self.view.status.get().startswith("Stopped."))
        self.assertTrue(self.view.start_button.instate(["!disabled"]))
        self.assertEqual(self.view.progress["value"], 0)

    def test_nonzero_exit_surfaces_and_stops_batch(self):
        source = self.folder / "failure.txt"
        source.write_text(f"unsupported://example\n{self.url}\n", encoding="utf-8")
        self.view.variables["source_mode"].set("Text file")
        self.view.variables["input_file"].set(str(source))
        self.view.start()
        self.view.after_cancel(self.view.timer)
        self.view.process.wait(timeout=15)
        with self.assertRaises(subprocess.CalledProcessError):
            self.view.poll()
        self.assertIsNone(self.view.process)
        self.assertIn("Queue stopped", self.view.status.get())
        self.assertNotIn("[2/2]", self.view.log_path.read_text(encoding="utf-8"))
        self.assertFalse((self.settings.directory / "downloads").exists())

    def test_empty_file_completes_without_process(self):
        source = self.folder / "empty.txt"
        source.write_text("\n \n", encoding="utf-8")
        self.view.variables["source_mode"].set("Text file")
        self.view.variables["input_file"].set(str(source))
        self.view.start()
        self.assertEqual(self.view.status.get(), "Completed 0 of 0 galleries.")
        self.assertIsNone(self.view.process)


if __name__ == "__main__":
    unittest.main()
