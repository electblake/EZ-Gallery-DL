"""Retain dependency notices and the exact gallery-dl source distribution."""

import hashlib
import importlib.metadata
import json
import shutil
import sys
import urllib.request
from pathlib import Path

target = Path("dist/EZ-Gallery-DL/licenses")
target.mkdir(parents=True, exist_ok=True)
shutil.copyfile("LICENSE", target.parent / "LICENSE")
for name in ("gallery-dl", "requests", "certifi", "charset-normalizer", "idna", "urllib3", "pyinstaller"):
    distribution = importlib.metadata.distribution(name)
    for file in distribution.files:
        if "license" in str(file).lower() or "copying" in str(file).lower():
            destination = target / name / file
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(distribution.locate_file(file), destination)
shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", target / "Python-LICENSE.txt")
shutil.copyfile(Path(sys.base_prefix) / "tcl/tk8.6/license.terms", target / "Tcl-Tk-license.terms")
version = importlib.metadata.version("gallery-dl")
with urllib.request.urlopen(f"https://pypi.org/pypi/gallery-dl/{version}/json") as response:
    metadata = json.load(response)
source = next(file for file in metadata["urls"] if file["packagetype"] == "sdist")
with urllib.request.urlopen(source["url"]) as response:
    content = response.read()
assert hashlib.sha256(content).hexdigest() == source["digests"]["sha256"]
(target / source["filename"]).write_bytes(content)
