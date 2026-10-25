"""Native cross-process title test with an isolated dummy Win32 window.

Does not interact with any game client.
"""
import ctypes
from ctypes import wintypes as wt
import json
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from arena_window_control import u32, label_session_windows, game_caption

if "--child" in sys.argv:
    create=u32.CreateWindowExW
    create.argtypes=[wt.DWORD,wt.LPCWSTR,wt.LPCWSTR,wt.DWORD,
                  ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,
                  wt.HWND,wt.HMENU,wt.HINSTANCE,ctypes.c_void_p]
    create.restype=wt.HWND
    hwnd=create(0,"STATIC","Brood War",0x00CF0000,120,120,340,150,None,None,None,None)
    assert hwnd
    u32.ShowWindow.argtypes=[wt.HWND,ctypes.c_int]
    u32.ShowWindow(hwnd, 5)
    print(int(hwnd),flush=True)
    class MSG(ctypes.Structure):
        _fields_=[("hwnd",wt.HWND),("message",wt.UINT),("wParam",wt.WPARAM),("lParam",wt.LPARAM),
                 ("time",wt.DWORD),("pt",wt.POINT)]
    msg=MSG()
    u32.GetMessageW.argtypes=[ctypes.POINTER(MSG),wt.HWND,wt.UINT,wt.UINT]
    while u32.GetMessageW(ctypes.byref(msg),None,0,0)>0:
        u32.TranslateMessage(ctypes.byref(msg))
        u32.DispatchMessageW(ctypes.byref(msg))
    sys.exit(0)

with TemporaryDirectory() as tmp:
    root=Path(tmp)
    session={"P1":"V2","P2":"CoG"}
    (root/"session-match.json").write_text(json.dumps(session),encoding="utf-8")
    process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),"--child"],
                             text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        hwnd=int(process.stdout.readline().strip())
        line={"slot":1,"active":True,"window":True,"hwnd":hwnd,"title":"Brood War"}
        changed=label_session_windows(root,[line])
        assert changed==[game_caption(1,session)],changed
        buff=ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(wt.HWND(hwnd),buff,len(buff))
        assert buff.value==game_caption(1,session),repr(buff.value)
        print("PASS: renamed a separate Windows process window to P1 / Pluto 2.0",flush=True)
    finally:
        process.terminate()
        process.wait(timeout=4)
