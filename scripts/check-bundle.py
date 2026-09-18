"""Exercise the relocated frozen CLI without Python or gallery-dl on PATH."""

import base64
import ctypes
import functools
import os
import shutil
import subprocess
import tempfile
import threading
import time
from ctypes import wintypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    bundle = root / "portable app"
    shutil.copytree("dist/EZ-Gallery-DL", bundle)
    image = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aDWQAAAAASUVORK5CYII=")
    (root / "sample.png").write_bytes(image)
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(SimpleHTTPRequestHandler, directory=str(root)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    environment = os.environ | {"PATH": str(Path(os.environ["SystemRoot"]) / "System32"), "PYTHONPATH": "", "PYTHONHOME": ""}
    executable = str(bundle / "gallery-dl.exe")
    subprocess.run([executable, "--version"], cwd=root, env=environment, check=True)
    subprocess.run([executable, "--config-ignore", "--no-input", "--directory", str(root / "downloads"),
                    "--filename", "{filename}.{extension}",
                    f"http://127.0.0.1:{server.server_port}/sample.png"],
                   cwd=root, env=environment, check=True)
    assert (root / "downloads/sample.png").read_bytes() == image
    failure = subprocess.run([executable, "--config-ignore", "unsupported://example"], cwd=root, env=environment)
    assert failure.returncode != 0
    gui = subprocess.Popen([str(bundle / "EZ-Gallery-DL.exe")], cwd=root,
                           env=environment | {"LOCALAPPDATA": str(root / "settings")})
    windows = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def find_window(window, parameter):
        owner = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(window, ctypes.byref(owner))
        title = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetWindowTextW(window, title, 256)
        if owner.value == gui.pid and title.value == "EZ Gallery DL":
            windows.append(window)
        return True

    deadline = time.monotonic() + 15
    while not windows and time.monotonic() < deadline:
        assert gui.poll() is None
        ctypes.windll.user32.EnumWindows(find_window, 0)
        time.sleep(0.1)
    assert windows
    ctypes.windll.user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    ctypes.windll.user32.PostMessageW(windows[0], 0x0010, 0, 0)
    assert gui.wait(timeout=15) == 0
    server.shutdown()
    server.server_close()
    thread.join()
print("Relocated bundle: GUI launch/close, download, and failure exit verified.")
