"""Frozen Qt GUI smoke test. Doesn't launch any StarCraft process."""
import os, subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
exe=root/"dist"/"PlutoRemasteredController-v0.1.0.exe"
assert exe.is_file()
env=os.environ.copy()
env["QT_QPA_PLATFORM"]="offscreen"
p=subprocess.run([str(exe),"--self-test"],env=env,cwd=root,timeout=100,capture_output=True)
print("Frozen exit:",p.returncode,flush=True)
print("Executable bytes:",exe.stat().st_size,flush=True)
assert p.returncode==0,(p.stderr[-2000:],p.stdout[-2000:])
print("PASS: frozen onefile GUI starts and initializes all controls, then exits cleanly",flush=True)
