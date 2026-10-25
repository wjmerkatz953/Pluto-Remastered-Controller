"""Safe CLI smoke tests only. Never launch StarCraft processes."""
from pathlib import Path
import subprocess, sys
folder=Path(__file__).resolve().parent
script=folder/"Start-Pluto-Match.ps1"
tests=[
    ("help",["-List"],0,"Supported slots:"),
    ("human-v2",["-P1","Human","-P2","V2","-VerifyOnly"],0,"PASS: exact SHA-256"),
    ("human-cog",["-P1","Human","-P2","CoG","-VerifyOnly"],0,"PASS: exact SHA-256"),
    ("cog-v2",["-P1","CoG","-P2","V2","-VerifyOnly"],0,"PASS: exact SHA-256"),
    ("v2-mirror",["-P1","V2","-P2","V2","-VerifyOnly"],0,"PASS: exact SHA-256"),
    ("v2-mirror-observer",["-P1","V2","-P2","V2","-Observer","-VerifyOnly"],0,"Observer=True; Language=Default"),
    ("v2-mirror-english",["-P1","V2","-P2","V2","-Observer","-Language","English","-VerifyOnly"],0,"Observer=True; Language=English"),
    ("bad-name",["-P1","Unknown","-P2","V2","-VerifyOnly"],1,"ValidateSet"),
]
for name,options,expected,needle in tests:
    proc=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(script),*options],capture_output=True,text=True,timeout=100)
    output=proc.stdout+"\n"+proc.stderr
    print(name,"exit="+str(proc.returncode)," ".join(proc.stdout.strip().splitlines()),flush=True)
    if expected==0:
        assert proc.returncode==0 and needle in output,(name,output)
    else:
        assert proc.returncode!=0,(name,output)
print("PASS: all model selection validation tests passed; no game was launched")
