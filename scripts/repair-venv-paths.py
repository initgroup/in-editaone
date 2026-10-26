"""Refresh this Windows venv's activation scripts and installed CLI launchers after a move."""
from importlib.metadata import distributions
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / 'venv'
PREVIOUS_ROOT = ROOT.parent / 'data-editing-system'
if Path(sys.prefix).resolve() != VENV.resolve():
    raise SystemExit('Run this script with this project venv/Scripts/python.exe.')

from pip._vendor.distlib.scripts import ScriptMaker

maker = ScriptMaker(None, str(VENV / 'Scripts'))
maker.executable = str(VENV / 'Scripts/python.exe')
maker.clobber = True
maker.variants = {''}
count = 0
for distribution in distributions():
    for entry in distribution.entry_points:
        if entry.group not in {'console_scripts', 'gui_scripts'}:
            continue
        maker.make(f'{entry.name} = {entry.value}', options={'gui': entry.group == 'gui_scripts'})
        count += 1

# pip registers pip/pip3 entry points, but its versioned installer launcher may
# not be listed in package metadata. Refresh it explicitly after relocation.
versioned_pip = f'pip{sys.version_info.major}.{sys.version_info.minor}'
maker.make(f'{versioned_pip} = pip._internal.cli.main:main')
count += 1

for name in ('activate', 'activate.bat', 'Activate.ps1'):
    path = VENV / 'Scripts' / name
    if path.is_file():
        data = path.read_bytes()
        # These generated files may contain the original absolute directory.
        data = data.replace(str(PREVIOUS_ROOT).encode('utf-8'), str(ROOT).encode('utf-8'))
        data = data.replace(PREVIOUS_ROOT.as_posix().encode('utf-8'), ROOT.as_posix().encode('utf-8'))
        data = data.replace(b'data-editing-system', b'in-editaone')
        path.write_bytes(data)
config = VENV / 'pyvenv.cfg'
if config.is_file():
    data = config.read_bytes().replace(str(PREVIOUS_ROOT).encode('utf-8'), str(ROOT).encode('utf-8'))
    config.write_bytes(data)
print(f'Regenerated {count} installed launchers for {ROOT}. No packages were installed or removed.')
