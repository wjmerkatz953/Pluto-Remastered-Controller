"""Compile Pluto Arena Qt-only EXE; NEVER bundle StarCraft or Pluto binaries."""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path
root=Path(__file__).resolve().parent
spec=root/"build-gui"/"spec"
dist=root/"dist"
work=root/"build-gui"/"work"
for d in (spec,dist,work):
    d.mkdir(parents=True,exist_ok=True)
args=[
    sys.executable,"-m","PyInstaller",
    "--noconfirm","--clean","--onefile","--windowed",
    "--name","PlutoRemasteredController-v0.1.0",
    "--icon",str(root/"pluto_arena.ico"),
    "--add-data",str(root/"pluto_arena.ico")+";.",
    "--distpath",str(dist),
    "--workpath",str(work),
    "--specpath",str(spec),
    "--exclude-module","tkinter",
    "--exclude-module","PyQt6",
    "--exclude-module","matplotlib",
    "--exclude-module","numpy",
    str(root/"pluto_arena_gui.py"),
]
print("Packaging Qt GUI only, game/model assets excluded",flush=True)
result=subprocess.run(args, cwd=str(root), timeout=360, capture_output=True,text=True,errors="replace")
print((result.stdout+"\n"+result.stderr)[-9000:],flush=True)
exe=dist/"PlutoRemasteredController-v0.1.0.exe"
assert result.returncode==0,f"PyInstaller returned {result.returncode}"
assert exe.is_file() and exe.stat().st_size>1_000_000,"Executable is missing/empty"
print(f"PASS: built {exe} ({exe.stat().st_size:,} bytes)",flush=True)
