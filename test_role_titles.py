"""No StarCraft game process is created or mutated.

Test the role-caption formatter and Windows label behavior on an isolated mock HWND.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes as wt
from pathlib import Path
from tempfile import TemporaryDirectory
import json
from arena_window_control import game_caption, role_text, label_session_windows, u32
role={"P1":"V2","P2":"CoG"}
assert "P1" in role_text(1,role) and "Pluto 2.0" in role_text(1,role)
assert "P2" in role_text(2,role) and "CoG" in role_text(2,role)
assert "P3" in role_text(3,role) and "AI 없음" in role_text(3,role)
assert "Human" in role_text(1,{"P1":"Human","P2":"V2"})
assert "StarCraft" in game_caption(3,role)
print("PASS: P1, P2, P3 roles are distinct and controller-specific",flush=True)
create = u32.CreateWindowExW
create.argtypes = [wt.DWORD,wt.LPCWSTR,wt.LPCWSTR,wt.DWORD,
                  ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,
                  wt.HWND,wt.HMENU,wt.HINSTANCE,ctypes.c_void_p]
create.restype=wt.HWND
destroy=u32.DestroyWindow
destroy.argtypes=[wt.HWND]
destroy.restype=wt.BOOL
hwnd=create(0,"STATIC","Brood War",0x00CF0000,50,50,300,120,None,None,None,None)
assert hwnd
try:
    with TemporaryDirectory() as temp:
        path=Path(temp)
        (path/"session-match.json").write_text(json.dumps(role),encoding="utf-8")
        rows=[{"slot":1,"active":True,"window":True,"hwnd":int(hwnd),"title":"Brood War"}]
        labels=label_session_windows(path,rows)
        assert len(labels)==1 and "P1" in labels[0]
        buffer=ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(hwnd,buffer,len(buffer))
        assert buffer.value==game_caption(1,role), buffer.value
        assert label_session_windows(path,[{**rows[0],"title":buffer.value}])==[]
        print("PASS: native Win32 title updated; identical title unchanged",flush=True)
finally:
    destroy(hwnd)
