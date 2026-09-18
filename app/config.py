"""Separate saved defaults from the last session, without third-party packages."""

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


CONFIG_DIR = Path(os.environ["LOCALAPPDATA"]) / "EZ-Gallery-DL"


@dataclass
class Options:
    source_mode: str = "URL"
    url: str = ""
    input_file: str = ""
    working_directory: str = ""
    executable: str = ""
    destination: str = ""
    exact_directory: bool = False
    gallery_config: str = ""
    cookies: str = ""
    browser: str = ""
    archive: str = ""
    filename: str = ""
    limit_rate: str = ""
    sleep: str = ""
    file_range: str = ""
    simulate: bool = False
    verbose: bool = False
    metadata: bool = False
    tags: bool = False
    extra_arguments: str = ""


class Settings:
    def __init__(self, directory=CONFIG_DIR):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.config_path = directory / "config.json"
        self.state_path = directory / "state.json"
        if not self.config_path.exists():
            self.save_config(Options())
        if not self.state_path.exists():
            self.save_state(Options(), "1180x780", 470)
        self.defaults = json.loads(self.config_path.read_text(encoding="utf-8"))
        self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.values = Options(**(self.defaults | self.state["options"]))

    def save_config(self, options):
        self.defaults = asdict(options)
        self.config_path.write_text(json.dumps(self.defaults, indent=2), encoding="utf-8")

    def save_state(self, options, geometry, divider):
        self.state_path.write_text(json.dumps({
            "options": asdict(options), "geometry": geometry, "divider": divider,
        }, indent=2), encoding="utf-8")
