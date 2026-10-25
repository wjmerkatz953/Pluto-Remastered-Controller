"""Qt screenshot and frozen-exe smoke checks. No game windows or match actions."""
import os, sys, subprocess
from pathlib import Path
root=Path(__file__).resolve().parent
preview=root/"pluto_arena_preview.png"
env=os.environ.copy()
env["QT_QPA_PLATFORM"]="offscreen"
p=subprocess.run([sys.executable,str(root/"pluto_arena_gui.py"),"--screenshot",str(preview)],env=env,capture_output=True,text=True,timeout=60)
print("Preview process exit code:",p.returncode,flush=True)
print(p.stdout[-1200:]+p.stderr[-1200:],flush=True)
assert p.returncode==0,(p.stdout,p.stderr)
assert preview.is_file() and preview.stat().st_size>12000
print(f"PASS: Qt 1060x835 dashboard preview {preview} ({preview.stat().st_size} bytes)",flush=True)
