from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

root = Path(SPECPATH).parent
gui = Analysis([str(root / 'scripts/gui-entry.py')], pathex=[str(root)])
gui_pyz = PYZ(gui.pure)
gui_exe = EXE(gui_pyz, gui.scripts, [], exclude_binaries=True,
              name='EZ-Gallery-DL', console=False)

# gallery-dl discovers site extractors, downloaders, and postprocessors by name.
cli = Analysis(
    [str(root / 'scripts/gallery-entry.py')], pathex=[str(root)],
    hiddenimports=(collect_submodules('gallery_dl.extractor')
                   + collect_submodules('gallery_dl.downloader')
                   + collect_submodules('gallery_dl.postprocessor')),
    datas=copy_metadata('gallery-dl'),
)
cli_pyz = PYZ(cli.pure)
cli_exe = EXE(cli_pyz, cli.scripts, [], exclude_binaries=True,
              name='gallery-dl', console=True)
COLLECT(gui_exe, cli_exe, gui.binaries, gui.datas, cli.binaries, cli.datas,
        name='EZ-Gallery-DL')
