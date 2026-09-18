"""Resolve input and construct argument lists; never invoke a shell."""

import sys
from pathlib import Path

from app.config import Options


def prepare_run(options: Options):
    if options.source_mode == "Text file":
        source = Path(options.input_file).expanduser().resolve(strict=True)
        urls = [line.strip() for line in source.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        directory = source.parent
    else:
        urls = [options.url.strip()]
        directory = Path.home() / "Downloads"
    if options.working_directory:
        directory = Path(options.working_directory).expanduser().resolve(strict=True)
    return urls, directory


def build_command(options: Options, url: str):
    if options.executable:
        command = [options.executable]
    elif getattr(sys, "frozen", False):
        command = [str(Path(sys.executable).parent / "gallery-dl.exe")]
    else:
        command = [sys.executable, "-u", "-m", "gallery_dl"]
    command += ["--no-input", "--no-colors"]
    for flag, value in (
        ("--directory" if options.exact_directory else "--destination", options.destination),
        ("--config", options.gallery_config),
        ("--cookies", options.cookies),
        ("--cookies-from-browser", options.browser),
        ("--download-archive", options.archive),
        ("--filename", options.filename),
        ("--limit-rate", options.limit_rate),
        ("--sleep", options.sleep),
        ("--range", options.file_range),
    ):
        if value:
            command += [flag, value]
    for flag, enabled in (
        ("--simulate", options.simulate), ("--verbose", options.verbose),
        ("--write-metadata", options.metadata), ("--write-tags", options.tags),
    ):
        if enabled:
            command.append(flag)
    command += [line for line in options.extra_arguments.splitlines() if line.strip()]
    return command + ["--", url]
